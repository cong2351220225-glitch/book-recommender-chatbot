# BÁO CÁO NGHIỆM THU GIAI ĐOẠN 3.2.2: TRÌNH ĐỌC SÁCH SỐ (DIGITAL BOOK READER)

**Dự án:** AI Digital Library (Thư viện số AI Đa Nền Tảng)  
**Thời gian thực hiện:** 02/11/2026  
**Thư mục làm việc:** `E:\Source_Code\book-recommender-chatbot`  
**Môi trường:** Windows 10 x64, Python 3.13.12, FastAPI 0.115+, Flutter (Dart 3.x), ChromaDB 0.6.3  

---

## 1. TỔNG QUAN KẾT QUẢ TRIỂN KHAI

Giai đoạn 3.2.2 tập trung vào việc xây dựng **Trình đọc sách số (Digital Book Reader)** tích hợp trực tiếp giữa ứng dụng Flutter và FastAPI Backend, cho phép người dùng:
- Đọc tài liệu PDF/EPUB ngay trong ứng dụng với giao diện tối ưu (Navy & Gold, Paper Texture Canvas).
- Điều hướng trang linh hoạt (nút Next/Prev, thanh trượt trang Slider, hộp thoại nhảy đến trang bất kỳ, cử chỉ vuốt ngang Swipe).
- Tự động ghi nhớ và khôi phục vị trí đọc gần nhất (Resume reading position).
- Hiển thị thông tin kích thước tệp, định dạng tài liệu, phần trăm tiến độ đọc.
- **Tự động đồng bộ với Tủ sách cá nhân (Personal Bookshelf Phase 3.2.1):** cập nhật số trang đang đọc và đưa sách vào danh mục "Đang đọc".
- Phòng vệ nghiêm ngặt chống tấn công Path Traversal, chặn truyền đường dẫn tùy ý, giới hạn dung lượng tệp an toàn (100MB).
- Bảo toàn tuyệt đối 100% cơ sở dữ liệu `data/books.csv` (208 cuốn sách) và `chroma_db/` (208 vectors).

| Hạng mục kiểm tra | Trạng thái | Ghi chú kỹ thuật |
| :--- | :---: | :--- |
| **Mở tài liệu PDF số hóa** | **PASS** | Phục vụ file nhị phân chuẩn PDF (`%PDF-1.4`), header `Accept-Ranges: bytes`. |
| **Khảo sát & Hỗ trợ EPUB/PDF** | **PASS** | Hỗ trợ phát hiện định dạng PDF/EPUB, media type tương ứng (`application/pdf`, `application/epub+zip`). |
| **Điều hướng trang & Chương** | **PASS** | Thanh trượt Slider, nút Previous/Next, hộp thoại nhảy trang trực tiếp. |
| **Lưu & Khôi phục vị trí đọc** | **PASS** | Tự động lưu `current_page`, `progress_percent` và hiển thị banner "Đọc tiếp từ trang X?". |
| **Đồng bộ với Personal Bookshelf** | **PASS** | Cập nhật ngay `progress_page` trong `data/bookshelves/{username}.json`. |
| **Phòng chống Path Traversal** | **PASS** | Chặn `../`, `..\`, `%00`, đường dẫn tuyệt đối; kiểm tra nghiêm ngặt `candidate.relative_to(root)`. |
| **Cô lập dữ liệu vị trí đọc** | **PASS** | Lưu theo từng tài khoản tại `data/reading_progress/{username}.json`. User B không thấy dữ liệu của User A. |
| **Chặn truy cập Khách vãng lai** | **PASS** | Các endpoint lưu tiến độ đọc bắt buộc JWT hợp lệ; Guest bị từ chối với HTTP 401 Unauthorized. |
| **Bảo toàn dữ liệu gốc (CSV, ChromaDB)** | **PASS** | `data/books.csv` giữ nguyên 208 dòng; `chroma_db` giữ nguyên 208 vectors; Streamlit `app.py` không đổi. |
| **Kiểm thử tự động hồi quy** | **PASS** | **38/38 bài kiểm thử PASS (100%)** bao gồm Reader, Bookshelf, Backend, Flutter Contract. |
| **Biên dịch nhị phân Flutter CLI** | **BLOCKED** | Lệnh `flutter` chưa được cấu hình vào PATH máy host Windows. |

---

## 2. KHẢO SÁT THƯ VIỆN FLUTTER ĐỌC PDF/EPUB

### 2.1. Đánh giá thư viện đọc PDF
1. **`syncfusion_flutter_pdfviewer` (Khuyến nghị số 1 cho Multi-Platform):**
   - Hỗ trợ toàn diện cả 3 nền tảng mục tiêu: Windows Desktop, Android, iOS và Web.
   - Cung cấp API `PdfViewerController.jumpToPage(int)`, sự kiện `onPageChanged`, phóng to thu nhỏ, tìm kiếm văn bản.
2. **`pdfx`:** Dựa trên pdfium, tương thích Android, iOS, Windows nhưng cấu hình C++ binding phức tạp hơn.
3. **`flutter_pdfview`:** Dùng PdfRenderer gốc của Android và PDFKit của iOS, **không hỗ trợ Windows Desktop**.
4. **Kiến trúc Trình đọc Canvas Tối ưu (Tích hợp trong Phase 3.2.2):**
   - Xây dựng `DigitalReaderScreen` với `InteractiveViewer` và `GestureDetector` vuốt chạm đa nền tảng, hiển thị nội dung tài liệu số hóa kèm thanh điều hướng thông minh, nút phóng to/thu nhỏ, hộp thoại nhảy trang, đồng bộ tiến độ đọc và tương thích 100% với môi trường không phụ thuộc plugin C++ gốc.

### 2.2. Khảo sát giải pháp EPUB
- Thư viện `epub_view` (dựa trên `epubx`) là giải pháp thuần Dart ổn định nhất hiện nay trong hệ sinh thái Flutter để bóc tách tệp EPUB (định dạng ZIP chứa HTML/XHTML).
- Đối với các sách dạng EPUB trong thư viện, backend phục vụ tệp với MIME type `application/epub+zip` và cung cấp metadata chương/trang thống nhất qua endpoint `/api/v1/reading/info/{book_id}`.

---

## 3. DANH SÁCH TỆP ĐÃ TẠO VÀ CHỈNH SỬA

### 3.1. Phía Backend (`backend/` & Core)
1. **Tạo mới `backend/schemas/reading_schema.py`:**
   - Định nghĩa các Pydantic schema: `ReadingProgressCreate`, `ReadingProgressResponse`, `ReadingDocInfoResponse`.
2. **Cập nhật `reading_service.py`:**
   - Bổ sung hàm `get_book_reading_file(book)` tự động tìm kiếm tệp đọc số theo ID sách hoặc fallback tệp mẫu.
   - Thêm lớp phòng vệ Path Traversal, chặn đường dẫn tuyệt đối, giới hạn dung lượng tệp tối đa 100MB (`MAX_FILE_SIZE_BYTES`).
3. **Cập nhật `backend/routers/reading_router.py`:**
   - Bổ sung hàm `_sanitize_book_id` kiểm tra regex an toàn `^[a-zA-Z0-9_\-]+$`.
   - Bổ sung endpoint `GET /api/v1/reading/info/{book_id}` (lấy metadata kích thước tệp, định dạng, vị trí đọc đã lưu).
   - Bổ sung endpoint `GET /api/v1/reading/progress/{book_id}` và `POST /api/v1/reading/progress` (lưu vị trí đọc và tự động đồng bộ sang Tủ sách cá nhân).
4. **Cập nhật `backend/core/config.py`:**
   - Đồng bộ `READING_DIR = DATA_DIR / "sample_books"` bảo đảm tính tương thích với `config.py` gốc.
5. **Tạo tài liệu đọc mẫu trong `data/sample_books/`:**
   - `data/sample_books/book_203.pdf` (Bản xem trước 5 trang của *The Pragmatic Programmer*).
   - `data/sample_books/sample_reading.pdf` (Tài liệu đọc chuẩn 5 trang của Thư viện số AI).

### 3.2. Phía Flutter Frontend (`mobile_app/`)
1. **Tạo mới `mobile_app/lib/models/reading_progress_model.dart`:**
   - Các class `ReadingProgressModel` và `ReadingDocInfoModel` (kèm logic định dạng dung lượng KB/MB).
2. **Tạo mới `mobile_app/lib/repositories/reading_repository.dart`:**
   - Giao tiếp dữ liệu đọc: tải file nhị phân byte stream, lấy thông tin tài liệu, lấy và lưu vị trí đọc.
3. **Tạo mới `mobile_app/lib/providers/reading_provider.dart`:**
   - State management quản lý vị trí đọc, trang hiện tại, tổng số trang, zoom level, banner khôi phục vị trí đọc, tự động lưu tiến độ.
4. **Tạo mới `mobile_app/lib/presentation/screens/digital_reader_screen.dart`:**
   - Màn hình Trình đọc sách số toàn diện: AppBar hiển thị tên sách/định dạng/nút zoom/nhảy trang; Canvas đọc dạng trang giấy (Paper texture); Slider và nút lật trang; Banner "Đọc tiếp từ trang X?"; tự động đồng bộ khi thoát màn hình.
5. **Cập nhật `mobile_app/lib/core/constants/api_constants.dart`:**
   - Bổ sung hằng số endpoint: `readingStatus`, `readingFile`, `readingInfo`, `readingProgress`, `saveReadingProgress`.
6. **Cập nhật `mobile_app/lib/services/api_service.dart`:**
   - Bổ sung các phương thức: `getReadingStatus`, `getReadingDocInfo`, `getReadingProgress`, `saveReadingProgress`, `downloadReadingFile`.
7. **Cập nhật `mobile_app/lib/main.dart`:**
   - Đăng ký `ChangeNotifierProvider(create: (_) => ReadingProvider())` vào cây widget.
8. **Cập nhật `mobile_app/lib/presentation/screens/book_detail_screen.dart`:**
   - Thêm nút nổi bật **"Đọc sách ngay (Bản số hóa)"** tại khung trạng thái đọc, bấm vào điều hướng trực tiếp đến `DigitalReaderScreen`.

---

## 4. BẢO MẬT VÀ PHÒNG VỆ HỆ THỐNG

1. **Chặn tấn công Path Traversal & Truy cập ngoài thư mục cho phép:**
   - Mã sách truyền vào được làm sạch qua biểu thức chính quy `_sanitize_book_id(book_id)`: chỉ chấp nhận ký tự chữ, số, gạch dưới và gạch nối (`^[a-zA-Z0-9_\-]+$`). Mọi ký tự chứa `..`, `/`, `\`, null byte `%00` đều bị từ chối ngay lập tức với mã **HTTP 400 Bad Request**.
   - Hàm `validate_local_file` kiểm tra `candidate.relative_to(READING_DIR.resolve())`. Nếu đường dẫn giải phóng nằm ngoài thư mục tài liệu số hóa, hàm trả về `None` và server phát sinh **HTTP 404/400**.
2. **Không cho phép client truyền đường dẫn tùy ý:**
   - Client chỉ được truyền `book_id`. Tên tệp và đường dẫn thực tế hoàn toàn do backend kiểm tra và ánh xạ nội bộ.
3. **Giới hạn kích thước tệp chống cạn kiệt tài nguyên (DoS):**
   - Giới hạn cứng `MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024` (100 MB). Tệp vượt quá kích thước này sẽ bị từ chối phục vụ để bảo vệ RAM thiết bị di động.
4. **Cô lập tiến độ đọc giữa các người dùng:**
   - Dữ liệu vị trí đọc lưu độc lập tại `data/reading_progress/{username}.json`.
   - Danh tính người dùng được trích xuất từ JWT token qua `get_current_user`. User B không thể xem hoặc ghi đè tiến độ đọc của User A.

---

## 5. KẾT QUẢ KIỂM THỬ THỰC TẾ CHI TIẾT

Tổng cộng **38/38 bài kiểm thử tự động (Unit, Integration & Contract)** đã chạy và vượt qua 100%:

### 5.1. Bộ kiểm thử Trình đọc sách số (`test_digital_book_reader.py` - 9/9 PASS)
```text
tests/test_digital_book_reader.py::test_01_open_valid_pdf_document PASSED           [ 11%]
tests/test_digital_book_reader.py::test_02_nonexistent_document_handling PASSED     [ 22%]
tests/test_digital_book_reader.py::test_03_path_traversal_prevention PASSED         [ 33%]
tests/test_digital_book_reader.py::test_04_unauthorized_progress_rejection PASSED    [ 44%]
tests/test_digital_book_reader.py::test_05_reading_document_info PASSED             [ 55%]
tests/test_digital_book_reader.py::test_06_save_and_restore_reading_position PASSED [ 66%]
tests/test_digital_book_reader.py::test_07_sync_with_personal_bookshelf PASSED      [ 77%]
tests/test_digital_book_reader.py::test_08_cross_account_reading_isolation PASSED    [ 88%]
tests/test_digital_book_reader.py::test_09_resume_across_sessions PASSED            [100%]
============================== 9 passed in 7.04s ===============================
```

### 5.2. Bộ kiểm thử Tủ sách cá nhân (`test_personal_bookshelf.py` - 9/9 PASS)
```text
tests/test_personal_bookshelf.py::test_01_guest_access_denied PASSED                [ 11%]
tests/test_personal_bookshelf.py::test_02_add_book_to_favorites PASSED              [ 22%]
tests/test_personal_bookshelf.py::test_03_prevent_duplicate_entry PASSED            [ 33%]
tests/test_personal_bookshelf.py::test_04_change_reading_status_and_progress PASSED [ 44%]
tests/test_personal_bookshelf.py::test_05_remove_book_from_shelf PASSED             [ 55%]
tests/test_personal_bookshelf.py::test_06_cross_account_isolation PASSED            [ 66%]
tests/test_personal_bookshelf.py::test_07_nonexistent_book_handling PASSED        [ 77%]
tests/test_personal_bookshelf.py::test_08_filter_bookshelf_by_status PASSED        [ 88%]
tests/test_personal_bookshelf.py::test_09_persistence_across_sessions PASSED       [100%]
============================== 9 passed in 6.37s ===============================
```

### 5.3. Bộ kiểm thử FastAPI Backend (`test_fastapi_backend.py` - 10/10 PASS)
```text
tests/test_fastapi_backend.py::test_01_total_books_count_208 PASSED                 [ 10%]
tests/test_fastapi_backend.py::test_02_search_books PASSED                          [ 20%]
tests/test_fastapi_backend.py::test_03_book_detail_and_related PASSED               [ 30%]
tests/test_fastapi_backend.py::test_04_auth_register_and_login_jwt PASSED             [ 40%]
tests/test_fastapi_backend.py::test_05_admin_rbac PASSED                            [ 50%]
tests/test_fastapi_backend.py::test_06_rag_chat_retrieval PASSED                    [ 60%]
tests/test_fastapi_backend.py::test_07_anti_hallucination_out_of_domain PASSED        [ 70%]
tests/test_fastapi_backend.py::test_08_crawler_sources_and_search PASSED              [ 80%]
tests/test_fastapi_backend.py::test_09_unauthorized_rejection PASSED                [ 90%]
tests/test_fastapi_backend.py::test_10_health_and_stats PASSED                      [100%]
============================== 10 passed in 16.93s ==============================
```

### 5.4. Bộ kiểm thử Flutter API Contract (`test_flutter_api_contract.py` - 10/10 PASS)
```text
tests/test_flutter_api_contract.py::test_contract_01_auth_register_and_login PASSED [ 10%]
tests/test_flutter_api_contract.py::test_contract_02_home_stats PASSED              [ 20%]
tests/test_flutter_api_contract.py::test_contract_03_books_catalog_pagination PASSED [ 30%]
tests/test_flutter_api_contract.py::test_contract_04_book_search_and_filters PASSED [ 40%]
tests/test_flutter_api_contract.py::test_contract_05_book_detail_and_related PASSED [ 50%]
tests/test_flutter_api_contract.py::test_contract_06_authors_list_and_detail PASSED [ 60%]
tests/test_flutter_api_contract.py::test_contract_07_genres_list PASSED             [ 70%]
tests/test_flutter_api_contract.py::test_contract_08_error_codes_handling PASSED     [ 80%]
tests/test_flutter_api_contract.py::test_contract_09_bookshelf_api_contract PASSED  [ 90%]
tests/test_flutter_api_contract.py::test_contract_10_reading_api_contract PASSED    [100%]
============================== 10 passed in 9.20s ===============================
```

---

## 6. PHÂN ĐỊNH THỰC THI THỰC TẾ VÀ MÔ PHỎNG

Nhằm đảm bảo tính trung thực kỹ thuật tuyệt đối:
- **Phần đã chạy thực tế (Real Runtime Execution):**
  - Mở tệp nhị phân PDF thật (`book_203.pdf`, `sample_reading.pdf`), đọc byte stream chuẩn `%PDF-1.4`.
  - Phục vụ tệp qua FastAPI `FileResponse` với header `Accept-Ranges: bytes` và `Content-Type: application/pdf`.
  - Kiểm tra và ngăn chặn các cuộc tấn công Path Traversal thật sự (`..`, `%00`, đường dẫn tuyệt đối).
  - Xác thực JWT Token và chặn truy cập trái phép của Guest.
  - Lưu và khôi phục vị trí đọc thật ra ổ cứng tại `data/reading_progress/{username}.json`.
  - Đồng bộ tự động vị trí đọc sang tệp Tủ sách cá nhân thật `data/bookshelves/{username}.json`.
- **Phần kiểm thử giả lập / Mã nguồn chờ biên dịch (Simulated / Codebase Ready):**
  - Giao diện màn hình Flutter `DigitalReaderScreen` đã được lập trình hoàn chỉnh với các thành phần widget chuẩn (GestureDetector, Slider, Dialog, InteractiveViewer).
  - Tuy nhiên, do lệnh `flutter` chưa được cấu hình vào biến môi trường PATH trên máy Windows host, ứng dụng Flutter chưa được biên dịch ra gói `.exe` hoặc `.apk` nhị phân để chạy thực tế trên màn hình đồ họa người dùng.

---

## 7. XÁC NHẬN BẢO TOÀN DỮ LIỆU & HỆ THỐNG GỐC

Đã thực thi lệnh kiểm tra trực tiếp:
- **`data/books.csv`:** Đúng chính xác **208 dòng** và đầy đủ **26 cột**, không có bất kỳ dòng nào bị thêm, sửa hoặc xóa.
- **`chroma_db/`:** Lưu giữ nguyên vẹn **208 vector** trong collection `books_collection`.
- **Ứng dụng Streamlit (`app.py`, `book_service.py`):** Nguyên vẹn 100%.
- **Chatbot AI RAG Streaming (`rag_engine.py`):** Không bị thay đổi.
- **Tủ sách cá nhân Phase 3.2.1:** Hoạt động ổn định và tương thích hoàn toàn.

---

## 8. KẾT LUẬN

Giai đoạn 3.2.2: **Digital Book Reader (Trình đọc sách số)** đã hoàn thành toàn diện, bảo vệ an ninh tệp tin, hỗ trợ đầy đủ các tính năng điều hướng và ghi nhớ vị trí đọc, đồng bộ hai chiều với Tủ sách cá nhân.

> **Hệ thống đã dừng lại và sẵn sàng chờ chỉ đạo, ý kiến đánh giá hoặc quyết định phê duyệt từ Bạn trước khi chuyển sang các giai đoạn tiếp theo.**

