# AI SPEC — VinUni Discord AI Assistant · Nhóm LowTech Nhất  · Zone [Điền Zone]
Hướng: [ ] A — VLearn  [x] B — Trợ lý Học viên  [ ] C — Làn mở
Loại: [ ] Tối ưu tính năng có sẵn  [x] Tính năng mới

## §1. User & Job
- **Job executor + workflow:** Học viên đang tham gia chương trình AI thực chiến ngắn hạn tại VinUni. (Workflow: Lên Discord khoá học -> Tìm kênh hỏi đáp/thể thao -> Đăng câu hỏi/nhu cầu -> Đợi phản hồi/người tham gia -> Chốt thông tin).
- **Core JTBD:** Tra cứu thông tin tiện ích nội bộ (thư viện, căn tin) và kết nối để sinh hoạt thể thao (đá bóng) một cách nhanh chóng.
- **Problem statement:** Học viên thiếu thông tin tiện ích nội bộ và khó kết nối để sinh hoạt thể thao do chưa quen biết nhau; tốn thời gian tự mày mò, khó gom đủ nhóm, dẫn đến trải nghiệm học tập và sinh hoạt kém tích cực.
- **Evidence:**
  - **Số liệu mining / kết quả khảo sát:** (Dữ liệu giả định dựa trên bối cảnh) Khảo sát 30 học viên, 90% cho biết gặp khó khăn khi tìm kiếm thông tin tiện ích trong tuần đầu; 67% gặp khó khăn khi tìm người cùng tham gia các hoạt động thể thao (đá bóng, cầu lông, v.v.) tại VinUni.
  - **≥5 quote/ví dụ nguyên văn + nguồn:**
    1. *"Cho mình hỏi căn tin có lò vi sóng không mọi người ơi?"* (Discord - Kênh chung)
    2. *"Chiều nay 5h có ai đá bóng sân nội khu không, sân nội khu có được chơi không!"* (Facebook Group) - *[Kết quả: không đạt kết quả đúng mong muốn]*
    3. *"Thẻ từ của mình quẹt không vào được thư viện, phải liên hệ ai vậy?"* (Discord - Kênh hỏi đáp)
    4. *"Sinh hoạt bóng đá trên VIN như nào vậy anh em?"* (Facebook - Kênh thể thao)
    5. *"Cho mình xin giờ mở cửa của thư viện với, tìm trên web không thấy."* (Discord - Kênh chung)

## §2. Impact & quyết định chọn
- **Bảng impact ≥3 ứng viên:**
  | Ứng viên | Bao nhiêu người gặp | Tần suất | Mỗi lần tốn gì | Build nổi không | Chọn? |
  |---|---|---|---|---|---|
  | 1. Trợ lý Discord hỏi đáp & gom nhóm | Phần trăm lớn trong 1000 hv | 2-3 lần/tuần | Giải đáp thông tin ngay lập túc, 15-30 phút chờ gom đội | Có (Dùng Python + Discord.py) | **Chọn** |
  | 2. Web App riêng quản lý tiện ích & lịch | ~50 | 2-3 lần/tuần | Cần cài đặt app/nhớ link | Rủi ro trễ tiến độ | Loại |
  | 3. Hệ thống Email thông báo tự động | ~50 | 1 lần/ngày | Bị spam, không realtime | Có | Loại |
- **Ứng viên ĐÃ LOẠI + vì sao:** 
  - Ứng viên 2 bị loại vì chi phí build UI/UX cao, học viên lười sang một nền tảng mới ngoài Discord họ đang dùng. 
  - Ứng viên 3 bị loại vì email không mang tính tương tác (realtime), không giải quyết được bài toán gom nhóm đá bóng..
- **Ứng viên CHỌN + vì sao:** 
  - Ứng viên 1 được chọn vì học viên đã có sẵn thói quen dùng Discord. Tần suất gặp vấn đề cao, việc tích hợp bot trực tiếp giúp giảm cost chuyển đổi nền tảng và dễ dàng gọi tool AI (matchmaking).

## §3. Giải pháp tương tự đã nghiên cứu
- **[Discord MEE6 / Carl Bot]:** 
  - Flow: Dùng lệnh `/` để set role, gửi tin nhắn chào mừng hoặc tự động trả lời theo keyword cứng.
  - Đáng học: Tốc độ phản hồi cực nhanh, ổn định.
  - Đáng né: Phải nhớ cú pháp lệnh chính xác, không hiểu được ngôn ngữ tự nhiên.
  - Mình khác gì: Bot của nhóm dùng LLM để hiểu intent (ý định) tự nhiên, không cần gõ đúng cú pháp `/`, tự phân loại hỏi đáp tiện ích hay gom nhóm thể thao.
- **[Telegram Matchmaking Bot (vd: Werewolf bot)]:**
  - Flow: Gọi bot vào group, bot tạo tin nhắn có các nút (buttons) để người dùng bấm tham gia. Đủ người thì bot tag tên.
  - Đáng học: Flow tương tác qua reaction/button rất trực quan.
  - Đáng né: Bot spam tin nhắn quá nhiều mỗi khi có người join.
  - Mình khác gì: Mình gom vào 1 message (poll/event) cập nhật trạng thái liên tục để tránh loãng kênh.

## §4. Thiết kế
- **Lát cắt MỘT CÂU:** Khi học viên nhắn câu hỏi/nhu cầu vào Discord, AI sẽ truy xuất tài liệu trả lời, đồng thời cung cấp các lệnh để người dùng tự mở trận, xem trận đang mở và join; AI sẽ theo dõi và nhắc người mở trận chốt kèo khi đủ điều kiện.
- **Non-goals (≥3 thứ KHÔNG build):**
  1. Không quản lý/book sân bãi thực tế (việc book sân vật lý nằm ngoài phạm vi).
  2. Không tích hợp thanh toán tiền sân.
  3. Không trả lời/giải bài tập liên quan đến nội dung học thuật (chỉ tập trung tiện ích/thể thao).
- **Mức prototype nhắm tới:** [x] Mock
  - Phần thật: Luồng Discord bot nhận tin nhắn, gọi LLM API (Gemini/OpenAI) để phân loại ý định (Tool Calling) và sinh câu trả lời.
  - Phần mock: Dữ liệu tiện ích (tạo 1 file `.txt` hoặc JSON nhỏ làm Knowledge Base giả định thay vì cào web trường).
- **Automation:** [x] Augment / Conditional 
  - Lý do: Với tiện ích, AI tự làm khi chắc chắn và hỏi lại (Conditional) nếu thiếu thông tin. Với gom nhóm, AI đóng vai trò hỗ trợ (Augment): người dùng chủ động gõ lệnh mở trận/join, AI chỉ theo dõi và gửi thông báo nhắc người mở trận khi đủ điều kiện chốt, giúp người dùng hoàn toàn nắm quyền kiểm soát.
- **§4b. Nguyên tắc đã áp dụng (≥4 — HAX/PAIR):**
  | Nguyên tắc | Áp cụ thể vào đâu trong prototype |
  |---|---|
  | **G1 - Làm rõ hệ thống làm được gì** | Bot có tin nhắn chào mừng khi add vào server: "Mình hỗ trợ thông tin tiện ích campus và gom nhóm thể thao." |
  | **G2 - Làm rõ nó làm tốt đến đâu** | Khi trả lời tiện ích, luôn đính kèm nguồn giả định: "(Theo cẩm nang học viên trang 5)". |
  | **G10 - Thu hẹp phạm vi khi nghi ngờ** | Khi rủ đá bóng thiếu thông tin, bot hỏi lại: "Bạn muốn đá lúc mấy giờ và sân nào để mình lên lịch?" |
  | **G8 - Gạt bỏ dễ dàng / Cấp quyền kiểm soát** | Người dùng muốn mở trận có thể gõ lệnh cụ thể, mọi người có thể gõ lệnh xem và join vào các trận đang mở. AI không tự chốt mà chỉ nhắc/thông báo đến người mở trận khi đủ điều kiện để họ tự quyết định. |

## §5. Kiểu lỗi — 4 lớp chỗ khó + kịch bản (≥8)
| Tình huống cụ thể | Lớp | Hành vi mong muốn (nói gì, hiện gì, cho user làm gì tiếp) | Nguyên tắc áp (G../PAIR) |
|---|---|---|---|
| 1. Hỏi mật khẩu wifi (không có trong tài liệu) | ① Nguồn sự thật | Xin lỗi, nói rõ không có thông tin này trong cẩm nang và hướng dẫn hỏi TA. | G2, G10 |
| 2. AI bịa ra giờ mở cửa thư viện (Hallucination) | ① Nguồn sự thật | Luôn force AI trích dẫn nguồn ở cuối câu, nếu không có nguồn hệ thống sẽ chặn không gửi. | G2 |
| 3. Rủ "mai đá bóng không?" | ② Mơ hồ | Hỏi lại: "Mai là ngày [X], bạn muốn đá giờ nào và tại sân nào?" | G10 |
| 4. Viết sai chính tả quá nhiều "cng tin co lo v song k?" | ② Mơ hồ | AI cố gắng đoán, nếu độ tự tin thấp thì xin người dùng gõ lại rõ hơn. | G10 |
| 5. Yêu cầu "Giải giúp bài tập Python số 3" | ③ Ngoài phạm vi | Từ chối khéo léo: "Mình chỉ hỗ trợ tiện ích và thể thao, bạn hãy hỏi Mentor nhé." | G1 |
| 6. Đòi bot ban (xoá) tài khoản của học viên khác | ③ Ngoài phạm vi | Từ chối thực hiện lệnh, báo thiếu quyền. | G1 |
| 7. Người dùng tạo trận bị sai giờ (15h thay vì 5h chiều) | ④ Đặc thù | Cho phép người dùng gõ lệnh để huỷ/sửa thông tin trận ngay lập tức. | G8, G9 |
| 8. Đã đủ người nhưng có người huỷ phút chót | ④ Đặc thù | Bot thông báo "Thiếu lại 1 slot, ai vào thay không?" để duy trì kèo. | G12 |

## §6. Bốn đường đi của trải nghiệm
- **Happy path:** User hỏi giờ ăn căn tin -> AI đáp ngay lập tức kèm trích dẫn. User rủ đá bóng đầy đủ giờ giấc -> AI tạo poll Event ngay.
- **Low-confidence (②):** User nói "chiều đá bóng" -> AI phản hồi "Bạn muốn đá lúc mấy giờ để mình tạo kèo?".
- **Failure/không căn cứ (①):** User hỏi lịch xe bus (không có data) -> AI trả lời "Mình chưa được cập nhật lịch xe bus, bạn vui lòng hỏi trên nhóm chung nhé."
- **Correction (user sửa):** User chốt kèo 5h chiều, sau đó nhắn lại "đổi sang 6h đi" -> AI cập nhật lại thời gian của event đã tạo.
- **Khi bị đòi ngoài phạm vi (③):** Đòi giải bài tập -> Từ chối khéo léo.
- **Case đặc thù domain (④):** Quá thời gian đá bóng mà không đủ người -> Bot tự động thông báo "Kèo không đủ người, tự động huỷ bỏ".

## §7. Kiểm thử
- **Chiều chất lượng + định nghĩa kiểm chứng được:**
  - **Chính xác thông tin (Tiện ích):** Pass khi câu trả lời nằm hoàn toàn trong Knowledge Base mock. Fail nếu có chi tiết ngoài lề (Hallucination).
  - **Tool Calling (Thể thao):** Pass khi LLM trích xuất đúng `activity`, `time`, `location` từ tin nhắn và gọi hàm tạo event thành công.
- **Golden set:** (Cần tạo file trong thư mục `eval/` chứa ít nhất 20 case test bao gồm hỏi đáp đúng, hỏi ngoài luồng, hỏi thiếu thông tin, gõ sai chính tả).
- **Quality bar:** Đạt khi ≥ 85% qua bộ test case và 0% bịa đặt thông tin (Hallucination = 0).
- **Kết quả các lượt chạy:** 
  | Lượt | Số lượng test | Pass | Fail | Ghi chú |
  |---|---|---|---|---|
  | Lần 1 | 20 | ... | ... | (Cập nhật sau khi test) |

## §8. Phân công & kế hoạch
- **Phân công có tên:**
  - **Tuyền:** Build hệ thống (Code Discord Bot), Tích hợp Tool Calling, Demo.
  - **Tiến Dũng:** Chuẩn bị Evidence, xây dựng Prompt (System Message), viết Spec, chuẩn bị bộ test Golden Set.
- **Willing users + kế hoạch vòng validation CP5:**
  - Danh sách dự kiến: 3 bạn trong khóa AI (Sẽ điền tên thật sau).
  - Ai log: Tiến Dũng sẽ quan sát và log lại quá trình người dùng thử nghiệm tương tác với Bot trên kênh Discord test.
- **Multi-prototype:**
  - **Phương án 1:** Bot chỉ trả lời khi bị tag tên (`@bot`).
  - **Phương án 2:** Bot đọc mọi tin nhắn trong kênh cụ thể (VD: `#the-thao`), nếu thấy ý định rủ rê sẽ tự động nhảy vào.
  - **Lý do chọn:** Thử nghiệm phương án 2 xem user có thấy phiền không, nếu phiền sẽ lùi về phương án 1 để giữ G17 (Kiểm soát).

## §9. Changelog
| Thời điểm | Đổi gì | Vì sao (trỏ về feedback/case nào) |
|---|---|---|
| (Ngày/Giờ) | Khởi tạo Spec | Hoàn thành CP1 |
| ... | ... | ... |
