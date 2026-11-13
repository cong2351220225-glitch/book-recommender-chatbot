import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants/app_colors.dart';
import '../../providers/author_provider.dart';
import '../widgets/state_views.dart';
import 'author_detail_screen.dart';

class AuthorsScreen extends StatefulWidget {
  const AuthorsScreen({super.key});

  @override
  State<AuthorsScreen> createState() => _AuthorsScreenState();
}

class _AuthorsScreenState extends State<AuthorsScreen> {
  final TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final authorProvider = context.read<AuthorProvider>();
      if (authorProvider.authors.isEmpty) {
        authorProvider.fetchAuthors();
      }
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final authorProvider = context.watch<AuthorProvider>();

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Tác Giả & Dịch Giả'),
      ),
      body: Column(
        children: [
          // Search Bar Header
          Container(
            color: Colors.white,
            padding: const EdgeInsets.all(16.0),
            child: Container(
              height: 44,
              decoration: BoxDecoration(
                color: AppColors.surfaceVariant,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppColors.border),
              ),
              child: TextField(
                controller: _searchController,
                textInputAction: TextInputAction.search,
                onSubmitted: (query) => authorProvider.fetchAuthors(query: query),
                decoration: InputDecoration(
                  hintText: 'Tìm kiếm tên tác giả...',
                  hintStyle: const TextStyle(fontSize: 13, color: AppColors.textMuted),
                  prefixIcon: const Icon(Icons.search_rounded, size: 20, color: AppColors.textSecondary),
                  suffixIcon: _searchController.text.isNotEmpty
                      ? IconButton(
                          icon: const Icon(Icons.clear_rounded, size: 18),
                          onPressed: () {
                            _searchController.clear();
                            authorProvider.fetchAuthors(query: '');
                          },
                        )
                      : null,
                  border: InputBorder.none,
                  enabledBorder: InputBorder.none,
                  focusedBorder: InputBorder.none,
                  contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                ),
              ),
            ),
          ),

          // Total Count Bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            decoration: const BoxDecoration(
              color: AppColors.surfaceVariant,
              border: Border(bottom: BorderSide(color: AppColors.border)),
            ),
            child: Row(
              children: [
                Text(
                  'Tổng số: ${authorProvider.authors.length} tác giả',
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),

          // Main Authors Grid
          Expanded(
            child: _buildBody(authorProvider),
          ),
        ],
      ),
    );
  }

  Widget _buildBody(AuthorProvider authorProvider) {
    if (authorProvider.isLoading && authorProvider.authors.isEmpty) {
      return const LoadingView(message: 'Đang tải danh sách tác giả...');
    }

    if (authorProvider.errorMessage != null && authorProvider.authors.isEmpty) {
      return ErrorView(
        message: authorProvider.errorMessage!,
        onRetry: () => authorProvider.fetchAuthors(),
      );
    }

    if (authorProvider.authors.isEmpty) {
      return EmptyView(
        title: 'Không tìm thấy tác giả',
        message: 'Thử tìm kiếm với tên khác.',
        icon: Icons.person_off_rounded,
        buttonText: 'Xem tất cả tác giả',
        onButtonPressed: () {
          _searchController.clear();
          authorProvider.fetchAuthors(query: '');
        },
      );
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        final isDesktop = constraints.maxWidth >= 1000;
        final isTablet = constraints.maxWidth >= 600 && !isDesktop;
        final colCount = isDesktop ? 3 : (isTablet ? 2 : 1);

        return Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1200),
            child: GridView.builder(
              padding: const EdgeInsets.all(14.0),
              itemCount: authorProvider.authors.length,
              gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: colCount,
                childAspectRatio: isDesktop ? 2.8 : (isTablet ? 2.5 : 3.2),
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
              ),
              itemBuilder: (context, index) {
                final author = authorProvider.authors[index];
                return Card(
                  child: InkWell(
                    borderRadius: BorderRadius.circular(12),
                    onTap: () {
                      Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => AuthorDetailScreen(authorId: author.authorId),
                        ),
                      );
                    },
                    child: Padding(
                      padding: const EdgeInsets.all(14.0),
                      child: Row(
                        children: [
                          CircleAvatar(
                            radius: 26,
                            backgroundColor: AppColors.navy.withOpacity(0.1),
                            child: Text(
                              author.name.isNotEmpty ? author.name[0].toUpperCase() : '?',
                              style: const TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                                color: AppColors.navyDark,
                              ),
                            ),
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Text(
                                  author.name,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                    fontSize: 14,
                                    fontWeight: FontWeight.bold,
                                    color: AppColors.navyDark,
                                  ),
                                ),
                                const SizedBox(height: 3),
                                Text(
                                  author.nationality.isNotEmpty
                                      ? author.nationality
                                      : (author.lifespan.isNotEmpty ? author.lifespan : 'Chưa rõ quốc tịch'),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                    fontSize: 11,
                                    color: AppColors.textSecondary,
                                  ),
                                ),
                                const SizedBox(height: 6),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: AppColors.gold.withOpacity(0.15),
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                  child: Text(
                                    '${author.workCount} tác phẩm trong thư viện',
                                    style: const TextStyle(
                                      fontSize: 10,
                                      fontWeight: FontWeight.bold,
                                      color: AppColors.goldDark,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const Icon(
                            Icons.arrow_forward_ios_rounded,
                            size: 14,
                            color: AppColors.textMuted,
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              },
            ),
          ),
        );
      },
    );
  }
}

