# ============================================================
# FILE: tools.py
# MỤC ĐÍCH: Tập trung TẤT CẢ cấu hình + "tools" (công cụ) mà AI Agent
#            (Gemini) được phép gọi vào một nơi duy nhất.
# ============================================================
from datetime import datetime
from pathlib import Path

from router import extract_hour  # dùng lại logic đoán giờ tường minh trong câu

BASE_DIR = Path(__file__).resolve().parent.parent

# ---- Danh sách Intent hợp lệ (dùng bởi classify_intent() — luồng cũ) ----
VALID_INTENTS = ["qna", "create_match", "list_matches", "join_match", "other"]


# ---- Sức chứa TỐI ĐA (đủ người là hết chỗ, không ai join thêm được) ----
# Dùng trong MatchManager ở match_manager.py
DEFAULT_SLOTS = {
    "bóng đá": 14,
    "cầu lông": 4,
    "bóng rổ": 6,
}

# ---- Sức chứa TỐI THIỂU (đủ để "mở được trận" — chưa cần đầy tới max) ----
# Ví dụ bóng đá: đủ 10 người là đã đá được (2 đội 5v5), dù max cho phép tới
# 14 (có người dự bị/xoay tua). Môn nào không khai báo riêng thì coi
# min = max (phải đủ hẳn mới được tính là sẵn sàng).
MIN_SLOTS = {
    "bóng đá": 10,
}


def get_min_players(sport: str) -> int:
    """Số người tối thiểu để 1 trận được coi là 'đủ để chơi' — xem MIN_SLOTS."""
    key = normalize_sport(sport).lower()
    return MIN_SLOTS.get(key, DEFAULT_SLOTS.get(key, 1))


# ---- Chuẩn hoá tên môn thể thao — user gõ từ đồng nghĩa khác nhau (đá
# banh/đá bóng/bóng đá) đều phải quy về ĐÚNG 1 tên gốc, không thì hệ thống
# sẽ hiểu nhầm thành nhiều môn khác nhau khi tạo/tìm/liệt kê trận. ----
SPORT_SYNONYMS = {
    "đá banh": "bóng đá",
    "đá bóng": "bóng đá",
    "banh": "bóng đá",
    "bóng đá": "bóng đá",
    "football": "bóng đá",
    "soccer": "bóng đá",
    "cầu lông": "cầu lông",
    "đánh cầu": "cầu lông",
    "badminton": "cầu lông",
    "bóng rổ": "bóng rổ",
    "rổ": "bóng rổ",
    "basketball": "bóng rổ",
}


def normalize_sport(sport: str) -> str:
    """Quy môn thể thao user gõ (bất kỳ từ đồng nghĩa nào) về đúng 1 tên gốc
    duy nhất — vd "đá banh"/"đá bóng"/"football" đều -> "bóng đá". Môn không
    có trong bảng đồng nghĩa thì giữ nguyên (chỉ strip khoảng trắng thừa)."""
    if not sport:
        return sport
    key = sport.strip().lower()
    return SPORT_SYNONYMS.get(key, sport.strip())


# ---- Schema mô tả tool trích xuất thông tin trận (luồng cũ, extract_match_info) ----
# Giữ lại để tương thích ngược — luồng mới dùng function-calling thật ở dưới.
TOOL_EXTRACT_MATCH = {
    "name": "extract_match_info",
    "description": "Trích xuất thông tin mở trận thể thao từ tin nhắn người dùng.",
    "parameters": {
        "type": "object",
        "properties": {
            "sport": {
                "type": "string",
                "description": "Môn thể thao (ví dụ: bóng đá, cầu lông, bóng rổ)",
            },
            "time": {
                "type": "string",
                "description": "Thời gian chơi (ví dụ: 17h, 5h chiều nay)",
            },
            "location": {
                "type": "string",
                "description": "Địa điểm/sân chơi (ví dụ: sân nội khu, sân cầu lông nhà thi đấu)",
            },
        },
        "required": ["sport", "time", "location"],
    },
}


# ---- Emoji mapping theo môn thể thao ----
# Dùng trong create_match_embed() ở match_manager.py
SPORT_EMOJI_MAP = {
    "bóng đá": {"emoji": "⚽", "color": "green"},
    "cầu lông": {"emoji": "🏸", "color": "blue"},
    "bóng rổ": {"emoji": "🏀", "color": "orange"},
}

# Emoji và màu mặc định cho các môn khác
DEFAULT_SPORT_STYLE = {"emoji": "🏅", "color": "purple"}


# ============================================================
# TOOLS MỚI CHO AGENT (Gemini function calling thật — package google-genai)
# ============================================================
# Cách hoạt động: mỗi hàm bên dưới là 1 "tool". Gemini tự đọc DOCSTRING +
# kiểu dữ liệu tham số để hiểu KHI NÀO nên gọi hàm nào, gọi với tham số gì
# (Automatic Function Calling — không cần tự viết JSON schema tay).
#
# ⚠️ QUY TẮC AN TOÀN QUAN TRỌNG NHẤT (đọc trước khi sửa gì trong file này):
#   - Tool ĐỌC dữ liệu (search_knowledge_base, list_open_matches,
#     find_nearest_match) — an toàn, agent được tự do gọi bao nhiêu lần
#     cũng được, không có hậu quả thật.
#   - Tool THAY ĐỔI dữ liệu thật (create_match, join_match, leave_match,
#     update_match, cancel_match) — LUÔN có tham số `confirmed: bool`.
#     Agent CHỈ được set confirmed=True khi user vừa xác nhận rõ ràng ở tin
#     nhắn hiện tại. Đây là "chốt chặn" thứ 2 (chốt chặn thứ 1 là chỉ dẫn
#     trong system prompt) — nếu agent lỡ quên hỏi mà set confirmed=True bừa,
#     ít nhất docstring vẫn nhắc lại ngay tại chỗ nó đang đọc để quyết định.
#     Xem thêm quy tắc đầy đủ trong system_prompt.py, mục
#     "QUY TẮC XÁC NHẬN TRƯỚC KHI HÀNH ĐỘNG".
#   - user_id/user_name của người đang chat KHÔNG bao giờ là tham số mà agent
#     tự điền — luôn được "khoá cứng" qua closure trong build_agent_tools()
#     bên dưới, lấy thẳng từ tin nhắn Discord thật. Agent không thể tự xưng
#     là người khác hoặc thao túng để hành động thay người khác.
# ============================================================


def _load_kb_text() -> str:
    """Đọc toàn bộ cẩm nang tiện ích từ data/knowledge_base.txt."""
    kb_path = BASE_DIR / "data" / "knowledge_base.txt"
    try:
        with open(kb_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "(Không tìm thấy file knowledge_base.txt — báo lỗi này cho user, không được bịa dữ liệu.)"


def build_agent_tools(match_manager, user_id: int, user_name: str) -> list:
    """
    Tạo danh sách "tools" cho MỘT lượt chat của MỘT người dùng cụ thể.

    Gọi hàm này lại từ đầu MỖI KHI xử lý 1 tin nhắn mới (xem run_agent() ở
    llm_handler.py) — vì mỗi lần gọi sẽ "khoá cứng" user_id/user_name của
    đúng người đang nhắn tin lúc đó vào các tool bên dưới qua closure, agent
    không thấy và không thể tự đổi 2 giá trị này.

    match_manager: instance MatchManager ĐANG DÙNG CHUNG với slash commands
                   trong bot.py (để state nhất quán, không bị lệch dữ liệu).
    """

    # ---------- TOOL 1: Tra cứu tiện ích (RAG) ----------
    def search_knowledge_base(query: str) -> str:
        """
        Tra cứu cẩm nang tiện ích VinUni (căn tin, thư viện, sân thể thao,
        phòng gym, liên hệ hỗ trợ...).

        LUÔN gọi tool này trước khi trả lời bất kỳ câu hỏi nào về tiện ích/
        campus — KHÔNG được tự bịa thông tin nếu không thấy trong kết quả
        trả về. Nếu không tìm thấy phần nào khớp câu hỏi trong cẩm nang, phải
        nói rõ với user là chưa có dữ liệu này, không suy đoán.

        Kết quả trả về là TOÀN BỘ nội dung cẩm nang, đã chia theo mục
        (# === TÊN MỤC ===). Chỉ dùng phần khớp câu hỏi, và khi trả lời phải
        trích dẫn đúng mục đã dùng, ví dụ: "(Theo mục THƯ VIỆN — Cẩm nang học
        viên VinUni)".

        Args:
            query: câu hỏi hoặc từ khoá gốc của học viên.
        """
        return _load_kb_text()

    # ---------- TOOL 2: Liệt kê / tóm tắt trận đang mở ----------
    def list_open_matches(sport: str = "") -> dict:
        """
        Liệt kê các trận thể thao đang mở, còn chỗ trống — kèm đầy đủ thời
        gian tạo, số người hiện tại/cần, trình độ, người tạo.

        Dùng khi user hỏi kiểu: "có trận nào đang mở không", "xem danh sách
        trận", hoặc "tóm tắt cho tôi các lịch/trận gần đây" — với yêu cầu
        "tóm tắt", KHÔNG có tool riêng để tóm tắt: agent tự đọc dữ liệu tool
        này trả về rồi tự viết đoạn tóm tắt ngắn gọn bằng lời văn tự nhiên.

        Args:
            sport: lọc theo môn thể thao (để trống "" = lấy tất cả các môn).
                   Không cần lo về từ đồng nghĩa (đá banh/đá bóng/bóng đá) —
                   tool tự chuẩn hoá trước khi lọc.
        """
        matches = match_manager.get_active_matches()
        if sport:
            s = normalize_sport(sport).lower()
            matches = [m for m in matches if s in normalize_sport(m["sport"]).lower()]
        matches.sort(key=lambda m: m.get("created_at_iso", ""), reverse=True)
        return {"count": len(matches), "matches": matches}

    # ---------- TOOL 3: Agent tự tìm & đề xuất trận phù hợp nhất ----------
    def find_nearest_match(sport: str, level: str = "") -> dict:
        """
        AGENT TỰ TÌM & ĐỀ XUẤT (không phải chỉ liệt kê): tìm trong các trận
        đang mở đúng môn thể thao, xếp hạng theo GIỜ GẦN NHẤT (đoán giờ từ
        chuỗi thời gian tự do mà người tạo đã nhập, ví dụ "17h", "5h chiều
        nay") và ưu tiên trận có trình độ khớp với `level` nếu có cung cấp.

        Dùng cho các câu kiểu: "hiện có team đá banh nào lịch sớm nhất hôm
        nay không, cho mình vào luôn" / "tìm giúp mình 1 trận cầu lông hợp
        trình độ trung bình".

        QUAN TRỌNG: tool này CHỈ TRẢ VỀ ĐỀ XUẤT — KHÔNG tự thêm user vào bất
        kỳ trận nào. Sau khi gọi tool này, BẮT BUỘC phải trình bày trận được
        đề xuất KÈM LÝ DO (trường "reason" trong kết quả trả về) cho user
        xem, rồi hỏi user có đồng ý không. CHỈ được gọi join_match ở LƯỢT
        CHAT TIẾP THEO, sau khi user xác nhận rõ ràng.

        Args:
            sport: môn thể thao cần tìm (bắt buộc). Không cần lo về từ đồng
                   nghĩa (đá banh/đá bóng/bóng đá) — tool tự chuẩn hoá.
            level: trình độ user mong muốn ("vui là chính"/"trung bình"/"khá"),
                   để trống "" nếu chưa biết trình độ user.
        """
        sport_l = normalize_sport(sport).lower()
        now_hour = datetime.now().hour
        candidates = [
            m
            for m in match_manager.get_active_matches()
            if sport_l in normalize_sport(m["sport"]).lower() and len(m["players"]) < m["target_players"]
        ]
        if not candidates:
            return {
                "status": "not_found",
                "message": f"Hiện chưa có trận {sport} nào còn chỗ trống trong dữ liệu.",
            }

        def _score(m):
            hour = extract_hour(m.get("time", ""))
            if hour is None:
                time_score = 999  # không đoán được giờ -> xếp cuối, không suy diễn
            else:
                diff = hour - now_hour
                time_score = diff if diff >= 0 else diff + 24
            level_penalty = 0
            if level and m.get("level", "chưa rõ").lower() != level.lower():
                level_penalty = 3
            return time_score + level_penalty

        ranked = sorted(candidates, key=_score)
        best = ranked[0]

        reasons = [f"còn {best['target_players'] - len(best['players'])} chỗ trống"]
        if extract_hour(best.get("time", "")) is not None:
            reasons.append(f"giờ chơi ({best['time']}) sớm nhất trong số các trận {sport} đang mở")
        if level and best.get("level", "chưa rõ").lower() == level.lower():
            reasons.append(f"trình độ khớp với bạn ({level})")

        return {
            "status": "found",
            "recommended": best,  # đã có sẵn key "id" = match_id
            "reason": "; ".join(reasons),
            "alternatives": ranked[1:3],
        }

    # ---------- TOOL 4: Tạo trận (thủ công HOẶC agent tự tạo từ prompt) ----------
    def create_match(sport: str, time: str, location: str, level: str = "chưa rõ", confirmed: bool = False) -> dict:
        """
        Tạo trận thể thao mới.

        CHỈ set confirmed=True nếu ĐỦ CẢ 3: user đã cung cấp đầy đủ sport +
        time + location, VÀ tin nhắn hiện tại của user thể hiện rõ ý muốn tạo
        thật (không phải đang hỏi thăm dò/nói chung chung). Nếu thiếu bất kỳ
        trường nào, PHẢI để confirmed=False và hỏi lại user trường còn thiếu
        — không được tự đoán giờ/sân/môn.

        Args:
            sport: môn thể thao. Cứ gõ đúng theo lời user nói (đá banh/đá
                   bóng/bóng đá đều được) — tool tự chuẩn hoá về 1 tên gốc.
            time: giờ chơi (giữ nguyên văn user nói, ví dụ "17h", "5h chiều nay").
            location: sân/địa điểm.
            level: trình độ mong muốn, "chưa rõ" nếu user không nói.
            confirmed: True CHỈ khi đã đủ thông tin và user thực sự muốn tạo.
        """
        missing = [n for n, v in [("môn thể thao", sport), ("giờ chơi", time), ("sân/địa điểm", location)] if not v]
        if missing:
            return {
                "status": "needs_more_info",
                "missing_fields": missing,
                "message": f"Còn thiếu: {', '.join(missing)}. Hỏi lại user trước khi tạo.",
            }
        if not confirmed:
            return {
                "status": "needs_confirmation",
                "message": "Đã đủ thông tin nhưng chưa có xác nhận rõ ràng từ user — hỏi lại trước khi tạo thật.",
            }

        sport_canon = normalize_sport(sport)
        match_id = match_manager.create_match(
            sport=sport_canon, time=time, location=location, creator_name=user_name, creator_id=user_id, level=level
        )
        return {
            "status": "created",
            "match_id": match_id,
            "sport": sport_canon,
            "time": time,
            "location": location,
            "min_players": get_min_players(sport_canon),
            "max_players": DEFAULT_SLOTS.get(sport_canon.lower(), 10),
        }

    # ---------- TOOL 5: Tham gia trận (kể cả từ luồng agent đề xuất) ----------
    def join_match(match_id: str, confirmed: bool) -> dict:
        """
        Thêm user hiện tại vào 1 trận đã tồn tại (biết trước match_id — từ
        list_open_matches hoặc find_nearest_match).

        CHỈ set confirmed=True nếu tin nhắn HIỆN TẠI của user chứa xác nhận
        rõ ràng (ví dụ: "ok", "đồng ý", "xác nhận", "cho mình vào", "chốt
        kèo"). Nếu user mới chỉ đang ĐƯỢC đề xuất/hỏi ý kiến (chưa trả lời),
        BẮT BUỘC set confirmed=False.

        Args:
            match_id: ID trận cần tham gia.
            confirmed: True CHỈ khi user vừa xác nhận ở tin nhắn hiện tại.
        """
        if not confirmed:
            return {
                "status": "needs_confirmation",
                "message": "Chưa có xác nhận từ user cho trận này — hỏi lại trước khi thêm vào.",
            }
        ok, msg = match_manager.join_match(match_id, user_id, user_name)
        return {"status": "joined" if ok else "failed", "message": msg}

    # ---------- TOOL 6: Rời trận ----------
    def leave_match(match_id: str) -> dict:
        """
        Cho user hiện tại rời khỏi 1 trận đã tham gia. Không cần xác nhận
        thêm vì đây là hành động tự nguyện, ít rủi ro, dễ hoàn tác (join lại).

        Args:
            match_id: ID trận muốn rời.
        """
        ok, msg = match_manager.leave_match(match_id, user_id)
        return {"status": "left" if ok else "failed", "message": msg}

    # ---------- TOOL 7: Sửa trận (Correction path) ----------
    def update_match(
        match_id: str, new_time: str = "", new_location: str = "", new_sport: str = "", confirmed: bool = False
    ) -> dict:
        """
        Sửa giờ/sân/môn của 1 trận DO CHÍNH user hiện tại tạo (không sửa
        được trận của người khác). Dùng cho case "tạo trận bị sai giờ muốn
        sửa ngay", hoặc user đổi ý sau khi tạo (ví dụ nhắn "đổi sang 6h đi").

        CHỈ set confirmed=True nếu user vừa xác nhận muốn đổi thành giá trị
        cụ thể. Để trống ("") cho trường nào không cần đổi.

        Args:
            match_id: ID trận cần sửa.
            new_time: giờ mới, "" nếu không đổi giờ.
            new_location: sân mới, "" nếu không đổi sân.
            new_sport: môn mới, "" nếu không đổi môn.
            confirmed: True CHỈ khi user vừa xác nhận muốn đổi.
        """
        if not confirmed:
            return {"status": "needs_confirmation", "message": "Hỏi lại user muốn đổi thành gì trước khi sửa."}
        ok, msg = match_manager.update_match(
            match_id,
            user_id,
            new_time=new_time or None,
            new_location=new_location or None,
            new_sport=normalize_sport(new_sport) if new_sport else None,
        )
        return {"status": "updated" if ok else "failed", "message": msg}

    # ---------- TOOL 8: Huỷ trận ----------
    def cancel_match(match_id: str, confirmed: bool) -> dict:
        """
        Huỷ hẳn 1 trận DO CHÍNH user hiện tại tạo. Đây là hành động KHÔNG
        hoàn tác được (mọi người đã join sẽ mất chỗ) — CHỈ set confirmed=True
        nếu user vừa xác nhận rõ ràng muốn huỷ thật.

        Args:
            match_id: ID trận cần huỷ.
            confirmed: True CHỈ khi user vừa xác nhận muốn huỷ.
        """
        if not confirmed:
            return {"status": "needs_confirmation", "message": "Xác nhận lại với user trước khi huỷ trận thật."}
        ok, msg = match_manager.cancel_match(match_id, user_id)
        return {"status": "cancelled" if ok else "failed", "message": msg}

    # ---------- TOOL 9: Thông báo thiếu slot ----------
    def notify_missing_slot(match_id: str, missing_count: int) -> dict:
        """
        Phát thông báo kêu gọi thêm thành viên vào một trận đang thiếu người.

        Dùng khi user nhắn đại loại: "kèo ... bị thiếu X người, nhắc mọi người",
        "cần thêm người cho trận ...", "ai rảnh đến bấm vào luôn"...
        Tool trả về nội dung thông báo đã soạn sẵn để bot gửi ra kênh Discord.
        Không cần xác nhận thêm vì đây là hành động đọc chỉ / phát
        thông báo, không tháy đổi dữ liệu trận.

        Args:
            match_id: ID trận cần không người.
            missing_count: số người còn thiếu.
        """
        matches = match_manager.get_active_matches()
        match = next((m for m in matches if m["id"] == match_id), None)
        if not match:
            return {"status": "not_found", "message": f"Không tìm thấy trận với ID {match_id}."}

        sport = match.get("sport", "thể thao")
        time_ = match.get("time", "chưa rõ giờ")
        location = match.get("location", "chưa rõ địa điểm")
        announcement = (
            f"🚨 **Cần thêm người!** Kèo **{sport}** lúc **{time_}** tại **{location}** "
            f"còn thiếu **{missing_count} người**. Ai rảnh nhảy vào ngay! "
            f"(ID trận: `{match_id}`)"
        )
        return {
            "status": "announced",
            "announcement": announcement,
            "match_id": match_id,
            "missing_count": missing_count,
        }

    # ---------- TOOL 10: Lấy giờ hiện tại thật ----------
    def get_current_time() -> dict:
        """
        Trả về ngày giờ THẬT hiện tại (không phải giờ trong dữ liệu trận đấu).

        LUÔN gọi tool này khi cần biết "bây giờ là mấy giờ/thứ mấy" để tính
        toán — ví dụ: trận này còn bao lâu nữa diễn ra, trận nào sắp diễn ra
        nhất, hôm nay/ngày mai là ngày bao nhiêu. KHÔNG tự đoán giờ hiện tại
        bằng kiến thức chung — múi giờ và ngày giờ thật chỉ tool này biết.

        Trả về: giờ:phút hiện tại, thứ trong tuần, ngày/tháng/năm.
        """
        now = datetime.now()
        weekday_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"][now.weekday()]
        return {
            "time_hhmm": now.strftime("%H:%M"),
            "weekday": weekday_vn,
            "date_ddmmyyyy": now.strftime("%d/%m/%Y"),
            "iso": now.isoformat(timespec="minutes"),
        }

    return [
        search_knowledge_base,
        list_open_matches,
        find_nearest_match,
        create_match,
        join_match,
        leave_match,
        update_match,
        cancel_match,
        notify_missing_slot,
        get_current_time,
    ]
