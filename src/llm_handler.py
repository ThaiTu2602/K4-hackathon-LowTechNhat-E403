import os
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path

# Import prompts và config từ file riêng (dễ tinh chỉnh)
from prompts import SYSTEM_PROMPT_QNA, SYSTEM_PROMPT_CLASSIFY, SYSTEM_PROMPT_EXTRACT
from tools import VALID_INTENTS

# ============================================================
# FILE: llm_handler.py
# MỤC ĐÍCH: Chứa toàn bộ logic giao tiếp với AI (Google Gemini).
#            Có 2 chức năng chính:
#            1. Trả lời câu hỏi tiện ích dựa trên Knowledge Base.
#            2. Phân loại ý định (intent) tin nhắn người dùng.
#
# LƯU Ý: Các system prompts được quản lý tập trung ở file prompts.py
#          Các tool definitions & config ở file tools.py
# ============================================================

# Tìm thư mục gốc dự án (thư mục cha của src/)
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# --- Khởi tạo Gemini Client ---
genai.configure(api_key=os.getenv("LLM_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")


def load_knowledge_base():
    """Đọc toàn bộ nội dung file knowledge_base.txt và trả về dưới dạng chuỗi."""
    kb_path = BASE_DIR / "data" / "knowledge_base.txt"
    try:
        with open(kb_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "(Không tìm thấy file knowledge_base.txt)"


# ============================================================
# CHỨC NĂNG 1: TRẢ LỜI CÂU HỎI TIỆN ÍCH (Q&A)
# ============================================================

def get_qna_answer(user_question: str) -> str:
    """
    Gửi câu hỏi của user + knowledge base cho Gemini để nhận câu trả lời.
    Đây là luồng Q&A (Hỏi đáp tiện ích).
    """
    knowledge_base = load_knowledge_base()
    prompt = SYSTEM_PROMPT_QNA.format(knowledge_base=knowledge_base)

    try:
        chat = model.start_chat(history=[])
        response = chat.send_message(
            f"System: {prompt}\n\nCâu hỏi của học viên: {user_question}"
        )
        return response.text
    except Exception as e:
        return f"⚠️ Lỗi khi gọi AI: {str(e)}"


# ============================================================
# CHỨC NĂNG 2: PHÂN LOẠI Ý ĐỊNH (INTENT CLASSIFICATION)
# ============================================================

def classify_intent(user_message: str) -> str:
    """
    Gửi tin nhắn user cho Gemini để phân loại ý định.
    Trả về 1 trong: 'qna', 'create_match', 'list_matches', 'join_match', 'other'.
    """
    try:
        response = model.generate_content(
            f"System: {SYSTEM_PROMPT_CLASSIFY}\n\nTin nhắn user: \"{user_message}\""
        )
        intent = response.text.strip().lower()

        if intent in VALID_INTENTS:
            return intent
        return "other"
    except Exception as e:
        print(f"⚠️ Lỗi phân loại intent: {e}")
        return "other"


# ============================================================
# CHỨC NĂNG 3: TRÍCH XUẤT THÔNG TIN MỞ TRẬN (TOOL CALLING ĐƠN GIẢN)
# ============================================================

def extract_match_info(user_message: str) -> dict:
    """
    Trích xuất thông tin trận đấu (sport, time, location) từ tin nhắn.
    Trả về dict: {'sport': ..., 'time': ..., 'location': ...}
    """
    try:
        response = model.generate_content(
            f"System: {SYSTEM_PROMPT_EXTRACT}\n\nTin nhắn: \"{user_message}\""
        )
        text = response.text.strip()

        info = {"sport": "chưa rõ", "time": "chưa rõ", "location": "chưa rõ"}
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("sport:"):
                info["sport"] = line.split(":", 1)[1].strip()
            elif line.startswith("time:"):
                info["time"] = line.split(":", 1)[1].strip()
            elif line.startswith("location:"):
                info["location"] = line.split(":", 1)[1].strip()
        return info
    except Exception as e:
        print(f"⚠️ Lỗi trích xuất match info: {e}")
        return {"sport": "chưa rõ", "time": "chưa rõ", "location": "chưa rõ"}
