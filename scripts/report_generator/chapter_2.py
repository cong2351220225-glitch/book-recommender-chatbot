# -*- coding: utf-8 -*-
"""
Chương 2: Cơ sở lý thuyết và công nghệ (Theoretical Background & Technologies)
"""

CHAPTER_2_DATA = {
    "title": "Chương 2. Cơ sở lý thuyết và công nghệ",
    "sections": [
        {
            "heading": "2.1 Kiến thức nền tảng",
            "paragraphs": [
                "Để xây dựng một hệ thống thư viện số và trợ lý ảo thông minh hoạt động chính xác, ổn định và có khả năng tương tác đa phương thức, đồ án dựa trên nền tảng của các lý thuyết và kỹ thuật hiện đại nhất trong lĩnh vực Xử lý Ngôn ngữ Tự nhiên (Natural Language Processing - NLP), Thị giác Máy tính (Computer Vision), Xử lý Tín hiệu Âm thanh (Audio Signal Processing) và Kỹ nghệ Phần mềm Đa nền tảng."
            ],
            "subsections": [
                {
                    "heading": "2.1.1 Mô hình ngôn ngữ lớn (LLMs) và Kiến trúc Transformer",
                    "paragraphs": [
                        "Mô hình Ngôn ngữ Lớn (Large Language Models - LLMs) đại diện cho bước nhảy vọt mang tính cách mạng của trí tuệ nhân tạo hiện đại. Cốt lõi của các LLMs là kiến trúc mạng nơ-ron Transformer được đề xuất bởi Vaswani và các cộng sự (2017) trong công trình kinh điển 'Attention Is All You Need'. Khác biệt căn bản của Transformer so với các kiến trúc hồi quy tuần tự trước đây (như RNN hay LSTM) nằm ở cơ chế Tự chú ý Đa đầu (Multi-Head Self-Attention).",
                        "Cơ chế Self-Attention cho phép mô hình tính toán mối tương quan ngữ nghĩa giữa tất cả các từ trong một câu văn bản đồng thời mà không phụ thuộc vào khoảng cách tuyến tính giữa chúng. Với đầu vào gồm ma trận biểu diễn các vector Truy vấn (Query - Q), Khóa (Key - K) và Giá trị (Value - V) có số chiều $d_k$, trọng số chú ý được tính toán theo công thức tích vô hướng tỉ lệ (Scaled Dot-Product Attention):",
                        "Attention(Q, K, V) = softmax( (Q * K^T) / sqrt(d_k) ) * V",
                        "Nhờ cơ chế này, mô hình có khả năng thấu hiểu sâu sắc ngữ pháp, ngữ cảnh phức tạp, thành ngữ, đại từ thay thế và các mối liên kết ngữ nghĩa ẩn trong văn bản dài. Được huấn luyện trên khối lượng dữ liệu khổng lồ (hàng nghìn tỷ tokens văn bản), các LLMs sở hữu năng lực suy luận ngôn ngữ, tóm tắt, dịch thuật và đối thoại tự nhiên vượt trội so với các hệ chuyên gia truyền thống."
                    ]
                },
                {
                    "heading": "2.1.2 Mô hình Google Gemini thế hệ mới",
                    "paragraphs": [
                        "Trong đề tài này, mô hình ngôn ngữ lớn được tin tưởng lựa chọn làm bộ não suy luận là thế hệ mô hình Google Gemini (cụ thể là các phiên bản Gemini 2.5-flash và Gemini 3.6-flash). Google Gemini được thiết kế theo kiến trúc Đa phương thức Bản địa (Natively Multimodal) ngay từ giai đoạn tiền huấn luyện, cho phép mô hình tiếp nhận, thấu hiểu và xử lý đồng thời nhiều dạng dữ liệu khác nhau như văn bản, hình ảnh, âm thanh và video mà không cần phải kết hợp rời rạc các mô hình đơn lẻ.",
                        "Phiên bản Gemini Flash nổi bật với ưu thế vượt trội về tốc độ suy luận cực nhanh, thời gian phản hồi mili-giây và chi phí tính toán tối ưu, đặc biệt phù hợp cho các ứng dụng đối thoại thời gian thực và xử lý luồng dữ liệu liên tục (streaming). Ngoài ra, Gemini hỗ trợ cửa sổ ngữ cảnh khổng lồ (lên đến 1 triệu tokens), cơ chế gọi hàm (Function Calling / Tool Use) mạnh mẽ và khả năng tuân thủ nghiêm ngặt các chỉ thị hệ thống (System Instructions) được cấu hình sẵn."
                    ]
                },
                {
                    "heading": "2.1.3 Kiến trúc Tạo sinh Tăng cường Truy xuất (RAG) & Cơ chế Grounding",
                    "paragraphs": [
                        "Mặc dù các mô hình ngôn ngữ lớn rất mạnh mẽ, việc ứng dụng trực tiếp LLMs vào các hệ thống chuyên biệt như thư viện thường gặp phải hai rào cản chí mạng: rào cản 'ảo giác' (Hallucination - mô hình tự tin khẳng định những thông tin sai lệch hoặc không tồn tại) và rào cản 'dữ liệu đóng' (mô hình không thể truy cập vào kho sách nội bộ riêng biệt của thư viện).",
                        "Kiến trúc RAG (Retrieval-Augmented Generation), được khởi xướng bởi Lewis và các cộng sự (2020), ra đời nhằm khắc phục triệt để các hạn chế trên. Quy trình hoạt động của RAG trong đồ án bao gồm ba giai đoạn liên hoàn:",
                        "1. Giai đoạn Chỉ mục hóa (Indexing): Dữ liệu các cuốn sách trong kho được chuẩn hóa, phân đoạn (chunking) và chuyển đổi thành các vector nhúng (embeddings) lưu trữ sẵn trong cơ sở dữ liệu vector.",
                        "2. Giai đoạn Truy xuất (Retrieval): Khi người dùng đưa ra câu hỏi, câu hỏi được chuyển đổi thành vector truy vấn có cùng không gian số chiều. Hệ thống thực hiện tìm kiếm ngữ nghĩa để tìm ra Top-K cuốn sách hoặc đoạn văn bản có độ tương đồng cao nhất trong kho dữ liệu.",
                        "3. Giai đoạn Tăng cường và Tạo sinh (Augmentation & Generation): Các tài liệu truy xuất được đóng gói thành một ngữ cảnh có cấu trúc (Retrieved Book Context). Ngữ cảnh này được ghép cùng câu hỏi của người dùng và truyền vào System Prompt của Google Gemini. Mô hình được chỉ thị nghiêm ngặt (Grounding) rằng chỉ được phép sử dụng tri thức trong ngữ cảnh cung cấp để giải đáp, nếu thiếu thông tin phải lịch sự thông báo chưa có dữ liệu.",
                        "Nhờ kiến trúc RAG, câu trả lời của trợ lý ảo luôn đảm bảo tính xác thực 100%, không bị bịa đặt tên sách hay tác giả, đồng thời cho phép cập nhật tri thức thư viện ngay lập tức mà không cần tốn kém chi phí tái huấn luyện (re-training) hoặc tinh chỉnh (fine-tuning) mô hình."
                    ]
                },
                {
                    "heading": "2.1.4 Kỹ thuật Vector Embeddings và Độ đo khoảng cách Cosine trong ChromaDB",
                    "paragraphs": [
                        "Tìm kiếm ngữ nghĩa (Semantic Search) là trái tim của giai đoạn truy xuất trong RAG. Để máy tính có thể so sánh ý nghĩa của hai đoạn văn bản thay vì so sánh mặt chữ, văn bản cần được ánh xạ vào một không gian vector đa chiều dày đặc (Dense Vector Space) thông qua các mô hình Embedding (mô hình `gemini-embedding-2` tạo ra vector có $n = 768$ chiều). Trong không gian này, những cuốn sách có nội dung hoặc chủ đề tương tự nhau sẽ nằm gần nhau về mặt hình học.",
                        "Để lượng hóa khoảng cách ngữ nghĩa giữa vector câu hỏi của người dùng $\\vec{u}$ và vector của cuốn sách $\\vec{v}$, hệ thống áp dụng độ đo Độ tương đồng Cosine (Cosine Similarity) và Khoảng cách Cosine (Cosine Distance). Độ tương đồng Cosine đo góc giữa hai vector trong không gian $n$ chiều, dao động trong đoạn $[-1, 1]$:",
                        "Cosine Similarity(u, v) = (u . v) / ( ||u|| * ||v|| ) = ( sum_{i=1}^n u_i * v_i ) / ( sqrt(sum_{i=1}^n u_i^2) * sqrt(sum_{i=1}^n v_i^2) )",
                        "Khoảng cách Cosine (Cosine Distance) biểu thị độ lệch ngữ nghĩa, có giá trị càng nhỏ thì hai văn bản càng giống nhau:",
                        "Cosine Distance(u, v) = 1 - Cosine Similarity(u, v)",
                        "Trong đồ án, cơ sở dữ liệu vector mã nguồn mở ChromaDB được tích hợp trực tiếp. ChromaDB sử dụng cấu trúc đồ thị phân tầng Hierarchical Navigable Small World (HNSW) kết hợp với độ đo Cosine. Thuật toán HNSW cho phép tìm kiếm xấp xỉ lân cận gần nhất (Approximate Nearest Neighbors - ANN) với độ phức tạp thời gian đạt cấp số $O(\\log N)$, giúp hệ thống thực hiện truy vấn Top-K cực nhanh chỉ trong vài mili-giây ngay cả khi số lượng vector gia tăng."
                    ]
                },
                {
                    "heading": "2.1.5 Trí tuệ nhân tạo Đa phương thức (Multimodal AI): Thị giác máy tính và Xử lý Âm thanh",
                    "paragraphs": [
                        "Nhằm nâng cao tối đa trải nghiệm người dùng hiện đại, đồ án mở rộng giao tiếp vượt ra ngoài giới hạn bàn phím văn bản thông thường bằng cách ứng dụng AI Đa phương thức:",
                        "- Thị giác Máy tính (Computer Vision): Mô hình Gemini Vision được tích hợp để đọc hiểu hình ảnh ảnh bìa sách tải lên từ máy tính hoặc camera. Mô hình tự động nhận diện bố cục chữ, trích xuất chính xác tựa đề sách, tên tác giả, nhà xuất bản và phân loại sơ bộ thể loại sách từ các đặc trưng đồ họa và văn bản trên bìa.",
                        "- Nhận diện giọng nói (Speech-to-Text - STT): Hệ thống sử dụng khả năng phân tích âm thanh đa phương thức của Gemini để giải mã tín hiệu giọng nói tiếng Việt từ micro máy tính, nhận diện chuẩn xác ngữ âm tiếng Việt có dấu đầy đủ.",
                        "- Tổng hợp giọng nói (Text-to-Speech - TTS): Hệ thống sử dụng công nghệ chuyển đổi văn bản thành tiếng nói tự nhiên (`gTTS`), tích hợp bộ lọc tiền xử lý làm sạch cú pháp Markdown, mã code và bảng biểu, chuyển hóa câu trả lời của AI thành âm thanh MP3 truyền phát theo thời gian thực (Audio Streaming) tới người nghe."
                    ]
                }
            ]
        },
        {
            "heading": "2.2 Công cụ và thư viện",
            "paragraphs": [
                "Hệ thống được xây dựng dựa trên sự kết hợp hài hòa giữa các công nghệ Backend hiệu năng cao và Framework Frontend hiện đại. Toàn bộ các công cụ, thư viện và thành phần phần mềm được sử dụng trong đồ án được tổng hợp chi tiết trong Bảng 2.1 dưới đây:"
            ],
            "tables": [
                {
                    "caption": "Bảng 2.1. Danh mục công cụ, thư viện và công nghệ sử dụng trong đồ án.",
                    "headers": ["Thành phần công nghệ", "Phiên bản", "Phân loại", "Vai trò và chức năng trong hệ thống"],
                    "rows": [
                        ["Python", "3.13.x", "Ngôn ngữ cốt lõi", "Ngôn ngữ lập trình chính cho toàn bộ hệ sinh thái Backend, xử lý dữ liệu và AI."],
                        ["FastAPI", "0.115+", "Web Framework", "Xây dựng hệ thống RESTful API bất đồng bộ (Asynchronous), hỗ trợ OpenAPI/Swagger và SSE."],
                        ["Uvicorn", "0.34+", "ASGI Server", "Máy chủ web hiệu năng cao chuẩn ASGI chạy ứng dụng FastAPI trên port 8000."],
                        ["ChromaDB", "0.6.x", "Vector Database", "Cơ sở dữ liệu vector nhúng cục bộ, lưu trữ và tìm kiếm vector 768 chiều bằng thuật toán HNSW."],
                        ["Google GenAI SDK", "0.8+", "AI SDK", "Bộ thư viện chính thức kết nối với Google Gemini API (gemini-2.5/3.6-flash, gemini-embedding-2)."],
                        ["SQLite", "3.x", "Relational DB", "Cơ sở dữ liệu quan hệ nhẹ lưu trữ người dùng, phân quyền, lịch sử chat và tủ sách cá nhân."],
                        ["Pydantic", "2.10+", "Data Validation", "Định nghĩa Schema, kiểm tra hợp lệ kiểu dữ liệu request/response giữa Client và Backend."],
                        ["PyJWT / Passlib", "2.9+ / 1.7+", "Bảo mật & Auth", "Mã hóa mật khẩu bằng thuật toán Bcrypt và tạo mã thông báo xác thực JWT."],
                        ["Pillow (PIL)", "11.x", "Xử lý ảnh", "Xử lý ảnh bìa sách, kiểm tra magic bytes (JPEG/PNG), giới hạn dung lượng bộ nhớ RAM an toàn."],
                        ["gTTS", "2.5+", "Tổng hợp âm thanh", "Chuyển đổi câu trả lời văn bản tiếng Việt thành luồng âm thanh MP3 stream trong RAM."],
                        ["Flutter SDK", "3.24+", "Cross-Platform UI", "Bộ công cụ phát triển ứng dụng giao diện đa nền tảng bằng ngôn ngữ Dart."],
                        ["Flutter Windows Runner", "C++ / CMake", "Desktop Engine", "Bộ khung biên dịch C++ native runner cho ứng dụng Windows x64 Desktop."],
                        ["Audioplayers", "6.1.0", "Flutter Plugin", "Plugin phát âm thanh MP3 stream trên Windows với đầy đủ các trạng thái điều khiển."],
                        ["Record", "5.2.0", "Flutter Plugin", "Plugin ghi âm âm thanh trực tiếp từ microphone trên hệ điều hành Windows."],
                        ["Flutter Markdown", "0.7.4", "Flutter Plugin", "Phân tích và hiển thị văn bản định dạng Markdown GitHub Flavored trong chat bubble."],
                        ["File Picker", "8.1.7", "Flutter Plugin", "Mở hộp thoại chọn tệp hình ảnh native của Windows để tải ảnh bìa sách."],
                        ["Streamlit", "1.40+", "Web Framework", "Xây dựng phiên bản Web đối chiếu phục vụ kiểm tra tính tương đương chức năng."],
                        ["Pytest", "9.x", "Kiểm thử phần mềm", "Khung kiểm thử tự động toàn diện từ Phase 1 đến Phase 5 với 41 test cases."]
                    ]
                }
            ]
        },
        {
            "heading": "2.3 Các công trình liên quan",
            "paragraphs": [
                "Lĩnh vực gợi ý sách và trợ lý thư viện đã trải qua nhiều giai đoạn phát triển với các cách tiếp cận công nghệ khác nhau. Việc khảo sát các công trình liên quan giúp định vị rõ tính mới và ưu thế vượt trội của đồ án:",
                "1. Phương pháp Lọc cộng tác (Collaborative Filtering): Các hệ thống gợi ý truyền thống như Amazon Book Recommender hay Goodreads dựa trên ma trận người dùng - sản phẩm (User-Item Matrix) và các thuật toán phân rã ma trận (Matrix Factorization như SVD). Điểm mạnh của phương pháp này là khai thác tốt hành vi số đông, nhưng gặp điểm yếu chí mạng là bài toán 'Khởi động lạnh' (Cold-start problem) - hoàn toàn bất lực khi người dùng mới chưa có lịch sử đọc hoặc sách mới nhập chưa có lượt đánh giá. Ngoài ra, phương pháp này không thể giải thích nguyên nhân tại sao cuốn sách đó phù hợp với người đọc.",
                "2. Phương pháp Lọc theo nội dung (Content-Based Filtering): Dựa trên việc phân tích thuộc tính văn bản của sách bằng mô hình túi từ (Bag of Words) hoặc TF-IDF. Mặc dù giải quyết được bài toán khởi động lạnh cho sách mới, phương pháp này chỉ so khớp từ vựng bề mặt (syntactic matching) mà không hiểu được quan hệ đồng nghĩa hay ngữ cảnh sâu sắc (ví dụ: không nhận ra 'AI' và 'trí tuệ nhân tạo' là một).",
                "3. Ứng dụng LLMs thuần túy không có RAG: Một số nghiên cứu gần đây sử dụng trực tiếp ChatGPT hoặc Gemini qua giao diện web để gợi ý sách. Dù đàm thoại tự nhiên, các mô hình này mắc phải sai lầm nghiêm trọng khi tự tạo ra các đầu sách không có thật, hoặc gợi ý những cuốn sách tiếng Anh ngoại văn không có sẵn trong thư viện địa phương, gây thất vọng cho người đọc.",
                "4. Tính mới và đột phá của đồ án: Đồ án này kế thừa ưu điểm của kiến trúc RAG hiện đại nhất thế giới, đồng thời tiên phong bổ sung 3 điểm sáng tạo kỹ thuật độc đáo: (a) Kết hợp hoàn hảo giữa tìm kiếm ngữ nghĩa ChromaDB và mô hình Gemini tạo sinh để gợi ý chính xác tuyệt đối theo kho sách thực tế 208 cuốn; (b) Nâng cấp năng lực tương tác đa phương thức toàn diện (ảnh bìa Vision, giọng nói STT, phát âm TTS); (c) Hiện thực hóa kiến trúc Client-Server đa nền tảng với ứng dụng Desktop Flutter Windows hoàn chỉnh, đóng gói thương mại và độc lập hoàn toàn với trình duyệt web."
            ]
        }
    ]
}
