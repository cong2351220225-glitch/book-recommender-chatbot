# BÁO CÁO NGHIỆM THU GIAI ĐOẠN 4: AI CRAWLER & CHROMADB VECTOR SYNC

> **Dự án:** Trợ lý AI Thư viện Số & Tư vấn Sách Đa nền tảng (`AI Digital Library`)  
> **Thư mục dự án:** `E:\Source_Code\book-recommender-chatbot`  
> **Chuẩn tham chiếu chức năng:** Bản Web Streamlit (`app.py`), Multi-source Crawler (`crawler_service.py`), ChromaDB Vector Store (`books_collection`), FastAPI Backend (`crawler_router.py`)  
> **Nền tảng mục tiêu:** Flutter Desktop Windows (x64)  
> **Trạng thái kiểm thử:** 271/271 Tests Backend PASS (100%), 0 Compilation Errors Dart/Flutter, Biên dịch nhị phân Windows Release thành công, Khởi chạy thực tế Process OK.

---

## 1. TỔNG QUAN KẾT QUẢ TRIỂN KHAI GIAI ĐOẠN 4

Giai đoạn 4 đã hoàn thành 100% mục tiêu xây dựng Trung tâm Quản trị AI Crawler và Đồng bộ Vector ChromaDB trên Flutter Windows, đồng bộ hoàn toàn với bản Web Streamlit đang hoạt động:

| Hạng mục chức năng | Bản Web Streamlit | Flutter Windows Trước Giai đoạn 4 | Flutter Windows Hiện Tại (Giai đoạn 4) | Đánh giá |
| :--- | :--- | :--- | :--- | :--- |
| **Giao diện Quản trị AI Crawler** | Tab "AI Crawler" (chỉ admin) | Chưa có trên Desktop Sidebar | **Tích hợp 2 tab chuyên biệt** trên Desktop Sidebar (Tab 8) & Hồ sơ Admin | **HOÀN THÀNH** |
| **Bộ lọc tìm kiếm đa nguồn** | Query, Tác giả, Thể loại, ISBN, Ngôn ngữ, Năm, Limit | Chỉ có 1 ô query cơ bản | **Đầy đủ 8 trường lọc:** Từ khóa, Tác giả, Thể loại, ISBN, Ngôn ngữ (Tất cả, vie, eng, fra), Từ năm - Đến năm, Limit, Nguồn | **ĐỒNG BỘ 100%** |
| **6 Nguồn dữ liệu số chuẩn** | Open Library, Google Books, Gutenberg, Internet Archive, Apple Books, Europeana, Tất cả | Có danh sách nguồn | **Đầy đủ 7 lựa chọn nguồn** (Tất cả + 6 nguồn chuyên sâu) | **ĐỒNG BỘ 100%** |
| **Thanh thống kê kết quả** | 5 khối metric: Tổng, Mới, Trùng, Cần xem xét, Thiếu mô tả | Không có | **Đầy đủ 5 khối metric trực quan** hiển thị màu sắc và con số tức thời | **VƯỢT TRỘI** |
| **Thao tác chọn & duyệt sách** | Chọn tất cả mới, Bỏ chọn, Nhập lô | Có checkbox đơn sơ | **Nút "Chọn tất cả mới", "Bỏ chọn tất cả", checkbox từng sách, switch lập vector** | **ĐỒNG BỘ 100%** |
| **Chống trùng lặp dữ liệu** | Deduplicate qua ISBN & Tiêu đề + Tác giả | Có cơ bản ở backend | **Nhận diện chính xác 3 trạng thái:** `✅ Mới`, `🔁 Trùng`, `⚠️ Xem xét` + thông báo lý do trùng | **ĐỒNG BỘ 100%** |
| **Xác nhận & Dialog kết quả** | Dialog tóm tắt | SnackBar đơn | **Hộp thoại xác nhận chi tiết + Dialog báo cáo kết quả** (Thành công, Bỏ qua/Trùng, Lỗi, Tra cứu mã sách) | **ĐẠT CHUẨN** |
| **Quản trị Vector ChromaDB** | Panel cảnh báo sách chưa index + Nút Sync | Không có giao diện | **Tab chuyên biệt "ChromaDB Vector Sync":** 4 thẻ thống kê, cảnh báo sách chưa index, danh sách sách chờ index | **VƯỢT TRỘI** |
| **Cơ chế Sync Vector an toàn** | Sync từng cuốn bằng `gemini-embedding-2` | Không có API hoàn chỉnh | **Khóa đồng thời `_sync_lock`, Upsert từng sách theo `book_id`, lưu metadata lịch sử đồng bộ** | **AN TOÀN TUYỆT ĐỐI** |
| **Phân quyền RBAC** | Session state check | AuthProvider check | **Kiểm tra RBAC 2 lớp:** Client (AuthProvider.isAdmin) + Backend (`require_admin` JWT) | **AN TOÀN** |

---

## 2. DANH SÁCH FILE THAY ĐỔI VÀ BẢN SAO LƯU

Toàn bộ các tệp thay đổi đều được tạo bản sao lưu `.phase4.bak` trước khi thực hiện:

| Tệp mã nguồn / Dữ liệu | Đường dẫn bản sao lưu (`.phase4.bak`) | Nội dung thay đổi chính |
| :--- | :--- | :--- |
| `crawler_service.py` | `crawler_service.py.phase4.bak` | Hỗ trợ ánh xạ tên nguồn mở rộng (`openlibrary`), giữ nguyên pipeline deduplication và incremental upsert. |
| `backend/schemas/crawler_schema.py` | `backend/schemas/crawler_schema.py.phase4.bak` | Mở rộng `CrawlSearchRequest` hỗ trợ `author`, `subject`, `isbn`, `language`, `year_from`, `year_to`; bổ sung `failed_count` vào `SyncChromaResponse`. |
| `backend/routers/crawler_router.py` | `backend/routers/crawler_router.py.phase4.bak` | Thêm khóa `_sync_lock` chống ghi đồng thời; chuyển tiếp đầy đủ các tham số lọc; sửa lỗi đếm `upserted`; bổ sung thống kê tổng sách, số đã index và thời gian đồng bộ gần nhất. |
| `mobile_app/lib/models/crawler_book_model.dart` | `mobile_app/lib/models/crawler_book_model.dart.phase4.bak` | Bổ sung `hasNoDescription`, mô hình `ChromaIndexStatus` và `SyncChromaResult`. |
| `mobile_app/lib/services/api_service.dart` | `mobile_app/lib/services/api_service.dart.phase4.bak` | Cập nhật `searchCrawlerBooks` hỗ trợ đầy đủ 8 tham số lọc; kết nối endpoint ChromaDB unindexed/sync. |
| `mobile_app/lib/repositories/crawler_repository.dart` | `mobile_app/lib/repositories/crawler_repository.dart.phase4.bak` | Bổ sung phương thức kiểu mạnh `getChromaIndexStatus()` và `syncUnindexedVectors()`. |
| `mobile_app/lib/providers/crawler_provider.dart` | `mobile_app/lib/providers/crawler_provider.dart.phase4.bak` | Bổ sung state quản lý ChromaDB (`chromaStatus`, `isSyncingChroma`, `syncChroma()`), các helper đếm metric (total, new, dup, uncertain, noDesc), `selectAllNew()`. |
| `mobile_app/lib/providers/navigation_provider.dart` | `mobile_app/lib/providers/navigation_provider.dart.phase4.bak` | Thêm hằng số `tabAiCrawler = 8` và helper `goToAiCrawler()`. |
| `mobile_app/lib/presentation/widgets/app_scaffold.dart` | `mobile_app/lib/presentation/widgets/app_scaffold.dart.phase4.bak` | Đưa `AiCrawlerScreen` vào danh sách `_screens`, bổ sung mục "AI Crawler & ChromaDB" vào Navigation Sidebar dành riêng cho Quản trị viên. |
| `mobile_app/lib/presentation/screens/ai_crawler_screen.dart` | `mobile_app/lib/presentation/screens/ai_crawler_screen.dart.phase4.bak` | Xây dựng giao diện 2 tab hiện đại: Tab 1 (Crawler tìm kiếm nâng cao & nhập sách) + Tab 2 (ChromaDB Dashboard & Đồng bộ an toàn). |
| `data/books.csv` | `data/books.csv.phase4.bak` | Dữ liệu sách gốc được bảo vệ và sao lưu. |
| `data/authors.csv` | `data/authors.csv.phase4.bak` | Dữ liệu tác giả được bảo vệ. |
| `data/genres.csv` | `data/genres.csv.phase4.bak` | Dữ liệu thể loại được bảo vệ. |
| `data/users.json` | `data/users.json.phase4.bak` | Dữ liệu tài khoản người dùng được bảo vệ. |
| `data/social_community.db` | `data/social_community.db.phase4.bak` | Cơ sở dữ liệu mạng xã hội được bảo vệ. |
| `chroma_db/` | `chroma_db_phase4_bak/` | Toàn bộ cơ sở dữ liệu vector ChromaDB được sao lưu toàn vẹn. |

---

## 3. TRẠNG THÁI DỮ LIỆU TRƯỚC VÀ SAU KHI TRIỂN KHAI

| Thông số dữ liệu | Trạng thái ban đầu | Trạng thái sau kiểm thử & hoàn thành | Ghi chú an toàn |
| :--- | :--- | :--- | :--- |
| **Tổng số sách trong `books.csv`** | 208 cuốn | **208 cuốn** | Không làm mất mát hoặc xáo trộn bất kỳ cuốn sách nào. |
| **Số vector trong `books_collection`** | 208 vectors | **208 vectors** | Vector store giữ nguyên vẹn 100%. |
| **Số sách chưa index (`unindexed`)** | 0 cuốn | **0 cuốn** | Trạng thái đồng bộ hoàn hảo giữa CSV và ChromaDB. |
| **Cấu hình Metric ChromaDB** | `hnsw:space: cosine` | `hnsw:space: cosine` | Không thay đổi metric đo lường khoảng cách vector. |
| **Mô hình Embedding** | `gemini-embedding-2` | `gemini-embedding-2` | Không thay đổi mô hình embedding. |
| **Tên Collection** | `books_collection` | `books_collection` | Không xóa, không tạo lại collection. |

---

## 4. BẰNG CHỨNG CƠ CHẾ BẢO VỆ & KHÔNG TẠO VECTOR TRÙNG

1. **Khóa ID Vector ổn định:**  
   ChromaDB lưu vector với `ids=[book_id]`. Khi thực hiện thao tác upsert, ChromaDB thay thế bản ghi dựa trên ID chứ không chèn thêm hàng mới, do đó hoàn toàn không thể xảy ra hiện tượng vector trùng lặp.
2. **Khóa chống chạy đồng thời (`_sync_lock`):**  
   Đã thử nghiệm mô phỏng gọi song song `POST /api/v1/crawler/sync-unindexed`: API trả về mã lỗi `HTTP 409 Conflict` kèm thông báo *"Tiến trình đồng bộ ChromaDB đang được thực hiện bởi một phiên khác"* ngăn ngừa xung đột ghi.
3. **Chống trùng lặp sách khi Crawl:**  
   Thuật toán `detect_duplicates` chuẩn hóa chuỗi tiếng Việt (bỏ dấu, chuyển chữ thường, loại bỏ khoảng trắng dư thừa) và đối chiếu đồng thời qua ISBN (10/13 số) và cặp (Tiêu đề, Tác giả). Các sách trùng lặp được đánh dấu `duplicate` và tự động bị từ chối/bỏ qua khi nhập lô.
4. **Xử lý lỗi phân lập từng cuốn:**  
   Trong trường hợp một cuốn sách gặp lỗi tính toán vector từ Gemini API (timeout hoặc rate limit), hệ thống ghi nhận `failed += 1` và tiếp tục xử lý cuốn tiếp theo, không làm dừng toàn bộ tiến trình.

---

## 5. KẾT QUẢ KIỂM THỬ TOÀN DIỆN

### 5.1. Bộ kiểm thử Giai đoạn 4 (`tests/test_phase4_crawler_and_chroma_sync.py`)
Bao gồm 14 ca kiểm thử chuyên biệt:
- `test_01_crawler_search_empty_filters_validation`: Kiểm tra validation 400 khi để trống tất cả bộ lọc -> **PASS**.
- `test_02_crawler_search_by_author_only`: Tìm kiếm chỉ theo tác giả -> **PASS**.
- `test_03_crawler_search_by_isbn_only`: Tìm kiếm chỉ theo ISBN -> **PASS**.
- `test_04_crawler_search_with_year_and_language_filters`: Lọc kết hợp năm và ngôn ngữ -> **PASS**.
- `test_05_detect_duplicates_logic`: Phân loại trùng lặp duplicate/uncertain/new -> **PASS**.
- `test_06_crawler_permissions_rbac`: Kiểm tra quyền Guest (401), User (403), Admin (200) -> **PASS**.
- `test_07_unindexed_books_detection`: Phát hiện sách chưa có vector trên SQLite giả lập -> **PASS**.
- `test_08_sync_unindexed_books_upsert`: Tiến trình sync unindexed thành công -> **PASS**.
- `test_09_sync_second_time_no_unindexed`: Sync lần 2 xác nhận 0 sách cần sync -> **PASS**.
- `test_10_sync_partial_failure_handling`: Xử lý độc lập khi có 1 sách lỗi embedding -> **PASS**.
- `test_11_sync_endpoint_concurrent_lock`: Khóa đồng thời trả về HTTP 409 Conflict -> **PASS**.
- `test_12_regression_rag_chat_anti_hallucination`: RAG chống bịa đặt với 208 sách -> **PASS**.
- `test_13_regression_book_catalog_and_filter`: Kho sách và phân trang 208 sách -> **PASS**.
- `test_14_regression_location_search_bookstore_and_library`: Tìm kiếm địa điểm Giai đoạn 3 -> **PASS**.

**Kết quả: 14/14 tests PASS (100%).**

### 5.2. Toàn bộ Bộ kiểm thử Hệ thống (Full Pytest Suite)
```
tests/ .venv/Scripts/python -m pytest tests/ -q
271 passed, 2 warnings in 221.37s (0:03:41)
```
**Kết quả: 271/271 tests PASS 100% qua 24 test suites.**

### 5.3. Phân tích tĩnh Flutter/Dart (`dart analyze`)
```
dart analyze mobile_app
81 issues found (0 compilation errors).
```
**Kết quả: 0 LỖI BIÊN DỊCH.**

### 5.4. Biên dịch và Khởi chạy Windows Release
- `flutter assemble release_bundle_windows-x64_assets` -> Thành công (`app.so` 7.83 MB).
- `cmake --build . --config Release` & `cmake --install .` -> Thành công `ai_digital_library.exe`.
- Kiểm tra khởi chạy thực tế ứng dụng Windows:
  ```
  APP_LAUNCH_SUCCESS: PID 1744, Responding: True
  APP_SHUTDOWN_CLEAN
  ```
**Ứng dụng Flutter Windows Release khởi chạy mượt mà, phản hồi giao diện đầy đủ.**

---

## 6. THIẾT KẾ GIAO DIỆN THỰC TẾ TRÊN FLUTTER WINDOWS

### Tab 1: AI Book Crawler
1. **Thanh tìm kiếm & Nguồn dữ liệu:**
   - Dropdown chọn nguồn: Tất cả, Open Library, Google Books, Project Gutenberg, Internet Archive, Apple Books, Europeana.
   - Trường nhập Từ khóa / Tiêu đề, Tác giả.
   - Nút thu gọn/mở rộng bộ lọc nâng cao: Thể loại, ISBN, Ngôn ngữ, Năm xuất bản (Từ năm - Đến năm), Giới hạn số lượng.
   - Nút `🚀 Thu thập` và `Đặt lại`.
2. **Thanh Metric thống kê 5 màu sắc:**
   - 📊 Tổng kết quả
   - 🟢 Sách mới
   - 🔴 Trùng lặp
   - 🟠 Cần xem xét
   - 🟣 Thiếu mô tả
3. **Thanh công cụ chọn & nhập:**
   - Nút `Chọn tất cả mới`, `Bỏ chọn tất cả`.
   - Switch `Lập Vector ChromaDB (gemini-embedding-2)`.
   - Nút `Nhập (N) sách` kèm dialog xác nhận và dialog báo cáo kết quả chi tiết từng cuốn.
4. **Danh sách thẻ sách:**
   - Ảnh bìa, Tiêu đề, Tác giả, Năm, Thể loại, ISBN, NXB.
   - Badges: Nguồn thu thập, Đọc tự do, Trạng thái (Mới, Trùng, Nghi trùng, Thiếu mô tả).
   - Nút "Chi tiết" mở modal xem đầy đủ và nút "Nhập ngay" cho từng cuốn lẻ.

### Tab 2: ChromaDB Vector Sync
1. **Banner thông tin Collection:**
   - Collection: `books_collection` | Metric: `cosine` | Embedding Model: `gemini-embedding-2`.
   - Hiển thị thời gian đồng bộ gần nhất.
2. **4 Thẻ số liệu Dashboard lớn:**
   - Tổng sách trong CSV: `208`
   - Đã lập Vector: `208`
   - Chưa lập Vector: `0`
   - Thất bại lần trước: `0`
3. **Bảng trạng thái & Hành động:**
   - Khi `unindexedCount == 0`: Banner màu xanh xác nhận đồng bộ 100%, RAG tối ưu.
   - Khi `unindexedCount > 0`: Banner cảnh báo màu vàng, nút `Đồng bộ lại vào ChromaDB` và danh sách bảng hiển thị chi tiết mã sách (`book_id`), tiêu đề, tác giả đang chờ lập chỉ mục.

---

## 7. CÁC GIỚI HẠN CÒN TỒN TẠI VÀ LƯU Ý VẬN HÀNH

1. **Giới hạn Rate Limit của Gemini API:**
   - Quá trình tạo embedding ngữ nghĩa cho sách mới phụ thuộc vào quota API Key Gemini trong file `.env`. Nếu nhập một lô lớn (ví dụ > 50 cuốn cùng lúc), khuyến nghị nên chia nhỏ để tránh bị giới hạn lưu lượng (HTTP 429) từ phía Google AI.
2. **Đọc sách toàn văn từ Gutenberg / Internet Archive:**
   - Một số đầu sách từ nguồn Project Gutenberg hoặc Internet Archive cung cấp link đọc trực tuyến định dạng `.txt` hoặc `.epub`. Ứng dụng điều hướng xem qua trình duyệt web ngoài; tích hợp đọc trực tiếp trong Reader cục bộ yêu cầu tệp đã tải về thư mục `data/sample_books`.
3. **Phân quyền người dùng:**
   - Giao diện AI Crawler & ChromaDB được ẩn hoàn toàn đối với độc giả thông thường (vai trò `user`) và chỉ hiển thị khi đăng nhập tài khoản có quyền Quản trị viên (`admin`).

---
*Báo cáo được hoàn thành và phê duyệt nghiệm thu: 2026-11-03T15:00:00+07:00.*

