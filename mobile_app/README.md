# AI Digital Library - Multi-Platform Flutter Client

Hệ thống ứng dụng Thư viện số AI đa nền tảng (**Windows Desktop**, **Android**, **iOS**) được xây dựng bằng **Flutter**, kết nối trực tiếp với **FastAPI Backend**, bảo toàn 100% kho dữ liệu 208 sách và mô hình AI RAG Google Gemini.

---

## 1. Phong cách Thiết kế (Navy & Gold Theme)

- **Navy Dark:** `#0B1F3A` — Màu thương hiệu chủ đạo, sidebar điều hướng desktop, header hero.
- **Navy:** `#123B66` — Nút bấm chính, app bar, tiêu đề tác giả.
- **Gold:** `#C9A227` — Điểm nhấn sang trọng, huy hiệu sách nổi bật, ngôi sao đánh giá.
- **Background:** `#F7F9FC` — Màu nền sáng hiện đại, tối ưu cho đọc sách và hiển thị nội dung.
- **Surface:** `#FFFFFF` — Thẻ sách và container với viền mỏng `#E2E8F0`.

---

## 2. Cấu trúc Dự án (Clean Architecture)

```
mobile_app/
├── pubspec.yaml
├── analysis_options.yaml
├── lib/
│   ├── main.dart                       # Entry point, MultiProvider setup, Theme config
│   ├── core/
│   │   ├── constants/
│   │   │   ├── api_constants.dart      # Base URL đa nền tảng (Windows/Android/iOS/Custom)
│   │   │   └── app_colors.dart         # Bảng màu Navy & Gold chuẩn
│   │   ├── network/
│   │   │   ├── api_exceptions.dart     # Xử lý lỗi tiếng Việt thân thiện (timeout, 401, 403, 500)
│   │   │   └── dio_client.dart         # Dio HTTP client, gắn Bearer token tự động
│   │   ├── storage/
│   │   │   └── auth_storage.dart       # Lưu trữ token bảo mật (FlutterSecureStorage + SharedPreferences)
│   │   ├── theme/
│   │   │   └── app_theme.dart          # ThemeData Material 3, typography Inter
│   │   └── utils/
│   │       └── responsive_layout.dart  # Breakpoints: Desktop (>1100), Tablet (650-1100), Mobile (<650)
│   ├── models/
│   │   ├── user_model.dart             # UserModel (username, role: Admin/User, token)
│   │   ├── book_model.dart             # BookModel (đầy đủ 26 trường dữ liệu CSV)
│   │   ├── book_list_response.dart     # Phân trang: items, total, page, pageSize, totalPages
│   │   ├── author_model.dart           # AuthorModel (tác giả, tiểu sử, số sách trong thư viện)
│   │   ├── genre_model.dart            # GenreModel (thể loại, icon, số sách)
│   │   └── home_stats_model.dart       # HomeStatsModel (tổng sách, tác giả, thể loại, nổi bật)
│   ├── services/
│   │   └── api_service.dart            # Tầng dịch vụ giao tiếp REST API
│   ├── repositories/
│   │   ├── auth_repository.dart        # Xác thực, đăng ký, đăng nhập, phân quyền
│   │   ├── book_repository.dart        # Tra cứu, lọc, lấy chi tiết & sách liên quan
│   │   ├── author_repository.dart      # Tác giả & tác phẩm
│   │   ├── genre_repository.dart       # Danh mục thể loại
│   │   └── home_repository.dart        # Thống kê tổng quan
│   ├── providers/
│   │   ├── auth_provider.dart          # Quản lý trạng thái đăng nhập, user profile
│   │   ├── home_provider.dart          # Dữ liệu trang chủ
│   │   ├── book_provider.dart          # Danh mục sách, tìm kiếm, lọc, phân trang tải thêm
│   │   ├── author_provider.dart        # Quản lý tác giả & chi tiết
│   │   ├── genre_provider.dart         # Danh sách thể loại
│   │   └── navigation_provider.dart    # Điều hướng tab ứng dụng
│   └── presentation/
│       ├── widgets/
│       │   ├── app_scaffold.dart       # Responsive Scaffold: Desktop Sidebar vs Mobile BottomNav
│       │   ├── book_card.dart          # Thẻ sách ảnh bìa, rating, huy hiệu nổi bật/đọc online
│       │   ├── custom_button.dart      # Nút bấm chuẩn thiết kế (Primary, Secondary, Outline)
│       │   ├── custom_text_field.dart  # Ô nhập liệu chuẩn hóa có hiển thị mật khẩu
│       │   ├── section_header.dart     # Tiêu đề phân mục có liên kết xem thêm
│       │   └── state_views.dart        # LoadingView, EmptyView, ErrorView
│       └── screens/
│           ├── splash_screen.dart       # Màn hình khởi động kiểm tra phiên đăng nhập
│           ├── login_screen.dart        # Đăng nhập (có nút thử nhanh tài khoản Admin cong1 / 123)
│           ├── register_screen.dart     # Đăng ký tài khoản mới
│           ├── home_screen.dart         # Trang chủ thống kê (208 sách) & sách nổi bật
│           ├── books_catalog_screen.dart# Kho sách phân trang, tìm kiếm tức thì, lọc thể loại
│           ├── search_filter_screen.dart# Bộ lọc nâng cao (tiêu đề, tác giả, ISBN, đọc online)
│           ├── book_detail_screen.dart  # Chi tiết sách (26 trường, đọc online, sách liên quan)
│           ├── authors_screen.dart      # Danh sách tác giả & tìm kiếm
│           ├── author_detail_screen.dart# Chi tiết tác giả & các sách trong thư viện
│           ├── genres_screen.dart       # Lưới 16 thể loại với icon và số lượng sách
│           └── profile_screen.dart      # Hồ sơ người dùng, phân quyền & cấu hình Base URL
├── windows/                            # Cấu hình Windows Desktop Runner
├── android/                            # Cấu hình Android App & Quyền Internet
└── ios/                                # Cấu hình iOS Runner
```

---

## 3. Hướng dẫn Khởi chạy

### Bước 1: Khởi động FastAPI Backend
Trước khi chạy Flutter, hãy đảm bảo Backend đang chạy tại cổng `8000`:
```powershell
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### Bước 2: Khởi chạy Ứng dụng Flutter

- **Chạy trên Windows Desktop:**
  ```powershell
  cd mobile_app
  flutter run -d windows
  ```

- **Chạy trên Android (Emulator hoặc thiết bị thật):**
  ```powershell
  cd mobile_app
  flutter run -d android
  ```
  *(Lưu ý: Trên Android Emulator, ứng dụng tự động kết nối máy chủ qua `http://10.0.2.2:8000`)*

- **Chạy trên iOS Simulator:**
  ```bash
  cd mobile_app
  flutter run -d ios
  ```

- **Đổi địa chỉ IP Backend khi chạy trên điện thoại thật:**
  Tại màn hình **Hồ sơ & Cài đặt**, người dùng có thể nhập địa chỉ IP mạng LAN của máy chủ (ví dụ: `http://192.168.1.10:8000`).

