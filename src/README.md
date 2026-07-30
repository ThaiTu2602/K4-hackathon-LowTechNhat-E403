# 🤖 VinUni Discord AI Assistant — Giải thích Code hoạt động thế nào

Tài liệu này giải thích cách toàn bộ code hoạt động cùng nhau, từ lúc user nhắn tin trên Discord cho đến lúc bot trả lời.

---

## 📁 Tổng quan các file

```
src/
├── bot.py              ← File chính. Chạy file này để khởi động bot.
├── llm_handler.py      ← Bộ não AI. Gọi Google Gemini để hiểu và trả lời.
├── match_manager.py    ← Bộ quản lý trận. Lưu trữ và xử lý gom nhóm thể thao.
├── prompts.py          ← Tất cả system prompts. Sửa file này để tinh chỉnh AI.
└── tools.py            ← Tool definitions & cấu hình (số người, intent, emoji...).

data/
├── knowledge_base.txt  ← "Sách giáo khoa" của bot. AI chỉ trả lời dựa trên file này.
└── matches.json        ← Dữ liệu trận đấu (được tự động tạo & cập nhật khi bot chạy).

eval/
└── golden_set.json     ← Bộ câu hỏi test để đánh giá bot trả lời đúng hay sai.

.env                    ← Chứa mật khẩu (Token, API Key). KHÔNG commit lên Git.
```

---

## 🔄 Luồng hoạt động chi tiết (Flow)

### Khi user nhắn tin trên Discord, điều gì xảy ra?

```
 User nhắn: "@bot Thư viện mấy giờ đóng cửa?"
              │
              ▼
 ┌─────────────────────────────┐
 │  bot.py — on_message()      │  ← Discord gửi tin nhắn đến code Python
 │  Kiểm tra: Bot có bị tag?   │
 │  Có → tiếp tục xử lý       │
 └─────────────┬───────────────┘
               │
               ▼
 ┌─────────────────────────────┐
 │  llm_handler.py             │
 │  classify_intent()          │  ← AI đọc tin nhắn, phân loại ý định
 │  Kết quả: "qna"             │     (hỏi đáp? mở trận? join? ...)
 └─────────────┬───────────────┘
               │
     ┌─────────┴──────────┐
     │ intent == "qna"    │
     ▼                    │
 ┌───────────────────┐    │
 │ llm_handler.py    │    │
 │ get_qna_answer()  │    │  ← AI đọc knowledge_base.txt + câu hỏi
 │ → Trả lời user    │    │     → Sinh câu trả lời
 └───────────────────┘    │
                          │
     ┌────────────────────┘
     │ intent == "create_match"
     ▼
 ┌───────────────────┐     ┌─────────────────────┐
 │ llm_handler.py    │────▶│ match_manager.py     │
 │ extract_match_    │     │ create_match()       │  ← Tạo trận mới
 │ info()            │     │ create_match_embed() │  ← Tạo bảng đẹp
 └───────────────────┘     └─────────────────────┘
                                      │
                                      ▼
                            Discord hiển thị Embed
                            (bảng xanh có tên, giờ, số người)
```

---

## 📝 Giải thích từng file

### 1. `src/bot.py` — Bộ điều hướng (Router)

**Vai trò:** Đây là file CHÍNH, giống như "lễ tân" của một khách sạn.

**Cách hoạt động:**
- Khi chạy `python src/bot.py`, code sẽ dùng Token để kết nối vào Discord.
- Bot lắng nghe **mọi tin nhắn** trong server. Nhưng chỉ xử lý khi:
  - User **tag bot** (`@VinUni Bot thư viện ở đâu?`) → AI xử lý tự động.
  - User gõ **Slash Command** bắt đầu bằng `/` (ví dụ: `/mo-tran`, `/join`, `/xem-tran`). Discord sẽ tự động gợi ý lệnh.

**Các lệnh có sẵn:**

| Lệnh | Chức năng | Ví dụ |
|---|---|---|
| `/ping` | Test bot có online không | `/ping` |
| `/mo-tran` | Mở trận thể thao mới | `/mo-tran môn:bóng-đá giờ:17h sân:sân-nội-khu` |
| `/xem-tran` | Xem danh sách trận đang mở | `/xem-tran` |
| `/join` | Tham gia trận | `/join id_trận:abc12345` |
| `/roi-tran` | Rời trận | `/roi-tran id_trận:abc12345` |
| `/huy-tran` | Huỷ trận (chỉ chủ trận) | `/huy-tran id_trận:abc12345` |
| `/help-bot` | Xem hướng dẫn | `/help-bot` |

---

### 2. `src/llm_handler.py` — Bộ não AI

**Vai trò:** Kết nối với Google Gemini API để xử lý ngôn ngữ tự nhiên.

**3 chức năng chính:**

| Hàm | Input | Output | Dùng khi nào |
|---|---|---|---|
| `classify_intent()` | Tin nhắn user | `"qna"`, `"create_match"`, `"other"`, ... | Mỗi lần user tag bot |
| `get_qna_answer()` | Câu hỏi user | Câu trả lời tiếng Việt | User hỏi về tiện ích |
| `extract_match_info()` | Tin nhắn rủ thể thao | `{"sport": ..., "time": ..., "location": ...}` | User muốn mở trận |

**Cách AI tránh bịa đặt:**
- Trong `get_qna_answer()`, System Prompt yêu cầu AI **CHỈ** trả lời dựa trên nội dung file `knowledge_base.txt`.
- Nếu không tìm thấy thông tin → AI sẽ nói "Mình chưa có thông tin này" thay vì bịa ra.

---

### 3. `src/match_manager.py` — Bộ quản lý trận

**Vai trò:** Lưu trữ và quản lý trạng thái các trận thể thao đang mở.

**Cách lưu trữ:** Dữ liệu được lưu vào file JSON (`data/matches.json`). Bot restart không mất dữ liệu trận đấu.

**Các hàm quan trọng:**

| Hàm | Mô tả |
|---|---|
| `create_match()` | Tạo trận mới, trả về ID trận |
| `join_match()` | Thêm người vào trận |
| `leave_match()` | Cho người rời trận |
| `cancel_match()` | Huỷ trận (chỉ chủ trận) |
| `is_match_full()` | Kiểm tra đã đủ người chưa (10 người cho bóng đá, 4 cho cầu lông) |
| `create_match_embed()` | Tạo bảng Embed đẹp hiển thị trên Discord |

---

### 4. `data/knowledge_base.txt` — Cơ sở dữ liệu

**Vai trò:** Đây là "nguồn sự thật duy nhất" (Single Source of Truth) mà AI dùng để trả lời.

**Hiện tại chứa thông tin về:** Căn tin, Thư viện, Thể thao, Liên hệ hỗ trợ.

> **Lưu ý:** Đây là dữ liệu GIẢ LẬP (mock). Nhóm cần cập nhật thông tin thật của VinUni vào đây.

---

### 5. `src/prompts.py` — Cấu hình Prompts

**Vai trò:** Tập trung tất cả system prompts vào một nơi duy nhất.

**3 prompt chính:**

| Biến | Dùng cho | Mục đích |
|---|---|---|
| `SYSTEM_PROMPT_QNA` | Hỏi đáp tiện ích | Quy tắc AI trả lời dựa trên KB, không bịa đặt |
| `SYSTEM_PROMPT_CLASSIFY` | Phân loại ý định | Phân loại tin nhắn vào qna/create_match/join_match/... |
| `SYSTEM_PROMPT_EXTRACT` | Trích xuất thông tin | Bóc tách sport, time, location từ tin nhắn |

> **Để tinh chỉnh prompt AI:** Mở file này và sửa nội dung prompt, không cần đụng vào code logic.

---

### 6. `src/tools.py` — Cấu hình Tools & Hằng số

**Vai trò:** Tập trung các "knob" cấu hình để dễ điều chỉnh.

| Biến | Mô tả |
|---|---|
| `VALID_INTENTS` | Danh sách intent hợp lệ (qna, create_match, ...) |
| `DEFAULT_SLOTS` | Số người mặc định theo môn (bóng đá: 10, cầu lông: 4, ...) |
| `TOOL_EXTRACT_MATCH` | Schema mô tả tool trích xuất thông tin trận |
| `SPORT_EMOJI_MAP` | Emoji và màu sắc theo môn thể thao |

---

## 🚀 Hướng dẫn chạy thử (Quick Start)

### Bước 1: Cài thư viện
```bash
pip install -r requirements.txt
```

### Bước 2: Tạo file `.env`
Copy file `.env.example` thành `.env`, điền 2 key:
```env
DISCORD_BOT_TOKEN=paste_token_từ_discord_developer_portal
LLM_API_KEY=paste_key_từ_aistudio.google.com/apikey
```

### Bước 3: Chạy bot
```bash
cd src
python bot.py
```

### Bước 4: Test trên Discord
- Gõ `/ping` → Bot trả lời "Pong!"
- Tag bot: `@bot Căn tin mấy giờ mở cửa?` → AI trả lời
- Gõ `/mo-tran` → Điền các tham số theo gợi ý của Discord → Bot tạo bảng gom nhóm
- Gõ `/xem-tran` → Xem danh sách trận
- Gõ `/help-bot` → Xem tất cả lệnh

---

## ⚠️ Lưu ý quan trọng

1. **Gemini API Key miễn phí** tại [Google AI Studio](https://aistudio.google.com/apikey). Có giới hạn 15 request/phút cho bản miễn phí.
2. **Bot chỉ online khi code đang chạy.** Tắt Terminal = bot offline. Sau này có thể deploy lên server (Railway, Render...) để chạy 24/7.
3. **File `.env` chứa mật khẩu** → KHÔNG BAO GIỜ commit lên Git. File `.gitignore` đã có dòng `.env` để bảo vệ.
4. **Dữ liệu trận đấu lưu vào file JSON** (`data/matches.json`) → Bot restart không mất dữ liệu.
5. **Muốn tinh chỉnh AI:** Sửa file `src/prompts.py` (prompts) và `src/tools.py` (cấu hình), không cần đụng code logic.
