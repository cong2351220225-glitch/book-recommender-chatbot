# ĐỀ XUẤT KẾ HOẠCH TRIỂN KHAI GIAI ĐOẠN 3.2
## DỰ ÁN: AI DIGITAL LIBRARY ĐA NỀN TẢNG (FLUTTER + FASTAPI)

**Tài liệu:** Đề xuất kỹ thuật & Phạm vi công việc Giai đoạn 3.2  
**Thời gian lập:** 02/11/2026  
**Trạng thái:** DỰ THẢO - CHỜ PHÊ DUYỆT (Chưa tiến hành sửa mã nguồn)  
**Tác giả:** Trợ lý Kỹ thuật AI  

---

## 1. CÁC CHỨC NĂNG FLUTTER ĐÃ HOÀN THÀNH (PHASE 2 & PHASE 3.1)

Tính đến hết Giai đoạn 3.1, ứng dụng Flutter trong `mobile_app/` đã hoàn thiện các khối chức năng nền tảng sau:

1. **Xác thực và phân quyền (Authentication & User Profile):**
   - Đăng ký tài khoản mới (`register_screen.dart`), Đăng nhập JWT (`login_screen.dart`).
   - Lưu trữ token an toàn và tự động phục hồi phiên bằng `SharedPreferences` (`auth_storage.dart`).
   - Xem thông tin tài khoản, vai trò người dùng (User/Admin) và đăng xuất (`profile_screen.dart`).
   - Không chứa bất kỳ tài khoản/mật khẩu hardcode nào trong mã nguồn.

2. **Trang chủ & Thống kê tổng quan (Home Dashboard):**
   - Hiển thị chính xác tổng số sách (**208 cuốn sách**), tổng số tác giả, thể loại.
   - Banner nổi bật, Carousel sách tiêu biểu, danh sách sách mới cập nhật (`home_screen.dart`).
   - Khung điều hướng chung đa nền tảng Responsive Layout (BottomNavigationBar trên Mobile, NavigationRail trên Tablet/Desktop) (`app_scaffold.dart`).

3. **Tra cứu & Danh mục sách (Books Catalog & Search):**
   - Xem danh sách sách dạng lưới (Grid) hoặc danh sách (List) với phân trang server-side (`page`, `page_size`, `total_pages`).
   - Tìm kiếm tức thời theo Tiêu đề, Tác giả, mã chuẩn ISBN.
   - Bộ lọc nhanh theo Thể loại (Genre filter).

4. **Chi tiết tác phẩm (Book Detail Screen):**
   - Hiển thị đầy đủ thông tin: Ảnh bìa, Tên sách, Tác giả, Năm xuất bản, Nhà xuất bản, Mô tả tóm tắt, Trạng thái sách, Nguồn liên kết.
   - Danh sách sách tương đồng / liên quan (Related Books).

5. **Tra cứu Tác giả & Thể loại (Authors & Genres Directory):**
   - Danh mục tác giả kèm tiểu sử vắn tắt và danh mục các tác phẩm của từng tác giả (`author_detail_screen.dart`).
   - Danh mục thể loại và số lượng đầu sách tương ứng (`genres_screen.dart`).

6. **Chatbot AI RAG Streaming (Nghiệm thu Phase 3.1):**
   - Khung chat AI thời gian thực kết nối FastAPI qua SSE streaming (`ai_chat_screen.dart`).
   - Trích xuất tài liệu tham khảo trong kho (RAG Sources) hiển thị dạng thẻ sách clickable.
   - Nút **"Dừng phản hồi" (Stop response)** hủy kết nối mạng và dừng sinh chữ ngay lập tức.
   - Cơ chế phòng vệ chống ảo giác, hỗ trợ tiếng Việt có dấu, cô lập dữ liệu người dùng (`403 Forbidden`).

---

## 2. NHỮNG CHỨC NĂNG CÒN THIẾU CỦA MỘT THƯ VIỆN SỐ THỰC TẾ

Mặc dù khung ứng dụng và Chatbot RAG đã hoàn thành, để trở thành một sản phẩm Thư viện số thực tế có thể đưa vào sử dụng, hệ thống hiện còn thiếu các chức năng cốt lõi sau:

1. **Quản lý Tủ sách cá nhân & Trạng thái đọc (Personal Bookshelf):**
   - Người dùng chưa thể lưu sách vào danh sách **Yêu thích (Favorites)**, **Muốn đọc (Want to read)**, **Đang đọc (Currently reading)**, hoặc **Đã đọc (Finished)**.
   - Chưa có giao diện theo dõi tiến độ đọc sách cá nhân (số trang đã đọc, ghi chú cá nhân).
2. **Trình đọc sách số & Xem tài liệu trực tuyến (In-App Digital Reader / Previewer):**
   - Đối với các sách có liên kết đọc miễn phí (Project Gutenberg, Internet Archive, Google Books preview) hoặc file PDF/EPUB trong kho, hiện tại người dùng chưa thể bấm mở trình đọc trực tiếp hoặc điều hướng an toàn qua trình duyệt mở ngoài.
3. **AI Crawler đa nguồn trên giao diện Flutter (Admin/Librarian Book Discovery):**
   - Trong ứng dụng Streamlit cũ, tính năng AI Crawler là một điểm sáng lớn (tìm kiếm trên 6 nguồn mở: Open Library, Google Books, Project Gutenberg, Internet Archive, Europeana, Apple Books và nhập tự động vào CSV + ChromaDB).
   - Trên ứng dụng Flutter, chức năng này hoàn toàn chưa có giao diện cho quản thư/admin.
4. **Đồng bộ hóa ngoại tuyến & Bộ nhớ đệm (Offline Caching):**
   - Khi mất kết nối Internet, ứng dụng chưa có cơ chế hiển thị dữ liệu đã lưu trong cache tạm thời.
5. **Bộ lọc đa tiêu chí nâng cao (Advanced Multi-criteria Filter):**
   - Chưa có bộ lọc kết hợp đồng thời nhiều điều kiện: Khoảng năm xuất bản (Từ năm - Đến năm), Ngôn ngữ (Việt / Anh), Sách có file đọc được ngay.

---

## 3. CÁC VẤN ĐỀ KỸ THUẬT VÀ BẢO MẬT CẦN XỬ LÝ

Trước khi xây dựng các tính năng mới, cần giải quyết các bài toán kỹ thuật sau:

1. **Bảo mật phân quyền vai trò (Role-Based Access Control):**
   - Chức năng AI Crawler và Nhập sách mới (`/api/v1/crawler/import`) tuyệt đối chỉ được mở cho tài khoản có vai trò `admin`. Giao diện Flutter phải ẩn hoàn toàn nút chức năng này với người dùng thông thường (`user`) và khách vãng lai (`guest`).
2. **Bảo vệ toàn vẹn dữ liệu gốc khi người dùng thao tác:**
   - Dữ liệu trạng thái đọc cá nhân (yêu thích, đang đọc) phải được lưu riêng theo từng `username` (trong cơ sở dữ liệu người dùng hoặc bảng mapping riêng), **tuyệt đối không được ghi đè hay sửa đổi file `data/books.csv`**. File `books.csv` chỉ được bổ sung dòng mới khi Admin nhập sách qua AI Crawler.
3. **Xử lý liên kết ngoài an toàn (Safe URL Handling):**
   - Việc mở các liên kết đọc sách bên ngoài (Internet Archive, Gutenberg, Google Books) cần được kiểm tra giao thức (`https://`), phòng chống tấn công điều hướng độc hại (Open Redirect) bằng thư viện `url_launcher` có cơ chế whitelist domain.
4. **Quản lý kích thước và tải dữ liệu tệp đọc số:**
   - Khi tải hoặc đọc tệp tài liệu số (PDF/EPUB) từ `/api/v1/reading/file/{book_id}`, cần hỗ trợ hiển thị thanh tiến trình (progress indicator), tránh nghẽn RAM ứng dụng trên thiết bị di động bộ nhớ thấp.

---

## 4. PHẠM VI ĐỀ XUẤT CHO GIAI ĐOẠN 3.2

Nhằm đảm bảo dự án phát triển chắc chắn, không gây quá tải và giữ vững chất lượng mã nguồn, tôi đề xuất phạm vi Giai đoạn 3.2 tập trung vào **2 TRỤ CỘT CHÍNH**:

### Trụ cột 1: Tủ sách cá nhân & Trải nghiệm Đọc sách số (Dành cho mọi độc giả)
- **Tủ sách của tôi (My Bookshelf Screen / Tab):**
  - Quản lý các tab: *Đang đọc*, *Muốn đọc*, *Đã đọc*, *Sách yêu thích*.
  - Thêm/bớt sách vào tủ cá nhân ngay tại màn hình `BookDetailScreen` chỉ bằng 1 chạm.
  - Lưu và cập nhật tiến độ đọc (số trang hiện tại / tổng số trang).
- **Trình đọc sách & Mở tài liệu số (Digital Reading Viewer & External Launcher):**
  - Tích hợp nút "Đọc sách ngay" hoặc "Xem bản số hóa" tại `BookDetailScreen`.
  - Mở các liên kết đọc trực tuyến an toàn thông qua `url_launcher`.
  - Tích hợp trình xem tài liệu nội bộ gọn nhẹ đối với các sách có file số hóa khả dụng.

### Trụ cột 2: AI Book Crawler & Khám phá sách đa nguồn (Dành cho Quản thư / Admin)
- **Màn hình AI Book Crawler (`ai_crawler_screen.dart`):**
  - Cho phép Admin chọn nguồn tìm kiếm: Tất cả (All), Open Library, Google Books, Project Gutenberg, Internet Archive, Europeana, Apple Books.
  - Nhập từ khóa (Tên sách, Tác giả, ISBN).
  - Hiển thị danh sách kết quả trả về từ backend với huy hiệu nguồn (source badge), ảnh bìa, tình trạng sách đã có trong thư viện hay chưa.
  - Nút **"Nhập vào Thư viện" (Import to Library)**: Gọi API backend để ghi thêm vào `data/books.csv` (đúng schema 26 cột) và tự động đồng bộ vector vào `ChromaDB` mà không cần khởi động lại ứng dụng.
  - Tự động làm mới bộ đếm tổng số sách trên trang chủ sau khi nhập thành công.

---

## 5. DANH SÁCH FILE DỰ KIẾN TẠO MỚI HOẶC CHỈNH SỬA

### 5.1. Phía Flutter Frontend (`mobile_app/`)
* **Tạo mới:**
  1. `lib/models/reading_item_model.dart`: Model lưu trạng thái đọc của người dùng (status, progress, updated_at).
  2. `lib/models/crawler_search_result_model.dart`: Model kết quả tìm kiếm từ 6 nguồn mở của AI Crawler.
  3. `lib/repositories/reading_repository.dart`: Repository gọi các API trạng thái đọc và tệp đọc sách.
  4. `lib/repositories/crawler_repository.dart`: Repository gọi API tìm kiếm nguồn mở và nhập sách của Admin.
  5. `lib/providers/reading_provider.dart`: Provider quản lý danh sách tủ sách cá nhân của user đang đăng nhập.
  6. `lib/providers/crawler_provider.dart`: Provider quản lý trạng thái tìm kiếm, lọc nguồn và tiến trình import sách.
  7. `lib/presentation/screens/my_bookshelf_screen.dart`: Màn hình hiển thị Tủ sách của tôi (phân loại theo tab).
  8. `lib/presentation/screens/ai_crawler_screen.dart`: Màn hình AI Crawler đa nguồn (chỉ hiển thị khi user là Admin).
* **Chỉnh sửa tối thiểu:**
  1. `lib/presentation/screens/book_detail_screen.dart`: Bổ sung nút "Thêm vào Tủ sách", chọn trạng thái đọc, và nút "Đọc trực tuyến".
  2. `lib/presentation/screens/profile_screen.dart`: Bổ sung nút tắt truy cập nhanh vào "Tủ sách cá nhân" và "AI Crawler" (nếu là Admin).
  3. `lib/presentation/widgets/app_scaffold.dart`: Bổ sung tab/mục điều hướng Tủ sách cá nhân.
  4. `lib/core/constants/api_constants.dart`: Bổ sung các hằng số endpoint của Reading và Crawler.

### 5.2. Phía FastAPI Backend (`backend/`)
* **Chỉnh sửa tối thiểu & Bổ sung an toàn:**
  1. `backend/routers/reading_router.py`:
     - Bổ sung endpoint lưu và truy xuất trạng thái đọc cá nhân theo user:
       - `POST /api/v1/reading/status`: Lưu trạng thái đọc (yêu cầu JWT token).
       - `GET /api/v1/reading/my-books`: Lấy toàn bộ sách trong tủ cá nhân của user đang đăng nhập.
     - Dữ liệu tủ sách cá nhân được lưu vào tệp riêng `data/user_reading.json` hoặc trường trong `users.json`, **tuyệt đối không làm thay đổi `books.csv`**.
  2. `backend/routers/crawler_router.py`:
     - Giữ nguyên các hàm cốt lõi đã chạy tốt ở Phase 1 (`/search`, `/import`, `/sources`).
     - Đảm bảo cơ chế khóa file `csv_write_lock` hoạt động ổn định khi Admin nhập sách từ giao diện Flutter.

---

## 6. CÁC API BACKEND SỬ DỤNG VÀ BỔ SUNG

| Phương thức | Endpoint | Vai trò | Quyền hạn | Mô tả |
| :--- | :--- | :--- | :--- | :--- |
| **GET** | `/api/v1/reading/status/{book_id}` | Hiện có | Mọi người | Kiểm tra sách có thể đọc số hóa hay không |
| **GET** | `/api/v1/reading/file/{book_id}` | Hiện có | Mọi người | Tải hoặc stream file đọc số (PDF/EPUB) |
| **POST** | `/api/v1/reading/status` | **Bổ sung** | Authenticated | Lưu trạng thái: `want_to_read`, `reading`, `completed`, `favorite` |
| **GET** | `/api/v1/reading/my-books` | **Bổ sung** | Authenticated | Lấy danh sách toàn bộ sách trong tủ cá nhân của user |
| **GET** | `/api/v1/crawler/sources` | Hiện có | Mọi người | Lấy danh sách 6 nguồn mở khả dụng |
| **POST** | `/api/v1/crawler/search` | Hiện có | Authenticated | Tìm kiếm sách xuyên suốt 6 nguồn dữ liệu mở |
| **POST** | `/api/v1/crawler/import` | Hiện có | **Admin Only** | Nhập sách vào CSV và nhúng vector vào ChromaDB |

---

## 7. KẾ HOẠCH KIỂM THỬ VÀ TIÊU CHÍ NGHIỆM THU PHASE 3.2

Mọi chức năng triển khai trong Phase 3.2 phải vượt qua các bài kiểm thử nghiêm ngặt:

1. **Kiểm thử Tủ sách cá nhân (Personal Bookshelf Test):**
   - User thêm sách vào mục Yêu thích / Đang đọc -> dữ liệu lưu thành công.
   - User A đăng nhập chỉ thấy tủ sách của User A; User B đăng nhập không thấy sách của User A (cô lập dữ liệu 100%).
   - Cập nhật tiến độ đọc (trang hiện tại) chính xác.
2. **Kiểm thử Trình đọc tài liệu (Digital Reading Test):**
   - Sách có link trực tuyến mở đúng qua `url_launcher`.
   - Sách có file cục bộ tải về an toàn qua `/reading/file/{book_id}`.
   - Sách không có bản đọc hiển thị thông báo hướng dẫn mượn sách giấy tại thư viện.
3. **Kiểm thử AI Crawler trên Flutter (Crawler & Import Test):**
   - Người dùng thường không thể truy cập màn hình AI Crawler (HTTP 403 khi gọi API import).
   - Admin tìm kiếm từ khóa thành công trên các nguồn (Open Library, Google Books, Gutenberg, Internet Archive...).
   - Admin nhập sách mới thành công:
     - CSV được ghi đúng cấu trúc 26 cột, `book_id` tự tăng không trùng lặp.
     - ChromaDB được cập nhật vector mới ngay lập tức.
     - Chatbot AI RAG có thể lập tức trả lời về cuốn sách mới này.
     - Bộ đếm tổng số sách trang chủ tự động tăng lên tương ứng.
4. **Kiểm thử hồi quy (Regression Test):**
   - Chạy lại toàn bộ 30 bài kiểm thử tự động của Phase 1, Phase 2 và Phase 3.1, đảm bảo đạt tỷ lệ **100% PASS**.

---

## 8. ĐÁNH GIÁ NGUY CƠ ẢNH HƯỞNG ĐẾN PHASE 1, PHASE 2, PHASE 3.1

| Hạng mục rủi ro tiềm ẩn | Đánh giá rủi ro | Biện pháp kiểm soát & ngăn chặn |
| :--- | :---: | :--- |
| **Làm xáo trộn `data/books.csv`** | **Cao** | Dữ liệu trạng thái đọc cá nhân được lưu ở tệp riêng `data/user_reading.json`. `books.csv` chỉ được thêm dòng khi Admin import sách qua lock an toàn `csv_write_lock`. |
| **Lỗi vector ChromaDB khi import** | **Trung bình** | Sử dụng hàm `ingest_books_to_chroma` sẵn có, tuyệt đối không tạo mới hay xóa collection `books_collection`. |
| **Làm ảnh hưởng Streamlit `app.py`** | **Không có** | Streamlit đọc trực tiếp từ CSV và dịch vụ nội bộ. Dữ liệu bổ sung từ Crawler hoàn toàn tương thích ngược với Streamlit. |
| **Lỗi bảo mật khi mở URL ngoài** | **Thấp** | Kiểm tra nghiêm ngặt scheme `https://` và xử lý ngoại lệ khi thiết bị không có trình duyệt. |
| **Xung đột mã nguồn Phase 3.1 (Chatbot)** | **Không có** | Module Chatbot AI RAG đã được đóng gói độc lập (`chat_router.py`, `ai_chat_screen.dart`, `chat_provider.dart`), không bị sửa đổi. |

---

## 9. KẾT LUẬN & CHỜ PHÊ DUYỆT

Tài liệu này đã khảo sát toàn diện và vạch rõ ranh giới kỹ thuật an toàn cho Giai đoạn 3.2. 

> **CAM KẾT TUÂN THỦ:**  
> Tôi đã dừng lại, không tự ý chỉnh sửa bất kỳ tệp mã nguồn nào và đang chờ Bạn xem xét, góp ý hoặc chính thức phê duyệt đề xuất trước khi bước vào triển khai Giai đoạn 3.2.

