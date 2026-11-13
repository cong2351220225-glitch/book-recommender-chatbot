# -*- coding: utf-8 -*-
"""
Front matter content: Trang bìa, Lời cam đoan, Lời cảm ơn, Tóm tắt (Abstract).
"""

COVER_DATA = {
    "ministry": "BỘ GIÁO DỤC VÀ ĐÀO TẠO",
    "university": "TRƯỜNG ĐẠI HỌC KIẾN TRÚC ĐÀ NẴNG",
    "faculty": "KHOA CÔNG NGHỆ THÔNG TIN",
    "report_type": "BÁO CÁO ĐỒ ÁN TRÍ TUỆ NHÂN TẠO",
    "course_code": "Học phần AIP202 · 2 tín chỉ",
    "project_title": "XÂY DỰNG TRỢ LÝ ẢO TƯ VẤN VÀ GỢI Ý SÁCH THÔNG MINH ĐA PHƯƠNG THỨC ỨNG DỤNG KIẾN TRÚC RAG, GOOGLE GEMINI, FASTAPI VÀ FLUTTER DESKTOP",
    "project_subtitle": "(AI Digital Library & Multimodal Book Recommender Chatbot)",
    "student_name": "Trần Hồng Công",
    "student_class": "23CT5",
    "student_major": "Công nghệ thông tin",
    "supervisor": "TS. Đỗ Phúc Hảo",
    "academic_year": "2026 - 2027",
    "location_year": "Đà Nẵng · 2026 - 2027"
}

STATEMENT_OF_INTEGRITY = """Tôi xin cam đoan đồ án này là công trình do chính tôi thực hiện dưới sự hướng dẫn khoa học của TS. Đỗ Phúc Hảo. Các nội dung nghiên cứu, phân tích kiến trúc, triển khai mã nguồn, số liệu thực nghiệm và kết quả đánh giá trình bày trong đồ án là hoàn toàn trung thực, khách quan và chưa từng được công bố trong bất kỳ công trình nghiên cứu nào khác.

Mọi số liệu khảo sát, hình ảnh kiến trúc, tài liệu tham khảo và thư viện mã nguồn mở của các tác giả khác được sử dụng trong đồ án đều được trích dẫn nguồn gốc xuất xứ rõ ràng và đầy đủ theo đúng quy chuẩn học thuật trong phần Tài liệu tham khảo. Toàn bộ phần mềm và thư viện lập trình được sử dụng đều tuân thủ giấy phép nguồn mở tương ứng. Quá trình phát triển và kiểm thử có sử dụng các công cụ trí tuệ nhân tạo hỗ trợ đã được khai báo và giải trình chi tiết trong nội dung báo cáo.

Nếu có bất kỳ sự gian lận hoặc vi phạm liêm chính học thuật nào bị phát hiện, tôi xin chịu hoàn toàn trách nhiệm trước Hội đồng đánh giá, Khoa Công nghệ Thông tin và Nhà trường."""

ACKNOWLEDGMENTS = """Lời đầu tiên, em xin bày tỏ lòng biết ơn sâu sắc và chân thành nhất đến TS. Đỗ Phúc Hảo – người thầy đã tận tình định hướng đề tài, gợi mở các hướng nghiên cứu hiện đại, tận tâm góp ý và theo sát tiến độ của em trong suốt quá trình triển khai và hoàn thiện đồ án này. Những lời chỉ dẫn quý báu của Thầy về kiến trúc hệ thống, nguyên lý xử lý ngôn ngữ tự nhiên và tư duy giải quyết vấn đề kỹ thuật thực tế là nền tảng cốt lõi giúp em vượt qua các thách thức công nghệ trong đề tài.

Em cũng xin trân trọng gửi lời cảm ơn đến quý Thầy, Cô giáo trong Khoa Công nghệ Thông tin – Trường Đại học Kiến trúc Đà Nẵng đã trang bị cho em nền tảng kiến thức chuyên môn vững chắc, tư duy khoa học và kỹ năng thực hành nghề nghiệp trong suốt các năm học vừa qua.

Cuối cùng, em xin gửi lời cảm ơn chân thành đến gia đình, người thân và bạn bè đã luôn ở bên cạnh động viên, khích lệ tinh thần và tạo mọi điều kiện thuận lợi nhất để em hoàn thành xuất sắc đồ án tốt nghiệp này."""

ABSTRACT_VI = """Trong kỷ nguyên bùng nổ thông tin và chuyển đổi số giáo dục, việc tìm kiếm và tiếp cận nguồn sách phù hợp với nhu cầu, năng lực và mục tiêu cá nhân của người đọc đang đối mặt với nhiều rào cản. Các hệ thống thư viện truyền thống dựa vào tra cứu từ khóa chính xác thường bộc lộ hạn chế rõ rệt khi người dùng diễn đạt nhu cầu bằng ngôn ngữ tự nhiên phức tạp. Mặt khác, các Mô hình Ngôn ngữ Lớn (LLMs) tạo sinh tuy có khả năng đối thoại linh hoạt nhưng lại thường mắc lỗi "ảo giác" (hallucination) và thiếu tri thức chuyên sâu về kho dữ liệu cục bộ thực tế của thư viện.

Nhằm giải quyết triệt để các vấn đề trên, đồ án này nghiên cứu và phát triển toàn diện Hệ thống Thư viện số và Trợ lý ảo gợi ý sách thông minh Đa phương thức (AI Digital Library & Multimodal Book Recommender Chatbot). Hệ thống kết hợp đột phá giữa kiến trúc Tạo sinh Tăng cường Truy xuất (Retrieval-Augmented Generation - RAG), Cơ sở dữ liệu Vector ChromaDB với độ đo Cosine Distance và mô hình tạo sinh Google Gemini 2.5/3.6 Flash. Về mặt kiến trúc, hệ thống được thiết kế theo mô hình Microservices/Client-Server hiện đại: Backend xây dựng trên nền tảng FastAPI hiệu năng cao, cung cấp hơn 25 RESTful API endpoints cùng cơ chế truyền phát trực tiếp dữ liệu Server-Sent Events (SSE); Frontend được triển khai đa nền tảng gồm bản Web tham chiếu bằng Streamlit và ứng dụng Desktop thương mại chuyên nghiệp bằng Flutter C++ Runner trên Windows x64.

Hệ thống mở rộng năng lực tương tác thông minh qua 3 cơ chế đa phương thức (Multimodal AI): (1) Computer Vision nhận diện ảnh bìa sách để tự động khớp nối thông tin kho sách; (2) Speech-to-Text (STT) nhận diện giọng nói tiếng Việt chuẩn xác bằng Gemini Multimodal Audio; (3) Text-to-Speech (TTS) tự động làm sạch Markdown/GFM và chuyển đổi câu trả lời thành luồng âm thanh MP3 stream phát tức thì, khắc phục hoàn toàn lỗi thiếu giọng đọc tiếng Việt SAPI trên hệ điều hành Windows. Hệ thống cũng tích hợp bộ định tuyến ý định thông minh (Intent Router) với 12 nhóm ngữ cảnh, tính năng bản đồ tìm kiếm vị trí nhà sách/thư viện thực tế (tích hợp Google Maps và cơ chế Fallback Đà Nẵng), cùng mô-đun AI Crawler tự động thu thập và tự chữa lành đồng bộ dữ liệu vector.

Kết quả thực nghiệm trên bộ dữ liệu chuẩn hóa gồm 208 đầu sách tiếng Việt (208 vector embedding 768 chiều) cho thấy hệ thống hoạt động cực kỳ ổn định, đạt tỷ lệ vượt qua 100% trong toàn bộ 41/41 ca kiểm thử tự động (Unit & Integration tests từ Phase 1 đến Phase 5). Thời gian trễ sinh từ đầu tiên (TTFT) qua SSE đạt dưới 1.2 giây; bảng so sánh sách Markdown cuộn ngang giải quyết dứt điểm hiện tượng tràn layout Desktop. Hệ thống chứng minh tính khả thi cao, đáp ứng xuất sắc các tiêu chí về độ chính xác, tính tương tác đa phương thức và trải nghiệm người dùng hiện đại."""

ABSTRACT_EN = """In the era of information explosion and digital transformation in education, discovering and accessing literature tailored to individual reader needs, competencies, and personal objectives poses considerable challenges. Traditional library catalog systems relying on exact lexical keyword matching fail to satisfy complex, contextual queries expressed in natural language. Conversely, while general-purpose Large Language Models (LLMs) provide natural conversational fluency, they are inherently susceptible to factual hallucinations and lack domain-specific awareness of a local library's tangible inventory.

To address these challenges comprehensively, this project designs and implements an enterprise-grade Multimodal AI Digital Library and Book Recommender Assistant. The architecture integrates Retrieval-Augmented Generation (RAG) paradigms, the ChromaDB vector database utilizing Cosine Distance metrics, and Google's state-of-the-art Gemini 2.5/3.6 Flash generative models. Built upon a high-performance Client-Server and Microservices architecture, the backend is engineered with FastAPI, exposing over 25 secured RESTful endpoints alongside real-time Server-Sent Events (SSE) streaming. The frontend offers cross-platform parity, featuring both a reference Streamlit web portal and a native Flutter Desktop application powered by the Windows x64 C++ Runner.

The system pioneers multimodal human-computer interaction across three distinct vectors: (1) Computer Vision for instant book cover analysis and catalog reconciliation; (2) Speech-to-Text (STT) for Vietnamese voice recognition via Gemini Multimodal Audio; and (3) Text-to-Speech (TTS) incorporating automated GFM Markdown normalization and real-time MP3 streaming, effectively bypassing Windows SAPI Vietnamese voice limitations. Additionally, the system incorporates an intelligent Intent Router handling 12 distinct conversational categories, location-aware library and bookstore mapping (leveraging Google Maps with Da Nang fallback mechanisms), and an autonomous AI Crawler with self-healing vector synchronization.

Empirical evaluations across a standardized collection of 208 Vietnamese books (208 corresponding 768-dimensional embeddings) demonstrate exceptional robustness, achieving a 100% pass rate across 41 comprehensive automated test cases (Phases 1 through 5). Time to First Token (TTFT) in streaming generation averaged under 1.2 seconds, and horizontally responsive Markdown tables eliminated desktop layout overflows entirely. The solution proves highly viable for modern academic and public digital libraries, offering superior retrieval grounding, multimodal adaptability, and polished user ergonomics."""
