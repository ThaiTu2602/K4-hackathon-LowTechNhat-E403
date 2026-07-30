import os

# TODO (Thành viên 3): Import thư viện LLM (google.generativeai hoặc openai)
# import google.generativeai as genai

def get_answer_from_knowledge_base(question, knowledge_base_text):
    """
    Hàm gọi LLM để trả lời câu hỏi dựa trên knowledge_base.
    """
    # 1. Khởi tạo LLM Client
    # 2. Xây dựng prompt: "Dựa vào đoạn văn bản sau {knowledge_base_text}, hãy trả lời {question}"
    # 3. Gọi API và trả về kết quả
    return f"[Mock LLM Response] Câu trả lời cho: {question}"

def extract_match_intent(user_message):
    """
    Hàm gọi LLM sử dụng Tool Calling (Function Calling) để trích xuất thông tin mở trận.
    """
    # 1. Định nghĩa schema Tool (thời gian, địa điểm, môn thể thao)
    # 2. Đưa user_message vào LLM để LLM trả về cấu trúc JSON tương ứng
    # 3. Parse JSON và trả về dict
    
    # Dữ liệu giả lập
    return {
        "intent": "create_match",
        "sport": "bóng đá",
        "time": "17h",
        "location": "sân nội khu"
    }
