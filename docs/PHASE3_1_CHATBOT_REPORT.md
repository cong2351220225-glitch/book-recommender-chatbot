# BÁO CÁO TRIỂN KHAI GIAI ĐOẠN 3.1: CHATBOT AI RAG STREAMING TRÊN FLUTTER
*(AI Digital Library — Multi-Platform RAG Chatbot)*

**Ngày thực hiện:** 02 tháng 11 năm 2026  
**Thư mục dự án:** `E:\Source_Code\book-recommender-chatbot`  
**Mục tiêu:** Tích hợp Chatbot AI sử dụng kiến trúc RAG hiện có vào ứng dụng đa nền tảng Flutter (`mobile_app/`), giao tiếp thời gian thực qua cơ chế Streaming (SSE) với FastAPI Backend, bảo toàn 100% kho dữ liệu 208 sách và mô hình Gemini.

---

## 1. Danh sách Tệp đã Tạo và Chỉnh sửa

### 1.1. Tệp tạo mới
1. [`mobile_app/lib/models/chat_message_model.dart`](file:///e:/Source_Code/book-recommender-chatbot/mobile_app/lib/models/chat_message_model.dart): Mô hình dữ liệu tin nhắn hội thoại (`ChatMessageModel`) và thông tin nguồn sách tham khảo RAG (`ChatSourceBook`) gồm tiêu đề, tác giả, thể loại, năm, rating, ảnh bìa, khoảng cách vector.
2. [`mobile_app/lib/repositories/chat_repository.dart`](file:///e:/Source_Code/book-recommender-chatbot/mobile_app/lib/repositories/chat_repository.dart): Tầng Repository điều phối gửi tin nhắn thường, streaming SSE và lấy lịch sử chat.
3. [`mobile_app/lib/providers/chat_provider.dart`](file:///e:/Source_Code/book-recommender-chatbot/mobile_app/lib/providers/chat_provider.dart): Quản lý trạng thái luồng hội thoại (`isStreaming`, `isThinking`), session ID, hủy luồng tức thì (`CancelToken`), danh sách gợi ý câu hỏi nhanh.
4. [`mobile_app/lib/presentation/widgets/chat_bubble.dart`](file:///e:/Source_Code/book-recommender-chatbot/mobile_app/lib/presentation/widgets/chat_bubble.dart): Widget hiển thị bong bóng chat phân biệt rõ người dùng (Navy) và AI (White Card + viền), trạng thái đang suy nghĩ, và danh sách các thẻ sách nguồn RAG có thể bấm để xem chi tiết.
5. [`mobile_app/lib/presentation/screens/ai_chat_screen.dart`](file:///e:/Source_Code/book-recommender-chatbot/mobile_app/lib/presentation/screens/ai_chat_screen.dart): Màn hình Chatbot AI hoàn chỉnh theo phong cách Navy & Gold, hỗ trợ tự động cuộn, nút "Dừng phản hồi" (Stop generation), gợi ý câu hỏi mẫu.
6. [`tests/test_chatbot_rag_streaming.py`](file:///e:/Source_Code/book-recommender-chatbot/tests/test_chatbot_rag_streaming.py): Bộ kiểm thử tự động 8 kịch bản cho Chatbot RAG và giao thức Streaming SSE.

### 1.2. Tệp chỉnh sửa bổ sung
1. [`mobile_app/lib/core/constants/api_constants.dart`](file:///e:/Source_Code/book-recommender-chatbot/mobile_app/lib/core/constants/api_constants.dart): Bổ sung các endpoint chat (`/api/v1/chat/message`, `/api/v1/chat/stream`, `/api/v1/chat/history/{sessionId}`).
2. [`mobile_app/lib/services/api_service.dart`](file:///e:/Source_Code/book-recommender-chatbot/mobile_app/lib/services/api_service.dart): Hiện thực hóa `sendChatMessage`, `sendChatMessageStream` (giải mã `Stream<Uint8List>` thành sự kiện SSE `LineSplitter`) và `getChatHistory`.
3. [`mobile_app/lib/main.dart`](file:///e:/Source_Code/book-recommender-chatbot/mobile_app/lib/main.dart): Đăng ký `ChatProvider` vào cây `MultiProvider` toàn ứng dụng.
4. [`mobile_app/lib/presentation/widgets/app_scaffold.dart`](file:///e:/Source_Code/book-recommender-chatbot/mobile_app/lib/presentation/widgets/app_scaffold.dart): Tích hợp tab **"Trợ lý AI"** vào thanh điều hướng Desktop Sidebar và Mobile Bottom Navigation.
5. [`mobile_app/lib/presentation/screens/home_screen.dart`](file:///e:/Source_Code/book-recommender-chatbot/mobile_app/lib/presentation/screens/home_screen.dart): Bổ sung banner quảng bá Chatbot AI với nút "Chat ngay" dẫn trực tiếp vào màn hình hội thoại.

---

## 2. Kiến trúc Hoạt động của Chatbot Flutter

Hệ thống được thiết kế chặt chẽ theo mô hình Client-Server không chia sẻ khóa bí mật:

```
+-------------------------------------------------------------------------+
|                         FLUTTER CLIENT                                  |
|                                                                         |
|  [AiChatScreen]  <--- Consumer --->  [ChatProvider]                     |
|         |                                  |                            |
|         v                                  v                            |
|    [ChatBubble]                    [ChatRepository]                     |
|         |                                  |                            |
|         +-- Mini Book Cards                v                            |
|             (RAG Sources)             [ApiService]                      |
|                                            |                            |
|                                            v (Dio SSE Stream)           |
+--------------------------------------------|----------------------------+
                                             | HTTP POST /api/v1/chat/stream
                                             v
+-------------------------------------------------------------------------+
|                         FASTAPI BACKEND                                 |
|                                                                         |
|  [chat_router.py]  --->  [rag_engine.py]                                |
|                                |                                        |
|              +-----------------+-----------------+                      |
|              v                                   v                      |
|      [ChromaDB Vector DB]               [Google Gemini AI]              |
|      (208 vectors embedding)          (gemini-3.6-flash model)          |
|              |                                   |                      |
|              v                                   v                      |
|       Cosine Search                      Prompt Grounding &             |
|       (Distance <= 0.85)                 Anti-Hallucination             |
|              |                                   |                      |
|              +-----------------+-----------------+                      |
|                                |                                        |
|                                v                                        |
|             Server-Sent Events (SSE Chunks)                             |
|             data: {"chunk": "..."} ... data: {"done": true, ...}        |
+-------------------------------------------------------------------------+
```

### Đặc điểm bảo mật & tối ưu:
- **Không có Gemini API Key trên Client:** Toàn bộ việc gọi API Google Gemini được giữ kín 100% trong FastAPI Backend.
- **Không tự bịa đặt nguồn:** Flutter chỉ hiển thị danh sách sách tham khảo khi backend trả về mảng `books` hợp lệ.
- **Kiểm soát luồng chặt chẽ:** Khi người dùng bấm "Dừng phản hồi" hoặc chuyển trang, `CancelToken` của Dio sẽ hủy kết nối ngay lập tức, giải phóng tài nguyên CPU và bộ nhớ.
- **Chống gửi trùng:** `ChatProvider` kiểm tra cờ `_isStreaming`, khóa ô nhập liệu và nút gửi khi câu trả lời đang được sinh.

---

## 3. Giao thức Streaming SSE Thực tế

Endpoint: `POST /api/v1/chat/stream`  
Content-Type: `text/event-stream`  
Encoding: `UTF-8`

### Định dạng sự kiện truyền nhận:
1. **Sự kiện nội dung từng phần (Streaming chunks):**
   ```
   data: {"chunk": "Cuốn sách The Pragmatic "}

   data: {"chunk": "Programmer là tác phẩm "}
   ```
2. **Sự kiện hoàn tất (Terminal done event):**
   ```json
   data: {
     "done": true,
     "answer": "Toàn bộ câu trả lời hoàn chỉnh...",
     "books": [
       {
         "id": "book_203",
         "metadata": {
           "title": "The Pragmatic Programmer",
           "author": "Andy Hunt, Dave Thomas",
           "genre": "Công nghệ",
           "year": "2019",
           "rating": "4.8",
           "cover_url": "https://..."
         },
         "document": "...",
         "distance": 0.284
       }
     ],
     "intent": "book_query",
     "session_id": "session_1730553000000"
   }
   ```
3. **Sự kiện báo lỗi (Error containment):**
   ```
   data: {"error": "Chi tiết lỗi xử lý..."}
   ```

---

## 4. Kết quả Kiểm thử Nghiệm thu Thực tế

Đã chạy toàn bộ **8 bài kiểm thử chuyên sâu** trong [`tests/test_chatbot_rag_streaming.py`](file:///e:/Source_Code/book-recommender-chatbot/tests/test_chatbot_rag_streaming.py):

```powershell
============================= test session starts =============================
platform win32 -- Python 3.13.12, pytest-9.1.1, pluggy-1.6.0
rootdir: E:\Source_Code\book-recommender-chatbot
collected 8 items

tests/test_chatbot_rag_streaming.py::test_01_chat_message_standard PASSED           [ 12%]
tests/test_chatbot_rag_streaming.py::test_02_chat_stream_protocol PASSED           [ 25%]
tests/test_chatbot_rag_streaming.py::test_03_rag_retrieval_with_sources PASSED    [ 37%]
tests/test_chatbot_rag_streaming.py::test_04_anti_hallucination_and_out_of_domain PASSED [ 50%]
tests/test_chatbot_rag_streaming.py::test_05_chat_history_persistence PASSED       [ 62%]
tests/test_chatbot_rag_streaming.py::test_06_sequential_conversation_flow PASSED  [ 75%]
tests/test_chatbot_rag_streaming.py::test_07_vietnamese_unicode_support PASSED     [ 87%]
tests/test_chatbot_rag_streaming.py::test_08_chat_validation_errors PASSED        [100%]

======================= 8 passed, 2 warnings in 72.66s ========================
```

### Chi tiết đánh giá từng kịch bản:
- **`test_01` (Standard Chat):** Trả về HTTP 200, phản hồi có đầy đủ `answer`, `intent`, `session_id`.
- **`test_02` (Streaming Protocol):** Nhận đầy đủ chuỗi sự kiện `chunk` và kết thúc bằng sự kiện `done: true`.
- **`test_03` (RAG Retrieval):** Truy xuất chính xác sách trong thư viện, metadata khớp với 208 đầu sách hiện có.
- **`test_04` (Anti-Hallucination):** Đối với câu hỏi phi liên quan (thời tiết sao Hỏa / ngoài đời thực), hệ thống định tuyến vào `out_of_domain` và **không tự bịa đặt sách trong thư viện** (`books == []`).
- **`test_05` (History Persistence):** Lưu đoạn hội thoại vào file JSON tại `data/chat_history/`, đọc lại chính xác tin nhắn người dùng và trợ lý AI.
- **`test_06` (Sequential Flow):** Duy trì ngữ cảnh hội thoại liên tiếp qua nhiều lượt hỏi đáp trong cùng một `session_id`.
- **`test_07` (Vietnamese Unicode):** Xử lý hoàn hảo các câu hỏi tiếng Việt có dấu phức tạp, không bị lỗi font hoặc hỏng ký tự.
- **`test_08` (Validation Errors):** Chặn các yêu cầu rỗng hoặc sai tham số bằng HTTP 422 chuẩn hóa.

---

## 5. Xác nhận Bảo toàn Dữ liệu và Ứng dụng Cũ

Đã chạy kiểm tra đối soát độc lập:
```
BOOKS ROWS: 208
BOOKS COLS: 26
CHROMA VECTORS: 208
STREAMLIT APP MODULE LOADED CLEANLY
```
- **`data/books.csv`:** Chính xác **208 sách**, giữ nguyên 26 cột.
- **ChromaDB (`books_collection`):** Chính xác **208 vector embedding**. Không ingest lại.
- **`app.py` & Streamlit:** Hoàn toàn nguyên vẹn, nạp module và chạy độc lập bình thường.

---

## 6. Hướng dẫn Khởi chạy Ứng dụng

### Bước 1: Khởi động FastAPI Backend
```powershell
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### Bước 2: Khởi động Ứng dụng Flutter
```powershell
cd mobile_app

# Khởi chạy trên Windows Desktop:
flutter run -d windows

# Khởi chạy trên Android Emulator:
flutter run -d android
```

Khi ứng dụng mở:
1. Nhấp tab **"Trợ lý AI"** ở thanh điều hướng dưới (hoặc Sidebar trên Desktop).
2. Chọn một gợi ý có sẵn hoặc nhập câu hỏi (ví dụ: *"Gợi ý cho tôi sách lập trình phần mềm"*).
3. Quan sát câu trả lời hiển thị Streaming theo thời gian thực và danh sách sách tham khảo RAG bên dưới.

---

> [!IMPORTANT]
> **Trạng thái:** Giai đoạn 3.1 đã hoàn thành đầy đủ, đạt 100% tiêu chí kiểm thử. Theo đúng yêu cầu, tôi **dừng lại tại đây** và chờ bạn xem xét, đánh giá trước khi chuyển sang các phần tiếp theo.

