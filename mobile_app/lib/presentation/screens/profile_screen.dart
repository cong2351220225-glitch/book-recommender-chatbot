import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants/app_colors.dart';
import '../../core/constants/api_constants.dart';
import '../../core/storage/auth_storage.dart';
import '../../providers/auth_provider.dart';
import '../../providers/bookshelf_provider.dart';
import '../../providers/navigation_provider.dart';
import '../../providers/recommendation_provider.dart';
import '../../providers/genre_provider.dart';
import '../widgets/custom_button.dart';
import 'login_screen.dart';
import 'ai_crawler_screen.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final TextEditingController _urlController = TextEditingController();
  final TextEditingController _goalController = TextEditingController();
  final Set<String> _selectedGenres = {};
  bool _isEditingUrl = false;
  bool _isPrefsLoaded = false;
  bool _isSavingPrefs = false;

  @override
  void initState() {
    super.initState();
    _urlController.text = ApiConstants.baseUrl;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final auth = context.read<AuthProvider>();
      if (auth.isAuthenticated) {
        context.read<RecommendationProvider>().loadPreferences(
              currentUsername: auth.currentUser?.username,
            );
      }
      context.read<GenreProvider>().fetchGenres();
    });
  }

  @override
  void dispose() {
    _urlController.dispose();
    _goalController.dispose();
    super.dispose();
  }

  Future<void> _saveCustomUrl() async {
    final newUrl = _urlController.text.trim();
    if (newUrl.isNotEmpty) {
      ApiConstants.setCustomBaseUrl(newUrl);
      await AuthStorage().saveCustomBaseUrl(newUrl);
      setState(() => _isEditingUrl = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Đã cập nhật máy chủ: $newUrl'),
            backgroundColor: AppColors.success,
          ),
        );
      }
    }
  }

  Future<void> _savePreferences() async {
    setState(() => _isSavingPrefs = true);
    final recProvider = context.read<RecommendationProvider>();

    final success = await recProvider.updatePreferences(
      preferredGenres: _selectedGenres.toList(),
      preferredAuthors: recProvider.preferences?.preferredAuthors ?? [],
      readingGoal: _goalController.text.trim(),
    );

    setState(() => _isSavingPrefs = false);

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            success
                ? 'Đã cập nhật sở thích & mục tiêu đọc sách thành công!'
                : (recProvider.errorMessage ?? 'Không thể lưu sở thích'),
          ),
          backgroundColor: success ? AppColors.success : AppColors.error,
        ),
      );
    }
  }

  void _showLogoutDialog() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Xác nhận đăng xuất'),
        content: const Text('Bạn có chắc chắn muốn đăng xuất khỏi ứng dụng?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Hủy'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.error),
            onPressed: () async {
              Navigator.of(ctx).pop();
              await context.read<AuthProvider>().logout();
              if (mounted) {
                Navigator.of(context).pushAndRemoveUntil(
                  MaterialPageRoute(builder: (_) => const LoginScreen()),
                  (route) => false,
                );
              }
            },
            child: const Text('Đăng xuất', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final authProvider = context.watch<AuthProvider>();
    final user = authProvider.currentUser;
    final recProvider = context.watch<RecommendationProvider>();
    final genreProvider = context.watch<GenreProvider>();

    if (!_isPrefsLoaded && recProvider.preferences != null) {
      _selectedGenres.clear();
      _selectedGenres.addAll(recProvider.preferences!.preferredGenres);
      if (_goalController.text.isEmpty && recProvider.preferences!.readingGoal.isNotEmpty) {
        _goalController.text = recProvider.preferences!.readingGoal;
      }
      _isPrefsLoaded = true;
    }

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Hồ Sơ & Cài Đặt'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20.0),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 680),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // User Card
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(24.0),
                    child: Row(
                      children: [
                        CircleAvatar(
                          radius: 36,
                          backgroundColor: AppColors.navyDark,
                          child: Text(
                            (user?.username.isNotEmpty ?? false)
                                ? user!.username[0].toUpperCase()
                                : '?',
                            style: const TextStyle(
                              fontSize: 28,
                              fontWeight: FontWeight.bold,
                              color: AppColors.gold,
                            ),
                          ),
                        ),
                        const SizedBox(width: 20),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                user?.username ?? 'Chưa đăng nhập (Khách)',
                                style: const TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold,
                                  color: AppColors.navyDark,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                decoration: BoxDecoration(
                                  color: (user?.isAdmin ?? false)
                                      ? AppColors.gold.withOpacity(0.2)
                                      : AppColors.surfaceVariant,
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                child: Text(
                                  (user?.isAdmin ?? false) ? 'QUẢN TRỊ VIÊN (ADMIN)' : 'ĐỘC GIẢ (USER)',
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                    color: (user?.isAdmin ?? false)
                                        ? AppColors.goldDark
                                        : AppColors.textSecondary,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

                // Admin Area Card: Hiển thị duy nhất khi là Quản trị viên
                if (user?.isAdmin ?? false) ...[
                  const SizedBox(height: 16),
                  Card(
                    color: const Color(0xFF1B263B),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                      side: const BorderSide(color: Color(0xFFD4AF37), width: 1.2),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: const [
                              Icon(Icons.admin_panel_settings_rounded, color: Color(0xFFD4AF37), size: 22),
                              SizedBox(width: 8),
                              Text(
                                'Khu vực Quản trị viên',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 15,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          const Text(
                            'Thu thập và nhập sách số tự động từ 6 nguồn chính thống, tự động kiểm tra trùng lặp và đồng bộ vector AI ChromaDB.',
                            style: TextStyle(color: Colors.white70, fontSize: 12, height: 1.3),
                          ),
                          const SizedBox(height: 12),
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton.icon(
                              style: ElevatedButton.styleFrom(
                                backgroundColor: const Color(0xFFD4AF37),
                                foregroundColor: const Color(0xFF0D1B2A),
                                padding: const EdgeInsets.symmetric(vertical: 12),
                              ),
                              icon: const Icon(Icons.travel_explore_rounded),
                              label: const Text(
                                'Mở AI Book Crawler',
                                style: TextStyle(fontWeight: FontWeight.bold),
                              ),
                              onPressed: () {
                                Navigator.of(context).push(
                                  MaterialPageRoute(
                                    builder: (_) => const AiCrawlerScreen(),
                                  ),
                                );
                              },
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],

                const SizedBox(height: 20),

                // My Bookshelf Quick Summary Card
                Builder(
                  builder: (context) {
                    final shelf = context.watch<BookshelfProvider>();
                    return Card(
                      child: Padding(
                        padding: const EdgeInsets.all(20.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                const Row(
                                  children: [
                                    Icon(Icons.collections_bookmark_rounded, size: 20, color: AppColors.gold),
                                    SizedBox(width: 8),
                                    Text(
                                      'Tủ Sách Của Tôi',
                                      style: TextStyle(
                                        fontSize: 15,
                                        fontWeight: FontWeight.bold,
                                        color: AppColors.navyDark,
                                      ),
                                    ),
                                  ],
                                ),
                                TextButton.icon(
                                  icon: const Icon(Icons.arrow_forward_rounded, size: 14),
                                  label: const Text('Xem tất cả'),
                                  onPressed: () {
                                    context.read<NavigationProvider>().setIndex(2); // Switch to Bookshelf tab
                                  },
                                ),
                              ],
                            ),
                            const SizedBox(height: 12),
                            Row(
                              children: [
                                Expanded(
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(vertical: 10),
                                    decoration: BoxDecoration(
                                      color: AppColors.surfaceVariant,
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                    child: Column(
                                      children: [
                                        Text(
                                          '${shelf.favoriteCount}',
                                          style: const TextStyle(
                                            fontSize: 16,
                                            fontWeight: FontWeight.bold,
                                            color: AppColors.error,
                                          ),
                                        ),
                                        const SizedBox(height: 2),
                                        const Text('Yêu thích', style: TextStyle(fontSize: 11, color: AppColors.textSecondary)),
                                      ],
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(vertical: 10),
                                    decoration: BoxDecoration(
                                      color: AppColors.surfaceVariant,
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                    child: Column(
                                      children: [
                                        Text(
                                          '${shelf.readingCount}',
                                          style: const TextStyle(
                                            fontSize: 16,
                                            fontWeight: FontWeight.bold,
                                            color: AppColors.goldDark,
                                          ),
                                        ),
                                        const SizedBox(height: 2),
                                        const Text('Đang đọc', style: TextStyle(fontSize: 11, color: AppColors.textSecondary)),
                                      ],
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(vertical: 10),
                                    decoration: BoxDecoration(
                                      color: AppColors.surfaceVariant,
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                    child: Column(
                                      children: [
                                        Text(
                                          '${shelf.completedCount}',
                                          style: const TextStyle(
                                            fontSize: 16,
                                            fontWeight: FontWeight.bold,
                                            color: AppColors.success,
                                          ),
                                        ),
                                        const SizedBox(height: 2),
                                        const Text('Đã đọc', style: TextStyle(fontSize: 11, color: AppColors.textSecondary)),
                                      ],
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),

                // AI Recommendation Preferences Card (chỉ cho user đã đăng nhập)
                if (authProvider.isAuthenticated) ...[
                  const SizedBox(height: 20),
                  _buildPreferencesCard(context, recProvider, genreProvider),
                ],

                const SizedBox(height: 20),

                // Server Configuration Card
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(20.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Row(
                          children: [
                            Icon(Icons.dns_rounded, size: 20, color: AppColors.navy),
                            SizedBox(width: 8),
                            Text(
                              'Kết nối FastAPI Backend',
                              style: TextStyle(
                                fontSize: 15,
                                fontWeight: FontWeight.bold,
                                color: AppColors.navyDark,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        const Text(
                          'Đường dẫn máy chủ backend API phục vụ dữ liệu và mô hình AI:',
                          style: TextStyle(fontSize: 12, color: AppColors.textSecondary),
                        ),
                        const SizedBox(height: 10),
                        if (_isEditingUrl) ...[
                          TextField(
                            controller: _urlController,
                            decoration: const InputDecoration(
                              hintText: 'http://127.0.0.1:8000',
                              labelText: 'Địa chỉ máy chủ (Base URL)',
                            ),
                          ),
                          const SizedBox(height: 12),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.end,
                            children: [
                              TextButton(
                                onPressed: () => setState(() => _isEditingUrl = false),
                                child: const Text('Hủy'),
                              ),
                              const SizedBox(width: 8),
                              ElevatedButton(
                                onPressed: _saveCustomUrl,
                                child: const Text('Lưu thay đổi'),
                              ),
                            ],
                          ),
                        ] else ...[
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                            decoration: BoxDecoration(
                              color: AppColors.surfaceVariant,
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    ApiConstants.baseUrl,
                                    style: const TextStyle(
                                      fontFamily: 'monospace',
                                      fontSize: 13,
                                      fontWeight: FontWeight.w600,
                                      color: AppColors.navyDark,
                                    ),
                                  ),
                                ),
                                IconButton(
                                  icon: const Icon(Icons.edit_rounded, size: 18, color: AppColors.navy),
                                  tooltip: 'Chỉnh sửa URL',
                                  onPressed: () => setState(() => _isEditingUrl = true),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 20),

                // System Information Card
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(20.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Row(
                          children: [
                            Icon(Icons.info_outline_rounded, size: 20, color: AppColors.navy),
                            SizedBox(width: 8),
                            Text(
                              'Thông tin ứng dụng',
                              style: TextStyle(
                                fontSize: 15,
                                fontWeight: FontWeight.bold,
                                color: AppColors.navyDark,
                              ),
                            ),
                          ],
                        ),
                        const Divider(height: 20),
                        _buildInfoRow('Phiên bản', '1.0.0 (Phase 2 Multi-Platform)'),
                        _buildInfoRow('Nền tảng hỗ trợ', 'Windows Desktop, Android, iOS'),
                        _buildInfoRow('AI RAG Engine', 'Google Gemini-3.6-flash & ChromaDB'),
                        _buildInfoRow('Thiết kế chủ đạo', 'Premium Navy & Gold Library System'),
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 28),

                // Login / Logout action
                if (authProvider.isAuthenticated)
                  CustomButton(
                    text: 'Đăng xuất khỏi tài khoản',
                    icon: Icons.logout_rounded,
                    type: ButtonType.outline,
                    onPressed: _showLogoutDialog,
                  )
                else
                  CustomButton(
                    text: 'Đăng nhập tài khoản',
                    icon: Icons.login_rounded,
                    onPressed: () {
                      Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => const LoginScreen()),
                      );
                    },
                  ),
                const SizedBox(height: 40),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontSize: 13, color: AppColors.textSecondary)),
          Text(value, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.navyDark)),
        ],
      ),
    );
  }

  Widget _buildPreferencesCard(
    BuildContext context,
    RecommendationProvider recProvider,
    GenreProvider genreProvider,
  ) {
    return Card(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: AppColors.gold.withOpacity(0.4), width: 1.2),
      ),
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: const [
                Icon(Icons.auto_awesome_rounded, size: 20, color: AppColors.goldDark),
                SizedBox(width: 8),
                Text(
                  'Sở Thích Đọc Sách & Mục Tiêu',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    color: AppColors.navyDark,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            const Text(
              'Chọn thể loại bạn quan tâm và đặt mục tiêu đọc để AI cá nhân hóa đề xuất sách chính xác hơn cho bạn.',
              style: TextStyle(fontSize: 12, color: AppColors.textSecondary, height: 1.3),
            ),
            const Divider(height: 24),

            // Thể loại yêu thích
            const Text(
              'Thể loại yêu thích:',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.bold,
                color: AppColors.navyDark,
              ),
            ),
            const SizedBox(height: 10),

            if (genreProvider.isLoading)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(12.0),
                  child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.gold),
                ),
              )
            else if (genreProvider.genres.isEmpty)
              const Text(
                'Chưa có danh mục thể loại.',
                style: TextStyle(fontSize: 12, color: AppColors.textSecondary),
              )
            else
              Wrap(
                spacing: 8.0,
                runSpacing: 8.0,
                children: genreProvider.genres.map((g) {
                  final isSelected = _selectedGenres.contains(g.name);
                  return FilterChip(
                    label: Text(
                      g.name,
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                        color: isSelected ? AppColors.navyDark : AppColors.textPrimary,
                      ),
                    ),
                    selected: isSelected,
                    selectedColor: AppColors.gold.withOpacity(0.28),
                    checkmarkColor: AppColors.navyDark,
                    backgroundColor: AppColors.surfaceVariant,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                      side: BorderSide(
                        color: isSelected ? AppColors.goldDark : Colors.transparent,
                        width: 1.2,
                      ),
                    ),
                    onSelected: (selected) {
                      setState(() {
                        if (selected) {
                          _selectedGenres.add(g.name);
                        } else {
                          _selectedGenres.remove(g.name);
                        }
                      });
                    },
                  );
                }).toList(),
              ),

            const SizedBox(height: 20),

            // Mục tiêu đọc sách
            const Text(
              'Mục tiêu đọc sách:',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.bold,
                color: AppColors.navyDark,
              ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _goalController,
              keyboardType: TextInputType.number,
              decoration: InputDecoration(
                labelText: 'Mục tiêu đọc sách trong năm',
                hintText: 'Ví dụ: 12',
                prefixIcon: const Icon(Icons.flag_rounded, color: AppColors.goldDark, size: 20),
                suffixText: 'cuốn / năm',
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              ),
            ),

            const SizedBox(height: 16),

            // Nút Lưu thay đổi
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.gold,
                  foregroundColor: AppColors.navyDark,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                icon: _isSavingPrefs
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: AppColors.navyDark,
                        ),
                      )
                    : const Icon(Icons.save_rounded, size: 18),
                label: Text(
                  _isSavingPrefs ? 'Đang lưu...' : 'Lưu sở thích & Mục tiêu',
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                ),
                onPressed: _isSavingPrefs ? null : _savePreferences,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
