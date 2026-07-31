"""
Router — lớp phân loại NHANH (keyword/regex), chạy TRƯỚC khi gọi LLM.

Vì sao không giao hết cho LLM tự phân loại:
- Ngoài phạm vi (③) cần bị chặn CHẮC CHẮN, không phụ thuộc LLM có tuân lệnh
  hệ thống hay không mỗi lần gọi — khớp nguyên tắc G1 (spec.md §4b) và
  R2 rubric ("automation chọn rõ + lý do theo cost-of-error").
- Rẻ & nhanh: 90% câu hỏi tiện ích/gom nhóm rõ ràng không cần LLM để định tuyến.
- Dễ audit: mỗi nhánh trỏ thẳng vào một dòng code cụ thể (đúng yêu cầu R2 —
  mỗi nguyên tắc HAX phải chỉ được vào chỗ cụ thể trong prototype).

Việc CÒN LẠI (trả lời có căn cứ, trích xuất chi tiết trận đấu) mới cần LLM
thật — xem llm_handler.py.
"""
import re
import unicodedata
from datetime import datetime, timedelta

# ============================================================
# ③ NGOÀI PHẠM VI — 4 nhóm riêng vì câu trả lời kỳ vọng khác nhau
#   (xem eval/golden_set.json test_03, 07, 14, 18)
# ============================================================
OOS_ACADEMIC = [
    "giải bài", "giải giúp bài", "bài tập", "làm hộ", "làm giúp bài",
    "code giúp", "viết code giúp", "fix code", "debug giúp",
    "viết báo cáo giúp", "làm đồ án", "giải thích thuật toán", "chấm bài",
]
OOS_INTEGRITY = [
    "đáp án", "đáp án quiz", "đáp án bài quiz", "đáp án bài kiểm tra", "đáp án đề thi",
]
OOS_ADMIN = [
    "ban tài khoản", "ban nick", "kick", "xoá tài khoản", "xóa tài khoản",
    "khoá tài khoản", "khóa tài khoản", "xoá quyền", "xóa quyền",
    "đuổi khỏi server", "xoá server", "xóa server", "cấm bạn",
]
OOS_SPAM = [
    "spam", "phá kênh", "flood tin nhắn", "đăng liên tục", "nhắn liên tục", "gửi liên tục",
]

OOS_REPLIES = {
    "academic": "Mình chỉ hỗ trợ tra cứu tiện ích campus và lập nhóm thể thao thôi 🙏 — mình không giải bài tập được, bạn nhắn Mentor hoặc TA giúp mình nhé.",
    "integrity": "Mình không thể cung cấp đáp án bài kiểm tra/quiz — việc này vi phạm quy định liêm chính học thuật của chương trình. Bạn ôn lại bài hoặc hỏi Mentor/TA nếu cần hỗ trợ nhé.",
    "admin": "Mình không có quyền thực hiện thao tác với tài khoản người khác (kick/ban/xoá quyền...). Bạn cần hỗ trợ về thành viên thì liên hệ Quản trị viên (Admin/Mod) hoặc Phòng CTSV giúp mình.",
    "spam": "Mình từ chối yêu cầu gửi tin nhắn hàng loạt/spam — việc này vi phạm quy định cộng đồng của kênh Discord. Bạn cần thông báo gì thì mình hỗ trợ gửi một lần gọn gàng nhé.",
}


def _norm(s: str) -> str:
    return s.lower().strip()


def check_out_of_scope(text: str):
    """Trả về (True, category, reply) nếu bị chặn; ngược lại (False, None, None)."""
    s = _norm(text)
    for kw in OOS_INTEGRITY:
        if kw in s:
            return True, "integrity", OOS_REPLIES["integrity"]
    for kw in OOS_ADMIN:
        if kw in s:
            return True, "admin", OOS_REPLIES["admin"]
    for kw in OOS_SPAM:
        if kw in s:
            return True, "spam", OOS_REPLIES["spam"]
    for kw in OOS_ACADEMIC:
        if kw in s:
            return True, "academic", OOS_REPLIES["academic"]
    return False, None, None


# ============================================================
# ② / ④ THỂ THAO — phát hiện ý định + độ mơ hồ trước khi gọi Tool Calling
# ============================================================
SPORT_WORDS = [
    "đá bóng", "bóng đá", "đá banh", "cầu lông", "bóng rổ", "chạy bộ",
    "giao lưu", "lập nhóm", "rủ", "team", "thể thao", "kèo", "trận",
]


def is_sport_intent(text: str) -> bool:
    s = _norm(text)
    return any(w in s for w in SPORT_WORDS)


_HOUR_RE = re.compile(r"(\d{1,2})\s*[:h]\s*(\d{0,2})|(\d{1,2})\s*giờ")

PERIOD_WORDS = ["sáng", "chiều", "tối", "đêm"]


def _canonical_period(hour: int) -> str:
    if 5 <= hour <= 10:
        return "sáng"
    if 11 <= hour <= 17:
        return "chiều"
    if 18 <= hour <= 21:
        return "tối"
    return "đêm"  # 22-23, 0-4


def extract_hour(text: str):
    """Trả về giờ (int 0-23) nếu tìm thấy mốc giờ tường minh trong câu, else None."""
    h, _ = extract_hour_minute(text)
    return h


def extract_hour_minute(text: str):
    """
    Trả về (giờ, phút) nếu tìm thấy mốc giờ tường minh trong câu, else
    (None, None). Khác extract_hour() ở chỗ KHÔNG bỏ qua phút — "12h43" phải
    ra (12, 43) chứ không phải (12, 0), nếu không các phép tính khoảng cách
    thời gian chính xác (vd khoá rời trận trước giờ bắt đầu) sẽ sai lệch.
    """
    m = _HOUR_RE.search(text)
    if not m:
        return None, None
    raw_h = m.group(1) or m.group(3)
    raw_m = m.group(2) if m.group(1) else None
    try:
        h = int(raw_h)
    except (TypeError, ValueError):
        return None, None
    if not (0 <= h <= 23):
        return None, None
    minute = 0
    if raw_m:
        try:
            minute = int(raw_m)
        except ValueError:
            minute = 0
        if not (0 <= minute <= 59):
            minute = 0
    return h, minute


def find_period_word(text: str):
    s = _norm(text)
    for w in PERIOD_WORDS:
        if w in s:
            return w
    return None


def check_sport_ambiguity(text: str):
    """
    Kiểm tra 1 câu rủ/tạo trận có đủ rõ để tạo trận thẳng không.
    Trả về None nếu đủ rõ (giao cho LLM Tool Calling xử lý).
    Trả về dict {"kind": "missing"|"conflict", "message": "..."} nếu cần hỏi lại
    TRƯỚC khi gọi LLM — khớp G10 (spec.md §4b) và test_05/12/15 trong golden_set.
    """
    hour = extract_hour(text)
    period = find_period_word(text)

    # ④ đặc thù: có giờ tường minh NHƯNG mâu thuẫn với buổi trong ngày
    # vd "15h đêm nay" — test_12
    if hour is not None and period is not None:
        canon = _canonical_period(hour)
        if canon != period:
            return {
                "kind": "conflict",
                "message": (
                    f"Mình thấy {hour}h thường là **{hour}h {canon}**, "
                    f"không phải buổi \"{period}\" — bạn xác nhận lại giúp mình đúng giờ nào để lên lịch chính xác nhé?"
                ),
            }
        return None  # rõ ràng, không mâu thuẫn -> cho qua LLM

    if hour is not None:
        return None  # có giờ tường minh, đủ rõ

    # ② mơ hồ: câu quá ngắn/chung chung, không rõ ý định làm gì với thể thao
    stripped = _norm(text).rstrip("?!. ")
    if len(stripped) <= 10:
        return {
            "kind": "too_short",
            "message": "Bạn muốn **tìm trận đang mở** để ghép vào, hay muốn **tạo kèo mới**? Nói rõ giúp mình môn + giờ + sân nhé.",
        }

    # ② mơ hồ: có buổi trong ngày (chiều/sáng/tối) nhưng thiếu giờ + sân cụ thể
    if period is not None:
        return {
            "kind": "missing_hour",
            "message": f"Bạn muốn đá vào **mấy giờ** buổi {period} và ở **sân nào** để mình lên lịch giúp — xác nhận giúp mình nhé?",
        }

    # ② mơ hồ: không có giờ, không có buổi -> hỏi đủ cả 3 trường
    return {
        "kind": "missing_all",
        "message": "Bạn muốn đá **ngày nào, giờ nào**, và ở **sân nào** để mình lên lịch giúp — xác nhận giúp mình nhé?",
    }


# ============================================================
# GIẢI MÃ NGÀY/GIỜ TỰ DO → datetime thật
# Dùng để tính "còn bao lâu nữa trận bắt đầu" (khoá rời trận 1 tiếng trước
# giờ, xem match_manager.leave_match) — đoán tốt nhất có thể từ chuỗi tự do
# người tạo trận đã gõ, KHÔNG phải lịch thật nên có giới hạn khi câu quá mơ hồ.
# ============================================================
_WEEKDAY_MAP = {
    "chủ nhật": 6, "cn": 6,
    "thứ 2": 0, "thứ hai": 0,
    "thứ 3": 1, "thứ ba": 1,
    "thứ 4": 2, "thứ tư": 2,
    "thứ 5": 3, "thứ năm": 3,
    "thứ 6": 4, "thứ sáu": 4,
    "thứ 7": 5, "thứ bảy": 5,
}


def resolve_match_date(text: str, now: datetime = None) -> "datetime.date":
    """Đoán NGÀY (không phải giờ) từ chuỗi tự do — mặc định hôm nay nếu
    không thấy từ khoá ngày nào (đa số trận ghi giờ trong ngày, không ghi
    ngày rõ vì ngầm hiểu là hôm nay)."""
    now = now or datetime.now()
    s = _norm(text)
    if re.search(r"\bmai\b", s):
        return (now + timedelta(days=1)).date()
    for label, weekday in _WEEKDAY_MAP.items():
        if label in s:
            days_ahead = (weekday - now.weekday()) % 7
            days_ahead = days_ahead or 7  # nếu trùng thứ hôm nay, hiểu là tuần sau
            return (now + timedelta(days=days_ahead)).date()
    return now.date()


def resolve_match_datetime(time_text: str, now: datetime = None):
    """
    Ghép ngày (resolve_match_date) + giờ (extract_hour) từ chuỗi thời gian
    tự do của 1 trận đấu (vd "17h", "5h chiều nay", "mai 9h") thành 1
    datetime thật. Trả về None nếu không đoán được giờ tường minh (không đủ
    cơ sở để tính, không suy diễn bừa).
    """
    hour, minute = extract_hour_minute(time_text)
    if hour is None:
        return None
    now = now or datetime.now()
    date_part = resolve_match_date(time_text, now=now)
    return datetime.combine(date_part, datetime.min.time()).replace(hour=hour, minute=minute)


def classify(text: str) -> dict:
    """Điểm vào chính cho server.py. Không gọi LLM ở đây."""
    is_oos, category, reply = check_out_of_scope(text)
    if is_oos:
        return {"route": "out_of_scope", "category": category, "reply": reply}

    if is_sport_intent(text):
        ambiguity = check_sport_ambiguity(text)
        if ambiguity:
            return {"route": "sport_clarify", **ambiguity}
        return {"route": "sport"}

    return {"route": "qna"}
