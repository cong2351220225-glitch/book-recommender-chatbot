import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants/app_colors.dart';
import '../../core/utils/responsive_layout.dart';
import '../../providers/author_provider.dart';
import '../widgets/book_card.dart';
import '../widgets/section_header.dart';
import '../widgets/state_views.dart';
import 'book_detail_screen.dart';

class AuthorDetailScreen extends StatefulWidget {
  final String authorId;

  const AuthorDetailScreen({super.key, required this.authorId});

  @override
  State<AuthorDetailScreen> createState() => _AuthorDetailScreenState();
}

class _AuthorDetailScreenState extends State<AuthorDetailScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<AuthorProvider>().fetchAuthorDetail(widget.authorId);
    });
  }

  @override
  Widget build(BuildContext context) {
    final authorProvider = context.watch<AuthorProvider>();

    if (authorProvider.isLoadingDetail) {
      return Scaffold(
        appBar: AppBar(title: const Text('Thông tin tác giả')),
        body: const LoadingView(message: 'Đang tải thông tin tác giả...'),
      );
    }

    if (authorProvider.detailError != null || authorProvider.selectedAuthor == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Thông tin tác giả')),
        body: ErrorView(
          message: authorProvider.detailError ?? 'Không tìm thấy tác giả.',
          onRetry: () => authorProvider.fetchAuthorDetail(widget.authorId),
        ),
      );
    }

    final author = authorProvider.selectedAuthor!;
    final colCount = ResponsiveLayout.getGridColumnCount(context);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Text(author.name),
      ),
      body: SingleChildScrollView(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1100),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 20.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Author Header Card
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(24.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              CircleAvatar(
                                radius: 36,
                                backgroundColor: AppColors.navy.withOpacity(0.12),
                                child: Text(
                                  author.name.isNotEmpty ? author.name[0].toUpperCase() : '?',
                                  style: const TextStyle(
                                    fontSize: 28,
                                    fontWeight: FontWeight.bold,
                                    color: AppColors.navyDark,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 18),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      author.name,
                                      style: const TextStyle(
                                        fontSize: 22,
                                        fontWeight: FontWeight.bold,
                                        color: AppColors.navyDark,
                                      ),
                                    ),
                                    const SizedBox(height: 4),
                                    Wrap(
                                      spacing: 8,
                                      runSpacing: 4,
                                      children: [
                                        if (author.nationality.isNotEmpty)
                                          _buildBadge(Icons.flag_rounded, author.nationality),
                                        if (author.lifespan.isNotEmpty)
                                          _buildBadge(Icons.calendar_today_rounded, author.lifespan),
                                        _buildBadge(Icons.book_rounded, '${author.workCount} sách trong thư viện'),
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                          if (author.bio.isNotEmpty) ...[
                            const Divider(height: 28),
                            const Text(
                              'Tiểu sử & Sự nghiệp',
                              style: TextStyle(
                                fontSize: 15,
                                fontWeight: FontWeight.bold,
                                color: AppColors.navyDark,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              author.bio,
                              style: const TextStyle(
                                fontSize: 13,
                                height: 1.6,
                                color: AppColors.textPrimary,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),

                  const SizedBox(height: 28),

                  // Books by this author
                  SectionHeader(
                    title: 'Tác phẩm trong Thư viện',
                    subtitle: 'Các cuốn sách hiện có thuộc bộ sưu tập của ${author.name}',
                  ),
                  const SizedBox(height: 12),

                  if (author.books.isEmpty)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 32.0),
                      child: Center(
                        child: Text(
                          'Chưa có tác phẩm nào của tác giả này trong thư viện.',
                          style: TextStyle(color: AppColors.textSecondary),
                        ),
                      ),
                    )
                  else
                    GridView.builder(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: author.books.length,
                      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: colCount,
                        childAspectRatio: 0.62,
                        crossAxisSpacing: 14,
                        mainAxisSpacing: 14,
                      ),
                      itemBuilder: (context, index) {
                        final book = author.books[index];
                        return BookCard(
                          book: book,
                          onTap: () {
                            Navigator.of(context).push(
                              MaterialPageRoute(
                                builder: (_) => BookDetailScreen(bookId: book.bookId),
                              ),
                            );
                          },
                        );
                      },
                    ),

                  const SizedBox(height: 40),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildBadge(IconData icon, String label) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: AppColors.textSecondary),
          const SizedBox(width: 4),
          Text(
            label,
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
}

