# -*- coding: utf-8 -*-
"""
Chương 1: Mở đầu (Introduction)
"""

CHAPTER_1_DATA = {
    "title": "Chương 1. Mở đầu",
    "sections": [
        {
            "heading": "1.1 Lý do chọn đề tài",
            "paragraphs": [
                "Trong dòng chảy chuyển đổi số toàn diện của cuộc Cách mạng Công nghiệp lần thứ tư, tri thức nhân loại đang được số hóa với tốc độ cấp số nhân. Sách và các tài liệu học thuật vẫn luôn giữ vị thế là nguồn tài nguyên tri thức cốt lõi, phục vụ đắc lực cho hoạt động học tập, nghiên cứu khoa học và hoàn thiện bản thân của con người. Tuy nhiên, sự gia tăng nhanh chóng về số lượng và chủng loại đầu sách trong các thư viện số hiện đại lại đặt ra một bài toán nghịch lý: người đọc ngày càng gặp nhiều khó khăn, mất nhiều thời gian và công sức để tiếp cận được đúng ấn phẩm phù hợp với nhu cầu học tập, sở thích đọc, tâm trạng hay trình độ chuyên môn của mình.",
                "Các hệ thống thư viện truyền thống và cổng tra cứu sách điện tử hiện nay hầu như vẫn vận hành dựa trên cơ chế tìm kiếm từ khóa kinh điển (lexical keyword matching) như tìm kiếm theo tiêu đề sách, tên tác giả, nhà xuất bản hoặc mã định danh tiêu chuẩn ISBN. Phương pháp tiếp cận cơ học này bộc lộ những rào cản rất lớn khi người dùng diễn đạt nhu cầu tìm kiếm bằng ngôn ngữ tự nhiên trừu tượng hoặc các câu hỏi đa chiều. Ví dụ, khi một sinh viên muốn tìm 'một cuốn sách nhập môn giúp rèn luyện tư duy logic cho người chưa biết lập trình' hoặc 'cuốn sách kỹ năng giúp chữa lành tâm lý và vượt qua áp lực công việc cho bạn trẻ', các bộ lọc từ khóa truyền thống gần như bất lực hoặc chỉ trả về các kết quả rời rạc, thiếu ngữ cảnh và không đúng trọng tâm.",
                "Sự bùng nổ của Trí tuệ Nhân tạo Tạo sinh (Generative AI), tiêu biểu là các Mô hình Ngôn ngữ Lớn (Large Language Models - LLMs) như Google Gemini, GPT-4, hay Claude, đã mở ra kỷ nguyên mới cho các giao diện đàm thoại thông minh. Người dùng có thể trò chuyện tự nhiên, trình bày khúc mắc và nhận được những phân tích, tổng hợp sâu sắc. Tuy nhiên, nếu chỉ sử dụng đơn lẻ mô hình LLM thuần túy, hệ thống đối mặt với hai rủi ro sống còn trong môi trường thư viện: hiện tượng 'ảo giác' (hallucination) - mô hình tự thêu dệt nên các cuốn sách, tác giả hoặc tóm tắt hoàn toàn không có thật; và vấn đề thiếu tri thức cục bộ - mô hình chỉ được huấn luyện trên dữ liệu đại trà trong quá khứ mà không có thông tin thời gian thực về kho sách thực tế đang lưu trữ tại thư viện.",
                "Để dung hòa hoàn hảo giữa khả năng truy xuất dữ liệu xác thực và năng lực suy luận ngôn ngữ tự nhiên xuất sắc, kiến trúc Tạo sinh Tăng cường Truy xuất (Retrieval-Augmented Generation - RAG) ra đời như một giải pháp chuẩn mực hàng đầu. RAG cho phép hệ thống truy xuất các đoạn văn bản (chunks) liên quan nhất từ cơ sở dữ liệu vector cục bộ thông qua biểu diễn ngữ nghĩa (embeddings), sau đó truyền các tài liệu thực tế này vào ngữ cảnh (context) đầu vào của LLM. Nhờ đó, câu trả lời do AI sinh ra luôn được neo chặt (grounded) trên cơ sở dữ liệu có sẵn, triệt tiêu ảo giác và mang lại độ tin cậy tuyệt đối.",
                "Xuất phát từ những phân tích thực tiễn và yêu cầu khoa học cấp thiết trên, đề tài 'Xây dựng Trợ lý ảo Tư vấn và Gợi ý Sách Thông minh Đa phương thức ứng dụng kiến trúc RAG, Google Gemini, FastAPI và Flutter Desktop' được lựa chọn thực hiện. Đề tài không chỉ giải quyết trọn vẹn bài toán gợi ý sách ngữ nghĩa mà còn tích hợp các năng lực tương tác đa phương thức hiện đại (AI Vision nhận diện ảnh bìa sách, Speech-to-Text, Text-to-Speech) và kiến trúc đa nền tảng (Web Streamlit đối chiếu & Flutter Windows Desktop chuyên nghiệp), mang lại giá trị ứng dụng cao cho ngành thư viện số và giáo dục thông minh."
            ]
        },
        {
            "heading": "1.2 Mục tiêu của đồ án",
            "paragraphs": [
                "Đồ án tập trung nghiên cứu, thiết kế và phát triển hoàn chỉnh một hệ thống phần mềm hoàn chỉnh từ A đến Z, hướng tới 6 mục tiêu cụ thể như sau:",
                "1. Mục tiêu 1 – Xây dựng và chuẩn hóa kho dữ liệu tri thức sách: Thu thập, làm sạch và chuẩn hóa bộ dữ liệu thực tế gồm 208 cuốn sách tiếng Việt đa dạng thể loại (Kỹ năng sống, Công nghệ thông tin, Trí tuệ nhân tạo, Kinh doanh khởi nghiệp, Văn học, Tâm lý học...). Thiết lập cấu trúc dữ liệu toàn diện bao gồm: định danh ID, tiêu đề, tác giả, thể loại, năm xuất bản, nhà xuất bản, mô tả chi tiết, bản tóm lược, đối tượng độc giả, từ khóa gắn nhãn (tags), mã số ISBN, đánh giá rating và đường dẫn ảnh bìa.",
                "2. Mục tiêu 2 – Xây dựng quy trình tìm kiếm ngữ nghĩa với ChromaDB: Triển khai pipeline chuyển đổi văn bản sách thành các vector embeddings 768 chiều chất lượng cao bằng mô hình nhúng tiên tiến của Google (gemini-embedding-2 / text-embedding-004). Lưu trữ và chỉ mục hóa 208 vector vào cơ sở dữ liệu vector ChromaDB, áp dụng độ đo khoảng cách Cosine Distance để truy xuất các đoạn tri thức có độ tương đồng ngữ nghĩa cao nhất với câu hỏi của người dùng.",
                "3. Mục tiêu 3 – Tích hợp Chatbot RAG với cơ chế định tuyến ý định và chống ảo giác: Kết nối ChromaDB với mô hình tạo sinh Google Gemini (phiên bản 2.5-flash và 3.6-flash). Xây dựng bộ định tuyến ý định (Intent Router) nhận diện chính xác 12 nhóm hội thoại khác nhau; áp dụng kỹ thuật Prompt Engineering nâng cao với quy tắc Grounding nghiêm ngặt (chỉ trả lời dựa trên context được truy xuất, từ chối lịch sự khi dữ liệu không đủ) và hỗ trợ phân tích đa tài liệu để so sánh sách theo bảng Markdown.",
                "4. Mục tiêu 4 – Phát triển Backend RESTful API & Server-Sent Events (FastAPI): Xây dựng hệ thống Backend hoàn chỉnh trên nền tảng FastAPI (Python 3.13), cung cấp hơn 25 API endpoints bảo mật bằng JWT và phân quyền người dùng (RBAC: Guest, User, Admin). Triển khai cơ chế truyền phát dữ liệu thời gian thực Server-Sent Events (SSE) cho phép mô hình AI phản hồi từng token mượt mà, giảm thiểu độ trễ cảm nhận của người dùng.",
                "5. Mục tiêu 5 – Nâng cấp trải nghiệm tương tác đa phương thức (Multimodal AI) trên Flutter Desktop Windows: Xây dựng ứng dụng Desktop thương mại bằng Flutter C++ Runner trên Windows x64. Tích hợp 3 tính năng đa phương thức vượt trội: (a) AI Vision quét và nhận diện bìa sách từ ảnh chụp; (b) Voice STT nhận diện giọng nói tiếng Việt bằng Gemini Multimodal Audio; (c) AI TTS chuyển đổi câu trả lời văn bản thành luồng âm thanh MP3 stream phát tức thì, đồng thời render bảng so sánh Markdown GFM cuộn ngang chống tràn màn hình.",
                "6. Mục tiêu 6 – Kiểm thử tự động và đánh giá chất lượng toàn diện: Xây dựng bộ kịch bản kiểm thử tự động toàn diện từ Phase 1 đến Phase 5 bằng Pytest với 41/41 ca kiểm thử đạt tỷ lệ thành công 100%. Đo lường cụ thể các chỉ số thời gian phản hồi (Latency), độ chính xác phân loại ý định (Intent Classification Accuracy), tính nhất quán dữ liệu và cơ chế tự chữa lành đồng bộ vector (Self-Healing Vector Sync)."
            ]
        },
        {
            "heading": "1.3 Phạm vi và đối tượng",
            "paragraphs": [
                "Để đảm bảo tính khả thi, chiều sâu nghiên cứu và chất lượng hoàn thiện của đồ án, phạm vi và đối tượng nghiên cứu được xác định rõ ràng qua 5 khía cạnh:"
            ],
            "subsections": [
                {
                    "heading": "1.3.1 Đối tượng nghiên cứu",
                    "paragraphs": [
                        "Đối tượng nghiên cứu trọng tâm của đồ án là Hệ thống trợ lý ảo tư vấn và thư viện số thông minh kết hợp kiến trúc RAG đa phương thức. Cụ thể bao gồm:",
                        "- Cấu trúc dữ liệu metadata của sách, phương pháp phân tích văn bản và kỹ thuật biểu diễn ngữ nghĩa (Vector Embedding).",
                        "- Cơ chế lưu trữ, lập chỉ mục và truy vấn không gian vector đa chiều trong ChromaDB sử dụng độ đo khoảng cách Cosine.",
                        "- Kỹ thuật định tuyến ý định người dùng (Intent Routing) dựa trên phân tích từ vựng và mô hình phân loại truy vấn.",
                        "- Kiến trúc kết hợp giữa tri thức truy xuất và mô hình ngôn ngữ lớn Google Gemini thông qua Prompt Engineering và System Instructions.",
                        "- Phương pháp xử lý đa phương thức: Phân tích thị giác máy tính (Computer Vision) với ảnh bìa sách và xử lý tín hiệu âm thanh (STT / TTS tiếng Việt).",
                        "- Quy trình thiết kế kiến trúc phần mềm Client-Server hiện đại, tích hợp giữa FastAPI Backend và Flutter Windows Desktop Client."
                    ]
                },
                {
                    "heading": "1.3.2 Phạm vi dữ liệu",
                    "paragraphs": [
                        "Dữ liệu phục vụ nghiên cứu và thực nghiệm được giới hạn ở kho dữ liệu thực tế gồm 208 cuốn sách tiếng Việt đã được thu thập, tinh chọn và chuẩn hóa từ các nguồn dữ liệu uy tín (như Apple Books API, Open Library và các nhà xuất bản uy tín tại Việt Nam).",
                        "Kho dữ liệu bao quát 10 thể loại sách phổ biến: Kỹ năng sống & Phát triển bản thân, Công nghệ thông tin & Lập trình, Trí tuệ nhân tạo, Kinh doanh & Khởi nghiệp, Tâm lý học, Văn học & Tiểu thuyết, Lịch sử & Triết học, Khoa học tự nhiên, Thiếu nhi & Giáo dục, Y học & Sức khỏe.",
                        "Dữ liệu được lưu trữ có cấu trúc trong tệp `data/books.csv`, tệp tác giả `authors.csv`, tệp thể loại `genres.csv` và cơ sở dữ liệu quan hệ SQLite `social_community.db` lưu trữ thông tin người dùng, lịch sử chat và tủ sách cá nhân."
                    ]
                },
                {
                    "heading": "1.3.3 Phạm vi ngôn ngữ",
                    "paragraphs": [
                        "Hệ thống tập trung tối ưu hóa chuyên sâu cho dữ liệu tiếng Việt có dấu chuẩn xác và tiếp nhận các câu hỏi, truy vấn của người dùng bằng tiếng Việt tự nhiên.",
                        "Các mô-đun tiền xử lý văn bản, hàm chuẩn hóa tiếng Việt loại bỏ dấu thanh khi so khớp fuzzy (`_normalize_query`), mô hình nhận diện giọng nói tiếng Việt và tổng hợp giọng đọc tiếng Việt đều được cấu hình và tinh chỉnh chuyên biệt cho ngôn ngữ tiếng Việt.",
                        "Đồ án không đặt mục tiêu xây dựng một hệ thống đa ngôn ngữ phức hợp nhiều thứ tiếng, nhằm tập trung nâng cao tối đa độ chính xác ngữ nghĩa cho ngữ cảnh ngôn ngữ và văn hóa đọc tại Việt Nam."
                    ]
                },
                {
                    "heading": "1.3.4 Phạm vi chức năng",
                    "paragraphs": [
                        "Các nhóm chức năng hoàn chỉnh thuộc phạm vi triển khai của đồ án gồm có:",
                        "1. Nhóm chức năng Quản lý Kho sách: Tìm kiếm toàn cục theo tên, ISBN, tác giả; bộ lọc nâng cao theo năm xuất bản, khoảng rating, ngôn ngữ, thể loại; xem chi tiết sách, mục lục và đọc sách trực tuyến.",
                        "2. Nhóm chức năng Trợ lý ảo RAG Chatbot: Đàm thoại ngôn ngữ tự nhiên theo ngữ cảnh (Multi-turn conversational memory); tư vấn và gợi ý sách cá nhân hóa; so sánh đa sách bằng bảng Markdown GFM cuộn ngang; phản hồi tức thì qua giao thức Server-Sent Events (SSE).",
                        "3. Nhóm chức năng Tương tác Đa phương thức: AI Vision quét ảnh bìa sách qua camera/file ảnh; Voice STT nhận diện câu hỏi từ microphone; AI TTS đọc câu trả lời bằng audio stream MP3 kèm thanh điều khiển đa trạng thái (Play/Pause/Resume/Stop).",
                        "4. Nhóm chức năng Định vị và Bản đồ: Tìm kiếm vị trí các nhà sách và thư viện thực tế tại Đà Nẵng và các tỉnh thành lớn trên bản đồ Google Maps và thẻ địa chỉ trực quan.",
                        "5. Nhóm chức năng Quản trị & Đồng bộ Vector (Admin): Tìm kiếm và cào sách tự động qua AI Crawler; thuật toán đối soát chống trùng lặp; bảng điều khiển theo dõi và đồng bộ sách thiếu vector vào ChromaDB theo thời gian thực (Self-Healing Sync)."
                    ]
                },
                {
                    "heading": "1.3.5 Giới hạn của đề tài",
                    "paragraphs": [
                        "Bên cạnh những tính năng toàn diện đã đạt được, đồ án tồn tại một số giới hạn nghiên cứu khách quan:",
                        "- Quy mô kho dữ liệu hiện tại dừng lại ở 208 cuốn sách mẫu điển hình nhằm phục vụ nghiên cứu thực nghiệm và đánh giá chất lượng giải thuật trong phạm vi một đồ án tốt nghiệp, chưa mở rộng ra quy mô hàng triệu đầu sách thương mại.",
                        "- Năng lực tạo sinh của Chatbot RAG và các mô-đun AI Vision/STT phụ thuộc vào kết nối Internet để gọi API của Google Gemini và dịch vụ bản đồ số.",
                        "- Hệ thống chưa triển khai hạ tầng phân tán trên cụm máy chủ đám mây (Cloud Kubernetes cluster) mà hiện tối ưu hóa để triển khai cục bộ (On-premises / Local Server) và đóng gói cài đặt ứng dụng Desktop trên hệ điều hành Windows."
                    ]
                }
            ]
        },
        {
            "heading": "1.4 Phương pháp nghiên cứu",
            "paragraphs": [
                "Để đảm bảo tính khoa học, chặt chẽ và bám sát thực tiễn công nghiệp, đồ án áp dụng kết hợp đồng bộ 4 phương pháp nghiên cứu:",
                "1. Phương pháp nghiên cứu lý thuyết: Thu thập, tổng hợp và phân tích các tài liệu học thuật quốc tế, bài báo khoa học hàng đầu về Mô hình Ngôn ngữ Lớn, cơ chế Transformer Attention, kiến trúc RAG (Retrieval-Augmented Generation), kỹ thuật Dense Vector Embeddings, thuật toán xấp xỉ lân cận gần nhất (HNSW / Approximate Nearest Neighbors) và độ đo Cosine Similarity.",
                "2. Phương pháp phân tích và thiết kế hệ thống: Khảo sát nghiệp vụ tra cứu thư viện thực tế; xây dựng đặc tả yêu cầu người dùng (User Requirements); thiết kế kiến trúc hệ thống Client-Server phân tầng; chuẩn hóa cơ sở dữ liệu và thiết kế giao diện theo triết lý trải nghiệm người dùng (UX/UI) trực quan, hiện đại.",
                "3. Phương pháp thực nghiệm và phát triển lặp (Iterative Software Engineering): Áp dụng quy trình phát triển phần mềm linh hoạt theo từng giai đoạn (Phase 1 đến Phase 5). Tại mỗi giai đoạn đều xây dựng các nguyên mẫu (prototypes), triển khai mã nguồn, tiến hành kiểm thử đơn vị, kiểm thử tích hợp và nghiệm thu tính năng tương đương giữa bản Web và bản Desktop.",
                "4. Phương pháp đo lường và đánh giá định lượng: Thiết kế bộ kịch bản kiểm thử tự động toàn diện; thu thập và phân tích định lượng các chỉ số hiệu năng hệ thống: thời gian đáp ứng API, thời gian trễ sinh từ đầu tiên (TTFT), độ chính xác phân loại ý định người dùng và khả năng kiểm soát ảo giác của mô hình AI."
            ]
        },
        {
            "heading": "1.5 Bố cục báo cáo",
            "paragraphs": [
                "Báo cáo đồ án được cấu trúc một cách logic, mạch lạc thành 6 chương chính cùng danh mục tài liệu tham khảo và các phụ lục kỹ thuật:",
                "- Chương 1: Mở đầu – Trình bày tổng quan về bối cảnh, lý do chọn đề tài, mục tiêu nghiên cứu, phạm vi, đối tượng, phương pháp tiếp cận và cấu trúc tài liệu.",
                "- Chương 2: Cơ sở lý thuyết và công nghệ – Trình bày cơ sở khoa học về LLM, Google Gemini, kiến trúc RAG, Vector Database ChromaDB, độ đo Cosine Distance, trí tuệ nhân tạo đa phương thức và tổng hợp các công cụ, thư viện sử dụng.",
                "- Chương 3: Phân tích và thiết kế hệ thống – Phân tích yêu cầu chức năng, phi chức năng; thiết kế kiến trúc tổng thể 3 tầng; thiết kế chi tiết dữ liệu (CSV, SQLite, ChromaDB); thiết kế các giải thuật cốt lõi (Intent Router, RAG Pipeline, Location Matching, AI Crawler, Audio Cleaning).",
                "- Chương 4: Cài đặt và thử nghiệm – Chi tiết môi trường triển khai; tổng hợp 25+ RESTful API endpoints; cài đặt các mô-đun Backend FastAPI; cài đặt ứng dụng Flutter Desktop Windows x64; trình bày kết quả bộ kiểm thử tự động 41 test cases.",
                "- Chương 5: Kết quả và đánh giá – Đánh giá đối chiếu mục tiêu đạt được; đo lường các chỉ số hiệu năng định lượng; bàn luận chuyên sâu về 4 giải pháp kỹ thuật thực tiễn độc đáo đã vượt qua rào cản nền tảng; chỉ ra các hạn chế của đề tài.",
                "- Chương 6: Kết luận và hướng phát triển – Tổng kết các đóng góp chính của đồ án; đúc kết các bài học kinh nghiệm quý giá về kỹ nghệ phần mềm và đề xuất định hướng mở rộng hệ thống trong tương lai.",
                "- Tài liệu tham khảo và Phụ lục – Danh mục các công trình học thuật trích dẫn chuẩn; hướng dẫn cài đặt chạy chương trình cho Hội đồng; bảng tự kiểm tra liêm chính học thuật và phiếu nhận xét của Giảng viên hướng dẫn."
            ]
        }
    ]
}
