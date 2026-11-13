# BÁO CÁO KHÔI PHỤC VÀ TÍCH HỢP TÍNH NĂNG TÌM KIẾM ĐỊA ĐIỂM (NHÀ SÁCH & THƯ VIỆN)
**Dự án:** Digital Library & AI Assistant (`E:\Source_Code\book-recommender-chatbot`)  
**Ngày hoàn thành:** 03/11/2026  
**Trạng thái:** ✅ **HOÀN TOÀN THÀNH CÔNG – TEST REGRESSION 232/232 PASS – FLUTTER ANALYZE 0 ERRORS**

---

## 1. TỔNG QUAN VÀ MỤC TIÊU KHÔI PHỤC

Trước đây, khi người dùng hỏi các câu liên quan đến tìm địa điểm vật lý trong Trợ lý AI (ví dụ: *"Tôi muốn tìm địa chỉ nhà sách gần đây"*, *"Tìm nhà sách ở Đà Nẵng"*):
- Hệ thống bị phân loại vào RAG hoặc kiểm tra phạm vi thư viện ("chỉ hỗ trợ tư vấn sách trong thư viện...").
- Các router `location_router.py` và `location_service.py` (tích hợp Google Local qua SerpApi) chưa được liên kết vào luồng chat thông minh của `chat_router.py`.
- Flutter Chat UI chưa có model nhận diện payload `locations` và chưa có giao diện trực quan hiển thị danh thiếp địa điểm.

**Mục tiêu đã giải quyết trọn vẹn:**
1. **Phân loại Intent chuẩn xác**: Nhận diện tức thì `location_bookstore` và `location_library`, tách biệt hoàn toàn với truy vấn sách (`book_search`) và thông tin quy mô thư viện (`library_info`).
2. **Trích xuất thực thể địa lý**: Trích xuất linh hoạt các khu vực, quận huyện, thành phố ("Đà Nẵng", "quận Liên Chiểu", "Hà Nội", "TP.HCM", "Huế", "gần đây"...).
3. **Tích hợp API Chat (Message & Stream)**: Bổ sung block `locations` vào response và session chat history. Khi người dùng chưa cung cấp vị trí, chatbot hướng dẫn lịch sự hỏi vị trí cụ thể.
4. **Hiển thị trực quan trên Flutter**: Xây dựng widget thẻ địa điểm (tên nhà sách/thư viện, địa chỉ, rating sao, trạng thái mở cửa, nút Google Maps và nút Chỉ đường tích hợp sâu qua URL launcher).

---

## 2. CHI TIẾT CÁC TỆP ĐÃ ĐƯỢC CHỈNH SỬA VÀ TẠO MỚI

Tất cả các tệp hiện hữu đã được sao lưu dự phòng (`.bak`) trước khi sửa đổi:

| STT | Tệp | Thành phần | Nội dung thay đổi |
|---|---|---|---|
| 1 | `backend/schemas/chat_schema.py` | Backend Schema | Thêm trường `locations: list[dict[str, Any]] = []` vào `ChatResponse` và `ChatMessageItem`. |
| 2 | `intent_router.py` | Intent Classifier | Bổ sung nhận diện pattern nơi bán sách ("noi ban", "tim noi ban", "dia chi nha sach"), cải thiện hàm `extract_user_location()`, tối ưu ưu tiên `LIBRARY_INFO` để không bắt nhầm câu hỏi số lượng sách. |
| 3 | `rag_engine.py` | RAG Engine | Thêm bộ lọc `location_signals` trong `_classify_explicit_query()` để không bao giờ gom các cụm từ địa điểm vào `BOOK_QUERY`. |
| 4 | `backend/routers/chat_router.py` | Chat API Router | Tích hợp Intent Router & Location Service vào cả `POST /api/v1/chat/message` và `POST /api/v1/chat/stream`. Trả về `locations` payload khi tìm thấy nhà sách/thư viện. |
| 5 | `mobile_app/lib/models/location_item_model.dart` | Flutter Model | **[Tạo mới]** Model ánh xạ đối tượng `LocationItemModel` và `LocationSearchResponseModel`. |
| 6 | `mobile_app/lib/core/utils/url_launcher_helper.dart` | Flutter Helper | **[Tạo mới]** Helper mở URL Google Maps và Directions đa nền tảng tối ưu cho Windows (tương thích Command Line URL launch). |
| 7 | `mobile_app/lib/core/constants/api_constants.dart` | Flutter Constants | Định nghĩa endpoint `ApiConstants.locationsSearch = '/api/v1/locations/search'`. |
| 8 | `mobile_app/lib/models/chat_message_model.dart` | Flutter Model | Mở rộng `ChatMessageModel` với `final List<LocationItemModel> locations;`. |
| 9 | `mobile_app/lib/services/api_service.dart` | Flutter Service | Bổ sung hàm `searchLocations()`, hỗ trợ bóc tách block `locations` trong chat message và SSE stream. |
| 10 | `mobile_app/lib/repositories/chat_repository.dart` | Flutter Repo | Chuyển giao dữ liệu `locations` từ API response sang model chat message. |
| 11 | `mobile_app/lib/providers/chat_provider.dart` | Flutter State | Cập nhật state provider lưu trữ `locations` cho trợ lý ảo. |
| 12 | `mobile_app/lib/presentation/widgets/chat_bubble.dart` | Flutter Widget | Thiết kế widget `_buildLocationsList()` hiển thị thẻ Card trực quan: Tên, địa chỉ, số sao, số lượt review, giờ mở cửa, nút Google Maps và nút Chỉ đường. |
| 13 | `mobile_app/lib/presentation/screens/ai_chat_screen.dart` | Flutter Screen | Bổ sung prompt gợi ý tìm nhà sách/thư viện ngay trên giao diện chat. |
| 14 | `tests/test_location_chat_integration.py` | Backend Test | **[Tạo mới]** Bộ 7 test cases bao quát toàn diện Intent, Extraction, Message API, SSE Stream API, Scope Check, và REST API. |

---

## 3. KẾT QUẢ KIỂM THỬ THỰC TẾ

### 3.1. Toàn bộ Pytest Suite (232/232 PASS)
```text
============================= test session starts =============================
platform win32 -- Python 3.13.12, pytest-9.1.1, pluggy-1.6.0
collected 232 items

tests\test_ai_crawler_admin.py .......                                   [  3%]
tests\test_chatbot_rag_streaming.py ............                         [  8%]
tests\test_continue_reading_progress_hotfix.py ....                      [  9%]
tests\test_crawler_service.py ..............................             [ 22%]
tests\test_digital_book_reader.py .........                              [ 26%]
tests\test_fastapi_backend.py ..........                                 [ 31%]
tests\test_flutter_api_contract.py ............                          [ 36%]
tests\test_flutter_recommendation_contract.py ................           [ 43%]
tests\test_flutter_recommendation_ui.py ........                         [ 46%]
tests\test_hotfix_verification.py ......                                 [ 49%]
tests\test_hybrid_recommendation_and_book_ai.py ............             [ 54%]
tests\test_library_services.py ...............                           [ 60%]
tests\test_location_chat_integration.py .......                          [ 63%]
tests\test_personal_bookshelf.py .........                               [ 67%]
tests\test_phase3_3_2b_final_verification.py ..........                  [ 71%]
tests\test_recommendations.py ..............                             [ 78%]
tests\test_social_community_phase3_4_1.py .................              [ 85%]
tests\test_social_follow_feed_privacy_phase3_4_2.py ..............       [ 91%]
tests\test_social_moderation_phase3_4_3.py ....................          [100%]

================= 232 passed, 2 warnings in 176.31s (0:02:56) =================
```

### 3.2. Kiểm thử Tĩnh Flutter (`flutter analyze`)
```text
Analyzing mobile_app...
81 issues found (ran in 20.5s) - 0 errors, 81 infos (chỉ gồm deprecated members cũ của Flutter SDK).
```

---

## 4. MA TRẬN KỊCH BẢN ĐÃ ĐƯỢC XÁC MINH TRÊN GIAO DIỆN

| Câu hỏi của người dùng | Phân loại Intent | Hành vi của AI | Giao diện hiển thị |
|---|---|---|---|
| *"Tôi muốn tìm nhà sách gần đây"* | `location_bookstore` | Nhận diện thiếu địa điểm cụ thể, hỏi người dùng khu vực/thành phố mong muốn. | Bong bóng tin nhắn AI hướng dẫn lịch sự. |
| *"Tìm nhà sách ở Đà Nẵng"* | `location_bookstore` (Location: `Đà Nẵng`) | Gọi SerpApi Google Local tìm kiếm nhà sách thực tế tại Đà Nẵng. | Thẻ địa điểm (Nhà sách Phương Nam, Kim Đồng, Fahasa...), rating, nút Mở Maps & Chỉ đường. |
| *"Có thư viện nào gần quận Liên Chiểu không?"* | `location_library` (Location: `quận Liên Chiểu`) | Gọi SerpApi tìm thư viện khu vực Liên Chiểu. | Danh sách thẻ thư viện địa phương, địa chỉ, rating và liên kết bản đồ. |
| *"Cho tôi địa chỉ nhà sách gần đây"* | `location_bookstore` | Nhận diện ý định tìm địa chỉ nhà sách. | Hướng dẫn cung cấp quận/huyện để tra cứu chính xác. |
| *"Tìm nơi bán cuốn sách này"* | `location_bookstore` | Nhận diện ý định tìm điểm bán sách. | Hướng dẫn vị trí hoặc tra cứu chuỗi nhà sách lớn. |
| *"Thư viện hiện có bao nhiêu cuốn sách?"* | `library_info` | Truy vấn thống kê thư viện số nội bộ (208 cuốn sách). | Câu trả lời số liệu chính xác, không bị lẫn sang tìm kiếm địa điểm. |
| *"Giới thiệu về Đắc Nhân Tâm"* | `book_search` | Chuyển luồng vào RAG Engine (ChromaDB + Gemini AI). | Tóm tắt sách và trích dẫn ngữ cảnh từ kho 208 sách. |

---

## 5. CAM KẾT VÀ AN TOÀN HỆ THỐNG
1. **Bảo toàn dữ liệu**: Toàn bộ dữ liệu 208 sách trong `data/books.csv`, 208 embeddings trong `chroma_db`, và database SQLite cộng đồng `data/social_community.db` được bảo toàn nguyên vẹn 100%.
2. **Không phá vỡ RAG Engine & Gemini**: Toàn bộ luồng RAG, Hybrid Recommendation, Streaming và Auth JWT đều giữ nguyên kiến trúc chuẩn.
3. **Sẵn sàng hoạt động ngay**: Backend FastAPI và ứng dụng Flutter Windows đã kết nối tương thích hoàn hảo.

