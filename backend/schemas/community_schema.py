"""
Pydantic Schemas for Social Community Module
Defines models for Reviews, Comments, Reactions, and User Profiles.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field, constr


# ==============================================================================
# User Profile Schemas
# ==============================================================================

class UserProfileUpdate(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=100, description="Tên hiển thị công khai")
    avatar_url: str = Field("", max_length=500, description="Đường dẫn ảnh đại diện")
    bio: str = Field("", max_length=500, description="Giới thiệu bản thân")


class UserProfileResponse(BaseModel):
    username: str
    display_name: str
    avatar_url: str = ""
    bio: str = ""
    reviews_count: int = 0
    followers_count: int = 0
    following_count: int = 0
    bookshelf_privacy: str = "public"
    activity_privacy: str = "public"
    created_at: str
    updated_at: str


# ==============================================================================
# Review Schemas
# ==============================================================================

class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Đánh giá sao từ 1 đến 5")
    title: str = Field(..., min_length=3, max_length=200, description="Tiêu đề nhận xét")
    content: str = Field(..., min_length=10, max_length=5000, description="Nội dung bài nhận xét")
    contains_spoiler: bool = Field(False, description="Cảnh báo tiết lộ nội dung sách")


class ReviewUpdate(BaseModel):
    rating: int | None = Field(None, ge=1, le=5, description="Đánh giá sao từ 1 đến 5")
    title: str | None = Field(None, min_length=3, max_length=200, description="Tiêu đề nhận xét")
    content: str | None = Field(None, min_length=10, max_length=5000, description="Nội dung nhận xét")
    contains_spoiler: bool | None = Field(None, description="Cảnh báo tiết lộ nội dung")


class ReviewResponse(BaseModel):
    id: str
    book_id: str
    username: str
    user_display_name: str
    user_avatar_url: str = ""
    rating: int
    title: str
    content: str
    contains_spoiler: bool
    likes_count: int = 0
    comments_count: int = 0
    user_liked: bool = False
    status: str = "active"
    created_at: str
    updated_at: str


class ReviewListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    average_rating: float = 0.0
    rating_breakdown: dict[str, int] = Field(default_factory=dict)
    reviews: list[ReviewResponse] = Field(default_factory=list)


# ==============================================================================
# Comment Schemas
# ==============================================================================

class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000, description="Nội dung bình luận")
    parent_comment_id: str | None = Field(None, description="Mã bình luận cha nếu là câu trả lời")


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000, description="Nội dung bình luận sửa đổi")


class CommentResponse(BaseModel):
    id: str
    review_id: str
    username: str
    user_display_name: str
    user_avatar_url: str = ""
    parent_comment_id: str | None = None
    content: str
    likes_count: int = 0
    user_liked: bool = False
    replies_count: int = 0
    status: str = "active"
    created_at: str
    updated_at: str


class CommentListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    comments: list[CommentResponse] = Field(default_factory=list)


# ==============================================================================
# Reaction / Like Schemas
# ==============================================================================

class ReactionCreate(BaseModel):
    target_type: str = Field(..., pattern=r"^(review|comment)$", description="Loại đối tượng: review hoặc comment")
    target_id: str = Field(..., min_length=1, description="Mã đối tượng review_id hoặc comment_id")


class ReactionResponse(BaseModel):
    success: bool
    target_type: str
    target_id: str
    liked: bool
    likes_count: int
    message: str


# ==============================================================================
# Follow & Relationship Schemas
# ==============================================================================

class FollowItemResponse(BaseModel):
    username: str
    display_name: str
    avatar_url: str = ""
    bio: str = ""
    created_at: str


class FollowListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[FollowItemResponse] = Field(default_factory=list)


class FollowActionResponse(BaseModel):
    success: bool
    message: str
    target_username: str
    is_following: bool


# ==============================================================================
# Friendship Schemas (Two-way mechanism for 'friends' privacy level)
# ==============================================================================

class FriendRequestItemResponse(BaseModel):
    id: str
    sender_username: str
    sender_display_name: str
    sender_avatar_url: str = ""
    receiver_username: str
    status: str
    created_at: str


class FriendRequestListResponse(BaseModel):
    total: int
    items: list[FriendRequestItemResponse] = Field(default_factory=list)


class FriendItemResponse(BaseModel):
    username: str
    display_name: str
    avatar_url: str = ""
    bio: str = ""
    created_at: str


class FriendListResponse(BaseModel):
    total: int
    items: list[FriendItemResponse] = Field(default_factory=list)


# ==============================================================================
# Privacy Settings Schemas
# ==============================================================================

class PrivacySettingsUpdate(BaseModel):
    bookshelf_privacy: str | None = Field(None, pattern=r"^(public|friends|private)$", description="Quyền riêng tư tủ sách: public, friends, private")
    activity_privacy: str | None = Field(None, pattern=r"^(public|friends|private)$", description="Quyền riêng tư hoạt động: public, friends, private")


class PrivacySettingsResponse(BaseModel):
    username: str
    bookshelf_privacy: str
    activity_privacy: str
    updated_at: str


# ==============================================================================
# Activity Feed Schemas
# ==============================================================================

class ActivityFeedItem(BaseModel):
    id: str
    username: str
    user_display_name: str
    user_avatar_url: str = ""
    activity_type: str  # review_created, reading_started, book_completed
    entity_id: str
    entity_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class ActivityFeedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ActivityFeedItem] = Field(default_factory=list)


# ==============================================================================
# Public Bookshelf Schemas
# ==============================================================================

class PublicBookshelfItem(BaseModel):
    id: str
    book_id: str
    title: str
    author: str
    cover_image: str = ""
    genre: str = ""
    publisher: str = ""
    publish_year: int = 0
    rating: float = 0.0
    status: str
    progress_page: int = 0
    total_pages: int = 0
    added_at: str
    updated_at: str


class PublicBookshelfResponse(BaseModel):
    username: str
    display_name: str
    bookshelf_privacy: str
    total: int
    items: list[PublicBookshelfItem] = Field(default_factory=list)


# ==============================================================================
# Phase 3.4.3: Social Moderation & Reporting Schemas
# ==============================================================================

class ReportCreate(BaseModel):
    target_type: str = Field(..., pattern=r"^(review|comment)$", description="Loại nội dung bị báo cáo: review hoặc comment")
    target_id: str = Field(..., min_length=1, max_length=100, description="Mã đối tượng bị báo cáo")
    reason: str = Field(..., pattern=r"^(spam|harassment|misinformation|inappropriate|copyright|other)$", description="Lý do báo cáo")
    description: str = Field("", max_length=500, description="Mô tả bổ sung chi tiết (tối đa 500 ký tự)")


class ReportResponse(BaseModel):
    id: str
    reporter_username: str
    target_type: str
    target_id: str
    reason: str
    description: str = ""
    status: str
    claimed_by: str | None = None
    claimed_at: str | None = None
    resolved_by: str | None = None
    resolved_at: str | None = None
    admin_notes: str = ""
    created_at: str
    updated_at: str


class ReportListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ReportResponse] = Field(default_factory=list)


class ReportDismissRequest(BaseModel):
    notes: str = Field(..., min_length=3, max_length=500, description="Lý do hoặc ghi chú bác bỏ báo cáo")


class ModerationActionRequest(BaseModel):
    action: str = Field(..., pattern=r"^(warn|hide|restore|delete)$", description="Hành động kiểm duyệt: warn, hide, restore, delete")
    reason: str = Field(..., min_length=3, max_length=500, description="Lý do xử lý kiểm duyệt")


class ModerationActionResponse(BaseModel):
    id: str
    admin_username: str
    target_type: str
    target_id: str
    report_id: str | None = None
    action: str
    previous_status: str
    new_status: str
    reason: str
    created_at: str


class ModerationActionListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ModerationActionResponse] = Field(default_factory=list)


class AdminReportDetailResponse(BaseModel):
    id: str
    reporter_username: str
    reporter_display_name: str
    target_type: str
    target_id: str
    target_content: str
    target_author_username: str
    target_status: str
    reason: str
    description: str
    status: str
    claimed_by: str | None = None
    claimed_at: str | None = None
    resolved_by: str | None = None
    resolved_at: str | None = None
    admin_notes: str = ""
    created_at: str
    updated_at: str
    history: list[ModerationActionResponse] = Field(default_factory=list)


class AdminReportListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    status_counts: dict[str, int] = Field(default_factory=dict)
    items: list[ReportResponse] = Field(default_factory=list)



