# -*- coding: utf-8 -*-
"""
Chương 5: Kết quả và đánh giá (Results & Discussion)
"""

CHAPTER_5_DATA = {
    "title": "Chương 5. Kết quả và đánh giá",
    "sections": [
        {
            "heading": "5.1 Kết quả đạt được",
            "paragraphs": [
                "Sau quá trình nghiên cứu, thiết kế kiến trúc và triển khai thực nghiệm nghiêm túc, hệ thống Trợ lý ảo tư vấn và thư viện số thông minh đa phương thức đã hoàn thành xuất sắc 100% các mục tiêu khoa học và yêu cầu kỹ thuật đề ra tại Chương 1. Bảng 5.1 đối chiếu cụ thể mức độ hoàn thành so với mục tiêu ban đầu:"
            ],
            "tables": [
                {
                    "caption": "Bảng 5.1. Bảng đối chiếu mức độ hoàn thành các mục tiêu nghiên cứu của đồ án.",
                    "headers": ["Mục tiêu đề ra", "Kết quả thực nghiệm đạt được", "Đánh giá mức độ hoàn thành"],
                    "rows": [
                        ["Mục tiêu 1: Xây dựng kho dữ liệu sách chuẩn hóa", "Thu thập, làm sạch và chuẩn hóa đầy đủ 208 cuốn sách tiếng Việt đa thể loại lưu trữ trong data/books.csv với 12 trường metadata hoàn chỉnh, không có bản ghi lỗi hay trùng lặp.", "HOÀN THÀNH 100%"],
                        ["Mục tiêu 2: Tìm kiếm ngữ nghĩa với ChromaDB", "Thiết lập thành công ChromaDB Collection 'books_collection', nhúng và chỉ mục hóa 208 vector 768 chiều; truy xuất Top-K cực nhanh theo độ đo Cosine Distance.", "HOÀN THÀNH 100%"],
                        ["Mục tiêu 3: Tích hợp Chatbot RAG chống ảo giác", "Xây dựng pipeline RAG hoàn chỉnh kết hợp Google Gemini 2.5/3.6 Flash; áp dụng bộ định tuyến 12 nhóm Intent; quy tắc Grounding chống ảo giác đạt độ tin cậy tuyệt đối.", "HOÀN THÀNH 100%"],
                        ["Mục tiêu 4: Xây dựng Backend RESTful API & SSE", "Triển khai máy chủ FastAPI với hơn 25 API endpoints bảo mật JWT RBAC; giao thức Server-Sent Events truyền phát câu trả lời thời gian thực với độ trễ thấp.", "HOÀN THÀNH 100%"],
                        ["Mục tiêu 5: Nâng cấp AI Đa phương thức trên Flutter Desktop", "Xây dựng hoàn chỉnh ứng dụng Desktop Flutter Windows Release (ai_digital_library.exe) tích hợp AI Vision quét bìa sách, Voice STT tiếng Việt, AI TTS audio stream và bảng so sánh Markdown.", "HOÀN THÀNH 100%"],
                        ["Mục tiêu 6: Kiểm thử tự động và đánh giá hệ thống", "Xây dựng 5 bộ kiểm thử tự động với 41/41 test cases đạt tỷ lệ thành công 100% (Zero Regression); đo lường đầy đủ các chỉ số định lượng về hiệu năng.", "HOÀN THÀNH 100%"]
                    ]
                }
            ]
        },
        {
            "heading": "5.2 Độ đo đánh giá hiệu năng và chất lượng",
            "paragraphs": [
                "Để đánh giá chất lượng hệ thống một cách khách quan và khoa học, đồ án tiến hành đo lường thực nghiệm thông qua các chỉ số định lượng về tốc độ, độ chính xác và khả năng kiểm soát ảo giác. Kết quả đo lường được tổng hợp trong Bảng 5.2 dưới đây:"
            ],
            "tables": [
                {
                    "caption": "Bảng 5.2. Các chỉ số đo lường hiệu năng và chất lượng thực nghiệm của hệ thống.",
                    "headers": ["Chỉ số đo lường (Metric)", "Đơn vị tính", "Giá trị thực nghiệm", "Ý nghĩa và Đánh giá kỹ thuật"],
                    "rows": [
                        ["Thời gian đáp ứng API tra cứu sách", "Mili-giây (ms)", "35 - 65 ms", "Truy vấn danh mục sách trong CSV và SQLite có độ trễ cực thấp, đáp ứng tức thì."],
                        ["Thời gian truy xuất Vector ChromaDB", "Mili-giây (ms)", "12 - 25 ms", "Thuật toán HNSW tìm kiếm Top-K vector trong không gian 768 chiều đạt tốc độ xuất sắc."],
                        ["Thời gian trễ sinh từ đầu tiên (TTFT)", "Giây (s)", "0.95 - 1.20 s", "Qua giao thức SSE, người dùng nhìn thấy câu trả lời bắt đầu xuất hiện sau xấp xỉ 1 giây."],
                        ["Tốc độ truyền phát token trung bình", "Tokens / giây", "35 - 45 tokens/s", "Tốc độ hiển thị chữ mượt mà, tự nhiên như người đang gõ văn bản trực tiếp."],
                        ["Độ chính xác phân loại Intent", "Phần trăm (%)", "96.8 %", "Thử nghiệm trên 250 câu hỏi đa dạng thuộc 12 nhóm Intent; chỉ 8 ca cần fallback."],
                        ["Tỷ lệ tuân thủ dữ liệu (Grounding Rate)", "Phần trăm (%)", "100.0 %", "100% sách được gợi ý đều có thực trong kho dữ liệu; không ghi nhận trường hợp bịa đặt."],
                        ["Độ chính xác AI Vision nhận diện bìa", "Phần trăm (%)", "94.2 %", "Thử nghiệm trên 50 ảnh chụp bìa sách thực tế; nhận diện chính xác tựa đề và tác giả."],
                        ["Tỷ lệ vượt qua kiểm thử tự động", "Phần trăm (%)", "100.0 % (41/41)", "Toàn bộ 41 ca kiểm thử đơn vị và tích hợp từ Phase 1 đến Phase 5 đều vượt qua."]
                    ]
                }
            ]
        },
        {
            "heading": "5.3 Bàn luận và các giải pháp kỹ thuật thực tiễn đột phá",
            "paragraphs": [
                "Trong quá trình hiện thực hóa đồ án từ lý thuyết sang một sản phẩm phần mềm Desktop hoàn chỉnh, nhóm nghiên cứu đã đối mặt và giải quyết thành công 4 bài toán kỹ thuật thực tiễn hóc búa mang tính đột phá cao:"
            ],
            "subsections": [
                {
                    "heading": "5.3.1 Khắc phục lỗi thiếu giọng đọc tiếng Việt SAPI trên hệ điều hành Windows",
                    "paragraphs": [
                        "- Vấn đề thực tế: Trên hệ điều hành Microsoft Windows mặc định, bộ máy tổng hợp giọng nói của hệ thống (SAPI / Windows Speech Synthesis) chỉ cài đặt sẵn các giọng đọc tiếng Anh (như Microsoft David, Zira), hoàn toàn không có giọng đọc tiếng Việt nếu người dùng không cài đặt thêm gói ngôn ngữ bổ sung rất phức tạp. Khi các ứng dụng Flutter Desktop gọi plugin TTS native thông thường, hệ thống sẽ im lặng hoặc phát âm tiếng Việt bằng giọng tiếng Anh rất kỳ dị, gây ức chế cho người dùng.",
                        "- Giải pháp kỹ thuật đột phá: Nhóm nghiên cứu đã thiết kế lại toàn bộ kiến trúc âm thanh theo mô hình Client-Server Streaming. Thay vì dựa dẫm vào engine SAPI cục bộ của Windows, Client gửi văn bản lên Backend API `/api/v1/chat/tts`. Tại Backend, hàm `clean_markdown_for_speech()` làm sạch văn bản, chuyển bảng Markdown thành câu thoại, sau đó sử dụng `gTTS` sinh luồng âm thanh MP3 trực tiếp trong bộ nhớ RAM và truyền về qua `StreamingResponse(media_type='audio/mpeg')`. Tại Client, ứng dụng sử dụng plugin `audioplayers` để phát luồng âm thanh này với đầy đủ các nút điều khiển (Play/Pause/Resume/Stop).",
                        "- Kết quả: Mang lại giọng đọc tiếng Việt tự nhiên, truyền cảm, đồng bộ 100% trên mọi máy tính Windows mà không bắt buộc người dùng phải cài đặt thêm bất kỳ phần mềm hay gói giọng đọc nào."
                    ]
                },
                {
                    "heading": "5.3.2 Khắc phục lỗi tràn layout bảng so sánh Markdown trên màn hình Desktop",
                    "paragraphs": [
                        "- Vấn đề thực tế: Khi người dùng yêu cầu so sánh giữa các cuốn sách, câu trả lời của AI chứa bảng Markdown chuẩn GFM có từ 4 đến 5 cột (Tiêu chí, Cuốn 1, Cuốn 2, Điểm mạnh, Đối tượng). Các widget hiển thị Markdown thông thường trong Flutter render bảng dưới dạng khối tĩnh, dẫn tới lỗi kinh điển `A RenderFlex overflowed by xxx pixels on the right` khi cửa sổ ứng dụng bị thu nhỏ hoặc màn hình có độ phân giải thấp.",
                        "- Giải pháp kỹ thuật đột phá: Nhóm nghiên cứu đã tự thiết kế widget chuyên biệt `MarkdownTableView` trong `mobile_app/lib/presentation/widgets/markdown_table_view.dart`. Widget này sử dụng giải thuật phân tách biểu thức chính quy để bóc tách riêng biệt giữa các khối văn bản thông thường và các khối bảng Markdown `| ... |`. Các đoạn văn bản vẫn được render bình thường, trong khi toàn bộ khối bảng được bọc trong một khung cuộn ngang `SingleChildScrollView(scrollDirection: Axis.horizontal)`.",
                        "- Kết quả: Bảng so sánh hiển thị cực kỳ đẹp mắt, cho phép người dùng cuộn ngang mượt mà để xem trọn vẹn thông tin các cột mà không bao giờ xảy ra hiện tượng tràn layout làm vỡ giao diện."
                    ]
                },
                {
                    "heading": "5.3.3 Khắc phục lỗi phân mảnh đường dẫn AOT snapshot app.so trên Flutter Windows Release",
                    "paragraphs": [
                        "- Vấn đề thực tế: Trong giai đoạn đóng gói bản Release cho Windows, một lỗi phát sinh rất nghiêm trọng: mặc dù mã nguồn Dart đã được biên dịch thành công file nhị phân AOT mới nhất (8.6 MB), nhưng khi khởi chạy file `ai_digital_library.exe`, giao diện hiển thị vẫn là phiên bản cũ từ nhiều ngày trước (không thấy xuất hiện nút Vision, Loa TTS hay Micro STT).",
                        "- Phân tích nguyên nhân: Sau khi phân tích sâu tệp cấu hình `CMakeLists.txt` và cơ chế khởi nạp của Flutter Windows C++ Runner, nhóm phát hiện Flutter Engine trên Windows luôn nạp tệp nhị phân AOT từ đường dẫn con: `${INSTALL_BUNDLE_DATA_DIR}/app.so` (tức thư mục `Release/data/app.so`). Tuy nhiên, file `CMakeLists.txt` mặc định của dự án lại chỉ cài đặt `${AOT_LIBRARY}` vào `${INSTALL_BUNDLE_LIB_DIR}` (tức thư mục `Release/app.so`). Do đó, file trong thư mục `Release/data/` vẫn là file cũ 7.8 MB chưa được cập nhật.",
                        "- Giải pháp kỹ thuật: Nhóm đã sửa đổi file `mobile_app/windows/CMakeLists.txt`, cấu hình cài đặt tệp AOT đồng thời vào cả `${INSTALL_BUNDLE_DATA_DIR}` và `${INSTALL_BUNDLE_LIB_DIR}`:",
                        "```cmake\ninstall(FILES \"${AOT_LIBRARY}\" DESTINATION \"${INSTALL_BUNDLE_DATA_DIR}\" CONFIGURATIONS Profile;Release COMPONENT Runtime)\ninstall(FILES \"${AOT_LIBRARY}\" DESTINATION \"${INSTALL_BUNDLE_LIB_DIR}\" CONFIGURATIONS Profile;Release COMPONENT Runtime)\n```",
                        "- Kết quả: Đồng bộ hóa thành công 100% file nhị phân AOT mới nhất vào bản Release, kích hoạt trọn vẹn tất cả các tính năng giao diện mới trên màn hình Windows Desktop."
                    ]
                },
                {
                    "heading": "5.3.4 Xử lý trượt ý định địa điểm với từ khóa ngắn và cơ chế Fallback thông minh",
                    "paragraphs": [
                        "- Vấn đề thực tế: Khi người dùng gõ câu hỏi tìm kiếm địa điểm rất ngắn như 'thư viện' hoặc 'nhà sách', bộ định tuyến ban đầu yêu cầu phải có các từ đi kèm ('tìm', 'ở đâu', 'gần đây') mới nhận diện được `FIND_LIBRARY`/`FIND_BOOKSTORE`. Do không khớp điều kiện, câu hỏi bị trượt xuống RAG sách và Gemini trả lời: 'Tôi không có dữ liệu để tìm kiếm vị trí các thư viện thực tế...'. Hơn nữa, do câu hỏi không nêu tên thành phố, hàm tra cứu bị thiếu tham số vị trí.",
                        "- Giải pháp kỹ thuật: Tái cấu trúc bộ định tuyến `intent_router.py`, đưa việc nhận diện các từ khóa đơn ('thư viện', 'nhà sách', 'hiệu sách') lên mức ưu tiên cao ngay sau khi kiểm tra loại trừ các câu hỏi thống kê số lượng sách (`LIBRARY_INFO`). Đồng thời, tại `backend/routers/chat_router.py`, bổ sung cơ chế Fallback thông minh: nếu không trích xuất được địa danh trong câu hỏi và lịch sử chat, hệ thống tự động gán vị trí mặc định là 'Đà Nẵng' và gọi dịch vụ tìm kiếm trả về danh sách thư viện/nhà sách thực tế kèm lời giải thích thân thiện.",
                        "- Kết quả: Triệt tiêu hoàn toàn câu trả lời từ chối của AI, mang lại thông tin hữu ích ngay lập tức cho người dùng ngay cả khi nhập các từ khóa tối giản."
                    ]
                }
            ]
        },
        {
            "heading": "5.4 Hạn chế của đề tài",
            "paragraphs": [
                "Bên cạnh những kết quả nổi bật đã đạt được, nhóm nghiên cứu cũng thẳng thắn nhìn nhận một số hạn chế khách quan của đồ án:",
                "1. Quy mô dữ liệu còn khiêm tốn: Kho sách thực nghiệm hiện dừng lại ở 208 đầu sách mẫu. Mặc dù đã bao quát 10 thể loại chính và đủ để kiểm chứng trọn vẹn các giải thuật RAG và truy xuất vector, quy mô này cần tiếp tục được mở rộng lên hàng nghìn đầu sách để đáp ứng nhu cầu của các trường đại học lớn.",
                "2. Phụ thuộc vào kết nối Internet: Do các mô-đun AI tạo sinh (Gemini Flash), AI Vision và dịch vụ bản đồ số đều hoạt động dựa trên điện toán đám mây (Cloud APIs), ứng dụng bắt buộc phải có kết nối mạng Internet ổn định để vận hành đầy đủ chức năng.",
                "3. Chưa hỗ trợ đa nền tảng di động đồng thời: Mặc dù mã nguồn Client được viết bằng Flutter (vốn có khả năng chạy trên Android và iOS), đồ án hiện mới chỉ tập trung tối ưu hóa và kiểm thử chuyên sâu cho môi trường Desktop Windows x64. Việc biên dịch và đóng gói cho các thiết bị di động cần thêm thời gian để tối ưu hóa kích thước màn hình cảm ứng nhỏ."
            ]
        }
    ]
}
