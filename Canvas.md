# VinUni Discord AI Assistant - Hackathon MVP 🚀

## 📖 Giới thiệu (Introduction)
Dự án MVP này là một Trợ lý AI tích hợp trên nền tảng Discord, được thiết kế đặc biệt dành cho các học viên tham gia chương trình AI thực chiến ngắn hạn tại VinUni. 
Mục tiêu của dự án là giúp học viên mới dễ dàng làm quen với môi trường xung quanh, tra cứu thông tin tiện ích nội khu (căn tin, thư viện, cách dùng thẻ) và đặc biệt là hỗ trợ kết nối, tạo nhóm sinh hoạt thể thao (như thiết lập các trận đá bóng) một cách tự động và nhanh chóng.

## 🎯 Tờ Canvas 7 Dòng (7-line Canvas)
1. **Chiến tuyến:** Nền tảng Discord.
2. **Người dùng mục tiêu:** Học viên đang tham gia chương trình AI thực chiến ngắn hạn tại VinUni.
3. **Vấn đề:** Học viên thiếu thông tin tiện ích nội bộ và khó kết nối để sinh hoạt thể thao (đá bóng) do chưa quen biết nhau. Hậu quả là tốn thời gian tự mày mò, khó gom đủ nhóm, dẫn đến trải nghiệm học tập và sinh hoạt kém tích cực.
4. **Bằng chứng:** Nhiều bài đăng trên Facebook tìm đồng đội đá bóng hay hỏi đáp tiện ích bị trôi, không chốt được lịch; các câu hỏi lặp lại trên nhóm không được phản hồi tức thì.
5. **Giải pháp cốt lõi:** Một học viên nhắn câu hỏi hoặc nhu cầu vào Discord, AI sẽ truy xuất tài liệu để trả lời ngay, hoặc tự động gọi tool để tạo thông báo gom nhóm và chốt lịch.
6. **Phạm vi của AI:** AI tự trả lời khi tìm được căn cứ, tự động gọi tool tạo lệnh gom nhóm, và chủ động hỏi lại để xác minh khi thiếu dữ liệu (tránh bịa đặt thông tin làm học viên vi phạm nội quy).
7. **Thử nghiệm & Phân công:** 
   - Cộng đồng học viên AI thực chiến sẽ là người dùng thử.
   - **Tuyền:** Build hệ thống & tích hợp Discord bằng Python.
   - **Tiến Dũng:** Xây dựng Prompt & Spec.

## ⚙️ Tính năng chính (Key Features)
- **Hỏi đáp thông tin (Campus Q&A):** AI giải đáp nhanh các thắc mắc thường gặp (ví dụ: căn tin có lò vi sóng không, thư viện ở đâu, cách quẹt thẻ).
- **Matchmaking & Lên lịch (Auto Setup):** Nhận diện nhu cầu (ví dụ: "mình muốn đá bóng chiều nay"), AI gọi tool tự động tạo poll/event trên Discord để gom người và chốt giờ.

## 🛠️ Công nghệ sử dụng (Tech Stack)
- **Ngôn ngữ:** Python (Phù hợp để thao tác với các tool AI).
- **Nền tảng giao tiếp:** Discord API (`discord.py`).
- **Lõi AI:** LLM có hỗ trợ Function Calling / Tool Calling để kích hoạt lệnh.

## 🚀 Hướng dẫn cài đặt & Khởi chạy
1. Clone repository về máy tính nội bộ.
2. Cài đặt các thư viện phụ thuộc: 
   ```bash
   pip install -r requirements.txt
   ```
3. Tạo file `.env` và cung cấp các khóa API cần thiết:
   ```env
   DISCORD_BOT_TOKEN=your_discord_token_here
   LLM_API_KEY=your_llm_api_key_here
   ```
4. Khởi chạy Bot:
   ```bash
   python bot.py
   ```