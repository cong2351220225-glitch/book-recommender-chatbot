import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants/app_colors.dart';
import '../../core/utils/responsive_layout.dart';
import '../../models/author_model.dart';
import '../../providers/author_provider.dart';
import '../../providers/book_provider.dart';
import '../../providers/genre_provider.dart';
import '../widgets/book_card.dart';
import '../widgets/state_views.dart';
import 'author_detail_screen.dart';
import 'book_detail_screen.dart';
import 'search_filter_screen.dart';

class BooksCatalogScreen extends StatefulWidget {
  const BooksCatalogScreen({super.key});

  @override
  State<BooksCatalogScreen> createState() => _BooksCatalogScreenState();
}

class _BooksCatalogScreenState extends State<BooksCatalogScreen> {
  final ScrollController _scrollController = ScrollController();
  final TextEditingController _searchController = TextEditingController();

  int _selectedTabIndex = 0; // 0: Sách, 1: Tác giả

  @override
  void initState() {
    super.initState();
    final bookProvider = context.read<BookProvider>();
    _searchController.text = bookProvider.searchQuery;

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (bookProvider.books.isEmpty) {
        bookProvider.fetchBooks(refresh: true);
      }
      bookProvider.fetchLanguages();
      context.read<GenreProvider>().fetchGenres();
      context.read<AuthorProvider>().fetchAuthors(query: bookProvider.searchQuery);
    });

    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_selectedTabIndex == 0) {
      if (_scrollController.position.pixels >=
          _scrollController.position.maxScrollExtent - 300) {
        context.read<BookProvider>().loadMore();
      }
    }
  }

  void _onSearchSubmitted(String query) {
    context.read<BookProvider>().setSearchQuery(query);
    context.read<AuthorProvider>().fetchAuthors(query: query);
  }

  @override
  Widget build(BuildContext context) {
    final bookProvider = context.watch<BookProvider>();
    final authorProvider = context.watch<AuthorProvider>();
    final genreProvider = context.watch<GenreProvider>();
    final isDesktop = ResponsiveLayout.isDesktop(context);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Kho Sách & Tra Cứu Toàn Cục'),
        actions: [
          IconButton(
            icon: const Icon(Icons.tune_rounded),
            tooltip: 'Bộ lọc nâng cao',
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const SearchFilterScreen()),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            tooltip: 'Làm mới',
            onPressed: () {
              bookProvider.fetchBooks(refresh: true);
              authorProvider.fetchAuthors(query: bookProvider.searchQuery);
            },
          ),
        ],
      ),
      body: Column(
        children: [
          // Filter Bar & Search Header
          Container(
            color: Colors.white,
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 10),
            child: Column(
              children: [
                // Search Input with Sort Dropdown
                Row(
                  children: [
                    Expanded(
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
                          onSubmitted: _onSearchSubmitted,
                          decoration: InputDecoration(
                            hintText: 'Tìm kiếm theo tên sách, tác giả, ISBN, từ khóa...',
                            hintStyle: const TextStyle(fontSize: 13, color: AppColors.textMuted),
                            prefixIcon: const Icon(Icons.search_rounded, size: 20, color: AppColors.textSecondary),
                            suffixIcon: _searchController.text.isNotEmpty
                                ? IconButton(
                                    icon: const Icon(Icons.clear_rounded, size: 18),
                                    onPressed: () {
                                      _searchController.clear();
                                      _onSearchSubmitted('');
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
                    const SizedBox(width: 8),

                    // Advanced Filter Button
                    OutlinedButton.icon(
                      icon: const Icon(Icons.tune_rounded, size: 16, color: AppColors.navy),
                      label: const Text('Bộ lọc', style: TextStyle(fontSize: 12, color: AppColors.navy, fontWeight: FontWeight.bold)),
                      style: OutlinedButton.styleFrom(
                        side: const BorderSide(color: AppColors.border),
                        backgroundColor: bookProvider.hasActiveFilters ? AppColors.goldLight.withValues(alpha: 0.2) : AppColors.surfaceVariant,
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                      onPressed: () {
                        Navigator.of(context).push(
                          MaterialPageRoute(builder: (_) => const SearchFilterScreen()),
                        );
                      },
                    ),
                    const SizedBox(width: 8),

                    // Sort Dropdown (only relevant in Sách tab)
                    if (_selectedTabIndex == 0)
                      Container(
                        height: 44,
                        padding: const EdgeInsets.symmetric(horizontal: 10),
                        decoration: BoxDecoration(
                          color: AppColors.surfaceVariant,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: AppColors.border),
                        ),
                        child: DropdownButtonHideUnderline(
                          child: DropdownButton<String>(
                            value: bookProvider.sortBy,
                            icon: const Icon(Icons.sort_rounded, size: 18, color: AppColors.navy),
                            style: const TextStyle(fontSize: 12, color: AppColors.textPrimary, fontWeight: FontWeight.w600),
                            items: const [
                              DropdownMenuItem(value: 'Phù hợp', child: Text('Phù hợp')),
                              DropdownMenuItem(value: 'Tên A-Z', child: Text('Tên A-Z')),
                              DropdownMenuItem(value: 'Tên Z-A', child: Text('Tên Z-A')),
                              DropdownMenuItem(value: 'Năm mới nhất', child: Text('Năm mới nhất')),
                              DropdownMenuItem(value: 'Năm cũ nhất', child: Text('Năm cũ nhất')),
                              DropdownMenuItem(value: 'Đánh giá cao', child: Text('Đánh giá cao')),
                              DropdownMenuItem(value: 'Đánh giá thấp', child: Text('Đánh giá thấp')),
                            ],
                            onChanged: (val) {
                              if (val != null) bookProvider.setSortBy(val);
                            },
                          ),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 10),

                // Global Search Group Switcher: Sách vs Tác giả
                Row(
                  children: [
                    ChoiceChip(
                      label: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.menu_book_rounded, size: 15),
                          const SizedBox(width: 6),
                          Text('Sách (${bookProvider.totalBooks})'),
                        ],
                      ),
                      selected: _selectedTabIndex == 0,
                      selectedColor: AppColors.navy,
                      backgroundColor: AppColors.surfaceVariant,
                      labelStyle: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: _selectedTabIndex == 0 ? Colors.white : AppColors.textPrimary,
                      ),
                      onSelected: (_) => setState(() => _selectedTabIndex = 0),
                    ),
                    const SizedBox(width: 8),
                    ChoiceChip(
                      label: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.people_rounded, size: 15),
                          const SizedBox(width: 6),
                          Text('Tác giả (${authorProvider.authors.length})'),
                        ],
                      ),
                      selected: _selectedTabIndex == 1,
                      selectedColor: AppColors.navy,
                      backgroundColor: AppColors.surfaceVariant,
                      labelStyle: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: _selectedTabIndex == 1 ? Colors.white : AppColors.textPrimary,
                      ),
                      onSelected: (_) => setState(() => _selectedTabIndex = 1),
                    ),
                    const Spacer(),
                    if (bookProvider.hasActiveFilters)
                      TextButton.icon(
                        icon: const Icon(Icons.close_rounded, size: 14, color: AppColors.error),
                        label: const Text('Xóa bộ lọc', style: TextStyle(fontSize: 11, color: AppColors.error, fontWeight: FontWeight.bold)),
                        onPressed: () {
                          _searchController.clear();
                          bookProvider.resetFilters();
                          authorProvider.fetchAuthors(query: '');
                        },
                      ),
                  ],
                ),

                // Genre Pills Horizontal Scroll (only when in Sách tab)
                if (_selectedTabIndex == 0) ...[
                  const SizedBox(height: 8),
                  SizedBox(
                    height: 32,
                    child: ListView(
                      scrollDirection: Axis.horizontal,
                      children: [
                        _buildGenreChip('Tất cả', bookProvider.selectedGenre == 'Tất cả', () {
                          bookProvider.setGenre('Tất cả');
                        }),
                        ...genreProvider.genres.map((g) {
                          final isSelected = bookProvider.selectedGenre == g.name;
                          return _buildGenreChip(g.name, isSelected, () {
                            bookProvider.setGenre(g.name);
                          });
                        }),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),

          // Active Filter Chips & Results Count Bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            decoration: const BoxDecoration(
              color: AppColors.surfaceVariant,
              border: Border(bottom: BorderSide(color: AppColors.border)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    _selectedTabIndex == 0
                        ? 'Tìm thấy ${bookProvider.books.length} / ${bookProvider.totalBooks} cuốn sách phù hợp trong kho'
                        : 'Tìm thấy ${authorProvider.authors.length} tác giả phù hợp',
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ),
                // Indicator for language / year / rating active filters
                if (_selectedTabIndex == 0 && (bookProvider.selectedLanguage != 'Tất cả' || bookProvider.minYear != null || bookProvider.minRating != null))
                  Text(
                    'Bộ lọc mở rộng: ${bookProvider.selectedLanguage != 'Tất cả' ? '${bookProvider.selectedLanguage} • ' : ''}${bookProvider.minYear != null ? '${bookProvider.minYear}-${bookProvider.maxYear} • ' : ''}${bookProvider.minRating != null ? '>=${bookProvider.minRating}⭐' : ''}',
                    style: const TextStyle(fontSize: 11, color: AppColors.navy, fontWeight: FontWeight.w600),
                  ),
              ],
            ),
          ),

          // Main View: Books Grid or Authors List
          Expanded(
            child: _selectedTabIndex == 0
                ? _buildBooksBody(bookProvider, isDesktop)
                : _buildAuthorsBody(authorProvider, isDesktop),
          ),
        ],
      ),
    );
  }

  Widget _buildGenreChip(String label, bool isSelected, VoidCallback onTap) {
    return Padding(
      padding: const EdgeInsets.only(right: 6.0),
      child: FilterChip(
        label: Text(label),
        selected: isSelected,
        onSelected: (_) => onTap(),
        selectedColor: AppColors.navy,
        backgroundColor: Colors.white,
        labelStyle: TextStyle(
          fontSize: 11,
          fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
          color: isSelected ? Colors.white : AppColors.textPrimary,
        ),
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 0),
        materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
        visualDensity: VisualDensity.compact,
      ),
    );
  }

  Widget _buildBooksBody(BookProvider bookProvider, bool isDesktop) {
    if (bookProvider.isLoading && bookProvider.books.isEmpty) {
      return const LoadingView(message: 'Đang tải danh mục sách...');
    }

    if (bookProvider.errorMessage != null && bookProvider.books.isEmpty) {
      return ErrorView(
        message: bookProvider.errorMessage!,
        onRetry: () => bookProvider.fetchBooks(refresh: true),
      );
    }

    if (bookProvider.books.isEmpty) {
      return EmptyView(
        title: 'Không tìm thấy sách phù hợp',
        message: 'Thử kiểm tra lại từ khóa hoặc nới lỏng các tiêu chí lọc.',
        buttonText: 'Xóa toàn bộ bộ lọc',
        onButtonPressed: () {
          _searchController.clear();
          bookProvider.resetFilters();
        },
      );
    }

    final colCount = ResponsiveLayout.getGridColumnCount(context);

    return RefreshIndicator(
      onRefresh: () async {
        await bookProvider.fetchBooks(refresh: true);
      },
      color: AppColors.gold,
      backgroundColor: AppColors.navyDark,
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1300),
          child: CustomScrollView(
            controller: _scrollController,
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              SliverPadding(
                padding: const EdgeInsets.all(14.0),
                sliver: SliverGrid(
                  gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: colCount,
                    childAspectRatio: 0.62,
                    crossAxisSpacing: 14,
                    mainAxisSpacing: 14,
                  ),
                  delegate: SliverChildBuilderDelegate(
                    (context, index) {
                      final book = bookProvider.books[index];
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
                    childCount: bookProvider.books.length,
                  ),
                ),
              ),

              // Bottom Loading More Indicator
              if (bookProvider.isLoadingMore)
                const SliverToBoxAdapter(
                  child: Padding(
                    padding: EdgeInsets.symmetric(vertical: 20),
                    child: Center(
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                  ),
                ),

              // Reached End of Catalog
              if (!bookProvider.hasMore && bookProvider.books.isNotEmpty)
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 24),
                    child: Center(
                      child: Text(
                        'Đã hiển thị toàn bộ ${bookProvider.totalBooks} cuốn sách trong kho.',
                        style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildAuthorsBody(AuthorProvider authorProvider, bool isDesktop) {
    if (authorProvider.isLoading && authorProvider.authors.isEmpty) {
      return const LoadingView(message: 'Đang tìm kiếm tác giả...');
    }

    if (authorProvider.errorMessage != null && authorProvider.authors.isEmpty) {
      return ErrorView(
        message: authorProvider.errorMessage!,
        onRetry: () => authorProvider.fetchAuthors(query: _searchController.text.trim()),
      );
    }

    if (authorProvider.authors.isEmpty) {
      return EmptyView(
        title: 'Không tìm thấy tác giả phù hợp',
        message: 'Thử kiểm tra lại tên tác giả hoặc tìm kiếm không dấu.',
        buttonText: 'Xem tất cả tác giả',
        onButtonPressed: () {
          _searchController.clear();
          authorProvider.fetchAuthors(query: '');
        },
      );
    }

    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: authorProvider.authors.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (context, index) {
        final author = authorProvider.authors[index];
        return _buildAuthorCard(author);
      },
    );
  }

  Widget _buildAuthorCard(AuthorModel author) {
    final initials = author.name.trim().isNotEmpty
        ? author.name.trim().split(' ').map((p) => p.isNotEmpty ? p[0] : '').take(2).join('').toUpperCase()
        : 'TG';

    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: const BorderSide(color: AppColors.border),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
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
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Monogram Avatar Navy & Gold
              CircleAvatar(
                radius: 26,
                backgroundColor: AppColors.navyDark,
                child: Text(
                  initials,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: AppColors.gold,
                  ),
                ),
              ),
              const SizedBox(width: 14),

              // Author Details
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Expanded(
                          child: Text(
                            author.name,
                            style: const TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.bold,
                              color: AppColors.navyDark,
                            ),
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: AppColors.navyLight,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Text(
                            '${author.workCount} tác phẩm',
                            style: const TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                              color: Colors.white,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      author.nationality.isNotEmpty
                          ? '${author.nationality}${author.birthYear != null ? ' • Sinh năm ${author.birthYear}' : ''}'
                          : (author.birthYear != null ? 'Sinh năm ${author.birthYear}' : 'Tác giả thư viện'),
                      style: const TextStyle(fontSize: 11, color: AppColors.textSecondary),
                    ),
                    if (author.bio.isNotEmpty) ...[
                      const SizedBox(height: 6),
                      Text(
                        author.bio,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 12, color: AppColors.textMuted, height: 1.3),
                      ),
                    ],
                  ],
                ),
              ),
              const Icon(Icons.chevron_right_rounded, color: AppColors.textMuted),
            ],
          ),
        ),
      ),
    );
  }
}
