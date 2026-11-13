# -*- coding: utf-8 -*-
"""
Chương 4: Cài đặt và thử nghiệm (Implementation & Testing)
"""

CHAPTER_4_DATA = {
    "title": "Chương 4. Cài đặt và thử nghiệm",
    "sections": [
        {
            "heading": "4.1 Môi trường triển khai",
            "paragraphs": [
                "Hệ thống được phát triển, tối ưu hóa và kiểm thử thực nghiệm trên môi trường máy trạm phần cứng tiêu chuẩn và cấu hình phần mềm hiện đại, đảm bảo tính sẵn sàng triển khai thực tế:",
                "- Cấu hình phần cứng: Vi xử lý Intel Core i7 (hoặc tương đương), 16 GB RAM DDR4/DDR5, ổ cứng thể rắn SSD NVMe 512 GB tốc độ cao, card mạng Gigabit Ethernet / Wi-Fi 6 kết nối Internet băng thông rộng.",
                "- Cấu hình phần mềm hệ thống: Hệ điều hành Microsoft Windows 10/11 Pro 64-bit; môi trường thực thi Python 3.13.x với môi trường ảo cách ly (.venv); trình biên dịch C++ Visual Studio Community 2022 (MSVC v143 / v180) tích hợp công cụ tạo lập CMake 3.28+; Flutter SDK 3.24+ trên kênh ổn định (channel stable) tích hợp Dart SDK 3.13+.",
                "- Cấu hình biến môi trường và khóa bảo mật: Dự án quản lý tập trung các tham số cấu hình nhạy cảm thông qua tệp `.env`, bao gồm: `GEMINI_API_KEY` (khóa xác thực truy cập Google GenAI), `SERPAPI_API_KEY` (khóa dịch vụ cào dữ liệu Google Books), `JWT_SECRET_KEY` (chuỗi khóa bí mật mã hóa token phiên), `CHROMA_PATH` (đường dẫn lưu trữ vector `chroma_db/`), `PORT=8000` (cổng mạng dịch vụ FastAPI)."
            ]
        },
        {
            "heading": "4.2 Cài đặt các thành phần Backend (FastAPI)",
            "paragraphs": [
                "Backend của hệ thống được tổ chức chuyên nghiệp, phân tách thành các bộ định tuyến (Routers) và tầng dịch vụ (Services) độc lập. Toàn bộ hơn 25 API endpoints được tổng hợp chi tiết trong Bảng 4.1:"
            ],
            "tables": [
                {
                    "caption": "Bảng 4.1. Danh mục các RESTful API endpoints cốt lõi của Backend FastAPI.",
                    "headers": ["Phương thức", "Đường dẫn API (Endpoint)", "Quyền hạn", "Chức năng và Dữ liệu trao đổi"],
                    "rows": [
                        ["POST", "/api/v1/auth/register", "Public", "Đăng ký tài khoản người dùng mới; kiểm tra trùng username; băm mật khẩu Bcrypt."],
                        ["POST", "/api/v1/auth/login", "Public", "Xác thực tài khoản; cấp mã thông báo JWT access_token có thời hạn 7 ngày."],
                        ["GET", "/api/v1/auth/me", "User", "Lấy thông tin tài khoản đang đăng nhập từ token Bearer Authorization."],
                        ["GET", "/api/v1/books", "Public", "Lấy danh sách sách có phân trang; hỗ trợ lọc theo thể loại, tác giả, năm, rating."],
                        ["GET", "/api/v1/books/{book_id}", "Public", "Lấy toàn bộ thông tin chi tiết, mô tả, tóm tắt và mục lục của một cuốn sách."],
                        ["GET", "/api/v1/books/search", "Public", "Tìm kiếm toàn cục theo từ khóa tiêu đề, ISBN, tác giả không phân biệt hoa thường."],
                        ["GET", "/api/v1/books/authors", "Public", "Lấy danh sách thống kê toàn bộ các tác giả và số lượng sách tương ứng."],
                        ["GET", "/api/v1/books/genres", "Public", "Lấy danh mục các thể loại sách hiện có trong kho thư viện."],
                        ["POST", "/api/v1/books/recognize-cover", "Public / User", "AI Vision: Tải file ảnh bìa (<=8MB); Gemini Vision nhận diện tựa đề/tác giả."],
                        ["POST", "/api/v1/chat/message", "Public / User", "Gửi tin nhắn chat RAG thông thường (JSON response kèm danh sách sources)."],
                        ["POST", "/api/v1/chat/stream", "Public / User", "Server-Sent Events: Truyền phát luồng trả lời AI RAG thời gian thực."],
                        ["POST", "/api/v1/chat/tts", "Public / User", "AI TTS: Nhận văn bản làm sạch Markdown, trả về luồng âm thanh audio/mpeg."],
                        ["POST", "/api/v1/chat/transcribe-audio", "Public / User", "Voice STT: Tải file âm thanh giọng nói, Gemini nhận diện ra văn bản tiếng Việt."],
                        ["GET", "/api/v1/chat/sessions", "User", "Lấy danh sách các phiên chat của tài khoản đang đăng nhập (User Isolation)."],
                        ["DELETE", "/api/v1/chat/sessions/{id}", "User", "Xóa vĩnh viễn một phiên chat sau khi người dùng xác nhận."],
                        ["GET", "/api/v1/chat/history/{id}", "User", "Tải lại toàn bộ lịch sử tin nhắn của một phiên chat cụ thể."],
                        ["GET", "/api/v1/locations/search", "Public", "Tìm kiếm vị trí nhà sách, thư viện theo địa danh hoặc fallback mặc định Đà Nẵng."],
                        ["GET", "/api/v1/crawler/search", "Admin", "Cào dữ liệu sách online qua SerpApi; trả về danh sách sách tiềm năng."],
                        ["POST", "/api/v1/crawler/import", "Admin", "Đối soát chống trùng lặp và nhập các cuốn sách được chọn vào books.csv."],
                        ["GET", "/api/v1/crawler/unindexed", "Admin", "Thống kê và liệt kê danh sách các cuốn sách trong CSV chưa được tạo vector."],
                        ["POST", "/api/v1/crawler/sync", "Admin", "Đồng bộ hóa các sách thiếu vector vào ChromaDB theo thời gian thực (Self-Healing)."],
                        ["GET", "/api/v1/health", "Public", "Kiểm tra sức khỏe hệ thống: số lượng sách trong CSV và số vector trong ChromaDB."]
                    ]
                }
            ]
        },
        {
            "heading": "4.2.1 Minh họa cài đặt mã nguồn các giải thuật cốt lõi Backend",
            "paragraphs": [
                "Dưới đây là một số đoạn mã nguồn cốt lõi tiêu biểu minh họa cho kiến trúc xử lý của hệ thống:",
                "Mã nguồn 4.1. Hàm phân loại ý định người dùng trong `intent_router.py`:",
                "```python\ndef classify_intent(question: str, conversation_history: list[dict] | None = None) -> str:\n    normalized = _normalize_query(question)\n    if not question or not question.strip():\n        return UNKNOWN\n\n    # 1. Ưu tiên nhận diện LIBRARY_INFO nếu câu hỏi về số lượng sách, tác giả, thể loại\n    library_stat_terms = (\n        \"bao nhieu sach\", \"co bao nhieu\", \"bao nhieu cuon\", \"bao nhieu dau sach\",\n        \"the loai nao\", \"tac gia nao\", \"kho du lieu\", \"kho thu vien\",\n        \"thu vien hien co\", \"du lieu sach\", \"the loai nao nhieu nhat\", \"thong ke\"\n    )\n    if any(term in normalized for term in library_stat_terms):\n        return LIBRARY_INFO\n\n    # 2. Nhận diện các ý định tìm kiếm Địa điểm (Thư viện / Nhà sách thực tế)\n    bookstore_location_terms = (\n        \"nha sach\", \"hieu sach\", \"bookstore\", \"noi ban\", \"tim noi ban\",\n        \"dia chi ban\", \"dia chi mua\", \"mua o dau\", \"ban o dau\", \"dia chi nha sach\",\n        \"mua sach o dau\", \"ban sach o dau\", \"mua sach\", \"ban sach\", \"tim nha sach\",\n        \"tim hieu sach\", \"nha sach gan day\", \"hieu sach gan day\", \"nha sach o dau\"\n    )\n    library_location_terms = (\n        \"thu vien\", \"library\", \"phong doc\", \"muon sach o dau\", \"muon sach\",\n        \"tim thu vien\", \"dia chi thu vien\", \"thu vien o dau\", \"thu vien gan day\",\n        \"thu vien gan toi\", \"thu vien nao\"\n    )\n    if any(term in normalized for term in bookstore_location_terms):\n        return FIND_BOOKSTORE\n    if any(term in normalized for term in library_location_terms):\n        return FIND_LIBRARY\n\n    # 3. Nhận diện so sánh sách đa tài liệu\n    if any(term in normalized for term in (\"so sanh\", \"so sánh\", \"nen doc cuon nao\", \"khac nhau\")):\n        return BOOK_COMPARISON\n\n    return classify_query(question, conversation_history)\n```",
                "Mã nguồn 4.2. Xử lý truyền phát Server-Sent Events (SSE) trong `backend/routers/chat_router.py`:",
                "```python\n@router.post(\"/stream\")\ndef send_chat_message_stream(chat_req: ChatRequest, current_user: dict | None = Depends(get_current_user_optional)):\n    username = current_user.get(\"username\", \"guest\") if current_user else \"guest\"\n    session_id = chat_req.session_id or str(uuid.uuid4())\n    history = _load_session_history(username, session_id)\n\n    def event_generator():\n        detected_intent = classify_intent(chat_req.message, history)\n        if detected_intent in LOCATION_INTENTS:\n            answer, locations, intent, loc = _handle_location_intent(chat_req.message, detected_intent, history, chat_req.top_k)\n            books = []\n        else:\n            answer, books, intent = handle_user_message(chat_req.message, chat_req.top_k, history)\n            locations = []\n\n        # Phân mảnh nhỏ truyền phát mượt mà tới UI Client\n        chunk_size = 20\n        for i in range(0, len(answer), chunk_size):\n            chunk = answer[i : i + chunk_size]\n            yield f\"data: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\\n\\n\"\n\n        # Gói tin hoàn thành (Done event)\n        yield f\"data: {json.dumps({'done': True, 'answer': answer, 'books': books, 'locations': locations, 'intent': intent}, ensure_ascii=False)}\\n\\n\"\n\n    return StreamingResponse(event_generator(), media_type=\"text/event-stream\")\n```"
            ]
        },
        {
            "heading": "4.3 Cài đặt ứng dụng Desktop Flutter Windows Release",
            "paragraphs": [
                "Ứng dụng Flutter Desktop (`mobile_app/`) được thiết kế kiến trúc theo chuẩn Clean Architecture phân lớp, quản lý trạng thái bằng Provider:",
                "- `lib/models/`: Định nghĩa các thực thể dữ liệu (`BookModel`, `UserModel`, `ChatMessageModel`, `BookVisionResult`).",
                "- `lib/services/`: Triển khai các dịch vụ giao tiếp HTTP (`AuthService`, `BookService`, `ChatService`, `VisionService`, `AudioService`).",
                "- `lib/providers/`: Quản lý trạng thái và luồng dữ liệu phản ứng (`AuthProvider`, `ChatProvider`, `BookProvider`).",
                "- `lib/presentation/`: Chứa các màn hình hiển thị và các widget giao diện tùy biến.",
                "",
                "Dưới đây là chi tiết các màn hình và tính năng tiêu biểu của ứng dụng:",
                "1. Màn hình Trợ lý ảo AI Chatbot (AI Chat Screen):",
                "   - Tích hợp Drawer bên trái hiển thị danh sách các phiên chat cá nhân của người dùng kèm tiêu đề tự động và thời gian.",
                "   - Nút 'Tạo đoạn chat mới' và nút xóa phiên với hộp thoại xác nhận an toàn.",
                "   - Dialog cấu hình RAG: Cho phép kéo Slider điều chỉnh Top-K tài liệu truy xuất (từ 1 đến 10) và điều chỉnh Temperature (độ sáng tạo từ 0.0 đến 1.0).",
                "   - Thanh công cụ hội thoại đa phương thức: Tích hợp nút Camera quét ảnh bìa sách, nút Micro ghi âm giọng nói STT, và các chips gợi ý câu hỏi so sánh sách thông minh.",
                "",
                "[HÌNH ẢNH MINH HỌA 4.1: Giao diện Chatbot AI RAG trên Flutter Windows với Drawer lịch sử và thanh công cụ đa phương thức]",
                "",
                "2. Hộp thoại Quét và Nhận diện Ảnh bìa sách (`BookVisionDialog`):",
                "   - Mở cửa sổ chọn file Windows native qua `file_picker`.",
                "   - Hiển thị xem trước ảnh (Image preview) và nút bấm 'Phân tích bìa sách với AI'.",
                "   - Hiển thị kết quả nhận diện: Tiêu đề, Tác giả, Thể loại và Tóm tắt.",
                "   - Khớp nối tự động với sách trong kho và cung cấp 2 nút hành động nhanh: 'Xem chi tiết sách' hoặc 'Hỏi AI về cuốn sách này'.",
                "",
                "[HÌNH ẢNH MINH HỌA 4.2: Hộp thoại AI Vision nhận diện ảnh bìa sách và tự động khớp nối vào kho dữ liệu thư viện]",
                "",
                "3. Trình hiển thị Bảng so sánh Markdown (`MarkdownTableView`) và Điều khiển Âm thanh TTS (`ChatBubble`):",
                "   - Giải quyết triệt để lỗi tràn layout màn hình khi AI trả về bảng so sánh nhiều cột: Widget tự động nhận diện khối bảng và bọc trong khung cuộn ngang `SingleChildScrollView(scrollDirection: Axis.horizontal)`.",
                "   - Từng bóng chat của trợ lý AI tích hợp nút Loa phát âm: Khi bấm, hệ thống gọi API `/chat/tts` và hiển thị mini-player cho phép Tạm dừng (Pause), Tiếp tục (Resume) hoặc Dừng hẳn (Stop).",
                "",
                "[HÌNH ẢNH MINH HỌA 4.3: Giao diện bóng chat AI hiển thị Bảng so sánh Markdown cuộn ngang và thanh phát âm thanh TTS]",
                "",
                "4. Màn hình Kho sách và Bộ lọc Đa tiêu chí (Book Catalog Screen):",
                "   - Thanh tìm kiếm toàn cục với cơ chế Debounce 300ms, hỗ trợ tìm tiếng Việt có dấu và không dấu.",
                "   - Chuyển đổi linh hoạt giữa hai tab kết quả: 'Sách' và 'Tác giả'.",
                "   - Thanh bộ lọc nâng cao bên cạnh: Lọc theo khoảng năm xuất bản, mức rating tối thiểu, ngôn ngữ và thể loại sách.",
                "",
                "[HÌNH ẢNH MINH HỌA 4.4: Màn hình Kho sách và hệ thống bộ lọc nâng cao trên giao diện Desktop Windows]",
                "",
                "5. Màn hình Bản đồ và Định vị Địa điểm Nhà sách / Thư viện (Location Screen):",
                "   - Tích hợp trực tiếp trên Sidebar giao diện.",
                "   - Lựa chọn loại địa điểm: 'Nhà sách' hoặc 'Thư viện'.",
                "   - Ô nhập địa danh với gợi ý nhanh và cơ chế Fallback tự động về Đà Nẵng.",
                "   - Hiển thị danh sách thẻ địa điểm kèm địa chỉ, nút mở chỉ đường trên trình duyệt và bản đồ trực quan.",
                "",
                "[HÌNH ẢNH MINH HỌA 4.5: Màn hình tìm kiếm địa điểm nhà sách và thư viện thực tế tại Đà Nẵng]",
                "",
                "6. Màn hình Quản trị AI Crawler và Đồng bộ ChromaDB Vector Sync (Admin Screen):",
                "   - Chỉ hiển thị với tài khoản có quyền Quản trị viên (`role: admin`).",
                "   - Tab AI Crawler: Nhập từ khóa, cào dữ liệu sách mới từ Internet, hiển thị nhãn cảnh báo 'ĐÃ TỒN TẠI' đối với các sách trùng lặp, cho phép chọn sách và bấm 'Nhập sách vào kho'.",
                "   - Tab ChromaDB Sync: Thẻ thống kê trực quan số lượng sách trong CSV (208) và số vector trong ChromaDB (208); danh sách các sách chưa được index và nút bấm 'Đồng bộ lại vào ChromaDB' thời gian thực.",
                "",
                "[HÌNH ẢNH MINH HỌA 4.6: Màn hình Quản trị AI Crawler và Bảng điều khiển đồng bộ Vector ChromaDB]"
            ]
        },
        {
            "heading": "4.4 Các kịch bản và kết quả kiểm thử phần mềm",
            "paragraphs": [
                "Để chứng minh tính đúng đắn khoa học và độ ổn định công nghiệp của toàn bộ hệ thống, đồ án đã xây dựng bộ kịch bản kiểm thử tự động toàn diện từ Phase 1 đến Phase 5 bằng thư viện Pytest. Bảng 4.2 tổng hợp chi tiết kết quả kiểm thử thực nghiệm:"
            ],
            "tables": [
                {
                    "caption": "Bảng 4.2. Bảng tổng hợp kết quả 41 ca kiểm thử tự động toàn diện từ Phase 1 đến Phase 5.",
                    "headers": ["Giai đoạn (Phase)", "Tập tin kiểm thử", "Số ca test", "Trọng tâm kiểm thử chức năng", "Kết quả thực nghiệm"],
                    "rows": [
                        ["Phase 1: Chat History & RAG Config", "test_phase1_chat_history_rag_config.py", "10 tests", "Lưu trữ phiên chat, phân quyền User Isolation, xóa phiên, cấu hình Top-K Slider (1-10), cấu hình Temperature.", "10/10 PASSED (100%)"],
                        ["Phase 2: Book Catalog & Filters", "test_phase2_book_catalog_advanced_search.py", "9 tests", "Tìm kiếm toàn cục theo tựa đề, ISBN, tác giả; bộ lọc đa tiêu chí (năm, rating, thể loại, ngôn ngữ); phân trang.", "9/9 PASSED (100%)"],
                        ["Phase 3: Locations & Book Actions", "test_phase3_locations_and_book_actions.py", "8 tests", "Tra cứu địa điểm nhà sách/thư viện, trích xuất địa danh, cơ chế fallback Đà Nẵng, 3 hành động nhanh trên chi tiết sách.", "8/8 PASSED (100%)"],
                        ["Phase 4: Crawler & Vector Sync", "test_phase4_crawler_and_chroma_sync.py", "8 tests", "Cào sách online, phát hiện trùng lặp ISBN/tiêu đề, nhập sách an toàn, phát hiện sách thiếu vector, tự chữa lành đồng bộ.", "8/8 PASSED (100%)"],
                        ["Phase 5: Multimodal Vision, TTS, STT", "test_phase5_vision_tts_stt.py", "6 tests", "Làm sạch văn bản Markdown cho TTS, sinh stream MP3 tiếng Việt, nhận diện ảnh bìa, xử lý file lỗi/vượt dung lượng 8MB, STT giọng nói.", "6/6 PASSED (100%)"],
                        ["TỔNG CỘNG HỆ THỐNG", "Toàn bộ 5 bộ kiểm thử", "41 tests", "Kiểm thử hồi quy tích hợp End-to-End toàn bộ hệ thống Backend và Hợp đồng giao tiếp Client-Server.", "41/41 PASSED (100% - Thời gian chạy: 102.57s)"]
                    ]
                }
            ]
        }
    ]
}
