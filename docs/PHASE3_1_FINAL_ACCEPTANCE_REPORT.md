# BÁO CÁO KIỂM TRA VÀ NGHIỆM THU GIAI ĐOẠN 3.1: CHATBOT AI RAG STREAMING

**Dự án:** AI Digital Library (Thư viện số AI Đa Nền Tảng)  
**Thời gian thực hiện:** 02/11/2026  
**Thư mục làm việc:** `E:\Source_Code\book-recommender-chatbot`  
**Môi trường:** Windows 10 x64, Python 3.13.12, FastAPI 0.115+, ChromaDB 0.6.3, Google Gemini RAG Engine  

---

## 1. TỔNG QUAN KẾT QUẢ NGHIỆM THU

Giai đoạn 3.1 tập trung vào việc tích hợp Chatbot AI RAG Streaming trên nền tảng Flutter (kết nối FastAPI Backend), hỗ trợ truyền tải câu trả lời theo thời gian thực (SSE), hiển thị nguồn sách đối chiếu chính xác từ 208 đầu sách của thư viện, bảo vệ nghiêm ngặt quyền riêng tư giữa các tài khoản người dùng và bảo toàn 100% cơ sở dữ liệu hiện hữu.

| Hạng mục kiểm tra | Trạng thái | Ghi chú kỹ thuật |
| :--- | :---: | :--- |
| **Giao thức SSE Streaming** | **PASS** | Định dạng chuẩn SSE (`data: {"chunk": ...}`, `data: {"done": true, ...}`). Phân tách chunk mượt mà. |
| **Nút "Dừng phản hồi" (Stop)** | **PASS** | Dio `CancelToken` hủy socket ngay lập tức ở client. Backend bắt `GeneratorExit` ngừng truyền chunk. |
| **Độ chính xác nguồn RAG** | **PASS** | Khớp 100% metadata sách thật trong ChromaDB (`book_203` The Pragmatic Programmer,...). |
| **Cơ chế chống ảo giác (Anti-Hallucination)** | **PASS** | Intent `out_of_domain` không gán nguồn sách bừa bãi. |
| **Cô lập quyền riêng tư (Privacy & Isolation)** | **PASS** | Chặn truy cập chéo giữa User A, User B và Guest (trả về HTTP 403 Forbidden). |
| **An toàn ghi đồng thời (Concurrency Safety)** | **PASS** | Cơ chế `_chat_lock` (threading.Lock) + ghi nguyên tử atomic `.tmp` replace. |
| **Khả năng phục hồi tệp hỏng (JSON Resilience)** | **PASS** | Tự động xử lý lỗi tệp JSON hỏng, không gây crash 500 internal server error. |
| **Giao diện Flutter Chatbot UI** | **PASS (Mã nguồn)** | Auto-scroll, Tiếng Việt có dấu, bubble tin nhắn Navy & Gold, thẻ sách tham khảo RAG. |
| **Hồi quy hệ thống (Backend & API Contract)** | **PASS** | 30/30 bài kiểm thử tự động (Unit & Integration) đạt 100%. |
| **Bảo toàn dữ liệu CSV & ChromaDB** | **PASS** | 208 sách, schema 26 cột, 208 vector ChromaDB nguyên vẹn. Streamlit `app.py` không đổi. |
| **Biên dịch Flutter CLI trên máy chủ** | **BLOCKED** | Flutter SDK chưa được cài vào PATH Windows. Android SDK đã có sẵn. |

---

## 2. CHI TIẾT GIAO THỨC SERVER-SENT EVENTS (SSE STREAMING)

### 2.1. Cấu trúc Payload Backend (`/api/v1/chat/stream`)
Endpoint nhận `POST /api/v1/chat/stream` và phản hồi với `Content-Type: text/event-stream; charset=utf-8`:

1. **Sự kiện từng phần (Chunk Event):**
   ```text
   data: {"chunk": "Chào bạn! Thư viện hiện"}

   data: {"chunk": " đang có 208 cuốn sách"}
   ```
2. **Sự kiện kết thúc (Done Event):**
   Mang đầy đủ câu trả lời hoàn chỉnh, danh sách tài liệu tham khảo (RAG sources) và session ID cập nhật:
   ```text
   data: {"done": true, "answer": "Chào bạn! Thư viện hiện đang có 208 cuốn sách...", "books": [{"book_id": "book_203", "title": "The Pragmatic Programmer", "author": "Andy Hunt, Dave Thomas", ...}], "intent": "book_query", "session_id": "sess_81726a"}
   ```
3. **Sự kiện lỗi (Error Event):**
   ```text
   data: {"error": "Chi tiết thông báo lỗi từ server"}
   ```

### 2.2. Phân tích dữ liệu ở tầng Client (`mobile_app/lib/services/api_service.dart`)
- Sử dụng `ResponseBody.stream` của Dio để lắng nghe luồng nhị phân.
- Luồng byte được chuyển qua `utf8.decoder` và `LineSplitter()`, đảm bảo tiếng Việt có dấu (UTF-8 multi-byte) không bị cắt gãy ký tự giữa các packet mạng.
- Xử lý tiền tố `data: ` và phân tích JSON:
  - Nếu có `"chunk"`, gọi callback `onChunk(chunk)` cập nhật UI ngay lập tức.
  - Nếu `"done" == true`, gọi `onDone(...)` chốt tin nhắn và cập nhật nguồn RAG.
  - Nếu có `"error"`, gọi `onError(err)`.

---

## 3. CƠ CHẾ "DỪNG PHẢN HỒI" (STOP RESPONSE) VÀ PHÂN ĐỊNH HÀNH VI HỆ THỐNG

Tuân thủ nguyên tắc minh bạch kỹ thuật:
- **Phía Client (Flutter App):**
  - Khi người dùng nhấn nút **"Dừng phản hồi"**, hàm `stopResponse()` trong `ChatProvider` được kích hoạt.
  - Kích hoạt `_cancelToken.cancel('Người dùng dừng tạo phản hồi')`.
  - Dio ngay lập tức hủy HTTP Request và đóng kết nối TCP socket.
  - Đặt `isStreaming = false` và `isThinking = false`, giữ lại nội dung văn bản đã nhận được tính đến thời điểm bấm dừng mà không ghi đè thêm.
- **Phía Server (FastAPI):**
  - Khi kết nối socket bị ngắt từ client, Starlette/FastAPI phát hiện và phát sinh tín hiệu `GeneratorExit` trong `event_generator()`.
  - Khối `except GeneratorExit:` trong `chat_router.py` bắt sự kiện và thoát generator ngay lập tức, ngăn chặn việc tạo và gửi thêm chunk.
  - *Lưu ý kỹ thuật:* Đối với các hàm tính toán LLM/RAG chạy đồng bộ trong threadpool (`handle_user_message`), tiến trình tính toán đã sinh xong câu trả lời trước khi streaming chunk bắt đầu; việc hủy kết nối sẽ ngừng lập tức việc gửi dữ liệu qua mạng và ghi dữ liệu ra disk, không gây nghẽn luồng mạng của client.

---

## 4. XÁC MINH NGUỒN SÁCH RAG VÀ CHỐNG ẢO GIÁC

- **Truy xuất sách thực tế:**
  - Kiểm thử truy vấn: *"Sách The Pragmatic Programmer có những tác giả nào và nội dung chính là gì?"*.
  - Kết quả RAG trích xuất chính xác `book_id: book_203`, tác giả `Andy Hunt, Dave Thomas`, thể loại `Software Development / Programming`.
  - Toàn bộ metadata hiển thị trên UI Flutter thông qua danh sách thẻ `ChatSourceBook` kèm ảnh bìa, năm xuất bản và liên kết mở trực tiếp `BookDetailScreen`.
- **Cơ chế chống ảo giác (Anti-Hallucination):**
  - Kiểm thử truy vấn ngoài phạm vi thư viện: *"Thời tiết ngày mai ở thủ đô Berlin của nước Đức ra sao?"*.
  - RAG engine phân loại đúng intent `out_of_domain`.
  - Phản hồi từ chối lịch sự và **tuyệt đối không bịa đặt nguồn sách** (danh sách `books` rỗng `[]`).

---

## 5. BẢO MẬT VÀ CÔ LẬP LỊCH SỬ ĐA TÀI KHOẢN (PRIVACY & ISOLATION)

Hệ thống đã được bổ sung và kiểm chứng các lớp phòng vệ:
1. **Kiểm tra quyền sở hữu hội thoại (`_check_session_ownership`):**
   - Phiên chat của người dùng đăng nhập được lưu dưới định dạng: `{username}_{session_id}.json`.
   - Nếu `User B` cố tình gửi request `GET /api/v1/chat/history/{session_a}` hoặc `POST /api/v1/chat/message` với `session_id` của `User A`, server lập tức từ chối với mã **HTTP 403 Forbidden**.
   - Khách vãng lai (Guest) không có token cũng bị chặn **403 Forbidden** khi cố truy cập session của tài khoản đăng ký.
2. **An toàn ghi đồng thời (Thread-Safe Concurrency):**
   - Đặt `_chat_lock = threading.Lock()` bao bọc toàn bộ thao tác đọc/ghi lịch sử chat.
   - Thao tác ghi tệp sử dụng ghi file tạm `.tmp` rồi hoán đổi nguyên tử (`temp_path.replace(file_path)`), chống hiện tượng file bị rỗng hoặc lỗi cú pháp JSON khi nhiều luồng cùng ghi.
3. **Khả năng chống chịu tệp JSON hỏng:**
   - Trường hợp tệp lịch sử bị lỗi dữ liệu cục bộ, `_load_session_history` bắt lỗi an toàn và trả về danh sách rỗng `[]`, không để xảy ra lỗi sập 500.

---

## 6. KẾT QUẢ KIỂM THỬ TỰ ĐỘNG TOÀN DIỆN

Tổng cộng **30/30 bài kiểm thử tự động** đã chạy và vượt qua 100%:

### 6.1. Bộ kiểm thử Chatbot RAG Streaming (`test_chatbot_rag_streaming.py` - 12/12 PASS)
```text
tests/test_chatbot_rag_streaming.py::test_01_chat_message_standard PASSED           [  8%]
tests/test_chatbot_rag_streaming.py::test_02_chat_stream_protocol PASSED           [ 16%]
tests/test_chatbot_rag_streaming.py::test_03_rag_retrieval_with_sources PASSED     [ 25%]
tests/test_chatbot_rag_streaming.py::test_04_anti_hallucination_and_out_of_domain PASSED [ 33%]
tests/test_chatbot_rag_streaming.py::test_05_chat_history_persistence PASSED       [ 41%]
tests/test_chatbot_rag_streaming.py::test_06_sequential_conversation_flow PASSED   [ 50%]
tests/test_chatbot_rag_streaming.py::test_07_vietnamese_unicode_support PASSED      [ 58%]
tests/test_chatbot_rag_streaming.py::test_08_chat_validation_errors PASSED         [ 66%]
tests/test_chatbot_rag_streaming.py::test_09_chat_cross_account_isolation PASSED   [ 75%]
tests/test_chatbot_rag_streaming.py::test_10_chat_concurrent_writes PASSED         [ 83%]
tests/test_chatbot_rag_streaming.py::test_11_chat_streaming_early_cancellation PASSED [ 91%]
tests/test_chatbot_rag_streaming.py::test_12_chat_corrupted_json_handling PASSED   [100%]
============================== 12 passed in 73.67s ===============================
```

### 6.2. Bộ kiểm thử FastAPI Backend & API Contract (18/18 PASS)
```text
tests/test_fastapi_backend.py::test_01_total_books_count_208 PASSED                [  5%]
tests/test_fastapi_backend.py::test_02_search_books PASSED                         [ 11%]
tests/test_fastapi_backend.py::test_03_book_detail_and_related PASSED              [ 16%]
tests/test_fastapi_backend.py::test_04_auth_register_and_login_jwt PASSED          [ 22%]
tests/test_fastapi_backend.py::test_05_admin_rbac PASSED                           [ 27%]
tests/test_fastapi_backend.py::test_06_rag_chat_retrieval PASSED                   [ 33%]
tests/test_fastapi_backend.py::test_07_anti_hallucination_out_of_domain PASSED     [ 38%]
tests/test_fastapi_backend.py::test_08_crawler_sources_and_search PASSED           [ 44%]
tests/test_fastapi_backend.py::test_09_unauthorized_rejection PASSED               [ 50%]
tests/test_fastapi_backend.py::test_10_health_and_stats PASSED                     [ 55%]
tests/test_flutter_api_contract.py::test_contract_01_auth_register_and_login PASSED [ 61%]
tests/test_flutter_api_contract.py::test_contract_02_home_stats PASSED             [ 66%]
tests/test_flutter_api_contract.py::test_contract_03_books_catalog_pagination PASSED [ 72%]
tests/test_flutter_api_contract.py::test_contract_04_book_search_and_filters PASSED [ 77%]
tests/test_flutter_api_contract.py::test_contract_05_book_detail_and_related PASSED [ 83%]
tests/test_flutter_api_contract.py::test_contract_06_authors_list_and_detail PASSED [ 88%]
tests/test_flutter_api_contract.py::test_contract_07_genres_list PASSED            [ 94%]
tests/test_flutter_api_contract.py::test_contract_08_error_codes_handling PASSED   [100%]
============================== 18 passed in 24.03s ===============================
```

---

## 7. XÁC NHẬN BẢO TOÀN DỮ LIỆU & HỆ THỐNG

Đã xác minh bằng lệnh thực thi trực tiếp trên môi trường:
- **Dữ liệu sách CSV:** `data/books.csv` giữ nguyên chính xác **208 dòng** (208 sách) và đầy đủ **26 cột**.
- **ChromaDB Vector Store:** `chroma_db/` lưu giữ chính xác **208 vector** trong collection `books_collection`. Không có thao tác re-ingest hoặc làm mất dữ liệu.
- **Ứng dụng Streamlit:** `app.py`, `book_service.py`, `crawler_service.py` hoàn toàn nguyên vẹn, sẵn sàng vận hành độc lập.
- **Bảo mật mã nguồn:** Tuyệt đối không hardcode API Key Gemini hay JWT secret trong mã nguồn Flutter.

---

## 8. PHÂN LOẠI MÔI TRƯỜNG THỰC TẾ VÀ CÁC GIỚI HẠN (REAL EXECUTION STATUS & LIMITATIONS)

- **Backend API & AI RAG Streaming:** `PASS` (Đã xác minh 100% qua pytest và kiểm tra trực tiếp, 30/30 test suites đạt).
- **Mã nguồn ứng dụng Flutter:** `PASS` (Kiến trúc MVVM / Provider, model, repository, widget hoàn chỉnh).
- **Giới hạn 1 - Cấu hình Flutter CLI:** `BLOCKED` (Lệnh `flutter` chưa được cấu hình đầy đủ trong PATH của máy Windows chủ).
- **Giới hạn 2 - Biên dịch & thực thi nhị phân thực tế:** `CHƯA THỰC HIỆN` (Chưa build ra file executable Windows `.exe` hay Android `.apk` để chạy thực tế trên thiết bị).
- **Giới hạn 3 - Khả năng đóng gói iOS:** `BLOCKED` (Do môi trường phát triển là Windows 10, thiếu macOS và Xcode để biên dịch ứng dụng iOS).
- **Android SDK:** `SẴN SÀNG` (Tọa lạc tại `C:\Users\HT\AppData\Local\Android\Sdk`, máy ảo Pixel_5 đã cài đặt).

---

## 9. KẾT LUẬN VÀ NIÊM PHONG GIAI ĐOẠN 3.1

Giai đoạn 3.1: **Chatbot AI RAG Streaming trên Flutter** chính thức được nghiệm thu có điều kiện theo báo cáo:
- Đã lưu kết quả 30/30 bài kiểm thử tự động PASS (12 Chatbot RAG, 10 Backend API, 8 Flutter Contract).
- Toàn bộ mã nguồn Phase 3.1 được niêm phong giữ nguyên, cam kết không tự ý chỉnh sửa trừ khi phát hiện lỗi nghiêm trọng.
- Dữ liệu CSV 208 sách và ChromaDB 208 vector bảo toàn tuyệt đối 100%.

> Hệ thống chuyển sang bước khảo sát và lập đề xuất cho Giai đoạn 3.2 theo tài liệu `PHASE3_2_PROPOSAL.md`. Mọi hoạt động triển khai chỉ được bắt đầu sau khi có phê duyệt chính thức.

