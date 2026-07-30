import os
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path

# ============================================================
# FILE: llm_handler.py
# MỤC ĐÍCH: Chứa toàn bộ logic giao tiếp với AI (Google Gemini).
#            Có 2 chức năng chính:
#            1. Trả lời câu hỏi tiện ích dựa trên Knowledge Base.
#            2. Phân loại ý định (intent) tin nhắn người dùng.
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

SYSTEM_PROMPT_QNA = """Bạn là trợ lý AI thân thiện của VinUni, hỗ trợ học viên về thông tin tiện ích nội khu và thể thao.

QUY TẮC BẮT BUỘC:
1. CHỈ trả lời dựa trên thông tin trong phần "DỮ LIỆU" bên dưới. TUYỆT ĐỐI không bịa đặt thêm thông tin ngoài dữ liệu.
2. Nếu câu hỏi KHÔNG có đáp án trong dữ liệu, hãy trả lời: "Xin lỗi, mình chưa có thông tin này trong cẩm nang. Bạn có thể hỏi thêm ở kênh #hoi-mentor nhé!"
3. Luôn trả lời bằng tiếng Việt, ngắn gọn, thân thiện, dùng emoji cho sinh động.
4. Cuối câu trả lời, ghi nguồn: "(Theo Cẩm nang học viên VinUni)"
5. Nếu câu hỏi liên quan đến bài tập, học thuật, hãy từ chối khéo: "Mình chỉ hỗ trợ thông tin tiện ích và thể thao thôi nha, bạn hãy hỏi Mentor nhé! 📚"

DỮ LIỆU:
{knowledge_base}
"""


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

SYSTEM_PROMPT_CLASSIFY = """Bạn là bộ phân loại ý định tin nhắn. Hãy đọc tin nhắn của user và phân loại vào MỘT trong các loại sau:

1. "qna" - Nếu user đang HỎI THÔNG TIN tiện ích (căn tin, thư viện, thẻ từ, phòng gym, liên hệ hỗ trợ...).
2. "create_match" - Nếu user muốn RỦ/MỞ TRẬN thể thao (đá bóng, cầu lông, v.v.), ví dụ: "ai đá bóng không", "rủ đá banh chiều nay".
3. "list_matches" - Nếu user muốn XEM các trận đang mở, ví dụ: "có trận nào đang mở không", "xem danh sách trận".
4. "join_match" - Nếu user muốn THAM GIA vào trận đang mở, ví dụ: "cho mình join", "mình tham gia".
5. "other" - Nếu không thuộc các loại trên (chào hỏi, nói chuyện linh tinh, bài tập...).

CHỈ trả lời DUY NHẤT 1 từ: qna, create_match, list_matches, join_match, hoặc other.
KHÔNG giải thích gì thêm.
"""


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

        valid_intents = ["qna", "create_match", "list_matches", "join_match", "other"]
        if intent in valid_intents:
            return intent
        return "other"
    except Exception as e:
        print(f"⚠️ Lỗi phân loại intent: {e}")
        return "other"


# ============================================================
# CHỨC NĂNG 3: TRÍCH XUẤT THÔNG TIN MỞ TRẬN (TOOL CALLING ĐƠN GIẢN)
# ============================================================

SYSTEM_PROMPT_EXTRACT = """Từ tin nhắn sau, hãy trích xuất thông tin mở trận thể thao.
Trả về ĐÚNG theo format sau (mỗi dòng 1 trường, không giải thích thêm):
sport: <môn thể thao>
time: <thời gian>
location: <địa điểm>

Nếu thiếu thông tin nào, ghi "chưa rõ" cho trường đó.

Ví dụ:
Tin nhắn: "5h chiều nay đá bóng sân nội khu không anh em"
Kết quả:
sport: bóng đá
time: 5h chiều nay
location: sân nội khu
"""


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
