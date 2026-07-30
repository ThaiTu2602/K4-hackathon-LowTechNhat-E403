# Hướng Dẫn Phát Triển (Development Guide) - Nhóm 4 Người

Chào mừng các bạn đến với dự án **VinUni Discord AI Assistant**. 
Dự án này đã được dựng sẵn một bộ khung sườn (skeleton) cơ bản dựa trên các file `architecture.md`, `spec.md` và `Canvas.md`.
Tài liệu này sẽ hướng dẫn chi tiết cách để nhóm 4 người bắt tay vào code và hoàn thiện sản phẩm một cách dễ dàng.

---

## 1. Cấu trúc thư mục (Project Structure)
Dự án được chia thành các thư mục sau để dễ quản lý:
```
├── data/
│   ├── knowledge_base.txt   # File văn bản chứa dữ liệu tiện ích giả lập (giờ mở cửa, quy định...)
│   └── matches.json         # File lưu trữ dữ liệu trận đấu (tự động tạo khi bot chạy)
├── eval/
│   └── golden_set.json      # Bộ dữ liệu test 20 câu để đánh giá độ chuẩn xác của Bot
├── src/
│   ├── bot.py               # File chính khởi chạy Bot Discord
│   ├── llm_handler.py       # File chứa logic gọi API LLM (Gemini/OpenAI) và xử lý Prompt
│   ├── match_manager.py     # File chứa logic quản lý trạng thái các trận đấu (gom nhóm)
│   ├── prompts.py           # Tất cả system prompts (dễ tinh chỉnh prompt AI)
│   └── tools.py             # Tool definitions & cấu hình (số người, intent, emoji...)
├── .env.example             # File mẫu chứa các biến môi trường (Copy ra thành file .env)
├── requirements.txt         # Chứa các thư viện Python cần cài đặt
└── DEVELOPMENT_GUIDE.md     # File hướng dẫn này
```

---

## 2. Cách khởi chạy dự án (Setup Instructions)

Mỗi thành viên trong nhóm cần thực hiện các bước sau trên máy tính cá nhân:

1. **Cài đặt thư viện:**
   Mở Terminal/Command Prompt tại thư mục dự án và chạy lệnh:
   ```bash
   pip install -r requirements.txt
   ```

2. **Cấu hình môi trường (.env):**
   - Copy file `.env.example` và đổi tên thành `.env` (lưu cùng cấp thư mục).
   - Điền Token Discord Bot của nhóm vào `DISCORD_BOT_TOKEN`. (Tạo bot trên [Discord Developer Portal](https://discord.com/developers/applications)).
   - Điền API Key của LLM (Gemini hoặc OpenAI) vào `LLM_API_KEY`.

3. **Chạy thử Bot:**
   ```bash
   python src/bot.py
   ```
   Nếu Terminal báo *"✅ Bot đã đăng nhập..."*, bạn có thể vào Discord gõ lệnh `/ping` để xem bot trả lời *"Pong!"*.

---

## 3. Phân công nhiệm vụ (Task Breakdown cho 4 thành viên)

Để nhóm 4 người làm việc song song không bị đụng code, dưới đây là đề xuất phân công cụ thể:

### 👨‍💻 Thành viên 1: Trưởng nhóm (Bot Core & Routing)
- **Nơi code chính:** `src/bot.py`
- **Nhiệm vụ:**
  - Viết hàm lắng nghe sự kiện `on_message` để đọc tin nhắn từ kênh Discord.
  - Phân loại (Routing): Viết logic IF/ELSE hoặc dùng regex/LLM đơn giản để xem tin nhắn người dùng là "Hỏi đáp tiện ích" hay "Rủ rê thể thao".
  - Nếu là Hỏi đáp -> Gọi hàm từ file `llm_handler.py`.
  - Nếu là Rủ rê -> Gọi hàm từ file `match_manager.py`.
  - Đảm bảo gửi tin trả lời (Reply) lại cho người dùng trên Discord.

### 🧠 Thành viên 2: AI & Prompt Engineer (LLM Handler)
- **Nơi code chính:** `src/prompts.py`, `src/tools.py`, `src/llm_handler.py` và `data/knowledge_base.txt`
- **Nhiệm vụ:**
  - Tinh chỉnh các System Prompt trong file `src/prompts.py` (không cần đụng vào code Python logic).
  - Cấu hình Tool Definitions, danh sách intent, số người mặc định trong file `src/tools.py`.
  - **Tính năng 1:** Viết System Prompt sao cho AI trả lời các câu hỏi tiện ích bằng cách CHỈ đọc nội dung từ file `knowledge_base.txt`. (Không bịa đặt).
  - **Tính năng 2:** Implement *Tool Calling (Function Calling)* để khi truyền vào câu chat "Mai 5h đá bóng không", AI trả về file JSON: `{"sport": "bóng đá", "time": "5h chiều mai"}`.
  - Bổ sung dữ liệu giả lập vào `knowledge_base.txt` cho đủ các trường hợp.

### ⚙️ Thành viên 3: Logic Gom nhóm (Matchmaking Manager)
- **Nơi code chính:** `src/match_manager.py` và `src/bot.py` (phần UI Discord)
- **Nhiệm vụ:**
  - Xây dựng hoàn chỉnh class `MatchManager` để quản lý các trận đang mở (Thêm trận, thêm người, huỷ trận).
  - Viết code tạo tin nhắn **Embed** đẹp trên Discord để hiển thị bảng gom nhóm.
  - Viết lệnh `/join` hoặc tính năng thả react (Emoji) để người dùng có thể tham gia vào trận.
  - Khi `is_match_full()` trả về True, viết logic ping (tag) người tạo trận để chốt kèo.

### 🧪 Thành viên 4: QA, Testing & Spec
- **Nơi làm chính:** `eval/golden_set.json` và kiểm tra toàn hệ thống.
- **Nhiệm vụ:**
  - Chuẩn bị đủ 20 test case (Golden Set) trong file JSON đại diện cho 4 lớp lỗi (Xem mục §5 trong `spec.md`).
  - Đóng vai User, tương tác với Bot trên Discord để tìm ra các lỗi (Edge cases: rủ sai giờ, hỏi ngoài phạm vi).
  - Thu thập Feedback (Evidence) từ các bạn trong lớp (như đã nêu ở mục §8 trong `spec.md`).
  - Viết script Python nhỏ để tự động chạy test hoặc test thủ công và báo lỗi lại cho 3 bạn dev sửa.

---

## 4. Quy trình làm việc nhóm (Workflow)
- Nhóm nên chia nhánh trên Git (Branch) cho mỗi tính năng. Ví dụ: nhánh `feature/bot-core`, `feature/llm-integration`.
- Hàng ngày kiểm tra chéo (Code Review) trước khi merge vào nhánh chính (main).
- Về phần UX/UI (Web): Tạm thời file `UX-Ui_texting.html` chỉ để nộp deadline nên chưa cần code logic vào đó vội, hãy tập trung làm Discord Bot chạy được luồng (Logic flow) trước.

Chúc nhóm hoàn thành tốt dự án! 🚀
