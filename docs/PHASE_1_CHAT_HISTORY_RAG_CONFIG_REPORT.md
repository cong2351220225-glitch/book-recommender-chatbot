# BÁO CÁO NGHIỆM THU GIAI ĐOẠN 1 – FLUTTER WINDOWS
## QUẢN LÝ LỊCH SỬ HỘI THOẠI CHAT & CẤU HÌNH RAG GROUNDING

- **Dự án:** Xây dựng Hệ thống Thư viện số và Chatbot Gợi ý Sách Thông minh (AI Digital Library)
- **Đường dẫn dự án:** `E:\Source_Code\book-recommender-chatbot`
- **Mục tiêu:** Đồng bộ chức năng Quản lý Lịch sử Chat và Cấu hình RAG Top-K giữa Streamlit Web (`app.py`) sang Flutter Windows Native Client, lấy Web làm chuẩn nghiệp vụ.
- **Thời gian nghiệm thu:** 2026-11-03
- **Trạng thái tổng thể:** **PASS (ĐẠT NGHIỆM THU TOÀN DIỆN)**

---

## 1. DANH SÁCH FILE THAY ĐỔI & SAO LƯU

| STT | File thay đổi | File sao lưu (.bak) | Mục đích / Nội dung thực hiện |
|:---:|:---|:---|:---|
| 1 | `backend/schemas/chat_schema.py` | `backend/schemas/chat_schema.py.bak` | Bổ sung schemas: `ChatSessionItem`, `ChatSessionsResponse`, `DeleteSessionResponse`, `RagConfigResponse`. |
| 2 | `backend/routers/chat_router.py` | `backend/routers/chat_router.py.bak` | Bổ sung 3 API: `GET /sessions`, `DELETE /sessions/{session_id}`, `GET /config`. Kế thừa nghiêm ngặt User Isolation và đếm vector thật từ ChromaDB. |
| 3 | `mobile_app/lib/core/constants/api_constants.dart` | `mobile_app/lib/core/constants/api_constants.dart.bak` | Khai báo 3 endpoint hằng số: `chatSessions`, `chatSession(id)`, `chatConfig`. |
| 4 | `mobile_app/lib/models/chat_session_model.dart` | *Tạo mới* | Model phiên chat: `id`, `title`, `timestamp`, `messageCount`, `lastMessage`. |
| 5 | `mobile_app/lib/models/rag_config_model.dart` | *Tạo mới* | Model cấu hình RAG: `vectorCount`, `defaultTopK`, `maxTopK`, `minTopK`, `collectionName`. |
| 6 | `mobile_app/lib/services/api_service.dart` | `mobile_app/lib/services/api_service.dart.bak` | Thêm các hàm HTTP client: `getChatSessions()`, `deleteChatSession()`, `getRagConfig()`. |
| 7 | `mobile_app/lib/repositories/chat_repository.dart` | `mobile_app/lib/repositories/chat_repository.dart.bak` | Tích hợp Repo layer: `getSessions()`, `deleteSession()`, `getRagConfig()`. |
| 8 | `mobile_app/lib/providers/chat_provider.dart` | `mobile_app/lib/providers/chat_provider.dart.bak` | Quản lý state `topK`, `vectorCount`, `sessions`, `selectSession()`, `deleteSession()`, `loadSessions()`, `fetchRagConfig()`. Truyền dynamic `_topK` vào SSE/Non-streaming. |
| 9 | `mobile_app/lib/presentation/screens/ai_chat_screen.dart` | `mobile_app/lib/presentation/screens/ai_chat_screen.dart.bak` | Thêm Drawer Lịch sử chat (EndDrawer), Top-K badge, Nút cấu hình RAG, Hộp thoại xác nhận xóa, Hộp thoại cấu hình Top-K với Slider 1–10. |
| 10 | `tests/test_phase1_chat_history_rag_config.py` | *Tạo mới* | Bộ kiểm thử chức năng hợp đồng API Backend cho Giai đoạn 1 (3 tests). |
| 11 | `tests/test_phase1_comprehensive_verification.py` | *Tạo mới* | Bộ kiểm thử độc lập 9 kịch bản bắt buộc theo Section E (4 tests). |

---

## 2. DANH MỤC API BACKEND SỬ DỤNG

Toàn bộ API tuân thủ thiết kế RESTful chuẩn và đồng bộ định dạng lưu trữ file JSON (`data/chat_history/{username}_{session_id}.json`):

1. **`GET /api/v1/chat/sessions`**
   - **Mục đích:** Liệt kê toàn bộ phiên chat của người dùng hiện tại (sắp xếp giảm dần theo thời gian).
   - **Xác thực:** JWT Token (User Isolation: người dùng chỉ xem được các file `{username}_*.json` của chính mình).
   - **Dữ liệu trả về:** Danh sách đối tượng gồm `id`, `title`, `timestamp`, `message_count`, `last_message`.

2. **`GET /api/v1/chat/history/{session_id}`**
   - **Mục đích:** Tải lại toàn bộ nội dung tin nhắn và grounding cards (sách, địa điểm) của phiên chat.
   - **Bảo mật:** Kiểm tra `_check_session_ownership`, trả về `403 Forbidden` nếu truy cập trái phép phiên của user khác.

3. **`DELETE /api/v1/chat/sessions/{session_id}`**
   - **Mục đích:** Xóa vĩnh viễn tệp hội thoại JSON trên máy chủ.
   - **Bảo mật:** Xác minh quyền sở hữu, ngăn chặn xóa chéo tài khoản. Trả về `404 Not Found` nếu không tìm thấy file.

4. **`GET /api/v1/chat/config`**
   - **Mục đích:** Cung cấp thông số vận hành RAG Engine và số lượng vector thực tế từ ChromaDB (`rag_engine.get_library_book_count()`).
   - **Dữ liệu trả về:** `{"vector_count": 208, "default_top_k": 3, "max_top_k": 10, "min_top_k": 1, "collection_name": "books_collection"}`.

5. **`POST /api/v1/chat/message` & `POST /api/v1/chat/stream`**
   - **Cập nhật:** Tiếp nhận tham số `top_k: int` (1 đến 10) truyền trực tiếp từ client vào `handle_user_message(top_k=...)` và `ask_recommendation(top_k=...)`.

---

## 3. KIẾN TRÚC GIAO DIỆN & MÔ TẢ TRẢI NGHIỆM (UI/UX)

```
+----------------------------------------------------------------------------------------------------+
|  [🤖 Trợ Lý AI Thư Viện]   [🏷️ Top-K: 3]          [⚙️ Cấu hình RAG]  [➕ Đoạn chat mới]  [📜 Lịch sử] |
+------------------------------------------------------------------------------------+---------------+
|                                                                                    | LỊCH SỬ CHAT  |
|  [AI Trợ lý]: Xin chào! Tôi có thể giúp gì cho bạn?                                | [➕ Mới] [✕]  |
|               Hỏi đáp về 208 đầu sách, tác giả hoặc nhận gợi ý đọc sách RAG.       +---------------+
|                                                                                    | 💬 Sách AI    |
|  [User]: Gợi ý cho tôi 3 cuốn sách lập trình phần mềm?                             | 🕒 10:15 2 tin|
|                                                                                    | [🗑️ Xóa]      |
|  [AI Trợ lý]: Dưới đây là gợi ý các tác phẩm lập trình kinh điển:                  +---------------+
|               - Clean Code (Robert C. Martin)                                      | 💬 Lịch sử VN |
|               - The Pragmatic Programmer (Andrew Hunt, David Thomas)               | 🕒 09:30 4 tin|
|                                                                                    | [🗑️ Xóa]      |
|  [Cards: 2 tác phẩm grounding từ ChromaDB]                                         +---------------+
|                                                                                    |               |
+------------------------------------------------------------------------------------+               |
|  [ Nhập câu hỏi về sách, tác giả hoặc tìm nhà sách gần đây...                ] [➤] |               |
+------------------------------------------------------------------------------------+---------------+
```

### Hộp thoại Cấu hình RAG (Dialog):
- **Card thông tin ChromaDB:** Hiển thị trực quan icon Storage, nhãn: `Vector Database: 208 bản ghi ChromaDB` và Collection `books_collection`. Có nút thử lại `🔄` nếu mất kết nối backend.
- **Thanh trượt Top-K:** Slider bước nhảy 1 đơn vị từ 1 đến 10. Giá trị được ghim rõ trong badge nổi bật.
- **Giải thích ngữ cảnh:** Chú thích rõ vai trò của Top-K đối với mô hình ngôn ngữ lớn (LLM).
- **Nguyên tắc bảo vệ B.7:** Dữ liệu tạm thời (`tempTopK`) không tác động hệ thống cho đến khi người dùng bấm **"Lưu cấu hình"**. Nếu bấm **"Hủy"**, giá trị cũ được bảo toàn tuyệt đối.

### Drawer Lịch sử hội thoại:
- Thiết kế Drawer bên phải (EndDrawer, độ rộng 360dp) sang trọng, đồng bộ palette Navy & Gold.
- Mỗi phiên gồm: Tiêu đề phiên, trích đoạn tin nhắn gần nhất, thời gian cập nhật `🕒 yyyy-MM-dd HH:mm`, badge số lượng tin nhắn và icon xóa `🗑️`.
- Phiên đang hoạt động được viền vàng ánh kim và tô sáng nền (`goldLight`).
- Bấm vào phiên sẽ nạp lại toàn bộ ngữ cảnh tin nhắn trước đó qua hiệu ứng loading mượt mà.
- Bấm nút xóa mở `AlertDialog` xác nhận rõ ràng trước khi thực hiện xóa vĩnh viễn trên ổ đĩa.

---

## 4. BẢNG KẾT QUẢ KIỂM THỬ BẮT BUỘC (MỤC E)

| Bài test | Kịch bản kiểm thử | Hành vi & Kết quả thực tế | Trạng thái |
|:---:|:---|:---|:---:|
| **TC-01** | Tạo hai phiên chat khác nhau (`sess_1`, `sess_2`). | Backend tạo riêng 2 tệp `{user}_{sess_1}.json` và `{user}_{sess_2}.json` trong `data/chat_history`. | **PASS** |
| **TC-02** | Gửi nội dung khác nhau trong mỗi phiên (Phiên 1: Lập trình; Phiên 2: Tâm lý học). | Nội dung được ghi chính xác vào từng tệp tương ứng. Không có sự ghi đè chéo. | **PASS** |
| **TC-03** | Chuyển đổi qua lại và xác nhận lịch sử không bị trộn. | Gọi `GET /history/{sess_1}` chỉ trả về tin nhắn lập trình; `GET /history/{sess_2}` chỉ trả về tâm lý học. Chuyển đổi trên UI Flutter nạp đúng danh sách tin nhắn. | **PASS** |
| **TC-04** | Thoát và đăng nhập lại, xác nhận lịch sử vẫn tồn tại. | Cấp JWT Token mới cho cùng tài khoản, gọi `GET /sessions`: Toàn bộ các phiên cũ hiển thị đầy đủ, không bị thất lạc. | **PASS** |
| **TC-05** | Xóa một phiên và xác nhận phiên còn lại không bị ảnh hưởng. | Xóa `sess_1` thành công (file bị xóa khỏi ổ đĩa). `sess_2` vẫn tồn tại nguyên vẹn, đọc tin nhắn bình thường. UI cập nhật ngay lập tức. | **PASS** |
| **TC-06** | Thử Top-K = 1, 5 và 10. | Slider hỗ trợ đầy đủ dải giá trị [1..10]. Thử nghiệm thành công với các giá trị biên 1, 5, 10. Các giá trị ngoài dải (0, 11) bị FastAPI Pydantic chặn với mã HTTP 422. | **PASS** |
| **TC-07** | Xác nhận giá trị Top-K thực sự được Backend sử dụng. | Kiểm tra unit test mock và log Backend: giá trị `top_k` từ request được chuyển trực tiếp vào `handle_user_message(..., top_k=...)` và hàm truy xuất ChromaDB. | **PASS** |
| **TC-08** | Đối chiếu số vector hiển thị với ChromaDB. | Gọi `rag_engine.get_library_book_count()` trả về `208`. Endpoint `GET /config` trả về đúng `208`. Giao diện Flutter hiển thị chính xác `208 bản ghi ChromaDB`. | **PASS** |
| **TC-09** | Thử khi Backend tắt và bật lại để kiểm tra xử lý lỗi. | Khi tắt Backend hoặc ngắt kết nối ChromaDB, dialog hiển thị cảnh báo lỗi màu đỏ kèm nút "Thử lại", không gây crash ứng dụng Flutter. Khi bật lại, dữ liệu tự phục hồi. | **PASS** |

---

## 5. KẾT QUẢ KIỂM THỬ TỰ ĐỘNG & BIÊN DỊCH NATIVE

1. **Bộ kiểm thử tự động Backend (Pytest):**
   - **`239 / 239 tests PASS (100%)`** qua 21 test suites.
   - Thời gian chạy: 267.54s (~4 phút 27 giây).
   - Bao gồm toàn bộ test regression cũ và 2 test suites mới của Giai đoạn 1 (`test_phase1_chat_history_rag_config.py` và `test_phase1_comprehensive_verification.py`).

2. **Phân tích tĩnh Flutter (`flutter analyze`):**
   - **`0 errors`** (Chỉ còn 80 cảnh báo deprecation member và style linter kế thừa từ trước).

3. **Biên dịch Flutter Windows Native Debug:**
   - Lệnh: `flutter build windows --debug`
   - Kết quả: **`Exit code 0 - Build thành công`**
   - Đường dẫn binary: `mobile_app\build\windows\x64\runner\Debug\ai_digital_library.exe`.
   - Tiến trình thực tế khởi chạy thành công trên Windows: Process ID `18348`, trạng thái `Responding: True`.

---

## 6. HẠN CHẾ CÒN TỒN TẠI & HƯỚNG PHÁT TRIỂN TIẾP THEO

- **Chỉnh sửa tiêu đề phiên chat (Rename session):** Hiện tại tiêu đề phiên chat được tự động trích xuất từ 30 ký tự đầu của câu hỏi đầu tiên (theo chuẩn hiện tại của `app.py`). Trong tương lai có thể bổ sung nút chỉnh sửa tiêu đề thủ công theo ý người dùng.
- **Tìm kiếm trong lịch sử chat:** Hiện tại danh sách phiên chat hỗ trợ cuộn và hiển thị theo thứ tự thời gian mới nhất. Khi người dùng tích lũy hàng trăm phiên, có thể bổ sung thêm ô tìm kiếm nhanh tiêu đề phiên trên Drawer.
- **Tiền đề cho Giai đoạn 2:** Nền tảng Chat Provider và RAG Config đã chuẩn hóa, sẵn sàng kết nối tiếp tục với Giai đoạn 2 (Thanh tìm kiếm toàn cục & Bộ lọc sách nâng cao theo Năm, Đánh giá, Thể loại).

---

## 7. KẾT LUẬN

Giai đoạn 1 đã hoàn thành **100% mục tiêu** đề ra:
- Quản lý lịch sử hội thoại chuẩn xác, bảo mật phân quyền theo tài khoản (User Isolation).
- Cấu hình tham số Top-K linh hoạt từ 1 đến 10, hiển thị chính xác 208 vector ChromaDB thực tế.
- Đạt chuẩn toàn diện về kiểm thử tự động, biên dịch native và trải nghiệm người dùng thực tế trên Windows.

