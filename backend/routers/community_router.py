"""
Community REST Router for Social Reading Module
Exposes endpoints for User Profiles, Reviews, Comments, and Reactions.
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.core.security import get_current_user, get_current_user_optional, require_admin
from backend.schemas.community_schema import (
    UserProfileUpdate,
    UserProfileResponse,
    ReviewCreate,
    ReviewUpdate,
    ReviewResponse,
    ReviewListResponse,
    CommentCreate,
    CommentUpdate,
    CommentResponse,
    CommentListResponse,
    ReactionCreate,
    ReactionResponse,
    FollowItemResponse,
    FollowListResponse,
    FollowActionResponse,
    FriendRequestItemResponse,
    FriendRequestListResponse,
    FriendItemResponse,
    FriendListResponse,
    PrivacySettingsUpdate,
    PrivacySettingsResponse,
    ActivityFeedItem,
    ActivityFeedResponse,
    PublicBookshelfItem,
    PublicBookshelfResponse,
    ReportCreate,
    ReportResponse,
    ReportListResponse,
    ReportDismissRequest,
    ModerationActionRequest,
    ModerationActionResponse,
    ModerationActionListResponse,
    AdminReportDetailResponse,
    AdminReportListResponse,
)
from backend.services import community_service

router = APIRouter(prefix="/community", tags=["Community"])


# ==============================================================================
# User Profile Endpoints
# ==============================================================================

@router.get("/profile/{username}", response_model=UserProfileResponse)
def get_user_profile(
    username: str,
    _: dict[str, Any] | None = Depends(get_current_user_optional),
) -> UserProfileResponse:
    """Get public profile of a user by username."""
    profile = community_service.get_user_profile(username)
    return UserProfileResponse(**profile)


@router.put("/profile/me", response_model=UserProfileResponse)
def update_my_profile(
    profile_in: UserProfileUpdate,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> UserProfileResponse:
    """Update profile details of the currently authenticated user."""
    updated = community_service.update_user_profile(
        username=current_user["username"],
        display_name=profile_in.display_name,
        avatar_url=profile_in.avatar_url,
        bio=profile_in.bio,
    )
    return UserProfileResponse(**updated)


# ==============================================================================
# Review Endpoints
# ==============================================================================

@router.post("/books/{book_id}/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_book_review(
    book_id: str,
    review_in: ReviewCreate,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> ReviewResponse:
    """Create a new review for a book. 1 review per user per book."""
    rev = community_service.create_review(
        username=current_user["username"],
        book_id=book_id,
        rating=review_in.rating,
        title=review_in.title,
        content=review_in.content,
        contains_spoiler=review_in.contains_spoiler,
    )
    return ReviewResponse(**rev)


@router.get("/books/{book_id}/reviews", response_model=ReviewListResponse)
def get_book_reviews(
    book_id: str,
    rating: int | None = Query(None, ge=1, le=5, description="Lọc theo số sao 1-5"),
    sort_by: str = Query("newest", pattern=r"^(newest|popular|highest_rating|lowest_rating)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
) -> ReviewListResponse:
    """List reviews for a book with pagination, ratings breakdown, and sort options."""
    current_username = current_user["username"] if current_user else None
    res = community_service.get_book_reviews(
        book_id=book_id,
        current_username=current_username,
        rating_filter=rating,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )
    return ReviewListResponse(**res)


@router.get("/reviews/{review_id}", response_model=ReviewResponse)
def get_review_detail(
    review_id: str,
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
) -> ReviewResponse:
    """Get single review details."""
    current_username = current_user["username"] if current_user else None
    is_admin = current_user.get("role") == "admin" if current_user else False
    rev = community_service.get_review_detail(review_id, current_username=current_username, is_admin=is_admin)
    return ReviewResponse(**rev)


@router.put("/reviews/{review_id}", response_model=ReviewResponse)
def update_review(
    review_id: str,
    review_in: ReviewUpdate,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> ReviewResponse:
    """Update a review owned by the caller."""
    updated = community_service.update_review(
        review_id=review_id,
        username=current_user["username"],
        rating=review_in.rating,
        title=review_in.title,
        content=review_in.content,
        contains_spoiler=review_in.contains_spoiler,
    )
    return ReviewResponse(**updated)


@router.delete("/reviews/{review_id}")
def delete_review(
    review_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Delete review. Author or Admin permitted."""
    is_admin = current_user.get("role") == "admin"
    community_service.delete_review(
        review_id=review_id,
        username=current_user["username"],
        is_admin=is_admin,
    )
    return {"success": True, "message": "Đã xóa bài đánh giá thành công"}


# ==============================================================================
# Comment Endpoints
# ==============================================================================

@router.post("/reviews/{review_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(
    review_id: str,
    comment_in: CommentCreate,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> CommentResponse:
    """Create a comment or reply under a review."""
    cmt = community_service.create_comment(
        username=current_user["username"],
        review_id=review_id,
        content=comment_in.content,
        parent_comment_id=comment_in.parent_comment_id,
    )
    return CommentResponse(**cmt)


@router.get("/reviews/{review_id}/comments", response_model=CommentListResponse)
def get_review_comments(
    review_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
) -> CommentListResponse:
    """List comments for a review with pagination."""
    current_username = current_user["username"] if current_user else None
    res = community_service.get_review_comments(
        review_id=review_id,
        current_username=current_username,
        page=page,
        page_size=page_size,
    )
    return CommentListResponse(**res)


@router.put("/comments/{comment_id}", response_model=CommentResponse)
def update_comment(
    comment_id: str,
    comment_in: CommentUpdate,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> CommentResponse:
    """Update a comment. Protected: author only."""
    updated = community_service.update_comment(
        comment_id=comment_id,
        username=current_user["username"],
        content=comment_in.content,
    )
    return CommentResponse(**updated)


@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Delete a comment. Author or Admin permitted."""
    is_admin = current_user.get("role") == "admin"
    community_service.delete_comment(
        comment_id=comment_id,
        username=current_user["username"],
        is_admin=is_admin,
    )
    return {"success": True, "message": "Đã xóa bình luận thành công"}


# ==============================================================================
# Reaction Endpoints (Like / Unlike)
# ==============================================================================

@router.post("/reactions", response_model=ReactionResponse)
def like_target(
    reaction_in: ReactionCreate,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> ReactionResponse:
    """Like a review or comment. Blocked on self-like and duplicate."""
    res = community_service.toggle_reaction(
        username=current_user["username"],
        target_type=reaction_in.target_type,
        target_id=reaction_in.target_id,
        is_like=True,
    )
    return ReactionResponse(**res)


@router.delete("/reactions", response_model=ReactionResponse)
def unlike_target(
    target_type: str = Query(..., pattern=r"^(review|comment)$"),
    target_id: str = Query(..., min_length=1),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> ReactionResponse:
    """Unlike a review or comment."""
    res = community_service.toggle_reaction(
        username=current_user["username"],
        target_type=target_type,
        target_id=target_id,
        is_like=False,
    )
    return ReactionResponse(**res)


# ==============================================================================
# Follow & Relationship Endpoints
# ==============================================================================

@router.post("/users/{username}/follow", response_model=FollowActionResponse)
def follow_user(
    username: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> FollowActionResponse:
    """Follow a user. One-way relationship."""
    res = community_service.follow_user(
        follower_username=current_user["username"],
        target_username=username,
    )
    return FollowActionResponse(**res)


@router.delete("/users/{username}/follow", response_model=FollowActionResponse)
def unfollow_user(
    username: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> FollowActionResponse:
    """Unfollow a user."""
    res = community_service.unfollow_user(
        follower_username=current_user["username"],
        target_username=username,
    )
    return FollowActionResponse(**res)


@router.get("/users/{username}/followers", response_model=FollowListResponse)
def get_user_followers(
    username: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: dict[str, Any] | None = Depends(get_current_user_optional),
) -> FollowListResponse:
    """List followers of a user."""
    res = community_service.get_user_followers(username=username, page=page, page_size=page_size)
    return FollowListResponse(**res)


@router.get("/users/{username}/following", response_model=FollowListResponse)
def get_user_following(
    username: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: dict[str, Any] | None = Depends(get_current_user_optional),
) -> FollowListResponse:
    """List accounts that a user is following."""
    res = community_service.get_user_following(username=username, page=page, page_size=page_size)
    return FollowListResponse(**res)


# ==============================================================================
# Friendship Endpoints (for 'friends' Privacy Level)
# ==============================================================================

@router.post("/users/{username}/friend-request")
def send_friend_request(
    username: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Send a friend request to establish a two-way friendship."""
    return community_service.send_friend_request(
        sender_username=current_user["username"],
        receiver_username=username,
    )


@router.post("/friend-requests/{request_id}/accept")
def accept_friend_request(
    request_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Accept incoming friend request. Only recipient can accept."""
    return community_service.accept_friend_request(
        request_id=request_id,
        current_username=current_user["username"],
    )


@router.post("/friend-requests/{request_id}/reject")
def reject_friend_request(
    request_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Reject incoming friend request."""
    return community_service.reject_friend_request(
        request_id=request_id,
        current_username=current_user["username"],
    )


@router.get("/me/friend-requests", response_model=FriendRequestListResponse)
def get_my_pending_friend_requests(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> FriendRequestListResponse:
    """Get list of incoming pending friend requests for the caller."""
    res = community_service.get_pending_friend_requests(username=current_user["username"])
    return FriendRequestListResponse(**res)


@router.get("/users/{username}/friends", response_model=FriendListResponse)
def get_user_friends(
    username: str,
    _: dict[str, Any] | None = Depends(get_current_user_optional),
) -> FriendListResponse:
    """Get list of confirmed two-way friends of a user."""
    res = community_service.get_user_friends(username=username)
    return FriendListResponse(**res)


@router.delete("/users/{username}/friends")
def remove_friend(
    username: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Remove friendship between current user and target user."""
    return community_service.remove_friend(
        user_a=current_user["username"],
        user_b=username,
    )


# ==============================================================================
# Privacy Settings Endpoints
# ==============================================================================

@router.put("/me/privacy", response_model=PrivacySettingsResponse)
def update_my_privacy_settings(
    privacy_in: PrivacySettingsUpdate,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> PrivacySettingsResponse:
    """Update privacy settings for bookshelf and activity feed. Takes effect immediately."""
    res = community_service.update_privacy_settings(
        username=current_user["username"],
        bookshelf_privacy=privacy_in.bookshelf_privacy,
        activity_privacy=privacy_in.activity_privacy,
    )
    return PrivacySettingsResponse(**res)


@router.get("/me/privacy", response_model=PrivacySettingsResponse)
def get_my_privacy_settings(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> PrivacySettingsResponse:
    """Get current privacy settings of the caller."""
    res = community_service.get_privacy_settings(username=current_user["username"])
    return PrivacySettingsResponse(**res)


# ==============================================================================
# Activity Feed Endpoints
# ==============================================================================

@router.get("/feed", response_model=ActivityFeedResponse)
def get_my_activity_feed(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> ActivityFeedResponse:
    """
    Get aggregated activity feed from accounts followed by the caller.
    Filters out private content and respects privacy preferences.
    """
    res = community_service.get_feed(
        current_username=current_user["username"],
        page=page,
        page_size=page_size,
    )
    return ActivityFeedResponse(**res)


@router.get("/users/{username}/activities", response_model=ActivityFeedResponse)
def get_user_activities(
    username: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
) -> ActivityFeedResponse:
    """Get activity timeline of a specific user, honoring privacy restrictions."""
    caller = current_user["username"] if current_user else None
    res = community_service.get_user_activities(
        target_username=username,
        current_username=caller,
        page=page,
        page_size=page_size,
    )
    return ActivityFeedResponse(**res)


# ==============================================================================
# Public Bookshelf Endpoints
# ==============================================================================

@router.get("/users/{username}/bookshelf", response_model=PublicBookshelfResponse)
def get_user_public_bookshelf(
    username: str,
    status_filter: str | None = Query(None, alias="status", pattern=r"^(favorite|reading|completed)$"),
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
) -> PublicBookshelfResponse:
    """
    Get bookshelf of a user. Access controlled via privacy settings:
    - public: open to everyone
    - friends: open only to caller if confirmed friend or owner
    - private: open strictly to owner
    """
    caller = current_user["username"] if current_user else None
    res = community_service.get_public_bookshelf(
        target_username=username,
        current_username=caller,
        status_filter=status_filter,
    )
    return PublicBookshelfResponse(**res)


# ==============================================================================
# Phase 3.4.3: Social Community Moderation Endpoints
# ==============================================================================

# ------------------------------------------------------------------------------
# User Reporting APIs
# ------------------------------------------------------------------------------

@router.post("/reports", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def submit_report(
    report_in: ReportCreate,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> ReportResponse:
    """Submit a report against an infringing review or comment."""
    res = community_service.create_report(
        reporter_username=current_user["username"],
        target_type=report_in.target_type,
        target_id=report_in.target_id,
        reason=report_in.reason,
        description=report_in.description,
    )
    return ReportResponse(**res)


@router.get("/me/reports", response_model=ReportListResponse)
def get_my_submitted_reports(
    status_filter: str | None = Query(None, alias="status", pattern=r"^(pending|reviewing|resolved|dismissed)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> ReportListResponse:
    """View reports submitted by the currently authenticated user."""
    res = community_service.get_my_reports(
        reporter_username=current_user["username"],
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )
    return ReportListResponse(**res)


# ------------------------------------------------------------------------------
# Admin Moderation APIs (Strict RBAC - Admin Only)
# ------------------------------------------------------------------------------

@router.get("/admin/reports", response_model=AdminReportListResponse)
def list_admin_reports(
    status_filter: str | None = Query(None, alias="status", pattern=r"^(pending|reviewing|resolved|dismissed)$"),
    target_type: str | None = Query(None, pattern=r"^(review|comment)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: dict[str, Any] = Depends(require_admin),
) -> AdminReportListResponse:
    """Admin: list all reported items with filtering and status breakdown."""
    res = community_service.get_admin_reports(
        status_filter=status_filter,
        target_type_filter=target_type,
        page=page,
        page_size=page_size,
    )
    return AdminReportListResponse(**res)


@router.get("/admin/reports/{report_id}", response_model=AdminReportDetailResponse)
def get_admin_report_detail(
    report_id: str,
    _: dict[str, Any] = Depends(require_admin),
) -> AdminReportDetailResponse:
    """Admin: inspect full details of a report including target content and action history."""
    res = community_service.get_admin_report_detail(report_id=report_id)
    return AdminReportDetailResponse(**res)


@router.post("/admin/reports/{report_id}/claim", response_model=ReportResponse)
def claim_admin_report(
    report_id: str,
    admin_user: dict[str, Any] = Depends(require_admin),
) -> ReportResponse:
    """Admin: claim ownership of a pending report."""
    res = community_service.claim_report(
        report_id=report_id,
        admin_username=admin_user["username"],
    )
    return ReportResponse(**res)


@router.post("/admin/reports/{report_id}/dismiss", response_model=ReportResponse)
def dismiss_admin_report(
    report_id: str,
    dismiss_in: ReportDismissRequest,
    admin_user: dict[str, Any] = Depends(require_admin),
) -> ReportResponse:
    """Admin: dismiss an invalid report with required notes."""
    res = community_service.dismiss_report(
        report_id=report_id,
        admin_username=admin_user["username"],
        notes=dismiss_in.notes,
    )
    return ReportResponse(**res)


@router.post("/admin/reports/{report_id}/actions")
def execute_admin_moderation_action(
    report_id: str,
    action_in: ModerationActionRequest,
    admin_user: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    """Admin: take moderation action (warn, hide, restore, delete) against reported content."""
    res = community_service.execute_moderation_action(
        report_id=report_id,
        admin_username=admin_user["username"],
        action=action_in.action,
        reason=action_in.reason,
    )
    return res


@router.get("/admin/moderation-actions", response_model=ModerationActionListResponse)
def list_admin_moderation_actions(
    target_type: str | None = Query(None, pattern=r"^(review|comment)$"),
    target_id: str | None = Query(None),
    admin_username: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: dict[str, Any] = Depends(require_admin),
) -> ModerationActionListResponse:
    """Admin: view immutable audit log of past moderation actions."""
    res = community_service.get_moderation_actions(
        target_type=target_type,
        target_id=target_id,
        admin_username=admin_username,
        page=page,
        page_size=page_size,
    )
    return ModerationActionListResponse(**res)


