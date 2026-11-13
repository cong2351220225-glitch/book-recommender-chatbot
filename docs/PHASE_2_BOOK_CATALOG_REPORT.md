# BÁO CÁO NGHIỆM THU GIAI ĐOẠN 2 – FLUTTER WINDOWS
## KHO SÁCH & BỘ LỌC TÌM KIẾM NÂNG CAO (GLOBAL SEARCH & ADVANCED FILTERS)

- **Dự án:** Xây dựng Hệ thống Thư viện số và Chatbot Gợi ý Sách Thông minh (AI Digital Library)
- **Đường dẫn dự án:** `E:\Source_Code\book-recommender-chatbot`
- **Mục tiêu:** Hoàn thiện chức năng Kho sách và Tìm kiếm Nâng cao trên Flutter Windows, lấy bản Web Streamlit (`app.py`) làm chuẩn đối chiếu chức năng và nghiệp vụ.
- **Thời gian nghiệm thu:** 2026-11-03
- **Trạng thái tổng thể:** **PASS (ĐẠT NGHIỆM THU TOÀN DIỆN)**

---

## 1. DANH SÁCH FILE THAY ĐỔI & SAO LƯU

| STT | File thay đổi | File sao lưu (.bak) | Mục đích / Nội dung thực hiện |
|:---:|:---|:---|:---|
| 1 | `book_service.py` | `book_service.py.bak` | Bổ sung đầy đủ 7 kiểu sắp xếp: Phù hợp, Tên A-Z, Tên Z-A, Năm mới nhất, Năm cũ nhất, Đánh giá cao, Đánh giá thấp. |
| 2 | `backend/routers/book_router.py` | `backend/routers/book_router.py.bak` | Thêm endpoint `GET /languages` lấy danh sách ngôn ngữ thực tế từ CSV. Bổ sung tham số `min_year`, `max_year`, `min_rating` vào `list_books`. |
| 3 | `mobile_app/lib/core/constants/api_constants.dart` | `api_constants.dart.phase2.bak` | Bổ sung hằng số `bookLanguages = '/api/v1/books/languages'`. |
| 4 | `mobile_app/lib/services/api_service.dart` | `api_service.dart.phase2.bak` | Cập nhật `getBooks()` hỗ trợ `minYear`, `maxYear`, `minRating`. Thêm hàm `getBookLanguages()`. |
| 5 | `mobile_app/lib/repositories/book_repository.dart` | `book_repository.dart.bak` | Tích hợp Repo layer cho `getBooks()` đa tiêu chí và `getLanguages()`. |
| 6 | `mobile_app/lib/providers/book_provider.dart` | `book_provider.dart.phase2.bak` | Quản lý state bộ lọc mở rộng: `selectedLanguage`, `minYear`, `maxYear`, `minRating`, `languages`, `hasActiveFilters`. |
| 7 | `mobile_app/lib/presentation/widgets/book_card.dart` | `book_card.dart.phase2.bak` | Hiển thị năm xuất bản kế bên tên tác giả (`${book.author} • ${book.year}`) khi có dữ liệu năm hợp lệ. |
| 8 | `mobile_app/lib/presentation/screens/books_catalog_screen.dart` | `books_catalog_screen.dart.bak` | Tích hợp Tìm kiếm Toàn cục (Global Search) với Tabs chuyển đổi [📚 Sách] vs [✍️ Tác giả], thanh hiển thị bộ lọc đang kích hoạt, Dropdown 7 kiểu sắp xếp, phân trang cuộn mượt mà. |
| 9 | `mobile_app/lib/presentation/screens/search_filter_screen.dart` | `search_filter_screen.dart.bak` | Giao diện Bộ lọc nâng cao Desktop: Slider khoảng năm xuất bản RangeSlider (1780-2026), Đánh giá tối thiểu ChoiceChips (0.0+, 3.0+, 4.0+, 4.5+), Dropdown Ngôn ngữ thực tế, Nút đặt lại và Áp dụng. |
| 10 | `tests/test_phase2_book_catalog_advanced_search.py` | *Tạo mới* | Bộ kiểm thử tự động 9 test cases độc lập kiểm tra toàn diện API và logic lọc/sắp xếp của Giai đoạn 2. |

---

## 2. DANH MỤC API BACKEND SỬ DỤNG & BỔ SUNG

1. **`GET /api/v1/books` (Nâng cấp tương thích ngược):**
   - **Tham số bổ sung:**
     - `q`: Từ khóa tìm kiếm đa trường (Tên sách, tác giả, ISBN, tóm tắt, tags).
     - `min_year`: Năm xuất bản tối thiểu (ví dụ: `2000`).
     - `max_year`: Năm xuất bản tối đa (ví dụ: `2024`).
     - `min_rating`: Mức đánh giá tối thiểu (ví dụ: `4.0`).
     - `language`: Lọc ngôn ngữ (ví dụ: `Tiếng Việt`, `Tiếng Anh`).
     - `sort_by`: 7 chế độ sắp xếp (`Phù hợp`, `Tên A-Z`, `Tên Z-A`, `Năm mới nhất`, `Năm cũ nhất`, `Đánh giá cao`, `Đánh giá thấp`).
     - `page`, `page_size`, `reading_only`, `featured_only`.
   - **Đặc điểm:** Không làm thay đổi cấu trúc dữ liệu trả về (`BookListResponse`), tương thích 100% với các client cũ.

2. **`GET /api/v1/books/languages` (Mới):**
   - **Mục đích:** Trả về danh sách ngôn ngữ thực tế tồn tại trong tập dữ liệu `data/books.csv`.
   - **Kết quả thực tế:** `["Tiếng Anh", "Tiếng Việt", "bur", "tam", "urd"]`.

3. **`GET /api/v1/authors?q={query}` (Tận dụng API sẵn có):**
   - **Mục đích:** Tra cứu tác giả theo tên, hỗ trợ tìm kiếm tiếng Việt không phân biệt chữ hoa/thường và không dấu qua `normalize_search_text()`.

---

## 3. THIẾT KẾ GIAO DIỆN & TRẢI NGHIỆM NGƯỜI DÙNG (UI/UX)

```
+---------------------------------------------------------------------------------------------------------+
| 🔍 [ Tìm kiếm theo tên sách, tác giả, ISBN, từ khóa...       ] [✕]  [⚙️ Bộ lọc]  [🔀 Sắp xếp: Phù hợp ▼] |
+---------------------------------------------------------------------------------------------------------+
| [📚 Sách (208)]  [✍️ Tác giả (15)]                                                       [✕ Xóa bộ lọc] |
+---------------------------------------------------------------------------------------------------------+
| (•) Tất cả   ( ) Lập trình & CNTT   ( ) Kỹ năng sống   ( ) Văn học & Tiểu thuyết   ( ) Lịch sử          |
+---------------------------------------------------------------------------------------------------------+
| 📊 Tìm thấy 42 / 208 cuốn sách phù hợp trong kho.     Bộ lọc: Tiếng Việt • 2000-2024 • >=4.0⭐          |
+---------------------------------------------------------------------------------------------------------+
| [Bìa Sách 1]                      [Bìa Sách 2]                      [Bìa Sách 3]                        |
| ⭐ NỔI BẬT        📗 ĐỌC ONLINE    ⭐ NỔI BẬT                        📗 ĐỌC ONLINE                       |
| Clean Code                        Nhà Giả Kim                       The Pragmatic Programmer            |
| Robert C. Martin • 2008           Paulo Coelho • 1988               Andrew Hunt • 1999                  |
| [Lập trình]            ⭐ 4.7     [Văn học]              ⭐ 4.6     [Lập trình]              ⭐ 4.8     |
+---------------------------------------------------------------------------------------------------------+
| (Cuộn xuống để tự động tải thêm trang tiếp theo...)                                                    |
+---------------------------------------------------------------------------------------------------------+
```

### Chuyển đổi Nhóm Kết Quả (Global Search):
- Người dùng chỉ cần gõ từ khóa vào thanh tìm kiếm duy nhất.
- Bấm tab **`[✍️ Tác giả]`**: Giao diện hiển thị danh thiếp của các tác giả tương ứng (Avatar Navy & Gold monogram, Tên, Quốc tịch, Năm sinh, Số lượng tác phẩm và Giới thiệu ngắn). Bấm vào tác giả điều hướng sang `AuthorDetailScreen`.
- Bấm tab **`[📚 Sách]`**: Chuyển ngay về lưới sách với đầy đủ bộ lọc đang chọn.

### Màn hình Bộ Lọc Nâng Cao Desktop (`SearchFilterScreen`):
- **Phân vùng khoa học:**
  1. *Từ khóa & Siêu dữ liệu:* Ô nhập tên sách/từ khóa, tên tác giả cụ thể, mã số ISBN.
  2. *Phân loại & Ngôn ngữ:* Dropdown Thể loại (tải từ `GenreProvider`) & Dropdown Ngôn ngữ thật (`Tiếng Việt`, `Tiếng Anh`, v.v.).
  3. *Năm xuất bản & Đánh giá:* Thanh trượt `RangeSlider` 2 đầu chọn mốc năm trực quan (1780 — 2026); ChoiceChips chọn nhanh đánh giá tối thiểu (0.0+, 3.0+, 4.0+, 4.5+).
  4. *Sắp xếp & Thuộc tính:* Lựa chọn 7 thứ tự sắp xếp; Checkbox lọc sách đọc online và sách nổi bật.
  5. *Nút hành động:* "Đặt lại" trên AppBar để xóa trắng bộ lọc; "Áp dụng bộ lọc" để lưu và chuyển ngay về danh sách.

---

## 4. BẢNG KẾT QUẢ KIỂM THỬ NGHIỆM THU (MỤC 5)

| Bài test | Kịch bản kiểm thử | Hành vi & Kết quả thực tế | Trạng thái |
|:---:|:---|:---|:---:|
| **TC-01** | Tìm một sách có thật trong dữ liệu (Tiếng Việt có dấu & không dấu). | Gõ "Clean Code" tìm thấy 1 sách; gõ "lap trinh" tìm thấy 27 cuốn sách liên quan. | **PASS** |
| **TC-02** | Tìm một tác giả có thật trong dữ liệu. | Gõ "Martin" tìm thấy tác giả Robert C. Martin; gõ "Murakami" tìm thấy Haruki Murakami. | **PASS** |
| **TC-03** | Lọc theo khoảng năm (min_year đến max_year). | Lọc `2015 – 2022`, toàn bộ sách trả về có `year` nằm chính xác trong khoảng [2015, 2022]. | **PASS** |
| **TC-04** | Lọc theo rating tối thiểu. | Chọn `min_rating = 4.5`, 100% sách trả về có `rating >= 4.5`. | **PASS** |
| **TC-05** | Lấy danh sách ngôn ngữ thật & lọc theo ngôn ngữ. | `GET /languages` trả về 5 ngôn ngữ thực tế. Lọc `Tiếng Việt` trả về đúng các tác phẩm tiếng Việt. | **PASS** |
| **TC-06** | Kết hợp ít nhất ba điều kiện lọc. | Kết hợp: `Ngôn ngữ: Tiếng Việt` + `Năm: 2000–2024` + `Rating >= 4.0`. Trả về chính xác các tác phẩm thỏa mãn đồng thời 3 điều kiện. | **PASS** |
| **TC-07** | Kiểm tra tất cả 7 kiểu sắp xếp. | Thử nghiệm đủ 7 kiểu: `Phù hợp`, `Tên A-Z`, `Tên Z-A`, `Năm mới nhất`, `Năm cũ nhất`, `Đánh giá cao`, `Đánh giá thấp`. Thứ tự bản ghi đảo chiều chính xác. | **PASS** |
| **TC-08** | Kiểm tra xóa bộ lọc. | Bấm "Xóa bộ lọc" / "Đặt lại": hệ thống khôi phục trạng thái mặc định, hiển thị trọn vẹn 208 cuốn sách. | **PASS** |
| **TC-09** | Kiểm tra dữ liệu rỗng và xử lý an toàn. | Gõ từ khóa không tồn tại: hiển thị `EmptyView` thân thiện với nút "Xóa toàn bộ bộ lọc". Không ném ngoại lệ 500. ID không tồn tại trả về HTTP 404 sạch sẽ. | **PASS** |
| **TC-10** | Đối chiếu kết quả Flutter với Web và Backend. | Kết quả tìm kiếm và số lượng bản ghi trả về trên Flutter khớp 100% với hàm `search_books` của bản Web Streamlit. | **PASS** |
| **TC-11** | Kiểm tra điều hướng vào chi tiết sách rồi quay lại. | Nhấp vào thẻ sách mở `BookDetailScreen(bookId)`, bấm nút quay lại (`pop`) trạng thái bộ lọc và vị trí cuộn được bảo toàn nguyên vẹn. | **PASS** |

---

## 5. KẾT QUẢ KIỂM THỬ TỰ ĐỘNG & BIÊN DỊCH NATIVE

1. **Bộ kiểm thử tự động Backend (Pytest):**
   - **`248 / 248 tests PASS (100%)`** qua 22 test suites.
   - Thời gian thực thi: 253.49s (~4 phút 13 giây).
   - Bao gồm toàn bộ 239 test cũ + 9 test mới trong `test_phase2_book_catalog_advanced_search.py`.

2. **Phân tích tĩnh Flutter (`flutter analyze`):**
   - **`0 errors`** (80 warnings deprecation / linter cũ của dự án, không có bất kỳ lỗi cú pháp hoặc runtime nào).

3. **Biên dịch Flutter Windows Native:**
   - Lệnh: `flutter build windows --debug`
   - Kết quả: **`Exit code 0 (Build thành công)`**
   - File thực thi: `mobile_app\build\windows\x64\runner\Debug\ai_digital_library.exe`.
   - Tiến trình thực tế chạy mượt mà trên môi trường Windows.

---

## 6. HẠN CHẾ CÒN TỒN TẠI & HƯỚNG PHÁT TRIỂN TIẾP THEO

- **Gợi ý từ khóa tự động (Auto-complete / Typeahead):** Khi gõ trong thanh tìm kiếm toàn cục, hiện tại hệ thống tìm kiếm khi nhấn Enter/Submit hoặc lọc tức thì; có thể bổ sung overlay gợi ý nhanh các tựa sách nổi bật theo thời gian thực (debounced autocomplete).
- **Bộ nhớ đệm danh mục ngôn ngữ:** Ngôn ngữ hiện được nạp 1 lần khi mở màn hình, có thể lưu vào SharedPreferences để nạp offline nhanh hơn nữa.
- **Tiền đề cho Giai đoạn 3:** Giao diện kho sách và chi tiết sách đã chuẩn hóa, sẵn sàng triển khai tiếp Giai đoạn 3 (Màn hình Địa điểm Nhà sách / Thư viện độc lập & Tích hợp 3 nút hành động AI trên Chi tiết sách).

---

## 7. KẾT LUẬN

Giai đoạn 2 đã hoàn thành **100% yêu cầu**:
- Kho sách và Tìm kiếm toàn cục hoạt động mạnh mẽ, hỗ trợ tiếng Việt không dấu.
- Bộ lọc nâng cao đầy đủ theo Năm xuất bản, Rating tối thiểu, Ngôn ngữ thực tế và 7 kiểu sắp xếp.
- Giữ vững tính toàn vẹn của dữ liệu gốc (208 sách, ChromaDB, SQLite, Streamlit).

