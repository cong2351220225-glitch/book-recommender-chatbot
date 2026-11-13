# -*- coding: utf-8 -*-
"""
Chương 6: Kết luận và hướng phát triển (Conclusion & Future Work)
"""

CHAPTER_6_DATA = {
    "title": "Chương 6. Kết luận và hướng phát triển",
    "sections": [
        {
            "heading": "6.1 Kết luận",
            "paragraphs": [
                "Đồ án 'Xây dựng Trợ lý ảo Tư vấn và Gợi ý Sách Thông minh Đa phương thức ứng dụng kiến trúc RAG, Google Gemini, FastAPI và Flutter Desktop' đã hoàn thành trọn vẹn và xuất sắc toàn bộ các mục tiêu nghiên cứu và nhiệm vụ thực nghiệm đề ra. Dự án không chỉ dừng lại ở một ý tưởng mô phỏng học thuật mà đã được hiện thực hóa thành một sản phẩm phần mềm thương mại hoàn chỉnh, chất lượng cao, có thể đưa vào vận hành thực tế tại các thư viện trường học và trung tâm học liệu.",
                "Những đóng góp khoa học và giá trị thực tiễn cốt lõi mà đồ án đã mang lại bao gồm:",
                "1. Về mặt học thuật và công nghệ AI: Đồ án đã làm chủ và ứng dụng thành công kiến trúc RAG (Retrieval-Augmented Generation) tiên tiến, kết hợp giữa cơ sở dữ liệu vector ChromaDB và mô hình ngôn ngữ lớn Google Gemini. Hệ thống đã giải quyết triệt để bài toán 'ảo giác' (Hallucination) trong các hệ thống đàm thoại AI, thiết lập tỷ lệ Grounding đạt 100% trên kho dữ liệu cục bộ.",
                "2. Về mặt tương tác người - máy (HCI): Hệ thống đã bứt phá khỏi các giao diện gõ chữ truyền thống bằng việc tích hợp toàn diện năng lực Đa phương thức (Multimodal AI): nhận diện bìa sách bằng thị giác máy tính (AI Vision), nhận diện giọng nói tiếng Việt (Voice STT) và chuyển đổi văn bản thành giọng đọc truyền cảm (AI TTS) cùng bảng so sánh Markdown trực quan.",
                "3. Về mặt kỹ nghệ phần mềm: Xây dựng thành công hệ thống Client-Server phân tầng vững chắc; Backend FastAPI với hơn 25 API endpoints bảo mật JWT RBAC; giao thức truyền phát thời gian thực Server-Sent Events (SSE); và ứng dụng Desktop Flutter Windows Release hoàn chỉnh, khắc phục triệt để các rào cản kỹ thuật về âm thanh SAPI và phân mảnh đường dẫn AOT.",
                "4. Về mặt kiểm thử và chất lượng: Toàn bộ 41/41 ca kiểm thử tự động trên Pytest đều đạt tỷ lệ thành công tuyệt đối (100%), chứng minh tính ổn định, độ tin cậy và khả năng chống hồi quy (Zero Regression) của hệ thống phần mềm."
            ]
        },
        {
            "heading": "6.2 Bài học rút ra",
            "paragraphs": [
                "Quá trình nghiên cứu và phát triển một dự án phần mềm trí tuệ nhân tạo hoàn chỉnh từ đầu đến cuối đã đem lại cho tác giả nhiều bài học kinh nghiệm sâu sắc:",
                "- Bài học về chất lượng dữ liệu (Data Quality First): Dữ liệu chính là linh hồn của hệ thống AI. Một mô hình ngôn ngữ dù hiện đại đến đâu cũng không thể phát huy tác dụng nếu dữ liệu đầu vào bị thiếu sót, sai lệch hoặc trùng lặp. Việc dành thời gian khảo sát, chuẩn hóa kỹ lưỡng 12 trường metadata và kiểm soát chặt chẽ quy trình nhúng vector mang lại giá trị lớn hơn nhiều so với việc chỉ tập trung điều chỉnh các siêu tham số.",
                "- Bài học về thiết kế kiến trúc phân tầng: Sự phân tách rõ ràng giữa tầng hiển thị Client và tầng xử lý Backend thông qua các bản hợp đồng API (API Contracts) chuẩn hóa giúp quá trình phát triển, nâng cấp và sửa lỗi diễn ra vô cùng thuận lợi. Khi cần thay đổi logic AI hoặc cập nhật mô hình, chỉ cần can thiệp tại Backend mà không làm ảnh hưởng đến mã nguồn ứng dụng Desktop.",
                "- Bài học về tư duy giải quyết vấn đề kỹ thuật thực tế (Engineering Problem Solving): Những bài toán phát sinh trong thực tế (như Windows thiếu giọng đọc tiếng Việt SAPI, hay bảng Markdown làm tràn layout màn hình) không thể giải quyết bằng các giải pháp chắp vá thông thường. Nó đòi hỏi người kỹ sư phải hiểu sâu sắc nguyên lý hoạt động của hệ điều hành, cơ chế render đồ họa và tư duy sáng tạo để tái cấu trúc giải pháp (như chuyển sang MP3 Streaming hay thiết kế widget cuộn ngang chuyên biệt).",
                "- Bài học về kỷ luật kiểm thử phần mềm: Việc duy trì bộ kiểm thử tự động hồi quy liên tục sau mỗi giai đoạn phát triển (Phase 1 đến Phase 5) là chiếc 'phao cứu sinh' giúp phát hiện sớm các lỗi tiềm ẩn, bảo vệ an toàn cho các chức năng cũ và giữ vững tiến độ đồ án."
            ]
        },
        {
            "heading": "6.3 Hướng phát triển",
            "paragraphs": [
                "Để tiếp tục nâng tầm đồ án và phát triển thành một nền tảng thư viện số thông minh quy mô lớn trong tương lai, nhóm nghiên cứu đề xuất 4 định hướng mở rộng trọng tâm:",
                "1. Mở rộng kho dữ liệu lớn và Phân đoạn ngữ nghĩa sâu (Hierarchical Chunking): Mở rộng kho dữ liệu lên quy mô 10.000+ cuốn sách; áp dụng kỹ thuật phân đoạn ngữ nghĩa theo từng chương/mục (Semantic Chunking) để chatbot có thể trích dẫn chính xác số trang và đoạn văn cụ thể trong sách khi trả lời người đọc.",
                "2. Đóng gói đa nền tảng di động (Android & iOS): Tận dụng tối đa ưu thế đa nền tảng của Flutter để biên dịch mã nguồn Client sang ứng dụng di động; tối ưu hóa giao diện cho màn hình cảm ứng nhỏ; bổ sung tính năng chụp ảnh bìa sách trực tiếp từ camera điện thoại.",
                "3. Tích hợp Mô hình Ngôn ngữ Cục bộ (Local LLM Offline): Nghiên cứu tích hợp các mô hình ngôn ngữ mã nguồn mở nhỏ gọn (như Llama 3 8B, Gemma 2 9B hoặc Qwen 2.5) thông qua framework Ollama để hệ thống có thể vận hành ngoại tuyến (Offline Mode) hoàn toàn khi máy tính mất kết nối Internet, đảm bảo tính riêng tư dữ liệu tuyệt đối cho các tổ chức giáo dục.",
                "4. Mở rộng tính năng Mạng xã hội Độc giả và Thương mại điện tử: Tích hợp chức năng đánh giá bình luận cộng đồng, theo dõi tiến độ đọc sách giữa bạn bè, chia sẻ danh sách gợi ý và kết nối API thanh toán điện tử (VNPay / MoMo) để hỗ trợ mượn sách hoặc mua sách bản quyền trực tiếp từ ứng dụng.",
                "5. Đóng gói Docker và Triển khai Đám mây (Cloud Deployment): Đóng gói toàn bộ Backend FastAPI và ChromaDB thành các Docker Containers; thiết lập quy trình tự động hóa CI/CD và triển khai lên cụm máy chủ đám mây (Google Cloud Platform / AWS) với cơ chế cân bằng tải tự động để phục vụ hàng chục nghìn sinh viên truy cập đồng thời."
            ]
        }
    ]
}
