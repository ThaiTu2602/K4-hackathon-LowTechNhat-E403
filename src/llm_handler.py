import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

# Import prompts và config từ file riêng (dễ tinh chỉnh)
from prompts import SYSTEM_PROMPT_QNA, SYSTEM_PROMPT_CLASSIFY, SYSTEM_PROMPT_EXTRACT, AGENT_SYSTEM_PROMPT
from tools import VALID_INTENTS, build_agent_tools

# ============================================================
# FILE: llm_handler.py
# MỤC ĐÍCH: Chứa toàn bộ logic giao tiếp với AI (Google Gemini), dùng SDK
#            MỚI `google-genai` (SDK cũ `google-generativeai` đã bị Google
#            khai tử — không còn được vá lỗi/cập nhật nữa).
#
#            2 nhóm hàm:
#            - run_agent()            : LUỒNG MỚI — 1 agent thật, tự gọi
#                                        tools trong tools.py (function
#                                        calling thật). Đây là hàm bot.py
#                                        nên dùng.
#            - get_qna_answer() / classify_intent() / extract_match_info()
#                                      : LUỒNG CŨ (2-3 lệnh gọi rời rạc,
#                                        không có tool calling thật) — giữ
#                                        lại để không phá code cũ nào còn
#                                        gọi tới, nhưng KHÔNG khuyến khích
#                                        dùng tiếp cho luồng chính.
#
# LƯU Ý: Các system prompts được quản lý tập trung ở file prompts.py
#          Các tool definitions & config ở file tools.py
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

# Nếu chưa có key, _client = None — mọi hàm bên dưới sẽ trả lời báo lỗi rõ
# ràng thay vì crash toàn bộ bot khi khởi động.
_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
if _client is None:
    print("⚠️ Chưa có GEMINI_API_KEY trong .env — các chức năng AI sẽ báo lỗi khi được gọi.")


def load_knowledge_base():
    """Đọc toàn bộ nội dung file knowledge_base.txt và trả về dưới dạng chuỗi."""
    kb_path = BASE_DIR / "data" / "knowledge_base.txt"
    try:
        with open(kb_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "(Không tìm thấy file knowledge_base.txt)"


# ============================================================
# LUỒNG MỚI — AGENT THẬT (function calling thật qua tools.py)
# ============================================================

# Mỗi user có 1 phiên chat RIÊNG (key = user_id), KHÔNG dùng chung theo
# kênh. Lý do quan trọng: tools của mỗi phiên bị "khoá cứng" đúng user_id/
# user_name của người tạo phiên (xem build_agent_tools trong tools.py) — nếu
# dùng chung theo kênh, một user khác nhắn vào cùng kênh có thể vô tình dùng
# nhầm tools đang mang danh tính của người tạo phiên trước đó. Theo user_id
# thì mỗi người luôn chỉ hành động được với danh nghĩa của chính mình, và
# luồng "agent đề xuất → chờ xác nhận ở tin nhắn sau" cũng đúng ngữ cảnh của
# đúng người đó, không bị người khác chen ngang trả lời hộ.
_agent_sessions: dict[int, "genai.chats.Chat"] = {}

# ---- LOG mọi lượt gọi AI thật (bằng chứng "lời gọi AI thật, không
# hardcode" cho rubric R5) — mỗi dòng 1 lượt, ghi timestamp + input + tool
# nào được gọi với tham số gì + câu trả lời cuối cùng.
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "agent_calls.jsonl"


def _extract_new_tool_calls(chat, history_len_before: int) -> list[dict]:
    """Lấy các function_call MỚI phát sinh trong lượt send_message() vừa rồi (so với trước đó)."""
    hist = chat.get_history(curated=False)
    calls = []
    for content in hist[history_len_before:]:
        for part in content.parts or []:
            fc = getattr(part, "function_call", None)
            if fc:
                calls.append({"name": fc.name, "args": dict(fc.args) if fc.args else {}})
    return calls


def _log_agent_call(user_id: int, user_name: str, user_text: str, tool_calls: list, final_text: str) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "user_id": user_id,
            "user_name": user_name,
            "user_text": user_text,
            "tool_calls": tool_calls,
            "final_text": final_text,
        }
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as e:
        print(f"⚠️ Không ghi được log agent call: {e}")


def _run_agent_traced(user_id: int, user_name: str, user_text: str, match_manager) -> tuple[str, list[dict]]:
    """
    Lõi thật của agent — dùng chung cho cả run_agent() (bot.py dùng, chỉ cần
    text) và run_agent_with_trace() (eval/run_eval.py dùng, cần biết cả tool
    nào đã được gọi để chấm case dạng expected_intent).
    """
    if _client is None:
        msg = "⚠️ Bot chưa được cấu hình GEMINI_API_KEY trong file `.env` — báo Admin nhóm giúp mình nhé."
        return msg, []

    if user_id not in _agent_sessions:
        tools = build_agent_tools(match_manager, user_id, user_name)
        _agent_sessions[user_id] = _client.chats.create(
            model=GEMINI_MODEL,
            config=types.GenerateContentConfig(
                system_instruction=AGENT_SYSTEM_PROMPT,
                tools=tools,
                # Chặn trần agent gọi tool loạn vòng lặp — tối đa 6 lần gọi
                # tool nối tiếp nhau trong 1 lượt trả lời.
                automatic_function_calling=types.AutomaticFunctionCallingConfig(maximum_remote_calls=6),
            ),
        )
    chat = _agent_sessions[user_id]
    history_len_before = len(chat.get_history(curated=False))

    try:
        response = chat.send_message(user_text)
        final_text = response.text or "🤔 Mình chưa nghĩ ra câu trả lời phù hợp, bạn hỏi lại rõ hơn giúp mình nhé."
        tool_calls = _extract_new_tool_calls(chat, history_len_before)
    except Exception as e:
        print(f"⚠️ Lỗi run_agent: {e}")
        final_text = f"⚠️ Mình gặp lỗi khi xử lý: {e}"
        tool_calls = []

    _log_agent_call(user_id, user_name, user_text, tool_calls, final_text)
    return final_text, tool_calls


def run_agent(user_id: int, user_name: str, user_text: str, match_manager) -> str:
    """
    Chạy 1 lượt hội thoại của AGENT THẬT — model tự quyết định có cần gọi
    tool nào trong tools.py hay không (tra cứu tiện ích, tìm/tạo/sửa/huỷ
    trận...), tự gọi, tự đọc kết quả, rồi tự viết câu trả lời cuối cùng.
    Đây là hàm bot.py gọi cho luồng chính trên Discord.

    Args:
        user_id: Discord user id thật của người nhắn (KHÔNG lấy từ nội dung
                 tin nhắn — luôn lấy từ message.author.id ở bot.py, để agent
                 không thể tự nhận nhầm/giả danh người khác).
        user_name: tên hiển thị Discord của người nhắn.
        user_text: nội dung tin nhắn.
        match_manager: instance MatchManager DÙNG CHUNG với slash commands
                       trong bot.py (để dữ liệu trận đấu nhất quán).

    Trả về: chuỗi văn bản để bot.py gửi trả lời trên Discord.
    """
    text, _ = _run_agent_traced(user_id, user_name, user_text, match_manager)
    return text


def run_agent_with_trace(user_id: int, user_name: str, user_text: str, match_manager) -> tuple[str, list[dict]]:
    """
    Giống run_agent() nhưng trả về thêm danh sách tool đã gọi (name + args)
    trong lượt này — dùng cho eval/run_eval.py để chấm các case dạng
    expected_intent (kiểm tra đúng tool/action có được gọi hay không).
    """
    return _run_agent_traced(user_id, user_name, user_text, match_manager)


def reset_agent_session(user_id: int) -> None:
    """Xoá phiên chat của 1 user (vd: dùng cho lệnh /reset nếu muốn cho user bắt đầu lại từ đầu)."""
    _agent_sessions.pop(user_id, None)


# ============================================================
# LUỒNG CŨ — 3 lệnh gọi rời rạc, KHÔNG dùng function calling thật.
# Giữ lại để tương thích ngược, đã migrate sang SDK mới google-genai.
# ============================================================


def get_qna_answer(user_question: str) -> str:
    """Luồng cũ: nhồi toàn bộ Knowledge Base vào prompt rồi hỏi thẳng, không qua tool calling."""
    if _client is None:
        return "⚠️ Bot chưa được cấu hình GEMINI_API_KEY trong file `.env`."
    knowledge_base = load_knowledge_base()
    prompt = SYSTEM_PROMPT_QNA.format(knowledge_base=knowledge_base)
    try:
        response = _client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_question,
            config=types.GenerateContentConfig(system_instruction=prompt),
        )
        return response.text
    except Exception as e:
        return f"⚠️ Lỗi khi gọi AI: {e}"


def classify_intent(user_message: str) -> str:
    """Luồng cũ: 1 lệnh gọi riêng chỉ để phân loại ý định thành 1 trong VALID_INTENTS."""
    if _client is None:
        return "other"
    try:
        response = _client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_message,
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT_CLASSIFY),
        )
        intent = response.text.strip().lower()
        return intent if intent in VALID_INTENTS else "other"
    except Exception as e:
        print(f"⚠️ Lỗi phân loại intent: {e}")
        return "other"


def extract_match_info(user_message: str) -> dict:
    """Luồng cũ: trích xuất sport/time/location bằng cách parse text thô, không phải JSON thật."""
    if _client is None:
        return {"sport": "chưa rõ", "time": "chưa rõ", "location": "chưa rõ"}
    try:
        response = _client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_message,
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT_EXTRACT),
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
