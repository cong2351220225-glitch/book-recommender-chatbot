# -*- coding: utf-8 -*-
"""
Chương 3: Phân tích và thiết kế hệ thống (System Analysis & Design)
"""

CHAPTER_3_DATA = {
    "title": "Chương 3. Phân tích và thiết kế hệ thống",
    "sections": [
        {
            "heading": "3.1 Phân tích bài toán và yêu cầu",
            "paragraphs": [
                "Trong quá trình phát triển phần mềm, việc phân tích thấu đáo bài toán thực tế và xác lập hệ thống yêu cầu chức năng, phi chức năng một cách tường minh là tiền đề quyết định sự thành bại của kiến trúc hệ thống. Đối với bài toán Trợ lý ảo tư vấn sách thông minh, hệ thống phải đáp ứng nhu cầu tra cứu đa dạng của nhiều đối tượng người dùng, từ độc giả thông thường đến quản trị viên thư viện."
            ],
            "subsections": [
                {
                    "heading": "3.1.1 Yêu cầu chức năng (Functional Requirements)",
                    "paragraphs": [
                        "Hệ thống được phân tích và thiết kế để đáp ứng 8 nhóm yêu cầu chức năng cốt lõi sau:",
                        "- FR1 - Quản lý và tra cứu Kho sách: Cung cấp giao diện duyệt danh mục sách trực quan; hỗ trợ tìm kiếm toàn cục đa trường (theo tên sách, tác giả, thể loại, mã ISBN); hỗ trợ bộ lọc nâng cao đa tiêu chí (năm xuất bản, khoảng rating, ngôn ngữ, thể loại sách); hỗ trợ phân trang và sắp xếp kết quả linh hoạt.",
                        "- FR2 - Xem chi tiết và Đọc sách trực tuyến: Hiển thị đầy đủ thông tin xuất bản, ảnh bìa, tóm tắt nội dung, đối tượng phù hợp, thẻ từ khóa; cho phép xem mục lục sách và trải nghiệm trình đọc sách kỹ thuật số (Digital Reader) với chế độ lưu tiến độ đọc.",
                        "- FR3 - Đối thoại và Gợi ý sách thông minh (RAG Chatbot): Tiếp nhận câu hỏi ngôn ngữ tự nhiên từ người dùng; tự động nhận diện ý định; truy xuất tri thức từ ChromaDB; sinh câu trả lời tư vấn cá nhân hóa; lưu trữ và duy trì ngữ cảnh hội thoại theo phiên (Multi-turn chat memory).",
                        "- FR4 - So sánh sách đa chiều: Khi người dùng phân vân giữa nhiều cuốn sách, hệ thống tự động suy luận đa tài liệu (Multi-document reasoning) và tổng hợp bảng so sánh Markdown (GFM) chi tiết các tiêu chí: Thể loại, Điểm nổi bật, Điểm hạn chế và Đối tượng phù hợp.",
                        "- FR5 - Tương tác Đa phương thức (Multimodal AI): Cho phép người dùng tải lên ảnh chụp bìa sách để AI nhận diện tựa đề/tác giả và khớp nối tự động vào kho sách; hỗ trợ nhập câu hỏi bằng giọng nói qua micro (STT); hỗ trợ nghe câu trả lời qua giọng đọc tiếng Việt tự nhiên (TTS) với thanh điều khiển mini-player.",
                        "- FR6 - Định vị Nhà sách và Thư viện: Tự động phát hiện ý định hỏi về địa điểm; hỗ trợ tra cứu các thư viện công cộng và nhà sách thực tế (FAHASA, Phương Nam, Tiền Phong...); hiển thị thông tin địa chỉ, khoảng cách, bản đồ Google Maps và cơ chế tự động Fallback về khu vực mặc định Đà Nẵng khi không có địa danh cụ thể.",
                        "- FR7 - Quản trị AI Crawler (Admin): Cho phép quản trị viên tìm kiếm và cào dữ liệu sách mới từ Internet (qua SerpApi / Google Books); thuật toán đối soát tự động kiểm tra trùng lặp theo ISBN, tên sách và tác giả; cho phép chọn lọc và nhập sách an toàn vào tệp `books.csv`.",
                        "- FR8 - Giám sát và Tự chữa lành đồng bộ Vector (ChromaDB Vector Sync): Bảng điều khiển quản trị hiển thị số lượng sách trong CSV và số lượng vector trong ChromaDB theo thời gian thực; tự động phát hiện các cuốn sách chưa được đánh chỉ mục; cung cấp nút 'Đồng bộ lại vào ChromaDB' an toàn mà không làm gián đoạn hệ thống."
                    ]
                },
                {
                    "heading": "3.1.2 Yêu cầu phi chức năng (Non-Functional Requirements)",
                    "paragraphs": [
                        "Để đảm bảo chất lượng công nghiệp và độ tin cậy vận hành, hệ thống tuân thủ nghiêm ngặt các yêu cầu phi chức năng:",
                        "- NFR1 - Hiệu năng và Thời gian đáp ứng (Performance): Thời gian phản hồi cho các truy vấn tra cứu kho sách đạt dưới 100ms. Thời gian trễ sinh từ đầu tiên (Time-to-First-Token - TTFT) của Chatbot RAG qua giao thức truyền phát SSE đạt dưới 1.2 giây trên môi trường mạng thông thường.",
                        "- NFR2 - Tính xác thực và Chống ảo giác (Grounding & Reliability): 100% các câu trả lời tư vấn sách phải bắt nguồn từ dữ liệu sách có thực trong context được truy xuất. Tuyệt đối không sinh tên sách hay tác giả hư cấu. Tỷ lệ phân loại chính xác ý định (Intent Accuracy) đạt trên 95%.",
                        "- NFR3 - Bảo mật và Phân quyền (Security & RBAC): Toàn bộ các API quản trị và lịch sử cá nhân phải được bảo vệ bằng mã thông báo JWT (JSON Web Token) với thuật toán ký SHA-256. Mật khẩu người dùng được băm an toàn bằng thuật toán Bcrypt. Đảm bảo tính cô lập dữ liệu tuyệt đối giữa các tài khoản (User Isolation).",
                        "- NFR4 - An toàn bộ nhớ và Tài nguyên (Memory Safety): Xử lý tải file ảnh bìa (<= 8MB) và âm thanh hoàn toàn trên bộ nhớ RAM, tự giải phóng sau khi xử lý xong, tuyệt đối không ghi file tạm bừa bãi làm tràn ổ đĩa lưu trữ.",
                        "- NFR5 - Trải nghiệm người dùng và Tính thích ứng giao diện (UI/UX Responsiveness): Giao diện Flutter Desktop được thiết kế chuẩn Desktop UX; bảng biểu Markdown tự động hỗ trợ cuộn ngang linh hoạt, triệt tiêu hoàn toàn lỗi vỡ khung hình (RenderFlex Overflowed) khi người dùng thu nhỏ cửa sổ ứng dụng.",
                        "- NFR6 - Tính tương thích đa nền tảng (Cross-Platform Parity): Đảm bảo sự tương đương 100% về mặt nghiệp vụ giữa phiên bản Web Streamlit đối chiếu và ứng dụng Desktop Flutter Windows Release thương mại."
                    ]
                },
                {
                    "heading": "3.1.3 Phân quyền người dùng trong hệ thống (RBAC)",
                    "paragraphs": [
                        "Hệ thống thiết lập cơ chế kiểm soát truy cập dựa trên vai trò (Role-Based Access Control - RBAC) với 3 nhóm vai trò rõ ràng:",
                        "1. Khách vãng lai (Guest): Có thể tra cứu kho sách, xem thông tin chi tiết, tìm kiếm vị trí nhà sách/thư viện và trò chuyện với Chatbot RAG. Phiên chat của khách được lưu tạm thời theo UUID ngẫu nhiên.",
                        "2. Người dùng thành viên (Authenticated User): Được cấp tài khoản, đăng nhập qua JWT; sở hữu tủ sách cá nhân (yêu thích, đang đọc, đã đọc); lưu vết tiến độ đọc sách điện tử; lưu trữ lịch sử hội thoại vĩnh viễn trên SQLite và quản lý các phiên chat cá nhân (tạo mới, đổi tên, xóa phiên với hộp thoại xác nhận).",
                        "3. Quản trị viên (Admin): Sở hữu toàn bộ quyền hạn của người dùng, đồng thời được cấp quyền truy cập các tính năng nhạy cảm tại `/api/v1/crawler/`: cào dữ liệu sách mới, duyệt và nhập sách vào kho, theo dõi sức khỏe cơ sở dữ liệu vector và kích hoạt tiến trình đồng bộ ChromaDB."
                    ]
                }
            ]
        },
        {
            "heading": "3.2 Thiết kế kiến trúc hệ thống",
            "paragraphs": [
                "Hệ thống được thiết kế theo mô hình Kiến trúc Ba tầng (Three-Tier Architecture) kết hợp kiến trúc hướng dịch vụ microservices, đảm bảo tính phân tách độc lập giữa giao diện người dùng, nghiệp vụ xử lý và lưu trữ dữ liệu."
            ],
            "subsections": [
                {
                    "heading": "3.2.1 Kiến trúc tổng thể 3 tầng của hệ thống",
                    "paragraphs": [
                        "Kiến trúc 3 tầng của hệ thống bao gồm:",
                        "1. Tầng Giao diện Người dùng (Presentation Tier / Client):",
                        "   - Ứng dụng Desktop Windows: Xây dựng bằng Flutter SDK và biên dịch thành tệp thực thi native `ai_digital_library.exe` qua C++ Runner. Giao diện được tổ chức theo mô hình Provider Pattern quản lý trạng thái, tích hợp các widget tùy biến cao cấp (`BookVisionDialog`, `MarkdownTableView`, `AudioPlayerControlBar`).",
                        "   - Ứng dụng Web tham chiếu: Xây dựng bằng Streamlit (`app.py`), phục vụ kiểm thử song song và đối chiếu tính nhất quán chức năng.",
                        "2. Tầng Dịch vụ và Xử lý Nghiệp vụ (Application / Business Logic Tier):",
                        "   - Xây dựng trên nền tảng FastAPI chạy trên máy chủ Uvicorn bất đồng bộ (port 8000).",
                        "   - Bao gồm các router chuyên trách: Auth Router (JWT, Bcrypt), Books Router (CRUD, search, filters), Chat Router (RAG SSE stream, history), Location Router (Maps, geocoding), Crawler Router (web scraping, deduplication, sync), Book Vision Router (Pillow, Gemini Vision), Media Router (TTS gTTS stream, STT Gemini Audio).",
                        "   - Các dịch vụ xử lý lõi: `rag_engine.py` (điều phối RAG), `intent_router.py` (phân loại ý định), `book_cover_vision_service.py` (thị giác máy tính), `audio_service.py` (xử lý âm thanh), `crawler_service.py` (cào và đồng bộ dữ liệu).",
                        "3. Tầng Dữ liệu và Trí tuệ Nhân tạo (Data & AI Inference Tier):",
                        "   - Cơ sở dữ liệu Vector: ChromaDB lưu trữ 208 vector nhúng 768 chiều cùng metadata chi tiết.",
                        "   - Dữ liệu tập tin & Quan hệ: `data/books.csv` (kho 208 đầu sách), `authors.csv`, `genres.csv` và cơ sở dữ liệu SQLite `social_community.db`.",
                        "   - Dịch vụ Đám mây Trí tuệ Nhân tạo: Google Gemini API (gemini-2.5/3.6-flash tạo sinh và gemini-embedding-2 tạo vector), Google Maps / OpenStreetMap APIs.",
                        "",
                        "[HÌNH ẢNH MINH HỌA 3.1: Sơ đồ kiến trúc tổng thể 3 tầng của Hệ thống AI Digital Library & Multimodal Chatbot]"
                    ]
                },
                {
                    "heading": "3.2.2 Luồng xử lý dữ liệu của Chatbot RAG (Data Flow Diagram)",
                    "paragraphs": [
                        "Khi người dùng gửi một câu hỏi (bằng văn bản hoặc giọng nói sau khi qua STT), luồng dữ liệu tuần tự diễn ra như sau:",
                        "1. Bước 1 - Tiếp nhận và Định tuyến Ý định: Câu hỏi đi vào `intent_router.classify_intent()`. Nếu câu hỏi thuộc các nhóm chuyên biệt (như hỏi địa điểm nhà sách, chào hỏi thông thường, tìm kiếm tác giả), hệ thống chuyển hướng ngay đến dịch vụ tương ứng mà không cần kích hoạt RAG, tiết kiệm tài nguyên tính toán.",
                        "2. Bước 2 - Phân tích Vector và Truy xuất Ngữ nghĩa (Retrieval): Nếu là câu hỏi tìm sách hoặc hỏi chi tiết (`BOOK_QUERY`), câu hỏi được chuyển đổi thành vector embedding qua Google Gemini Embedding API. Vector này được gửi vào ChromaDB để thực hiện tìm kiếm Cosine Similarity, lọc ra Top-K cuốn sách phù hợp nhất (mặc định Top-K = 3, người dùng có thể cấu hình từ 1 đến 10 qua Slider).",
                        "3. Bước 3 - Xây dựng Ngữ cảnh Tri thức (Augmentation): Các trường metadata (tiêu đề, tác giả, thể loại, mô tả, tóm tắt, đối tượng phù hợp, đánh giá) của Top-K cuốn sách được ghép nối thành chuỗi văn bản `Retrieved Book Context` có cấu trúc chuẩn hóa.",
                        "4. Bước 4 - Suy luận và Tạo sinh Câu trả lời (Generation): Ghép nối System Prompt (chỉ định quy tắc trả lời tiếng Việt, bắt buộc trung thực dựa trên context, phân tích cảm xúc, so sánh bảng) + Recent Conversation History + Retrieved Book Context + Câu hỏi hiện tại, gửi đến Google Gemini 2.5/3.6 Flash.",
                        "5. Bước 5 - Truyền phát Thời gian thực (SSE Streaming): Mô hình sinh câu trả lời theo từng đoạn (chunks). Backend đóng gói từng chunk vào định dạng `data: {\"chunk\": \"...\"}\\n\\n` và truyền về Client qua Server-Sent Events. Khi kết thúc, gửi gói tin `{\"done\": true, \"answer\": \"...\", \"books\": [...]}` và lưu trữ lịch sử vào SQLite.",
                        "",
                        "[HÌNH ẢNH MINH HỌA 3.2: Sơ đồ luồng xử lý tuần tự (Sequence Diagram) của tiến trình RAG Streaming SSE]"
                    ]
                }
            ]
        },
        {
            "heading": "3.3 Thiết kế dữ liệu",
            "paragraphs": [
                "Cơ sở dữ liệu của đồ án được thiết kế đồng bộ, phân tách rõ ràng giữa dữ liệu bảng có cấu trúc, dữ liệu phi quan hệ vector và dữ liệu người dùng giao dịch."
            ],
            "subsections": [
                {
                    "heading": "3.3.1 Cấu trúc kho dữ liệu sách (data/books.csv)",
                    "paragraphs": [
                        "Tệp `data/books.csv` là nguồn chân lý dữ liệu (Single Source of Truth) cho 208 cuốn sách trong thư viện. Mỗi bản ghi gồm 12 trường thuộc tính được chuẩn hóa nghiêm ngặt, mô tả chi tiết trong Bảng 3.1:"
                    ]
                }
            ],
            "tables": [
                {
                    "caption": "Bảng 3.1. Cấu trúc trường dữ liệu của tệp books.csv (208 đầu sách).",
                    "headers": ["Tên trường", "Kiểu dữ liệu", "Bắt buộc", "Mô tả chi tiết và Ví dụ"],
                    "rows": [
                        ["book_id", "String (PK)", "Có", "Mã định danh duy nhất của cuốn sách trong hệ thống. Ví dụ: 'book_001', 'book_208'."],
                        ["title", "String", "Có", "Tựa đề đầy đủ của cuốn sách bằng tiếng Việt. Ví dụ: 'Atomic Habits - Thay Đổi Tí Hon, Hiệu Quả Bất Ngờ'."],
                        ["author", "String", "Có", "Tên tác giả hoặc nhóm tác giả biên soạn. Ví dụ: 'James Clear'."],
                        ["genre", "String", "Có", "Thể loại chính của cuốn sách. Ví dụ: 'Kỹ năng sống', 'Công nghệ thông tin'."],
                        ["year", "Integer", "Có", "Năm xuất bản của cuốn sách. Ví dụ: 2018, 2021."],
                        ["publisher", "String", "Không", "Nhà xuất bản ấn hành tại Việt Nam. Ví dụ: 'NXB Thế Giới', 'NXB Trẻ'."],
                        ["description", "Text", "Có", "Mô tả tổng quan nội dung và bối cảnh cuốn sách (200 - 500 từ)."],
                        ["summary", "Text", "Có", "Bản tóm lược các bài học hoặc luận điểm cốt lõi nhất của ấn phẩm."],
                        ["target_audience", "String", "Không", "Đối tượng độc giả hướng tới. Ví dụ: 'Sinh viên, người đi làm muốn xây dựng thói quen tốt'."],
                        ["tags", "String", "Có", "Danh sách từ khóa ngữ nghĩa phân tách bằng dấu phẩy. Ví dụ: 'thoi quen, nang suat, phat trien ban than'."],
                        ["isbn", "String", "Có", "Mã số tiêu chuẩn quốc tế cho sách (ISBN-10 hoặc ISBN-13). Ví dụ: '9786047752187'."],
                        ["rating", "Float", "Có", "Điểm đánh giá trung bình của độc giả trên thang điểm 5.0 (từ 1.0 đến 5.0)."],
                        ["cover_image", "String (URL)", "Có", "Đường dẫn URL tải ảnh bìa chất lượng cao từ CDN (Open Library / Apple Books)."]
                    ]
                }
            ]
        },
        {
            "heading": "3.3.2 Cấu trúc cơ sở dữ liệu quan hệ SQLite (social_community.db)",
            "paragraphs": [
                "Hệ thống sử dụng SQLite để quản lý người dùng, bảo mật và lưu vết tương tác. Các bảng chính được thiết kế như sau:"
            ],
            "tables": [
                {
                    "caption": "Bảng 3.2. Cấu trúc các bảng quan hệ trong cơ sở dữ liệu SQLite.",
                    "headers": ["Tên bảng", "Khóa chính", "Các trường thuộc tính cốt lõi", "Chức năng nghiệp vụ"],
                    "rows": [
                        ["users", "id (INT AUTO)", "username (VARCHAR UK), hashed_password, role ('user'/'admin'), created_at", "Lưu trữ tài khoản người dùng, băm mật khẩu Bcrypt và phân quyền RBAC."],
                        ["chat_sessions", "session_id (UUID PK)", "user_id (FK), title (VARCHAR), top_k (INT), temperature (FLOAT), created_at, updated_at", "Quản lý danh sách các phiên chat của từng tài khoản, lưu cấu hình RAG riêng."],
                        ["chat_messages", "id (INT AUTO)", "session_id (FK), role ('user'/'assistant'), content (TEXT), sources (JSON), locations (JSON), timestamp", "Lưu trữ toàn bộ nội dung tin nhắn, nguồn sách trích dẫn và địa điểm đính kèm."],
                        ["user_bookshelf", "id (INT AUTO)", "user_id (FK), book_id (VARCHAR), shelf_type ('favorite'/'reading'/'finished'), added_at", "Quản lý tủ sách cá nhân: sách yêu thích, sách đang đọc và sách đã hoàn thành."],
                        ["reading_progress", "id (INT AUTO)", "user_id (FK), book_id (VARCHAR), current_chapter, progress_percentage, last_read_at", "Ghi nhớ tiến độ đọc sách điện tử trực tuyến theo thời gian thực của người dùng."]
                    ]
                }
            ]
        },
        {
            "heading": "3.3.3 Thiết kế cấu trúc dữ liệu Vector trong ChromaDB",
            "paragraphs": [
                "Trong ChromaDB, hệ thống khởi tạo Collection chuyên biệt có tên `books_collection`. Mỗi cuốn sách tương ứng với một bản ghi vector có cấu trúc như sau:"
            ],
            "tables": [
                {
                    "caption": "Bảng 3.3. Cấu trúc một phần tử chỉ mục trong ChromaDB Collection.",
                    "headers": ["Thành phần", "Kiểu dữ liệu", "Mô tả nội dung lưu trữ"],
                    "rows": [
                        ["ID", "String", "Mã cuốn sách tương ứng trong CSV, ví dụ: 'book_001'."],
                        ["Document (Chunk Text)", "Text", "Đoạn văn bản tổng hợp giàu ngữ nghĩa: bao gồm Tiêu đề, Tác giả, Thể loại, Mô tả, Tóm lược, Đối tượng và Tags nhằm tối ưu hóa khả năng biểu diễn ngữ nghĩa của mô hình embedding."],
                        ["Embedding Vector", "Float Array [768]", "Vector nhúng 768 chiều được sinh ra bởi mô hình gemini-embedding-2 từ đoạn Document."],
                        ["Metadata", "Dictionary", "Bao gồm các trường tìm kiếm nhanh: {'book_id': '...', 'title': '...', 'author': '...', 'genre': '...', 'year': 2018, 'isbn': '...', 'rating': 4.8}."]
                    ]
                }
            ]
        },
        {
            "heading": "3.4 Thiết kế các giải thuật và quy trình xử lý cốt lõi",
            "paragraphs": [
                "Các giải thuật xử lý đóng vai trò huyết mạch tạo nên trí thông minh, độ chính xác và tính thích ứng cao của hệ thống."
            ],
            "subsections": [
                {
                    "heading": "3.4.1 Bộ định tuyến ý định thông minh (intent_router.py)",
                    "paragraphs": [
                        "Khi nhận câu hỏi từ người dùng, việc đẩy toàn bộ truy vấn vào quy trình RAG gây lãng phí tài nguyên và làm chậm tốc độ phản hồi đối với những câu hỏi thông thường. Bộ định tuyến `intent_router.py` sử dụng cây quyết định kết hợp biểu thức chính quy (Regex) và phân tích từ vựng tiếng Việt để phân loại câu hỏi vào đúng 1 trong 12 nhóm ý định:"
                    ]
                }
            ],
            "tables": [
                {
                    "caption": "Bảng 3.4. Bảng phân loại 12 nhóm Intent trong bộ định tuyến intent_router.py.",
                    "headers": ["Mã Intent", "Tên nhóm ý định", "Dấu hiệu nhận biết đặc trưng", "Hành động xử lý của hệ thống"],
                    "rows": [
                        ["small_talk", "Trò chuyện xã giao", "Chào hỏi ('xin chào', 'hello'), cảm ơn ('cảm ơn bạn'), tâm sự ('tôi buồn').", "Phản hồi hội thoại tự nhiên, đồng cảm, không gọi RAG."],
                        ["book_query", "Truy vấn sách ngữ nghĩa", "Hỏi nội dung, xin gợi ý sách, tìm sách theo chủ đề, nhu cầu học tập.", "Kích hoạt RAG: ChromaDB Cosine Search -> Gemini RAG."],
                        ["book_comparison", "So sánh các cuốn sách", "Chứa từ khóa 'so sánh', 'nên đọc cuốn nào giữa', 'khác nhau thế nào'.", "Kích hoạt Multi-Document RAG -> Bắt buộc vẽ Bảng Markdown."],
                        ["book_search", "Tìm kiếm tựa sách", "Chứa 'tìm sách', 'cuốn sách tên là', 'có sách nào của'.", "Tìm kiếm chính xác trong Catalog sách CSV theo tiêu đề/ISBN."],
                        ["book_detail", "Xem chi tiết cuốn sách", "Chứa 'chi tiết về cuốn', 'sách này nói về gì', 'nội dung cuốn'.", "Truy xuất bản ghi sách cụ thể, trả về full metadata và tóm tắt."],
                        ["author_search", "Tìm kiếm tác giả", "Chứa 'tác giả', 'sách của ai viết', 'những tác phẩm của'.", "Lọc danh sách sách theo tên tác giả tương ứng."],
                        ["genre_search", "Tìm theo thể loại", "Chứa 'thể loại nào', 'những thể loại có trong thư viện'.", "Thống kê và hiển thị danh mục các thể loại sách."],
                        ["read_book", "Đọc sách trực tuyến", "Chứa 'đọc sách', 'muốn đọc', 'mở sách', 'đọc online'.", "Mở giao diện Digital Reader hiển thị nội dung điện tử."],
                        ["library_info", "Thống kê thư viện số", "Chứa 'có bao nhiêu sách', 'số lượng cuốn', 'thư viện có bao nhiêu'.", "Đếm trực tiếp số lượng sách trong CSV (208 cuốn) và báo cáo."],
                        ["location_library", "Tìm thư viện thực tế", "Chứa 'thư viện', 'tìm thư viện', 'thư viện ở đâu', 'mượn sách ở đâu'.", "Tra cứu Thư viện Đà Nẵng / thành phố yêu cầu qua Maps API."],
                        ["location_bookstore", "Tìm nhà sách thực tế", "Chứa 'nhà sách', 'hiệu sách', 'mua sách ở đâu', 'địa chỉ nhà sách'.", "Tra cứu các nhà sách FAHASA, Phương Nam gần vị trí yêu cầu."],
                        ["set_location", "Cập nhật vị trí người dùng", "Chứa 'tôi ở Hà Nội', 'khu vực Đà Nẵng', 'tại TP.HCM'.", "Lưu vị trí người dùng vào session, sẵn sàng cho tìm kiếm địa điểm."]
                    ]
                }
            ]
        },
        {
            "heading": "3.4.2 Thiết kế quy trình RAG Pipeline và Prompt Engineering nâng cao",
            "paragraphs": [
                "Trong `rag_engine.py`, System Prompt được thiết kế công phu nhằm chỉ dẫn mô hình Gemini hành xử như một chuyên gia tư vấn thư viện thông thái, bao gồm 3 trụ cột kỹ thuật nâng cao:",
                "1. Nguyên tắc Neo chặt Tri thức (Grounding Rules):",
                "   - Chỉ được phép sử dụng thông tin trong `RETRIEVED BOOK CONTEXT` để giải đáp.",
                "   - Không tự ý bịa đặt tên sách, tác giả, năm xuất bản hay nội dung mới.",
                "   - Khi câu hỏi nằm ngoài phạm vi dữ liệu sách hiện có, bắt buộc phải trả lời trung thực: 'Dữ liệu thư viện hiện chưa có thông tin về cuốn sách này'.",
                "2. Kỹ thuật Suy luận Đa tài liệu (Multi-Document Reasoning):",
                "   - Khi người dùng yêu cầu so sánh hoặc hỏi nên chọn cuốn nào, mô hình BẮT BUỘC phải tổ chức câu trả lời dưới dạng Bảng Markdown chuẩn GFM với các cột: Tiêu chí so sánh, Cuốn sách 1, Cuốn sách 2, Đối tượng phù hợp. Sau bảng phải có đoạn tổng kết đúc rút lời khuyên thực tế.",
                "3. Kỹ thuật Phân tích Cảm xúc người đọc (Sentiment Analysis):",
                "   - Đọc vị cảm xúc của người dùng qua văn phong: Nếu người dùng biểu lộ tâm trạng tiêu cực (mệt mỏi, căng thẳng, buồn bã), AI phải mở đầu bằng lời đồng cảm, chia sẻ nhẹ nhàng và ưu tiên gợi ý các cuốn sách chữa lành, tâm lý, giải tỏa áp lực. Nếu người dùng hào hứng, quyết tâm, AI đáp lại bằng năng lượng tích cực và gợi ý sách phát triển bản thân, tư duy đột phá."
            ]
        },
        {
            "heading": "3.4.3 Thiết kế luồng Định vị Nhà sách, Thư viện và Cơ chế Fallback Đà Nẵng",
            "paragraphs": [
                "Để kết nối sách từ thế giới số đến đời thực, `location_service.py` và `chat_router.py` cung cấp tính năng tìm kiếm địa điểm vật lý:",
                "- Trích xuất thực thể địa danh: Sử dụng biểu thức chính quy nhận diện các cấu trúc ngữ pháp như 'ở [địa danh]', 'tại [địa danh]', 'khu vực [địa danh]'.",
                "- Cơ chế Fallback thông minh: Một vấn đề thực tế phát sinh là người dùng thường gõ rất ngắn gọn: 'thư viện' hoặc 'nhà sách gần đây' mà không nói rõ tỉnh/thành. Khi đó, hệ thống tự động kiểm tra lịch sử chat; nếu vẫn chưa có địa danh, hệ thống tự động chọn mặc định là 'Đà Nẵng' (địa bàn phục vụ chính của đề tài) và trả về ngay danh sách địa điểm thực tế kèm ghi chú thân thiện, tuyệt đối không báo lỗi thiếu dữ liệu.",
                "- Gọi dịch vụ bản đồ: Hệ thống gửi truy vấn đến dịch vụ bản đồ (Google Places API / Overpass OpenStreetMap), lọc theo bán kính, trả về danh sách gồm: Tên địa điểm, Địa chỉ cụ thể, Tọa độ kinh độ/vĩ độ, và khoảng cách ước tính."
            ]
        },
        {
            "heading": "3.4.4 Thiết kế luồng AI Crawler, Kiểm soát Trùng lặp và Tự chữa lành Vector Sync",
            "paragraphs": [
                "Mô-đun `crawler_service.py` giúp thư viện liên tục mở rộng tri thức một cách tự động:",
                "1. Thu thập dữ liệu: Tiếp nhận từ khóa tìm kiếm sách online, gọi SerpApi Google Books để lấy về danh sách các đầu sách tiềm năng kèm đầy đủ metadata và ảnh bìa.",
                "2. Thuật toán kiểm tra trùng lặp (Deduplication):",
                "   - Kiểm tra mã ISBN: Nếu ISBN đã tồn tại trong `books.csv` -> Đánh dấu TRÙNG LẶP (Duplicate).",
                "   - So khớp mờ (Fuzzy Matching): Nếu tên sách và tác giả trùng khớp sau khi chuẩn hóa chữ thường và bỏ dấu tiếng Việt -> Đánh dấu TRÙNG LẶP.",
                "   - Chỉ cho phép quản trị viên nhập những cuốn sách chưa có trong hệ thống, tự động sinh mã `book_xxx` tiếp theo một cách an toàn.",
                "3. Cơ chế Tự chữa lành đồng bộ Vector (Self-Healing Vector Sync):",
                "   - Khi cào sách hoặc import sách mới, nếu xảy ra sự cố mạng làm gián đoạn tiến trình tạo embedding, sách có thể đã ghi vào CSV nhưng bị thiếu vector trong ChromaDB.",
                "   - Hàm `get_unindexed_books()` đối chiếu toàn bộ ID trong CSV với ID trong bảng SQLite của ChromaDB.",
                "   - Giao diện Admin hiển thị bảng cảnh báo những sách chưa có vector và cung cấp nút 'Đồng bộ ngay'. Tiến trình chỉ tính toán embedding và chèn bổ sung các sách còn thiếu (Idempotency) mà không cần xóa hay xây dựng lại toàn bộ cơ sở dữ liệu."
            ]
        },
        {
            "heading": "3.4.5 Thuật toán Chuẩn hóa Văn bản phục vụ Text-to-Speech (audio_service.py)",
            "paragraphs": [
                "Các công cụ Text-to-Speech (TTS) thông thường sẽ phát âm rất kỳ quặc khi gặp các ký tự định dạng Markdown (như dấu sao `**`, dấu thăng `#`, gạch nối, code block hay bảng biểu). Hàm `clean_markdown_for_speech()` trong `backend/services/audio_service.py` được thiết kế đặc thù:",
                "- Loại bỏ sạch sẽ các ký tự Markdown `#`, `*`, `_`, `~`, backticks ```` ``` ````.",
                "- Loại bỏ các đường dẫn siêu liên kết URL (`https://...`).",
                "- Đặc biệt, giải thuật phân tích bảng Markdown (Markdown Tables): Tách các dòng bảng `| Cột 1 | Cột 2 |`, trích xuất tiêu đề cột và nội dung từng dòng, sau đó chuyển hóa thành câu thoại đối thoại tự nhiên: 'Về tiêu chí [Cột 1], cuốn [Sách A] là [...], trong khi cuốn [Sách B] là [...]'.",
                "- Văn bản sau khi làm sạch được đưa vào `gTTS(lang='vi')` để tổng hợp thành luồng âm thanh MP3 mượt mà, truyền phát tức thì tới loa của người dùng."
            ]
        }
    ]
}
