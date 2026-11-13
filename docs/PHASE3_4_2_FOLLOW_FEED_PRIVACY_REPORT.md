# BÁO CÁO NGHIỆM THU PHASE 3.4.2 – FOLLOW, ACTIVITY FEED & PUBLIC BOOKSHELF PRIVACY

**Dự án:** Hệ thống Thư viện số và Chatbot Gợi ý Sách Thông minh (AI Digital Library & Recommendation System)  
**Thư mục làm việc:** `E:\Source_Code\book-recommender-chatbot`  
**Giai đoạn:** Phase 3.4.2 – Triển khai Follow/Unfollow, Friendship hai chiều, Activity Feed và Public Bookshelf Privacy  
**Thời gian hoàn thành:** 02/11/2026  
**Trạng thái kiểm thử:** ✅ **130/130 BÀI TEST PASS 100% (TOÀN BỘ 12 TEST SUITES HỆ THỐNG)**  

---

## 1. DANH SÁCH CÁC TỆP ĐÃ TẠO VÀ CHỈNH SỬA

| Tập tin | Trạng thái | Mục đích & Chức năng |
| :--- | :---: | :--- |
| `backend/services/community_db.py` | Chỉnh sửa | Đăng ký **Migration phiên bản 2** (`schema_version = 2`): tạo bảng `follows`, `friend_requests`, `friendships`, `activity_feed` và bổ sung 2 cột `bookshelf_privacy`, `activity_privacy` cho `user_profiles`. |
| `backend/schemas/community_schema.py` | Chỉnh sửa | Bổ sung Pydantic schemas: `FollowItemResponse`, `FollowListResponse`, `FollowActionResponse`, `FriendRequestItemResponse`, `FriendRequestListResponse`, `FriendItemResponse`, `FriendListResponse`, `PrivacySettingsUpdate`, `PrivacySettingsResponse`, `ActivityFeedItem`, `ActivityFeedResponse`, `PublicBookshelfItem`, `PublicBookshelfResponse`. Cập nhật `UserProfileResponse` tương thích ngược. |
| `backend/services/community_service.py` | Chỉnh sửa | Bổ sung logic nghiệp vụ: Follow/Unfollow (chống self-follow, chống trùng lặp), cơ chế Friendship hai chiều (`are_friends`, gửi/chấp nhận/từ chối lời mời), bộ ghi nhận hoạt động `record_activity` (ngăn trùng lặp sự kiện qua ràng buộc UNIQUE), bộ lọc Activity Feed theo quan hệ follow và quyền riêng tư, API kiểm tra quyền truy cập tủ sách cá nhân. |
| `backend/routers/community_router.py` | Chỉnh sửa | Bổ sung 14 REST API endpoints mới dưới `/api/v1/community/` cho Follow, Friendship, Privacy, Activity Feed và Public Bookshelf. |
| `backend/routers/reading_router.py` | Chỉnh sửa | Tích hợp kích hoạt ghi nhận sự kiện hoạt động `reading_started` và `book_completed` an toàn khi người dùng lưu tiến độ đọc. |
| `backend/routers/bookshelf_router.py` | Chỉnh sửa | Tích hợp kích hoạt ghi nhận sự kiện hoạt động khi người dùng thêm/cập nhật sách vào mục `reading` hoặc `completed`. |
| `tests/test_social_follow_feed_privacy_phase3_4_2.py` | **Tạo mới** | Bộ 14 bài kiểm thử chuyên sâu cho Phase 3.4.2 bao gồm Unit Tests, API Integration Tests, và Real Concurrency Tests. |
| `PHASE3_4_2_FOLLOW_FEED_PRIVACY_REPORT.md` | **Tạo mới** | Tài liệu báo cáo nghiệm thu toàn diện giai đoạn Phase 3.4.2. |

---

## 2. MIGRATION & DATABASE SCHEMA (VERSION 2)

Hệ thống tái sử dụng hoàn toàn cơ sở dữ liệu SQLite độc lập `data/social_community.db` (chế độ WAL, foreign keys ON, `busy_timeout = 5000ms`).

### Migration Script v2:
```sql
-- 1. Mở rộng quyền riêng tư trong user_profiles
ALTER TABLE user_profiles ADD COLUMN bookshelf_privacy TEXT NOT NULL DEFAULT 'public';
ALTER TABLE user_profiles ADD COLUMN activity_privacy TEXT NOT NULL DEFAULT 'public';

-- 2. Bảng follows (quan hệ một chiều)
CREATE TABLE IF NOT EXISTS follows (
    follower_username TEXT NOT NULL,
    following_username TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (follower_username, following_username),
    FOREIGN KEY (follower_username) REFERENCES user_profiles(username) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (following_username) REFERENCES user_profiles(username) ON UPDATE CASCADE ON DELETE CASCADE,
    CHECK (follower_username != following_username)
);

CREATE INDEX IF NOT EXISTS idx_follows_following ON follows(following_username);
CREATE INDEX IF NOT EXISTS idx_follows_follower ON follows(follower_username);

-- 3. Bảng friend_requests (lời mời kết bạn)
CREATE TABLE IF NOT EXISTS friend_requests (
    id TEXT PRIMARY KEY,
    sender_username TEXT NOT NULL,
    receiver_username TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'rejected')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (sender_username) REFERENCES user_profiles(username) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (receiver_username) REFERENCES user_profiles(username) ON UPDATE CASCADE ON DELETE CASCADE,
    CHECK (sender_username != receiver_username),
    UNIQUE (sender_username, receiver_username)
);

CREATE INDEX IF NOT EXISTS idx_friend_requests_receiver ON friend_requests(receiver_username, status);
CREATE INDEX IF NOT EXISTS idx_friend_requests_sender ON friend_requests(sender_username, status);

-- 4. Bảng friendships (quan hệ bạn bè hai chiều chuẩn hóa)
CREATE TABLE IF NOT EXISTS friendships (
    user1_username TEXT NOT NULL,
    user2_username TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user1_username, user2_username),
    FOREIGN KEY (user1_username) REFERENCES user_profiles(username) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (user2_username) REFERENCES user_profiles(username) ON UPDATE CASCADE ON DELETE CASCADE,
    CHECK (user1_username < user2_username)
);

CREATE INDEX IF NOT EXISTS idx_friendships_user1 ON friendships(user1_username);
CREATE INDEX IF NOT EXISTS idx_friendships_user2 ON friendships(user2_username);

-- 5. Bảng activity_feed (dòng hoạt động người dùng)
CREATE TABLE IF NOT EXISTS activity_feed (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    activity_type TEXT NOT NULL CHECK (activity_type IN ('review_created', 'reading_started', 'book_completed')),
    entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    metadata_json TEXT DEFAULT '{}',
    is_hidden INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (username) REFERENCES user_profiles(username) ON UPDATE CASCADE ON DELETE CASCADE,
    UNIQUE (username, activity_type, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_activity_feed_user ON activity_feed(username, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_feed_type ON activity_feed(activity_type);
```

---

## 3. DANH SÁCH REST API ĐÃ TRIỂN KHAI

Tất cả các API được tích hợp thống nhất dưới prefix `/api/v1/community`:

### A. Follow / Unfollow APIs
1. `POST /api/v1/community/users/{username}/follow`:
   - Xác thực: Yêu cầu JWT Token.
   - Thao tác: Theo dõi một người dùng. Chặn tự follow (400), chặn follow người không tồn tại (404), chặn follow trùng lặp (400).
2. `DELETE /api/v1/community/users/{username}/follow`:
   - Xác thực: Yêu cầu JWT Token.
   - Thao tác: Bỏ theo dõi người dùng. Chặn nếu chưa từng follow (400).
3. `GET /api/v1/community/users/{username}/followers`:
   - Xác thực: Công khai (Hỗ trợ Guest & Logged-in).
   - Thao tác: Lấy danh sách người đang theo dõi tài khoản, phân trang `page` & `page_size`.
4. `GET /api/v1/community/users/{username}/following`:
   - Xác thực: Công khai.
   - Thao tác: Lấy danh sách tài khoản mà người dùng đang theo dõi, phân trang `page` & `page_size`.

### B. Hai chiều Friendship APIs (Hỗ trợ mức quyền riêng tư `friends`)
5. `POST /api/v1/community/users/{username}/friend-request`:
   - Xác thực: Yêu cầu JWT Token.
   - Thao tác: Gửi lời mời kết bạn. Chặn gửi cho chính mình, chặn gửi nếu đã là bạn bè hoặc đang chờ duyệt.
6. `POST /api/v1/community/friend-requests/{request_id}/accept`:
   - Xác thực: Yêu cầu JWT Token (chống IDOR: chỉ người nhận mới có quyền duyệt).
   - Thao tác: Chấp thuận kết bạn -> tự động ghi nhận vào bảng `friendships` theo cặp thứ tự từ điển chuẩn hóa `(user1 < user2)`.
7. `POST /api/v1/community/friend-requests/{request_id}/reject`:
   - Xác thực: Yêu cầu JWT Token (chỉ người nhận được từ chối).
   - Thao tác: Chuyển trạng thái yêu cầu sang `rejected`.
8. `GET /api/v1/community/me/friend-requests`:
   - Xác thực: Yêu cầu JWT Token.
   - Thao tác: Lấy danh sách lời mời kết bạn đang chờ người gọi phản hồi.
9. `GET /api/v1/community/users/{username}/friends`:
   - Xác thực: Công khai.
   - Thao tác: Lấy danh sách bạn bè chính thức của người dùng.
10. `DELETE /api/v1/community/users/{username}/friends`:
    - Xác thực: Yêu cầu JWT Token.
    - Thao tác: Hủy quan hệ bạn bè hai chiều.

### C. Quyền riêng tư & Tủ sách công khai APIs
11. `PUT /api/v1/community/me/privacy`:
    - Xác thực: Yêu cầu JWT Token.
    - Thao tác: Cập nhật quyền riêng tư `bookshelf_privacy` và `activity_privacy` (`public`, `friends`, `private`). Có hiệu lực ngay lập tức.
12. `GET /api/v1/community/me/privacy`:
    - Xác thực: Yêu cầu JWT Token.
    - Thao tác: Xem thiết lập quyền riêng tư hiện tại của tài khoản.
13. `GET /api/v1/community/users/{username}/bookshelf`:
    - Xác thực: Hỗ trợ Guest và Logged-in.
    - Thao tác: Xem tủ sách cá nhân theo ma trận phân quyền.

### D. Activity Feed APIs
14. `GET /api/v1/community/feed`:
    - Xác thực: Yêu cầu JWT Token.
    - Thao tác: Lấy dòng hoạt động từ các tài khoản mà người dùng đang follow. Không sinh dữ liệu giả; tự động lọc bỏ các hoạt động riêng tư hoặc sách nằm trong tủ sách bị ẩn.
15. `GET /api/v1/community/users/{username}/activities`:
    - Xác thực: Hỗ trợ Guest và Logged-in.
    - Thao tác: Lấy dòng lịch sử hoạt động của một cá nhân, tuân thủ nghiêm ngặt quyền riêng tư của tài khoản đó.

---

## 4. MA TRẬN PHÂN QUYỀN VÀ QUYỀN RIÊNG TƯ

### A. Ma trận kiểm soát tủ sách cá nhân (`bookshelf_privacy`)
| Đối tượng yêu cầu | Tủ sách `public` | Tủ sách `friends` | Tủ sách `private` |
| :--- | :---: | :---: | :---: |
| **Chính chủ (Owner)** | ✅ Được xem toàn bộ | ✅ Được xem toàn bộ | ✅ Được xem toàn bộ |
| **Bạn bè đã xác nhận (Friend)** | ✅ Được xem | ✅ Được xem | ❌ 403 Forbidden |
| **Người dùng khác / Follower** | ✅ Được xem | ❌ 403 Forbidden | ❌ 403 Forbidden |
| **Khách vãng lai (Guest)** | ✅ Được xem | ❌ 403 Forbidden | ❌ 403 Forbidden |

### B. Cơ chế bảo vệ dòng hoạt động (Activity Feed Privacy)
1. **Chống trùng lặp:** Ràng buộc `UNIQUE (username, activity_type, entity_id)` đảm bảo sự kiện đọc sách hoặc viết nhận xét chỉ được tạo duy nhất một lần.
2. **Không tiết lộ tủ sách riêng tư:** Khi một tài khoản đặt `bookshelf_privacy = 'private'`, toàn bộ hoạt động `reading_started` và `book_completed` của tài khoản đó sẽ tự động bị loại khỏi dòng Feed của người theo dõi.
3. **Ẩn theo người dùng:** Khi tài khoản đặt `activity_privacy = 'private'`, mọi hoạt động của họ đều bị ẩn khỏi Feed chung.
4. **Đồng bộ khi xóa bài:** Khi bài đánh giá bị xóa, sự kiện `review_created` tương ứng bị xóa khỏi feed ngay lập tức.

---

## 5. BẢNG PHÂN LOẠI & KẾT QUẢ KIỂM THỬ

Toàn bộ 14 bài test trong `tests/test_social_follow_feed_privacy_phase3_4_2.py` đều chạy trực tiếp trên môi trường thực tế (Real FastAPI App, SQLite WAL, Real Auth JWT, Real Books CSV):

| STT | Tên bài kiểm thử | Phân loại | Mô tả kiểm thử & Kết quả |
| :---: | :--- | :---: | :--- |
| 1 | `test_unit_migration_v2_applied` | **Unit Test** | Xác minh Migration v2 áp dụng thành công, bảng `follows`, `friend_requests`, `friendships`, `activity_feed` tồn tại đầy đủ. |
| 2 | `test_unit_are_friends_bilateral_logic` | **Unit Test** | Xác minh tính đối xứng hai chiều của thuật toán kiểm tra bạn bè `(user1 < user2)`. |
| 3 | `test_unit_duplicate_activity_prevention` | **Unit Test** | Xác minh cơ chế `INSERT OR IGNORE` và `UNIQUE` ngăn chặn sự kiện trùng lặp. |
| 4 | `test_real_integration_follow_unfollow_lifecycle` | **Real Integration Test** | Quy trình đầy đủ: User A follow User B -> User B có follower -> User A có following -> User A unfollow -> Danh sách cập nhật chuẩn xác. |
| 5 | `test_real_integration_follow_validations` | **Real Integration Test** | Chặn tự follow (400), chặn follow user không tồn tại (404), chặn follow trùng lặp (400). |
| 6 | `test_real_integration_followers_following_pagination` | **Real Integration Test** | Phân trang danh sách followers/following, kiểm tra số lượng và tính rời rạc giữa các trang. |
| 7 | `test_real_integration_friendship_request_lifecycle` | **Real Integration Test** | Quy trình kết bạn hai chiều: Gửi yêu cầu -> Kiểm tra danh sách chờ -> Chặn IDOR người thứ 3 can thiệp -> Chấp nhận -> Kiểm tra danh sách bạn bè cả hai bên -> Hủy kết bạn. |
| 8 | `test_real_integration_privacy_settings_update_immediate` | **Real Integration Test** | Gọi `PUT /me/privacy` cập nhật quyền riêng tư và xác minh có hiệu lực ngay lập tức qua `GET /me/privacy`. |
| 9 | `test_real_integration_public_bookshelf_privacy_matrix` | **Real Integration Test** | Kiểm chứng toàn bộ ma trận: Public (ai cũng xem được), Friends (chỉ bạn bè được xem, người lạ và guest bị 403), Private (chỉ owner xem được). |
| 10 | `test_real_integration_activity_feed_following_only` | **Real Integration Test** | Feed của User A chỉ hiển thị bài của User B (được follow), không hiển thị bài của User C (không follow). Không sinh sự kiện giả. |
| 11 | `test_real_integration_activity_feed_privacy_controls` | **Real Integration Test** | Khi tác giả đổi `activity_privacy` sang 'private', các hoạt động biến mất ngay khỏi Feed của follower. |
| 12 | `test_real_integration_deleted_review_removed_from_feed` | **Real Integration Test** | Khi bài đánh giá bị tác giả xóa, hoạt động tương ứng lập tức biến mất khỏi dòng Feed. |
| 13 | `test_real_integration_private_bookshelf_hides_reading_activities` | **Real Integration Test** | Khi tác giả đặt `bookshelf_privacy = 'private'`, hoạt động đọc sách không bị rò rỉ vào feed của người theo dõi. |
| 14 | `test_real_integration_concurrent_follow_unfollow` | **Real Integration Test** | Kiểm thử áp lực: 6 luồng đồng thời gửi yêu cầu follow tới 1 tài khoản, SQLite WAL xử lý hoàn hảo không gặp lỗi khóa cơ sở dữ liệu (`database is locked`). |

---

## 6. KẾT QUẢ HỒI QUY TOÀN BỘ HỆ THỐNG (FULL REGRESSION)

Đã chạy kiểm thử hồi quy toàn bộ 12 test suites của dự án (từ Phase 1 đến Phase 3.4.2):
```powershell
.venv\Scripts\python -m pytest tests/test_social_follow_feed_privacy_phase3_4_2.py tests/test_social_community_phase3_4_1.py tests/test_continue_reading_progress_hotfix.py tests/test_phase3_3_2b_final_verification.py tests/test_flutter_recommendation_ui.py tests/test_flutter_recommendation_contract.py tests/test_recommendations.py tests/test_ai_crawler_admin.py tests/test_digital_book_reader.py tests/test_personal_bookshelf.py tests/test_fastapi_backend.py tests/test_flutter_api_contract.py -v
```

**Kết quả:**
- **130/130 bài kiểm thử PASSED (100%)** trong thời gian 87.68 giây.
- Không có bất kỳ lỗi hồi quy hay suy giảm hiệu năng nào xảy ra.

---

## 7. BẰNG CHỨNG BẢO TOÀN DỮ LIỆU GỐC & TÍNH TOÀN VẸN HỆ THỐNG

| Thành phần | Trạng thái yêu cầu | Trạng thái thực tế xác minh |
| :--- | :---: | :---: |
| `data/books.csv` | Đúng 208 cuốn sách, 26 cột | ✅ **Chính xác 208 sách, 26 cột** |
| ChromaDB `books_collection` | Đúng 208 vectors | ✅ **Chính xác 208 vectors** |
| Gemini RAG Engine & Embedding | Giữ nguyên vẹn, không re-ingest | ✅ Không thay đổi |
| Digital Book Reader | Giữ nguyên vẹn cơ chế đọc PDF & file | ✅ 9/9 tests pass |
| Personal Bookshelf & Reading Progress | Giữ nguyên vẹn định dạng JSON | ✅ Đồng bộ hoạt động ổn định |
| AI Recommendation Engine | Giữ nguyên thuật toán Hybrid Rec | ✅ 12/12 tests pass |
| AI Crawler Admin Interface | Giữ nguyên 6 nguồn cào dữ liệu | ✅ 7/7 tests pass |
| Streamlit App (`app.py`) | Giữ nguyên cấu trúc | ✅ Không thay đổi |

---

## 8. HẠN CHẾ CÒN TỒN TẠI & HƯỚNG PHÁT TRIỂN TIẾP THEO

1. **Giao diện người dùng (Flutter UI):**
   - Phase 3.4.2 tuân thủ chặt chẽ chỉ thị: **chỉ triển khai tầng Backend Social Engine & REST APIs**, chưa tích hợp giao diện người dùng trên Flutter.
   - Flutter UI cho Community (Trang cá nhân, Danh sách Followers/Following, Activity Feed, nút Thích/Bình luận) sẽ sẵn sàng được triển khai trong Phase 3.4.3 khi có phê duyệt.
2. **Cơ chế Notification thời gian thực:**
   - Dòng Feed hiện tại hoạt động theo mô hình truy vấn phân trang qua REST API. Việc đẩy thông báo đẩy thời gian thực (WebSockets hoặc SSE) có thể bổ sung trong các giai đoạn tiếp theo nếu có yêu cầu.

---

## 9. QUY TẮC DỪNG

> [!IMPORTANT]
> Toàn bộ các yêu cầu của **PHASE 3.4.2** đã được hoàn tất và nghiệm thu 100%.  
> Hệ thống **DỪNG LẠI TẠI ĐÂY**, không tự ý chuyển sang Phase 3.4.3 hay viết mã Flutter UI, chờ chỉ thị và phê duyệt chính thức từ Bạn!

