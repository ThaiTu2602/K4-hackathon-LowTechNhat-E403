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
    m = _HOUR_RE.search(text)
    if not m:
        return None
    raw = m.group(1) or m.group(3)
    try:
        h = int(raw)
    except (TypeError, ValueError):
        return None
    return h if 0 <= h <= 23 else None


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
                    f"Mình thấy {hour}h thường là <b>{hour}h {canon}</b>, "
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
            "message": "Bạn muốn <b>tìm trận đang mở</b> để ghép vào, hay muốn <b>tạo kèo mới</b>? Nói rõ giúp mình môn + giờ + sân nhé.",
        }

    # ② mơ hồ: có buổi trong ngày (chiều/sáng/tối) nhưng thiếu giờ + sân cụ thể
    if period is not None:
        return {
            "kind": "missing_hour",
            "message": f"Bạn muốn đá vào <b>mấy giờ</b> buổi {period} và ở <b>sân nào</b> để mình lên lịch giúp — xác nhận giúp mình nhé?",
        }

    # ② mơ hồ: không có giờ, không có buổi -> hỏi đủ cả 3 trường
    return {
        "kind": "missing_all",
        "message": "Bạn muốn đá <b>ngày nào, giờ nào</b>, và ở <b>sân nào</b> để mình lên lịch giúp — xác nhận giúp mình nhé?",
    }


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
