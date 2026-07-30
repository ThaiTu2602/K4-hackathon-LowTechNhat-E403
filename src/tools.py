# ============================================================
# FILE: tools.py
# MỤC ĐÍCH: Tập trung TẤT CẢ cấu hình tool/function definitions
#            và các hằng số dùng chung vào một nơi duy nhất.
#            Khi cần thêm/sửa tool hoặc thay đổi config, chỉ cần mở file này.
# ============================================================

# ---- Danh sách Intent hợp lệ ----
# Dùng trong hàm classify_intent() ở llm_handler.py
VALID_INTENTS = ["qna", "create_match", "list_matches", "join_match", "other"]


# ---- Số người mặc định để đủ 1 trận theo từng môn ----
# Dùng trong MatchManager ở match_manager.py
DEFAULT_SLOTS = {
    "bóng đá": 10,
    "cầu lông": 4,
    "bóng rổ": 6,
}


# ---- Schema mô tả tool trích xuất thông tin trận ----
# Có thể dùng khi chuyển sang Gemini Function Calling chính thức
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
