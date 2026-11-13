# Thư viện sách thông minh + AI

Ứng dụng Streamlit biến kho CSV hiện có thành một thư viện điện tử có catalog, tác giả, thể loại, chi tiết sách, chính sách đọc hợp pháp, tìm nơi mua/tìm thư viện bằng Google Maps và trợ lý AI grounded bằng Gemini + ChromaDB.

## Tính năng

- Trang chủ với sách nổi bật, tìm kiếm nhanh và khám phá thể loại.
- Kho sách: tìm kiếm, lọc theo thể loại/tác giả/năm/ngôn ngữ/rating, sắp xếp và xem card.
- Chi tiết sách: mô tả, tóm tắt, tags, đối tượng, độ khó, sách tương tự, tác giả và link mua.
- Cơ sở dữ liệu tác giả và thể loại từ `data/authors.csv`, `data/genres.csv`.
- AI Assistant giữ lại RAG hiện tại, ChromaDB, Gemini embedding, Top-K, chat history, small talk và phỏng vấn sở thích cá nhân hóa.
- Yêu cầu nhà sách/thư viện trong chat được định tuyến riêng, không gọi RAG, và tạo Google Maps Search URL.
- Kết quả RAG có nút mở chi tiết sách; PDF hợp lệ hiển thị bằng viewer Streamlit và EPUB dùng tải file an toàn.
- Chatbot có thể ghi nhận khu vực người dùng nhập trong phiên, hiểu yêu cầu “gần tôi”, rồi hiển thị kết quả SerpApi ngay trong hội thoại.
- Tìm địa điểm nhà sách/thư viện thực tế bằng SerpApi Google Maps API, có bản đồ, rating, giờ mở cửa, chỉ đường và website khi dữ liệu có.
- Google Maps Search URL vẫn được dùng làm fallback cho địa điểm thiếu link trực tiếp hoặc khi cần mở kết quả tổng quát.
- Đọc trực tuyến chỉ mở file trong `data/sample_books/` khi bản ghi được đánh dấu `reading_available=true`.
- Không tạo tên sách, tác giả, giá, địa chỉ hoặc link đọc toàn văn không có trong dữ liệu.

## Kiến trúc

```text
Streamlit app
  |- book_service.py       CSV catalog, filter, related books
  |- author_service.py     author lookup
  |- location_service.py   Google Maps fallback URL
  |- reading_service.py    path validation and reading policy
  |- intent_router.py      intents for library workflows
  |- rag_engine.py         routing, profile, Gemini, Chroma retrieval
  `- ingest.py             stable-ID document embedding

books.csv -> semantic documents -> Gemini embedding -> ChromaDB -> Top-K -> Gemini answer
```

Generation model hiện tại là `gemini-3.6-flash`, embedding model là `gemini-embedding-2`; không thay đổi nếu cấu hình API hiện tại đang hỗ trợ chúng.

## Cấu trúc thư mục

```text
app.py
config.py
book_service.py
author_service.py
location_service.py
reading_service.py
intent_router.py
rag_engine.py
ingest.py
data/books.csv
data/authors.csv
data/genres.csv
tests/test_library_services.py
chroma_db/
```

## Cài đặt

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Tạo `.env` ở root và chỉ đặt secret trong đó:

```env
GEMINI_API_KEY=your_key_here
GOOGLE_MAPS_API_KEY=
```

`.env`, `.venv/`, `chroma_db/` và `.streamlit/secrets.toml` đã nằm trong `.gitignore`.

## Chạy

Nạp lại vector database sau khi thay đổi `books.csv`:

```powershell
.\.venv\Scripts\python.exe ingest.py
```

Mỗi lần ingest xóa collection cũ, tạo document giàu ngữ nghĩa và ghi ID ổn định theo `book_id`, vì vậy không tạo duplicate.

Khởi động website:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Nếu thiếu Gemini key, website catalog vẫn mở; chỉ các luồng AI/RAG báo lỗi thân thiện.

## Dữ liệu và grounding

`data/books.csv` có 26 trường gồm `book_id`, `author_id`, metadata mô tả, `rating`, `featured`, `tags`, `target_audience`, `mood`, `difficulty`, trường đọc và link hợp pháp. Dữ liệu demo hiện có 24 sách, 24 tác giả và 16 thể loại. Các mô tả bắt đầu bằng “Dữ liệu mô tả demo” là metadata minh họa, không phải tiểu sử xác thực.

Hồ sơ recommendation chỉ tồn tại trong `st.session_state` của phiên hiện tại. Khi người dùng chưa nêu đủ mục tiêu, chủ đề hoặc sở thích, chatbot hỏi bổ sung trước khi truy xuất.

RAG tìm trên title, author, genre, description, summary, tags, audience, mood và difficulty. Câu trả lời sách chỉ được tạo từ context truy xuất; phần “Nguồn sách được AI sử dụng” hiển thị title, author, year, genre và distance.

## Đọc và bản quyền

Ứng dụng không giả định người dùng có quyền đọc sách có bản quyền. Chỉ file được cấp phép đặt trong `data/sample_books/`, có đuôi PDF/EPUB và được đánh dấu trong CSV mới được mở. Đường dẫn được resolve và kiểm tra nằm dưới thư mục cho phép; giá trị `../` hoặc absolute path bị từ chối. Nếu không có bản đọc, giao diện nêu rõ chính sách và chỉ hiện nguồn mua/catalog nếu dữ liệu có.

## Google Maps và SerpApi

Đặt `SERPAPI_API_KEY` trong `.env`, sau đó nhập thành phố hoặc khu vực ở trang “Thư viện & Nhà sách”. Ứng dụng gọi SerpApi Google Maps với `engine=google_maps`, hiển thị các kết quả `local_results`, tọa độ hợp lệ trên bản đồ, và không tự bịa tên, địa chỉ, khoảng cách hoặc đánh giá. `GOOGLE_MAPS_API_KEY` không được dùng cho luồng này.

Nếu SerpApi thiếu link chỉ đường, ứng dụng tạo Google Maps URL riêng theo tên và địa chỉ địa điểm. Nếu thiếu API key, API lỗi hoặc không có kết quả, giao diện hiển thị thông báo tiếng Việt an toàn.

## Kiểm tra

```powershell
.\.venv\Scripts\python.exe -m compileall -q .
.\.venv\Scripts\python.exe -m pytest -q tests
.\.venv\Scripts\python.exe -c "import chromadb, pandas, streamlit; from google import genai; print('imports ok')"
```

Các kiểm tra service không cần API key bao gồm load dữ liệu, khóa ngoại, tìm sách/tác giả, intent small talk/recommendation, Maps URL và reading path security. Kiểm tra embedding thực, retrieval Vietnamese và generation Gemini cần mạng, quota và API key hợp lệ; không ghi PASS nếu chưa chạy được.

## Troubleshooting

- `Vector database not found`: chạy `ingest.py`.
- `GEMINI_API_KEY is missing`: đặt key trong `.env`, không đặt trong code.
- Lỗi quota/model/network: kiểm tra quyền model và quota Gemini; trang catalog vẫn có thể dùng độc lập.
- CSV lỗi: kiểm tra cột bắt buộc `title`, `author`, `genre`, `description`, `year`, ID duy nhất và năm số nguyên.
