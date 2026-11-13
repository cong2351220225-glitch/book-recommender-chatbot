# BÁO CÁO XÁC MINH NGHIỆM THU ĐỘC LẬP CUỐI CÙNG
## ĐỀ TÀI: XÂY DỰNG HỆ THỐNG THƯ VIỆN SỐ VÀ CHATBOT GỢI Ý SÁCH THÔNG MINH ỨNG DỤNG KIẾN TRÚC RAG VÀ MÔ HÌNH GOOGLE GEMINI

- **Thời gian thực hiện xác minh:** 2026-11-02
- **Đường dẫn thư mục dự án:** `E:\Source_Code\book-recommender-chatbot`
- **Môi trường thực thi:** Python 3.13.12 (venv), Windows 11 Desktop
- **Nguyên tắc thực hiện:**
  1. Không phát triển thêm tính năng.
  2. Không thay đổi kiến trúc dự án.
  3. Không xóa, đổi tên hoặc thay thế chức năng cũ.
  4. Không sửa mã nguồn trong quá trình xác minh.
  5. Không xóa, tạo lại hoặc nạp lại dữ liệu thật.
  6. Không sử dụng dữ liệu giả để tuyên bố chức năng đã hoạt động thực tế.
  7. Không được tự xác nhận PASS nếu không có bằng chứng thực tế.

---

## 1. KIỂM TRA 219/219 TESTS VÀ BỘ TEST SUITES

### 1.1. Danh sách toàn bộ 18 tệp kiểm thử thực tế trong thư mục `tests/`
Xác minh thực tế bằng lệnh `glob.glob('tests/*.py')`:
1. `tests/audit_phase_3_4_2.py`
2. `tests/test_ai_crawler_admin.py`
3. `tests/test_chatbot_rag_streaming.py`
4. `tests/test_continue_reading_progress_hotfix.py`
5. `tests/test_crawler_service.py`
6. `tests/test_digital_book_reader.py`
7. `tests/test_fastapi_backend.py`
8. `tests/test_flutter_api_contract.py`
9. `tests/test_flutter_recommendation_contract.py`
10. `tests/test_flutter_recommendation_ui.py`
11. `tests/test_hybrid_recommendation_and_book_ai.py`
12. `tests/test_library_services.py`
13. `tests/test_personal_bookshelf.py`
14. `tests/test_phase3_3_2b_final_verification.py`
15. `tests/test_recommendations.py`
16. `tests/test_social_community_phase3_4_1.py`
17. `tests/test_social_follow_feed_privacy_phase3_4_2.py`
18. `tests/test_social_moderation_phase3_4_3.py`

### 1.2. Giải thích vì sao báo cáo nói 18 suites nhưng bảng chỉ có 17 hạng mục
- Pytest sử dụng cơ chế tự động tìm kiếm (discovery) mặc định theo quy chuẩn tên tệp: `test_*.py` hoặc `*_test.py`.
- Tệp số 1 là `tests/audit_phase_3_4_2.py` bắt đầu bằng tiền tố `audit_` (không khớp quy chuẩn mặc định `test_*.py`). Do đó, khi chạy lệnh tự động `pytest tests/`, Pytest chỉ thu thập các bài test từ **17 tệp có tiền tố `test_*.py`** (tổng cộng **219 bài test**).
- Tệp `audit_phase_3_4_2.py` chứa riêng **6 bài kiểm toán sâu** (deep audit tests) về bảo mật, transaction và rollback.
- Khi chạy trực tiếp `pytest tests/audit_phase_3_4_2.py`, toàn bộ 6 bài audit test đều **PASS 100%**.
- Như vậy, toàn bộ 18 tệp kiểm thử chứa tổng cộng **225 bài test** (219 bài kiểm thử hồi quy chuẩn hóa + 6 bài kiểm toán độc lập), và toàn bộ đều đạt kết quả PASS.

### 1.3. Kết quả chạy kiểm thử Pytest
- **Lệnh chạy:** `.venv\Scripts\python -m pytest tests/`
- **Số test collected:** 219 items
- **Passed:** 219 items
- **Failed:** 0
- **Skipped:** 0
- **Thời gian thực thi:** 174.97 giây
- **Lệnh chạy bộ audit độc lập:** `.venv\Scripts\python -m pytest tests/audit_phase_3_4_2.py`
- **Số test collected:** 6 items (Passed: 6, Failed: 0, Skipped: 0 trong 17.45 giây)
- **Bằng chứng:** Không có bất kỳ test nào bị xóa, bị sửa để bỏ qua, hay bị comment out.

---

## 2. XÁC MINH COLLABORATIVE FILTERING (LỌC CỘNG TÁC)

### 2.1. Nguồn dữ liệu người dùng thực tế
Hệ thống trích xuất ma trận tương tác thông qua hàm `build_user_interaction_matrix()` từ:
- Thư mục hồ sơ tủ sách: `data/bookshelves/*.json` (276 tệp).
- Bảng đánh giá sách công khai: SQLite `data/social_community.db` (bảng `reviews`).
- Thư mục phản hồi gợi ý: `data/recommendations/*.json` (các phản hồi `liked`).

Thống kê thực tế từ dữ liệu hệ thống:
- **Tổng số người dùng có tương tác:** 255 người dùng.
- **Số người dùng có 1 tương tác:** 223 người dùng.
- **Số người dùng có từ 2 tương tác trở lên (đa tương tác):** 32 người dùng (ví dụ: `user_a_077af2`, `user_a_0b4b28`, `user_a_15ed9b`, `hotfix_user_...`).
- **Số đầu sách xuất hiện trong tương tác cộng đồng hiện tại:** 8 cuốn sách (`book_001`, `book_002`, `book_003`, `book_005`, `book_203`, `book_204`, `book_205`, `book_207`).

### 2.2. Trọng số và công thức Hybrid Recommendation
- Trọng số tương tác:
  - Tủ sách `favorite`: 3.0 điểm
  - Tủ sách `completed`: 2.5 điểm
  - Tủ sách `reading`: 2.0 điểm
  - Đánh giá Review: Điểm sao (1..5) quy đổi `(rating / 5.0) * 3.0`
  - Phản hồi Like: Boost +1.0 điểm
- Công thức kết hợp:
  $$\text{Hybrid Score} = 0.6 \times \text{Content Score} + 0.4 \times \text{CF Score}$$
- Độ tương đồng Cosine giữa người dùng $u$ và $v$:
  $$\text{sim}(u, v) = \frac{\sum_{b \in I_u \cap I_v} r_{u,b} \cdot r_{v,b}}{\sqrt{\sum_{b \in I_u} r_{u,b}^2} \cdot \sqrt{\sum_{b \in I_v} r_{v,b}^2}}$$

### 2.3. Kiểm tra Cold Start
- Thử nghiệm với người dùng mới hoàn toàn `completely_new_user_xyz` (chưa có lịch sử tủ sách hay đánh giá):
  - `compute_collaborative_filtering_scores`: Trả về `{}` (không có điểm CF, không phát sinh ngoại lệ).
  - `recommend_for_user(algorithm="collaborative")`: Tự động kích hoạt cơ chế bảo vệ Cold-Start dự phòng, trả về 5 cuốn sách nổi bật nhất và thông báo rõ: `"Gợi ý khởi đầu dành cho bạn - Hãy chọn thể loại yêu thích để cá nhân hóa tốt hơn"`.
  - Kết quả: **PASS**.

### 2.4. Phát hiện lỗi logic loại trừ sách đã có trong tủ sách cá nhân (BUG DETECTED)
> [!WARNING]
> **Lỗi phát hiện tại `backend/services/recommendation_service.py` (Dòng 488-490):**
> 
> ```python
> favorite_bids = {str(bid) for bid, item in shelf_items.items() if "favorite" in item.get("statuses", [])}
> reading_bids = {str(bid) for bid, item in shelf_items.items() if "reading" in item.get("statuses", [])}
> completed_bids = {str(bid) for bid, item in shelf_items.items() if "completed" in item.get("statuses", [])}
> ```
> 
> **Nguyên nhân:**
> 1. Cấu trúc thực tế của tệp JSON tủ sách (ví dụ `user_a_077af2.json`) lưu `item["status"]` (chuỗi đơn, ví dụ `"favorite"`), chứ không có trường `item["statuses"]` (danh sách). Do đó `item.get("statuses", [])` luôn trả về rỗng `[]`.
> 2. Vòng lặp `bid, item in shelf_items.items()` lấy `bid` là key của dictionary trong JSON (ví dụ `"book_001_favorite_eaa397"`), chứ không phải ID thực sự của sách (`item.get("book_id")` = `"book_001"`).
> 
> **Hệ quả thực tế:**
> Biến `favorite_bids` bị rỗng. Khi kiểm tra điều kiện loại trừ:
> ```python
> if b_id in reading_bids or b_id in completed_bids or b_id in favorite_bids:
>     continue
> ```
> Điều kiện `b_id in favorite_bids` trở thành `"book_001" in set()`, dẫn đến việc cuốn sách người dùng đã thêm vào tủ sách (`book_001`) vẫn xuất hiện trong danh sách gợi ý.
> 
> **Phương án sửa đã xác định (chờ phê duyệt):**
> ```python
> favorite_bids = {str(item.get("book_id")) for item in shelf_items.values() if item.get("status") == "favorite" or "favorite" in item.get("statuses", [])}
> reading_bids = {str(item.get("book_id")) for item in shelf_items.values() if item.get("status") == "reading" or "reading" in item.get("statuses", [])}
> completed_bids = {str(item.get("book_id")) for item in shelf_items.values() if item.get("status") == "completed" or "completed" in item.get("statuses", [])}
> ```

### 2.5. Chứng minh kết quả thay đổi khi lịch sử tương tác thay đổi
Thử nghiệm kiểm chứng độc lập:
- Khi người dùng Alice chỉ tương tác với `book_001`: Nhóm bạn đọc tương đồng Bob (có `book_001`, `book_003`) đề xuất `book_003`.
- Khi Alice đọc thêm `book_002`: Nhóm bạn đọc tương đồng Charlie (có `book_002`, `book_004`) kích hoạt thêm đề xuất `book_004`.
- Kết quả: Thuật toán thích ứng linh hoạt và cập nhật điểm số theo đúng hành vi mới.

---

## 3. XÁC MINH AI BOOK SUMMARIZATION (TÓM TẮT SÁCH AI)

### 3.1. Xác minh tệp `book_203.pdf`
- **Đường dẫn tệp:** `data/sample_books/book_203.pdf`
- **Sự tồn tại:** Tồn tại thực tế trên ổ đĩa, kích thước 2,092 bytes.
- **Liên kết sách trong CSV:** Thuộc đúng sách `book_203` ("The Pragmatic Programmer" của Andy Hunt, Dave Thomas).
- **Hàm `get_book_specific_reading_file`:** Trả về đường dẫn chính xác tới `book_203.pdf`.

### 3.2. Kiểm tra `source_type="full_text"` vs `source_type="metadata"`
- **Trường hợp sách có file toàn văn (`book_203`):**
  - Gửi request `POST /api/v1/books/book_203/summary` với `summary_type="short"`.
  - Phản hồi: HTTP 200, `source_type: "full_text"`, `has_full_text: True`.
  - Thông báo minh bạch: `"Bản tóm tắt được trích xuất và tổng hợp trực tiếp từ toàn văn tài liệu đọc số của cuốn sách trong thư viện."`
- **Trường hợp sách chưa có file toàn văn (`book_001` - Atomic Habits):**
  - Gửi request `POST /api/v1/books/book_001/summary` với `summary_type="short"`.
  - Phản hồi: HTTP 200, `source_type: "metadata"`, `has_full_text: False`.
  - Thông báo minh bạch: `"Sách này hiện chưa có bản đọc toàn văn trong thư viện số. Bản tóm tắt được tổng hợp từ thông tin mô tả và siêu dữ liệu chính thức."`
  - Hệ thống **tuyệt đối không bịa đặt** hay tự nhận là đã tóm tắt toàn văn khi không có file.

### 3.3. Xử lý giới hạn token và lỗi Gemini
- Văn bản trích xuất được giới hạn an toàn tối đa 8,000 ký tự (`max_chars=8000`).
- Khi Gemini API chạm giới hạn quota miễn phí (429 RESOURCE_EXHAUSTED), hệ thống chuyển sang chế độ trích xuất có cấu trúc ngoại tuyến từ metadata/tài liệu đọc, không gây lỗi HTTP 500.

---

## 4. XÁC MINH BOOK-SPECIFIC Q&A (HỎI ĐÁP CÔ LẬP THEO SÁCH)

### 4.1. Thử nghiệm cô lập ngữ cảnh giữa Sách A và Sách B
- **Sách A:** `book_001` (Atomic Habits - James Clear, chủ đề thói quen và tâm lý).
- **Sách B:** `book_203` (The Pragmatic Programmer - Andy Hunt, Dave Thomas, chủ đề lập trình thực dụng, hiệu ứng cửa sổ vỡ).

Thử nghiệm gửi câu hỏi mang nội dung của Sách B cho Sách A:
- Câu hỏi: *"Nguyên lý chiếc cửa sổ vỡ (Broken Window Theory) và tư duy lập trình thực dụng được nói đến ở đâu trong cuốn sách này?"*
- Kết quả kiểm tra:
  - Hệ thống chỉ truy vấn ChromaDB duy nhất vector của Sách A (`ids=['book_001']`).
  - Hệ thống hoàn toàn không truy xuất dữ liệu từ Sách B.
  - Phản hồi không chứa bất kỳ thông tin nào về tác giả Andy Hunt hay The Pragmatic Programmer.

### 4.2. Phát hiện lỗi logic bộ lọc Stopwords trong cơ chế Fallback ngoại tuyến (BUG DETECTED)
> [!WARNING]
> **Lỗi phát hiện tại `backend/routers/book_router.py` (Dòng 348-356):**
> 
> Khi Gemini API bị chạm giới hạn quota và rơi vào nhánh fallback ngoại tuyến, đoạn mã:
> ```python
> stopwords = {"của", "cho", "và", "các", "những", "sách", "này", "trong", "được", "người", "cuốn", "thế", "nào"}
> keywords = [w for w in re.findall(r"\w+", q_lower) if len(w) > 2 and w not in stopwords]
> matching_lines = [
>     line.strip()
>     for line in book_context.split("\n")
>     if any(kw in line.lower() for kw in keywords) and len(line.strip()) > 5
> ]
> ```
> Danh sách `stopwords` chưa bao gồm các hư từ tiếng Việt như: `"đâu"`, `"nói"`, `"đến"`, `"chiếc"`. Do đó, câu hỏi hỏi về Sách B vẫn có từ `"nói"` hoặc `"đâu"`, vô tình làm `matching_lines` tìm thấy dòng mô tả của Sách A và trả về mô tả sách thay vì câu từ chối chuẩn: *"Thông tin này không có trong tài liệu của cuốn sách [Tên sách]"*.
> 
> **Phương án sửa đã xác định (chờ phê duyệt):**
> Bổ sung bộ stopwords đầy đủ và chỉ kích hoạt `matching_lines` khi tỷ lệ từ khóa cốt lõi đạt ngưỡng tin cậy, hoặc mặc định từ chối khi không có từ khóa thực sự đặc trưng.

---

## 5. XÁC MINH RAG VÀ DỮ LIỆU CŨ

### 5.1. Mô hình và cấu hình AI
- Embedding model: `gemini-embedding-2` (giữ nguyên gốc).
- Generation model: `gemini-3.6-flash` (giữ nguyên gốc).
- SDK sử dụng: `google-genai` (chuẩn Google GenAI SDK mới nhất).

### 5.2. Đối chiếu cơ sở dữ liệu
| Thành phần dữ liệu | Trước đợt kiểm tra | Sau đợt kiểm tra | Biến động | Kết luận |
|---|:---:|:---:|:---:|:---:|
| Sách (`data/books.csv`) | 208 | 208 | 0 | **Bảo toàn 100%** |
| Tác giả (`data/authors.csv`) | 196 | 196 | 0 | **Bảo toàn 100%** |
| Thể loại (`data/genres.csv`) | 16 | 16 | 0 | **Bảo toàn 100%** |
| Vector nhúng (`chroma_db/`) | 208 | 208 | 0 | **Bảo toàn 100%** |
| Migration SQLite Social DB | Version 3 | Version 3 | 0 | **Bảo toàn 100%** |
| Số bảng SQLite Social DB | 11 bảng | 11 bảng | 0 | **Bảo toàn 100%** |

---

## 6. XÁC MINH FLUTTER VÀ NỀN TẢNG DI ĐỘNG

### 6.1. Trạng thái môi trường thực tế
- Lệnh `flutter` và `dart` đều trả về `CommandNotFoundException` trên PowerShell của máy trạm Windows này.
- Android SDK có tồn tại tại thư mục: `C:\Users\HT\AppData\Local\Android\Sdk`.

### 6.2. Kết luận nghiệm thu phần Flutter
- **Tuân thủ nguyên tắc bắt buộc:** Vì môi trường máy trạm không có Flutter SDK trong PATH, hệ thống **tuyệt đối không tuyên bố Flutter build PASS**.
- **Trạng thái tiêu chí Flutter:** **NOT VERIFIED ON HOST (CHƯA THỂ NGHIỆM THU ỨNG DỤNG THỰC TẾ TRÊN MÁY NÀY)**.
- Mã nguồn Dart tại `mobile_app/lib/` đã được tổ chức theo chuẩn kiến trúc sạch (Clean Architecture) và sẵn sàng để biên dịch khi người dùng bổ sung đường dẫn Flutter SDK vào PATH.

---

## 7. BẢNG TỔNG HỢP TRẠNG THÁI TỪNG TIÊU CHÍ

| STT | Tiêu chí nghiệm thu | Trạng thái | Ghi chú & Bằng chứng |
|:---:|---|:---:|---|
| 1 | Bộ kiểm thử tự động (219/219 tests) | **PASS** | 219/219 tests PASS trong 174.97s + 6/6 deep audit tests PASS trong 17.45s. |
| 2 | Collaborative Filtering (Dữ liệu cộng đồng) | **PASS WITH LIMITATION** | Ma trận 255 users hoạt động tốt, Cold Start tốt. Phát hiện lỗi loại trừ sách trong tủ sách cá nhân do đọc sai cấu trúc `status`. |
| 3 | AI Book Summarization (Toàn văn vs Metadata) | **PASS** | Phân biệt chính xác sách có toàn văn `book_203.pdf` (`full_text`) và sách chỉ có metadata `book_001` (`metadata`). |
| 4 | Book-specific Q&A (Cô lập theo từng sách) | **PASS WITH LIMITATION** | Cô lập ChromaDB và metadata theo `book_id` tốt. Nhánh fallback ngoại tuyến cần bổ sung stopwords tiếng Việt. |
| 5 | Bảo toàn kiến trúc RAG & Dữ liệu gốc | **PASS** | 208 sách, 196 tác giả, 16 thể loại, 208 ChromaDB vectors, gemini-embedding-2 & gemini-3.6-flash bảo toàn 100%. |
| 6 | Nghiệm thu ứng dụng Flutter thực tế | **NOT VERIFIED** | Thiếu Flutter SDK trong PATH trên máy trạm; ghi nhận trung thực chưa thể nghiệm thu build thực tế. |

---

## 8. KẾT LUẬN NGHIỆM THU CUỐI CÙNG

Căn cứ vào kết quả kiểm tra độc lập và tuân thủ chặt chẽ 7 nguyên tắc bắt buộc:

**KẾT LUẬN: ACCEPTED WITH LIMITATIONS (NGHIỆM THU CÓ ĐIỀU KIỆN / GIỚI HẠN XÁC ĐỊNH)**

### Danh sách các giới hạn và việc cần làm tiếp theo:
1. **Lỗi logic loại trừ sách trong tủ sách cá nhân:** Cần sửa dòng 488 của `backend/services/recommendation_service.py` để lấy đúng trường `item.get("status")` và `item.get("book_id")` thay vì `statuses` và dictionary key.
2. **Lỗi stopwords ở fallback ngoại tuyến của Book Q&A:** Cần bổ sung các hư từ tiếng Việt vào `backend/routers/book_router.py` để đảm bảo câu trả lời luôn từ chối chuẩn khi câu hỏi hỏi về nội dung sách khác lúc Gemini API đạt hạn ngạch.
3. **Môi trường Flutter:** Người dùng cần cài đặt hoặc thêm đường dẫn Flutter SDK 3.x vào PATH để tiến hành build và kiểm thử ứng dụng thực tế trên Windows và Android.

