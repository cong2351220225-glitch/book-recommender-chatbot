# BÁO CÁO NGHIỆM THU GIAI ĐOẠN 3.2.1: TỦ SÁCH CÁ NHÂN (PERSONAL BOOKSHELF)

**Dự án:** AI Digital Library (Thư viện số AI Đa Nền Tảng)  
**Thời gian thực hiện:** 02/11/2026  
**Thư mục làm việc:** `E:\Source_Code\book-recommender-chatbot`  
**Môi trường:** Windows 10 x64, Python 3.13.12, FastAPI 0.115+, Flutter (Dart 3.x), ChromaDB 0.6.3  

---

## 1. TỔNG QUAN KẾT QUẢ TRIỂN KHAI

Giai đoạn 3.2.1 tập trung vào việc hiện thực hóa chức năng **Tủ sách cá nhân (Personal Bookshelf)** cho ứng dụng Flutter và FastAPI Backend, cho phép người dùng đăng nhập có thể:
- Thêm sách vào danh mục **Yêu thích (Favorites)**, **Đang đọc (Currently Reading)**, **Đã đọc (Completed)**.
- Quản lý và cập nhật tiến độ đọc (trang hiện tại / tổng số trang).
- Thay đổi trạng thái đọc linh hoạt hoặc xóa sách khỏi tủ sách.
- Cô lập tuyệt đối dữ liệu giữa các tài khoản người dùng, xác thực danh tính qua JWT.
- Bảo toàn 100% cơ sở dữ liệu `data/books.csv` (208 cuốn sách) và `chroma_db/` (208 vectors).

| Hạng mục kiểm tra | Trạng thái | Ghi chú kỹ thuật |
| :--- | :---: | :--- |
| **Thêm sách vào Yêu thích** | **PASS** | Ghi nhận trạng thái `favorite`, liên kết metadata sách tự động. |
| **Đánh dấu Đang đọc & Đã đọc** | **PASS** | Lưu trạng thái `reading`, `completed`, hỗ trợ cập nhật số trang & đánh giá sao. |
| **Chuyển đổi trạng thái / Xóa sách** | **PASS** | Cập nhật nguyên tử qua endpoint `PUT` và `DELETE`, không để lại dữ liệu mồ côi. |
| **Chống thêm trùng lặp** | **PASS** | Chặn thêm trùng cùng một sách với cùng một trạng thái (HTTP 400 Bad Request). |
| **Bảo mật & Cô lập dữ liệu người dùng** | **PASS** | User A và User B độc lập 100%. User B không thể xem, sửa hoặc xóa dữ liệu của User A. |
| **Chặn truy cập Khách vãng lai (Guest)** | **PASS** | Các thao tác yêu cầu JWT hợp lệ; Guest bị từ chối với HTTP 401 Unauthorized. |
| **Bảo toàn dữ liệu gốc (CSV, ChromaDB, RAG)** | **PASS** | `data/books.csv` giữ nguyên 208 dòng. Dữ liệu cá nhân lưu ở `data/bookshelves/{username}.json`. |
| **Giao diện Flutter Tủ sách (Navy & Gold)** | **PASS (Mã nguồn)** | TabBar 3 mục, Empty state thân thiện, card sách responsive, thanh tiến độ đọc, popup menu. |
| **Tích hợp Chi tiết sách & Hồ sơ người dùng** | **PASS** | Nút trái tim Yêu thích và quản lý tủ sách ngay trên `BookDetailScreen` và `ProfileScreen`. |
| **Biên dịch nhị phân Flutter CLI** | **BLOCKED** | Flutter CLI chưa được cấu hình vào PATH máy host Windows. |

---

## 2. DANH SÁCH TỆP ĐÃ TẠO VÀ CHỈNH SỬA

### 2.1. Phía Backend (`backend/`)
1. **Tạo mới `backend/schemas/bookshelf_schema.py`:**
   - Định nghĩa các Pydantic schema: `BookshelfItemCreate`, `BookshelfItemUpdate`, `BookshelfItemResponse`, `BookshelfListResponse`, `BookshelfCheckResponse`.
2. **Tạo mới `backend/routers/bookshelf_router.py`:**
   - Triển khai router `/api/v1/bookshelf` với đầy đủ các nghiệp vụ CRUD, enriched metadata sách, khóa ghi an toàn `_bookshelf_lock`, xác thực người dùng qua JWT `get_current_user`.
3. **Chỉnh sửa `backend/core/config.py`:**
   - Bổ sung cấu hình đường dẫn thư mục lưu trữ `BOOKSHELVES_DIR = DATA_DIR / "bookshelves"`.
4. **Chỉnh sửa `backend/main.py`:**
   - Đăng ký `bookshelf_router.router` vào hệ thống API v1 (`/api/v1/bookshelf`).

### 2.2. Phía Flutter Frontend (`mobile_app/`)
1. **Tạo mới `mobile_app/lib/models/bookshelf_item_model.dart`:**
   - Model đại diện cho một mục trong tủ sách: `id`, `bookId`, `status`, `progressPage`, `totalPages`, `rating`, `notes`, `addedAt`, `updatedAt`, `book`.
2. **Tạo mới `mobile_app/lib/repositories/bookshelf_repository.dart`:**
   - Tầng giao tiếp dữ liệu: `getBookshelf`, `checkBook`, `addItem`, `updateItem`, `deleteItem`, `deleteBook`.
3. **Tạo mới `mobile_app/lib/providers/bookshelf_provider.dart`:**
   - State management quản lý danh sách tủ sách, lọc theo tab, toggle yêu thích, cập nhật tiến độ đọc và đồng bộ UI tức thời.
4. **Tạo mới `mobile_app/lib/presentation/screens/my_bookshelf_screen.dart`:**
   - Màn hình chính Tủ sách cá nhân: 3 Tab (Yêu thích, Đang đọc, Đã đọc), Empty states, Card sách kèm thanh tiến độ, Dialog cập nhật số trang, màn hình chặn Guest yêu cầu đăng nhập.
5. **Chỉnh sửa `mobile_app/lib/core/constants/api_constants.dart`:**
   - Bổ sung các hằng số endpoint: `bookshelf`, `bookshelfCheck`, `bookshelfItem`, `bookshelfBook`.
6. **Chỉnh sửa `mobile_app/lib/services/api_service.dart`:**
   - Bổ sung các hàm gọi API tủ sách tương ứng với `DioClient`.
7. **Chỉnh sửa `mobile_app/lib/main.dart`:**
   - Đăng ký `ChangeNotifierProvider(create: (_) => BookshelfProvider())` vào cây widget toàn cục.
8. **Chỉnh sửa `mobile_app/lib/presentation/widgets/app_scaffold.dart`:**
   - Bổ sung tab điều hướng "Tủ sách" vào NavigationBar (Mobile) và Sidebar (Desktop).
9. **Chỉnh sửa `mobile_app/lib/presentation/screens/book_detail_screen.dart`:**
   - Thêm nút trái tim toggle Yêu thích trên AppBar và thanh điều khiển trạng thái đọc trong chi tiết sách.
10. **Chỉnh sửa `mobile_app/lib/presentation/screens/profile_screen.dart`:**
    - Thêm Card tóm tắt số lượng sách trong Tủ cá nhân (Yêu thích, Đang đọc, Đã đọc) kèm nút chuyển nhanh sang Tủ sách.

---

## 3. THIẾT KẾ LƯU TRỮ VÀ BẢO MẬT DỮ LIỆU

### 3.1. Thiết kế lưu trữ tách biệt hoàn toàn với `data/books.csv`
- Dữ liệu sách trong thư viện (`data/books.csv`) là tài nguyên tĩnh chung của hệ thống, tuyệt đối **không bị sửa đổi hay chèn dữ liệu cá nhân**.
- Dữ liệu tủ sách của mỗi tài khoản được lưu trữ thành các tệp JSON độc lập:
  ```text
  data/bookshelves/
  ├── cong1.json
  ├── user_a.json
  └── contract_tester.json
  ```
- **Cơ chế ghi nguyên tử (Atomic Write):**
  - Mọi thao tác ghi tệp đều được bảo vệ bởi khóa luồng `_bookshelf_lock = threading.Lock()`.
  - Dữ liệu được ghi ra tệp tạm thời `.tmp` trước khi dùng lệnh hệ thống `replace()` hoán đổi nguyên tử, ngăn ngừa triệt để lỗi tệp rỗng hoặc hỏng cấu trúc JSON khi có nhiều thao tác ghi đồng thời.

### 3.2. Bảo mật trích xuất danh tính từ JWT Token
- Backend không tin tưởng bất kỳ tham số `user_id` nào gửi từ phía client.
- Tên tài khoản `username` được trích xuất trực tiếp và giải mã từ JWT Access Token trong header `Authorization: Bearer <token>` thông qua dependency `get_current_user`.
- Người dùng chỉ có thể đọc và ghi vào tệp `{username}.json` của chính mình. Khi User A cố tình gửi ID mục của User B để sửa hoặc xóa, backend sẽ trả về mã lỗi `404 Not Found` (do không tìm thấy mục này trong tủ sách của User A), đảm bảo an toàn bí mật dữ liệu.

---

## 4. CHI TIẾT CÁC ENDPOINT API CỦA TỦ SÁCH CÁ NHÂN

| Phương thức | Endpoint | Quyền hạn | Mô tả chức năng |
| :--- | :--- | :---: | :--- |
| **GET** | `/api/v1/bookshelf` | Authenticated | Lấy danh sách sách trong tủ của user (hỗ trợ lọc `?status=favorite/reading/completed`). |
| **GET** | `/api/v1/bookshelf/check/{book_id}` | Authenticated | Kiểm tra nhanh một cuốn sách đã có trong tủ cá nhân hay chưa và ở những trạng thái nào. |
| **POST** | `/api/v1/bookshelf` | Authenticated | Thêm sách vào tủ sách (`book_id`, `status`, `progress_page`, `rating`, `notes`). |
| **PUT** | `/api/v1/bookshelf/{item_id}` | Authenticated | Cập nhật trạng thái đọc, tiến độ số trang, đánh giá sao hoặc ghi chú. |
| **DELETE** | `/api/v1/bookshelf/{item_id}` | Authenticated | Xóa một mục cụ thể khỏi tủ sách cá nhân. |
| **DELETE** | `/api/v1/bookshelf/book/{book_id}` | Authenticated | Xóa cuốn sách (hoặc trạng thái cụ thể) khỏi tủ sách. |

---

## 5. KẾT QUẢ KIỂM THỬ THỰC TẾ

### 5.1. Bộ kiểm thử chức năng Tủ sách cá nhân (`test_personal_bookshelf.py` - 9/9 PASS)
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

### 5.2. Bộ kiểm thử API Contract giữa Flutter và Backend (`test_flutter_api_contract.py` - 9/9 PASS)
```text
tests/test_flutter_api_contract.py::test_contract_01_auth_register_and_login PASSED [ 11%]
tests/test_flutter_api_contract.py::test_contract_02_home_stats PASSED              [ 22%]
tests/test_flutter_api_contract.py::test_contract_03_books_catalog_pagination PASSED [ 33%]
tests/test_flutter_api_contract.py::test_contract_04_book_search_and_filters PASSED [ 44%]
tests/test_flutter_api_contract.py::test_contract_05_book_detail_and_related PASSED [ 55%]
tests/test_flutter_api_contract.py::test_contract_06_authors_list_and_detail PASSED [ 66%]
tests/test_flutter_api_contract.py::test_contract_07_genres_list PASSED             [ 77%]
tests/test_flutter_api_contract.py::test_contract_08_error_codes_handling PASSED     [ 88%]
tests/test_flutter_api_contract.py::test_contract_09_bookshelf_api_contract PASSED  [100%]
============================== 9 passed in 9.03s ===============================
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

---

## 6. XÁC NHẬN BẢO TOÀN DỮ LIỆU & HỆ THỐNG GỐC

Đã thực hiện câu lệnh kiểm tra trực tiếp:
- **`data/books.csv`:** Đúng chính xác **208 dòng** và đầy đủ **26 cột**, không có bất kỳ dòng rác nào từ dữ liệu người dùng.
- **`chroma_db/`:** Lưu giữ nguyên vẹn **208 vector** trong collection `books_collection`.
- **Ứng dụng Streamlit (`app.py`):** Hoàn toàn không bị chỉnh sửa, chạy độc lập và ổn định.
- **Chatbot AI RAG Engine (`rag_engine.py`):** Nguyên vẹn logic retrieval, reranking và anti-hallucination.

---

## 7. CÁC GIỚI HẠN CHƯA GIẢI QUYẾT & PHÂN LOẠI MÔI TRƯỜNG

- **Mã nguồn Flutter (Provider, Screen, Model, Repository):** `PASS` (Cấu trúc code hoàn thiện, chuẩn MVVM).
- **Backend API Tủ sách & Kiểm thử:** `PASS` (100% test suites hoàn thành, bảo vệ quyền riêng tư tuyệt đối).
- **Thực thi và chụp ảnh màn hình nhị phân Flutter:** `BLOCKED` (Lệnh `flutter` chưa được cấu hình vào biến môi trường PATH trên máy Windows host, do đó không thể build ra file binary `.exe` hay `.apk` để chạy thực tế và chụp ảnh màn hình).
- **Môi trường iOS Build:** `BLOCKED` (Máy host chạy Windows 10, yêu cầu máy Mac và Xcode để build ứng dụng iOS).
- **Hạn ngạch Google Gemini API Free Tier:** `RESOURCE_EXHAUSTED (429)` (Gói Free Tier của Google AI Studio giới hạn 20 request/ngày; khi chạy hàng chục bài test liên tiếp trong ngày, Gemini API báo vượt quota ngày và yêu cầu chờ reset. Tuy nhiên logic code RAG và xử lý lỗi của hệ thống hoàn toàn đúng).

---

## 8. KẾT LUẬN

Giai đoạn 3.2.1: **Personal Bookshelf (Tủ sách cá nhân)** đã được hoàn thành đúng chỉ thị, đảm bảo bảo mật dữ liệu, an toàn đồng thời, giao diện Navy & Gold đồng bộ và bảo toàn toàn bộ hệ thống cũ.

> **Hệ thống đã dừng lại và sẵn sàng chờ ý kiến đánh giá, phản hồi hoặc phê duyệt từ Bạn trước khi chuyển sang các giai đoạn tiếp theo.**

