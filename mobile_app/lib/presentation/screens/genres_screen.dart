import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants/app_colors.dart';
import '../../providers/genre_provider.dart';
import '../../providers/book_provider.dart';
import '../../providers/navigation_provider.dart';
import '../widgets/state_views.dart';

class GenresScreen extends StatefulWidget {
  const GenresScreen({super.key});

  @override
  State<GenresScreen> createState() => _GenresScreenState();
}

class _GenresScreenState extends State<GenresScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<GenreProvider>().fetchGenres();
    });
  }

  IconData _getGenreIcon(String iconName) {
    switch (iconName.toLowerCase()) {
      case 'menu_book':
        return Icons.menu_book_rounded;
      case 'business_center':
        return Icons.business_center_rounded;
      case 'psychology':
        return Icons.psychology_rounded;
      case 'auto_awesome':
        return Icons.auto_awesome_rounded;
      case 'trending_up':
        return Icons.trending_up_rounded;
      case 'memory':
        return Icons.memory_rounded;
      case 'code':
        return Icons.code_rounded;
      case 'smart_toy':
        return Icons.smart_toy_rounded;
      case 'science':
        return Icons.science_rounded;
      case 'history_edu':
        return Icons.history_edu_rounded;
      case 'school':
        return Icons.school_rounded;
      case 'auto_stories':
        return Icons.auto_stories_rounded;
      case 'lightbulb':
        return Icons.lightbulb_outline_rounded;
      case 'rocket_launch':
        return Icons.rocket_launch_rounded;
      case 'child_care':
        return Icons.child_care_rounded;
      case 'account_balance':
        return Icons.account_balance_rounded;
      default:
        return Icons.bookmark_rounded;
    }
  }

  void _onGenreTap(String genreName) {
    final bookProvider = context.read<BookProvider>();
    final navProvider = context.read<NavigationProvider>();
    bookProvider.setGenre(genreName);
    navProvider.setIndex(1); // Switch to Catalog tab
  }

  @override
  Widget build(BuildContext context) {
    final genreProvider = context.watch<GenreProvider>();

    if (genreProvider.isLoading && genreProvider.genres.isEmpty) {
      return const Scaffold(
        body: LoadingView(message: 'Đang tải danh mục thể loại...'),
      );
    }

    if (genreProvider.errorMessage != null && genreProvider.genres.isEmpty) {
      return Scaffold(
        body: ErrorView(
          message: genreProvider.errorMessage!,
          onRetry: () => genreProvider.fetchGenres(),
        ),
      );
    }

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Phân Loại Chủ Đề & Thể Loại'),
      ),
      body: LayoutBuilder(
        builder: (context, constraints) {
          final isDesktop = constraints.maxWidth >= 1000;
          final isTablet = constraints.maxWidth >= 650 && !isDesktop;
          final colCount = isDesktop ? 3 : (isTablet ? 2 : 1);

          return Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1200),
              child: GridView.builder(
                padding: const EdgeInsets.all(16.0),
                itemCount: genreProvider.genres.length,
                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: colCount,
                  childAspectRatio: isDesktop ? 2.6 : (isTablet ? 2.4 : 3.0),
                  crossAxisSpacing: 14,
                  mainAxisSpacing: 14,
                ),
                itemBuilder: (context, index) {
                  final genre = genreProvider.genres[index];
                  final icon = _getGenreIcon(genre.icon);

                  return Card(
                    child: InkWell(
                      borderRadius: BorderRadius.circular(12),
                      onTap: () => _onGenreTap(genre.name),
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: AppColors.navy.withOpacity(0.08),
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: Icon(icon, size: 28, color: AppColors.navy),
                            ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      Text(
                                        genre.name,
                                        style: const TextStyle(
                                          fontSize: 15,
                                          fontWeight: FontWeight.bold,
                                          color: AppColors.navyDark,
                                        ),
                                      ),
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                                        decoration: BoxDecoration(
                                          color: AppColors.gold.withOpacity(0.18),
                                          borderRadius: BorderRadius.circular(12),
                                        ),
                                        child: Text(
                                          '${genre.bookCount} sách',
                                          style: const TextStyle(
                                            fontSize: 10,
                                            fontWeight: FontWeight.bold,
                                            color: AppColors.goldDark,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                  if (genre.description.isNotEmpty) ...[
                                    const SizedBox(height: 4),
                                    Text(
                                      genre.description,
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(
                                        fontSize: 12,
                                        color: AppColors.textSecondary,
                                        height: 1.3,
                                      ),
                                    ),
                                  ],
                                ],
                              ),
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
      ),
    );
  }
}

