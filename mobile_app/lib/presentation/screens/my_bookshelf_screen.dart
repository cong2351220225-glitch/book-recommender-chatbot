import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:cached_network_image/cached_network_image.dart';

import '../../core/constants/app_colors.dart';
import '../../models/bookshelf_item_model.dart';
import '../../providers/auth_provider.dart';
import '../../providers/bookshelf_provider.dart';
import '../../providers/navigation_provider.dart';
import 'book_detail_screen.dart';
import 'login_screen.dart';

class MyBookshelfScreen extends StatefulWidget {
  const MyBookshelfScreen({super.key});

  @override
  State<MyBookshelfScreen> createState() => _MyBookshelfScreenState();
}

class _MyBookshelfScreenState extends State<MyBookshelfScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final auth = context.read<AuthProvider>();
      if (auth.isAuthenticated) {
        context.read<BookshelfProvider>().loadBookshelf();
      }
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final authProvider = context.watch<AuthProvider>();
    final shelfProvider = context.watch<BookshelfProvider>();

    if (!authProvider.isAuthenticated) {
      return _buildGuestView(context);
    }

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Row(
          children: [
            Icon(Icons.collections_bookmark_rounded, size: 20, color: AppColors.gold),
            SizedBox(width: 8),
            Text('Tủ Sách Cá Nhân'),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            tooltip: 'Làm mới',
            onPressed: () => shelfProvider.loadBookshelf(),
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: AppColors.gold,
          indicatorWeight: 3,
          labelColor: AppColors.gold,
          unselectedLabelColor: Colors.white70,
          labelStyle: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
          tabs: [
            Tab(
              icon: const Icon(Icons.favorite_rounded, size: 18),
              text: 'Yêu thích (${shelfProvider.favoriteCount})',
            ),
            Tab(
              icon: const Icon(Icons.auto_stories_rounded, size: 18),
              text: 'Đang đọc (${shelfProvider.readingCount})',
            ),
            Tab(
              icon: const Icon(Icons.check_circle_rounded, size: 18),
              text: 'Đã đọc (${shelfProvider.completedCount})',
            ),
          ],
        ),
      ),
      body: shelfProvider.isLoading && shelfProvider.items.isEmpty
          ? const Center(
              child: CircularProgressIndicator(color: AppColors.gold),
            )
          : shelfProvider.errorMessage != null && shelfProvider.items.isEmpty
              ? _buildErrorView(context, shelfProvider)
              : TabBarView(
                  controller: _tabController,
                  children: [
                    _buildShelfTab(
                      context,
                      shelfProvider.favoriteItems,
                      emptyTitle: 'Chưa có sách yêu thích',
                      emptySubtitle: 'Nhấn vào biểu tượng trái tim ở chi tiết sách để lưu vào đây.',
                      tabType: 'favorite',
                    ),
                    _buildShelfTab(
                      context,
                      shelfProvider.readingItems,
                      emptyTitle: 'Chưa có sách đang đọc',
                      emptySubtitle: 'Đánh dấu sách bạn đang đọc để theo dõi tiến độ trang thuận tiện.',
                      tabType: 'reading',
                    ),
                    _buildShelfTab(
                      context,
                      shelfProvider.completedItems,
                      emptyTitle: 'Chưa có sách đã đọc',
                      emptySubtitle: 'Lưu lại những tác phẩm bạn đã đọc xong và chấm điểm đánh giá.',
                      tabType: 'completed',
                    ),
                  ],
                ),
    );
  }

  Widget _buildGuestView(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Tủ Sách Cá Nhân'),
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 400),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: AppColors.navyDark,
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.gold.withOpacity(0.2),
                        blurRadius: 16,
                      ),
                    ],
                  ),
                  child: const Icon(
                    Icons.lock_person_rounded,
                    size: 48,
                    color: AppColors.gold,
                  ),
                ),
                const SizedBox(height: 20),
                const Text(
                  'Yêu Cầu Đăng Nhập',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                    color: AppColors.navyDark,
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Đăng nhập tài khoản của bạn để quản lý danh sách yêu thích, đánh dấu tiến độ đọc và lưu giữ tủ sách cá nhân.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 13,
                    color: AppColors.textSecondary,
                    height: 1.4,
                  ),
                ),
                const SizedBox(height: 24),
                ElevatedButton.icon(
                  icon: const Icon(Icons.login_rounded, size: 18),
                  label: const Text('Đăng nhập ngay'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.navy,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10),
                    ),
                  ),
                  onPressed: () {
                    Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => const LoginScreen()),
                    );
                  },
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildErrorView(BuildContext context, BookshelfProvider provider) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline_rounded, size: 48, color: AppColors.error),
            const SizedBox(height: 12),
            Text(
              provider.errorMessage ?? 'Không thể tải tủ sách',
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 14, color: AppColors.textPrimary),
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              icon: const Icon(Icons.refresh_rounded, size: 16),
              label: const Text('Thử lại'),
              onPressed: () => provider.loadBookshelf(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildShelfTab(
    BuildContext context,
    List<BookshelfItemModel> items, {
    required String emptyTitle,
    required String emptySubtitle,
    required String tabType,
  }) {
    if (items.isEmpty) {
      return RefreshIndicator(
        onRefresh: () => context.read<BookshelfProvider>().loadBookshelf(),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(32.0),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 400),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const SizedBox(height: 40),
                  Container(
                    padding: const EdgeInsets.all(18),
                    decoration: BoxDecoration(
                      color: AppColors.surfaceVariant,
                      shape: BoxShape.circle,
                      border: Border.all(color: AppColors.border),
                    ),
                    child: Icon(
                      tabType == 'favorite'
                          ? Icons.favorite_border_rounded
                          : (tabType == 'reading'
                              ? Icons.auto_stories_outlined
                              : Icons.check_circle_outline_rounded),
                      size: 40,
                      color: AppColors.goldDark,
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    emptyTitle,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: AppColors.navyDark,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    emptySubtitle,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      fontSize: 13,
                      color: AppColors.textSecondary,
                      height: 1.4,
                    ),
                  ),
                  const SizedBox(height: 24),
                  OutlinedButton.icon(
                    icon: const Icon(Icons.explore_rounded, size: 16, color: AppColors.navy),
                    label: const Text(
                      'Khám phá sách trong kho',
                      style: TextStyle(color: AppColors.navy, fontWeight: FontWeight.bold),
                    ),
                    style: OutlinedButton.styleFrom(
                      side: const BorderSide(color: AppColors.navy),
                      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                    onPressed: () {
                      context.read<NavigationProvider>().setIndex(1); // switch to Catalog tab
                    },
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () => context.read<BookshelfProvider>().loadBookshelf(),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 900),
          child: ListView.builder(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
            itemCount: items.length,
            itemBuilder: (context, index) {
              final item = items[index];
              return _buildBookshelfCard(context, item);
            },
          ),
        ),
      ),
    );
  }

  Widget _buildBookshelfCard(BuildContext context, BookshelfItemModel item) {
    final book = item.book;
    final title = book?.title ?? 'Tác phẩm #${item.bookId}';
    final author = book?.author ?? 'Không rõ tác giả';
    final cover = book?.coverUrl ?? '';
    final genre = book?.genre ?? '';

    return Card(
      elevation: 1,
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: AppColors.border),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () {
          Navigator.of(context).push(
            MaterialPageRoute(
              builder: (_) => BookDetailScreen(bookId: item.bookId),
            ),
          );
        },
        child: Padding(
          padding: const EdgeInsets.all(12.0),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Cover thumbnail
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: SizedBox(
                  width: 65,
                  height: 95,
                  child: cover.isNotEmpty
                      ? CachedNetworkImage(
                          imageUrl: cover,
                          fit: BoxFit.cover,
                          placeholder: (context, url) => Container(
                            color: AppColors.surfaceVariant,
                            child: const Center(
                              child: SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              ),
                            ),
                          ),
                          errorWidget: (context, url, error) => Container(
                            color: AppColors.navyDark,
                            child: const Icon(Icons.book_rounded, color: AppColors.gold, size: 28),
                          ),
                        )
                      : Container(
                          color: AppColors.navyDark,
                          child: const Icon(Icons.book_rounded, color: AppColors.gold, size: 28),
                        ),
                ),
              ),
              const SizedBox(width: 14),

              // Info & Actions
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      author,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 12,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    if (genre.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: AppColors.surfaceVariant,
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: AppColors.border),
                        ),
                        child: Text(
                          genre,
                          style: const TextStyle(fontSize: 10, color: AppColors.navy),
                        ),
                      ),
                    ],

                    // Reading progress indicator for 'reading'
                    if (item.isReading) ...[
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(4),
                              child: LinearProgressIndicator(
                                value: item.progressPercentage,
                                backgroundColor: AppColors.border,
                                valueColor: const AlwaysStoppedAnimation<Color>(AppColors.gold),
                                minHeight: 6,
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            item.totalPages > 0
                                ? 'Trang ${item.progressPage}/${item.totalPages}'
                                : 'Trang ${item.progressPage}',
                            style: const TextStyle(fontSize: 11, color: AppColors.textSecondary),
                          ),
                        ],
                      ),
                    ],

                    // Rating for completed
                    if (item.isCompleted && item.rating > 0) ...[
                      const SizedBox(height: 6),
                      Row(
                        children: List.generate(
                          5,
                          (i) => Icon(
                            i < item.rating ? Icons.star_rounded : Icons.star_border_rounded,
                            size: 14,
                            color: AppColors.gold,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),

              // Action buttons (Popup Menu)
              PopupMenuButton<String>(
                icon: const Icon(Icons.more_vert_rounded, size: 20, color: AppColors.textSecondary),
                onSelected: (value) => _handleCardAction(context, item, value),
                itemBuilder: (context) => [
                  if (item.status != 'reading')
                    const PopupMenuItem(
                      value: 'set_reading',
                      child: Row(
                        children: [
                          Icon(Icons.auto_stories_rounded, size: 16, color: AppColors.navy),
                          SizedBox(width: 8),
                          Text('Đang đọc', style: TextStyle(fontSize: 13)),
                        ],
                      ),
                    ),
                  if (item.status != 'completed')
                    const PopupMenuItem(
                      value: 'set_completed',
                      child: Row(
                        children: [
                          Icon(Icons.check_circle_rounded, size: 16, color: AppColors.success),
                          SizedBox(width: 8),
                          Text('Đã đọc xong', style: TextStyle(fontSize: 13)),
                        ],
                      ),
                    ),
                  if (item.isReading)
                    const PopupMenuItem(
                      value: 'update_progress',
                      child: Row(
                        children: [
                          Icon(Icons.edit_note_rounded, size: 16, color: AppColors.goldDark),
                          SizedBox(width: 8),
                          Text('Cập nhật số trang', style: TextStyle(fontSize: 13)),
                        ],
                      ),
                    ),
                  const PopupMenuDivider(),
                  const PopupMenuItem(
                    value: 'remove',
                    child: Row(
                      children: [
                        Icon(Icons.delete_outline_rounded, size: 16, color: AppColors.error),
                        SizedBox(width: 8),
                        Text('Xóa khỏi tủ sách', style: TextStyle(fontSize: 13, color: AppColors.error)),
                      ],
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _handleCardAction(BuildContext context, BookshelfItemModel item, String action) {
    final provider = context.read<BookshelfProvider>();

    if (action == 'set_reading') {
      provider.updateStatus(item.id, 'reading');
    } else if (action == 'set_completed') {
      provider.updateStatus(item.id, 'completed');
    } else if (action == 'remove') {
      provider.removeItem(item.id);
    } else if (action == 'update_progress') {
      _showProgressDialog(context, item);
    }
  }

  void _showProgressDialog(BuildContext context, BookshelfItemModel item) {
    final pageController = TextEditingController(text: item.progressPage.toString());
    final totalController = TextEditingController(
      text: item.totalPages > 0 ? item.totalPages.toString() : '',
    );

    showDialog(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Cập nhật tiến độ đọc', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: pageController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Trang hiện tại',
                  hintText: 'Nhập số trang bạn đã đọc đến',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: totalController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Tổng số trang',
                  hintText: 'Để trống nếu không rõ',
                  border: OutlineInputBorder(),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Hủy'),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.navy,
                foregroundColor: Colors.white,
              ),
              onPressed: () {
                final page = int.tryParse(pageController.text.trim()) ?? item.progressPage;
                final total = int.tryParse(totalController.text.trim());
                context.read<BookshelfProvider>().updateProgress(
                      item.id,
                      page,
                      totalPages: total,
                    );
                Navigator.of(dialogContext).pop();
              },
              child: const Text('Lưu'),
            ),
          ],
        );
      },
    );
  }
}

