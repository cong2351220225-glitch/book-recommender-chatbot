import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants/app_colors.dart';
import '../../providers/book_provider.dart';
import '../../providers/genre_provider.dart';
import '../widgets/custom_button.dart';
import '../widgets/custom_text_field.dart';

class SearchFilterScreen extends StatefulWidget {
  const SearchFilterScreen({super.key});

  @override
  State<SearchFilterScreen> createState() => _SearchFilterScreenState();
}

class _SearchFilterScreenState extends State<SearchFilterScreen> {
  late TextEditingController _titleController;
  late TextEditingController _authorController;
  late TextEditingController _isbnController;
  late String _selectedGenre;
  late String _selectedLanguage;
  late RangeValues _yearRange;
  late double _minRating;
  late String _sortBy;
  late bool _readingOnly;
  late bool _featuredOnly;

  static const double _kMinYear = 1780;
  static const double _kMaxYear = 2026;

  @override
  void initState() {
    super.initState();
    final bookProvider = context.read<BookProvider>();
    _titleController = TextEditingController(text: bookProvider.searchQuery);
    _authorController = TextEditingController(text: bookProvider.authorFilter ?? '');
    _isbnController = TextEditingController(text: bookProvider.isbnFilter ?? '');
    _selectedGenre = bookProvider.selectedGenre;
    _selectedLanguage = bookProvider.selectedLanguage;

    final startYear = (bookProvider.minYear ?? _kMinYear).toDouble().clamp(_kMinYear, _kMaxYear);
    final endYear = (bookProvider.maxYear ?? _kMaxYear).toDouble().clamp(_kMinYear, _kMaxYear);
    _yearRange = RangeValues(startYear, endYear);

    _minRating = bookProvider.minRating ?? 0.0;
    _sortBy = bookProvider.sortBy;
    _readingOnly = bookProvider.readingOnly;
    _featuredOnly = bookProvider.featuredOnly;

    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<BookProvider>().fetchLanguages();
      context.read<GenreProvider>().fetchGenres();
    });
  }

  @override
  void dispose() {
    _titleController.dispose();
    _authorController.dispose();
    _isbnController.dispose();
    super.dispose();
  }

  void _applyFilters() {
    final bookProvider = context.read<BookProvider>();

    final isDefaultYearRange = _yearRange.start <= _kMinYear && _yearRange.end >= _kMaxYear;
    final minYear = isDefaultYearRange ? null : _yearRange.start.round();
    final maxYear = isDefaultYearRange ? null : _yearRange.end.round();
    final minRating = _minRating > 0 ? _minRating : null;

    bookProvider.applyAdvancedFilter(
      query: _titleController.text.trim(),
      author: _authorController.text.trim(),
      isbn: _isbnController.text.trim(),
      genre: _selectedGenre,
      language: _selectedLanguage,
      minYear: minYear,
      maxYear: maxYear,
      minRating: minRating,
      sortBy: _sortBy,
      readingOnly: _readingOnly,
      featuredOnly: _featuredOnly,
    );
    Navigator.of(context).pop();
  }

  void _reset() {
    setState(() {
      _titleController.clear();
      _authorController.clear();
      _isbnController.clear();
      _selectedGenre = 'Tất cả';
      _selectedLanguage = 'Tất cả';
      _yearRange = const RangeValues(_kMinYear, _kMaxYear);
      _minRating = 0.0;
      _sortBy = 'Phù hợp';
      _readingOnly = false;
      _featuredOnly = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final genreProvider = context.watch<GenreProvider>();
    final bookProvider = context.watch<BookProvider>();

    final allLanguages = ['Tất cả', ...bookProvider.languages];

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Bộ Lọc & Tìm Kiếm Nâng Cao'),
        actions: [
          TextButton.icon(
            icon: const Icon(Icons.refresh_rounded, size: 16, color: AppColors.gold),
            onPressed: _reset,
            label: const Text(
              'Đặt lại',
              style: TextStyle(color: AppColors.gold, fontWeight: FontWeight.bold),
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20.0),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 700),
            child: Card(
              elevation: 2,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              child: Padding(
                padding: const EdgeInsets.all(24.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Section 1: Keywords & Authors
                    const Row(
                      children: [
                        Icon(Icons.search_rounded, size: 20, color: AppColors.navy),
                        SizedBox(width: 8),
                        Text(
                          'Từ Khóa & Siêu Dữ Liệu',
                          style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: AppColors.navyDark),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),

                    CustomTextField(
                      controller: _titleController,
                      label: 'Tiêu đề hoặc từ khóa nội dung',
                      hint: 'Ví dụ: Lập trình, Clean Code, Trí tuệ nhân tạo...',
                      prefixIcon: Icons.menu_book_rounded,
                    ),
                    const SizedBox(height: 14),

                    Row(
                      children: [
                        Expanded(
                          child: CustomTextField(
                            controller: _authorController,
                            label: 'Tác giả',
                            hint: 'Ví dụ: Andy Hunt, Martin Fowler...',
                            prefixIcon: Icons.person_rounded,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: CustomTextField(
                            controller: _isbnController,
                            label: 'Mã ISBN',
                            hint: 'Ví dụ: 0132350882...',
                            prefixIcon: Icons.qr_code_rounded,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 20),

                    const Divider(color: AppColors.border),
                    const SizedBox(height: 14),

                    // Section 2: Genre & Language
                    const Row(
                      children: [
                        Icon(Icons.category_rounded, size: 20, color: AppColors.navy),
                        SizedBox(width: 8),
                        Text(
                          'Phân Loại & Ngôn Ngữ',
                          style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: AppColors.navyDark),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),

                    Row(
                      children: [
                        // Genre Dropdown
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text('Thể loại', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                              const SizedBox(height: 6),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 12),
                                decoration: BoxDecoration(
                                  color: Colors.white,
                                  borderRadius: BorderRadius.circular(8),
                                  border: Border.all(color: AppColors.border),
                                ),
                                child: DropdownButtonHideUnderline(
                                  child: DropdownButton<String>(
                                    value: _selectedGenre,
                                    isExpanded: true,
                                    items: [
                                      const DropdownMenuItem(value: 'Tất cả', child: Text('Tất cả thể loại')),
                                      ...genreProvider.genres.map((g) {
                                        return DropdownMenuItem(value: g.name, child: Text(g.name));
                                      }),
                                    ],
                                    onChanged: (val) {
                                      if (val != null) setState(() => _selectedGenre = val);
                                    },
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 12),

                        // Language Dropdown
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text('Ngôn ngữ', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                              const SizedBox(height: 6),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 12),
                                decoration: BoxDecoration(
                                  color: Colors.white,
                                  borderRadius: BorderRadius.circular(8),
                                  border: Border.all(color: AppColors.border),
                                ),
                                child: DropdownButtonHideUnderline(
                                  child: DropdownButton<String>(
                                    value: allLanguages.contains(_selectedLanguage) ? _selectedLanguage : 'Tất cả',
                                    isExpanded: true,
                                    items: allLanguages.map((lang) {
                                      return DropdownMenuItem(value: lang, child: Text(lang));
                                    }).toList(),
                                    onChanged: (val) {
                                      if (val != null) setState(() => _selectedLanguage = val);
                                    },
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 20),

                    const Divider(color: AppColors.border),
                    const SizedBox(height: 14),

                    // Section 3: Year Range & Rating
                    const Row(
                      children: [
                        Icon(Icons.calendar_month_rounded, size: 20, color: AppColors.navy),
                        SizedBox(width: 8),
                        Text(
                          'Năm Xuất Bản & Đánh Giá',
                          style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: AppColors.navyDark),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),

                    // Year Range Slider
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Khoảng năm xuất bản:', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                          decoration: BoxDecoration(
                            color: AppColors.navyLight,
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Text(
                            '${_yearRange.start.round()} — ${_yearRange.end.round()}',
                            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white),
                          ),
                        ),
                      ],
                    ),
                    RangeSlider(
                      values: _yearRange,
                      min: _kMinYear,
                      max: _kMaxYear,
                      divisions: (_kMaxYear - _kMinYear).round(),
                      activeColor: AppColors.gold,
                      inactiveColor: AppColors.border,
                      labels: RangeLabels(
                        '${_yearRange.start.round()}',
                        '${_yearRange.end.round()}',
                      ),
                      onChanged: (values) {
                        setState(() => _yearRange = values);
                      },
                    ),
                    const SizedBox(height: 14),

                    // Minimum Rating Choices
                    const Text('Đánh giá tối thiểu (Rating):', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      children: [0.0, 3.0, 3.5, 4.0, 4.5].map((r) {
                        final isSelected = (_minRating == r) || (r == 0.0 && _minRating <= 0.0);
                        return ChoiceChip(
                          label: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              if (r > 0) const Icon(Icons.star_rounded, size: 14, color: AppColors.gold),
                              Text(r == 0.0 ? 'Tất cả' : ' $r+ ⭐'),
                            ],
                          ),
                          selected: isSelected,
                          selectedColor: AppColors.navy,
                          labelStyle: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                            color: isSelected ? Colors.white : AppColors.textPrimary,
                          ),
                          onSelected: (_) {
                            setState(() => _minRating = r);
                          },
                        );
                      }).toList(),
                    ),
                    const SizedBox(height: 20),

                    const Divider(color: AppColors.border),
                    const SizedBox(height: 14),

                    // Section 4: Sort Order & Badges
                    const Row(
                      children: [
                        Icon(Icons.sort_rounded, size: 20, color: AppColors.navy),
                        SizedBox(width: 8),
                        Text(
                          'Sắp Xếp & Tùy Chọn Khác',
                          style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: AppColors.navyDark),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),

                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Thứ tự sắp xếp:', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                        const SizedBox(height: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: AppColors.border),
                          ),
                          child: DropdownButtonHideUnderline(
                            child: DropdownButton<String>(
                              value: _sortBy,
                              isExpanded: true,
                              items: const [
                                DropdownMenuItem(value: 'Phù hợp', child: Text('Phù hợp nhất')),
                                DropdownMenuItem(value: 'Tên A-Z', child: Text('Tên sách A–Z')),
                                DropdownMenuItem(value: 'Tên Z-A', child: Text('Tên sách Z–A')),
                                DropdownMenuItem(value: 'Năm mới nhất', child: Text('Năm xuất bản mới nhất')),
                                DropdownMenuItem(value: 'Năm cũ nhất', child: Text('Năm xuất bản cũ nhất')),
                                DropdownMenuItem(value: 'Đánh giá cao', child: Text('Đánh giá cao nhất')),
                                DropdownMenuItem(value: 'Đánh giá thấp', child: Text('Đánh giá thấp nhất')),
                              ],
                              onChanged: (val) {
                                if (val != null) setState(() => _sortBy = val);
                              },
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),

                    CheckboxListTile(
                      value: _readingOnly,
                      title: const Text('Chỉ hiện sách có sẵn bản đọc toàn văn trong thư viện', style: TextStyle(fontSize: 13)),
                      activeColor: AppColors.navy,
                      contentPadding: EdgeInsets.zero,
                      onChanged: (val) => setState(() => _readingOnly = val ?? false),
                    ),
                    CheckboxListTile(
                      value: _featuredOnly,
                      title: const Text('Chỉ hiện sách nổi bật được ban biên tập tuyển chọn ⭐', style: TextStyle(fontSize: 13)),
                      activeColor: AppColors.navy,
                      contentPadding: EdgeInsets.zero,
                      onChanged: (val) => setState(() => _featuredOnly = val ?? false),
                    ),
                    const SizedBox(height: 24),

                    // Apply Button
                    CustomButton(
                      text: 'Áp dụng bộ lọc',
                      icon: Icons.check_rounded,
                      onPressed: _applyFilters,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
