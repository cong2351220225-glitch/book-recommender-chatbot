import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants/app_colors.dart';
import '../../models/crawler_book_model.dart';
import '../../providers/auth_provider.dart';
import '../../providers/crawler_provider.dart';
import '../../core/utils/url_launcher_helper.dart';

class AiCrawlerScreen extends StatefulWidget {
  const AiCrawlerScreen({super.key});

  @override
  State<AiCrawlerScreen> createState() => _AiCrawlerScreenState();
}

class _AiCrawlerScreenState extends State<AiCrawlerScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  // Search filter controllers
  final TextEditingController _queryController = TextEditingController();
  final TextEditingController _authorController = TextEditingController();
  final TextEditingController _subjectController = TextEditingController();
  final TextEditingController _isbnController = TextEditingController();
  final TextEditingController _yearFromController =
      TextEditingController(text: '1900');
  final TextEditingController _yearToController =
      TextEditingController(text: '2026');

  String _selectedLanguage = '';
  int _selectedLimit = 20;
  bool _upsertChroma = true;
  bool _showAdvancedFilters = false;

  final List<Map<String, String>> _languages = const [
    {'value': '', 'label': '(Tất cả ngôn ngữ)'},
    {'value': 'vie', 'label': 'Tiếng Việt (vie)'},
    {'value': 'eng', 'label': 'Tiếng Anh (eng)'},
    {'value': 'fra', 'label': 'Tiếng Pháp (fra)'},
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _tabController.addListener(() {
      if (_tabController.indexIsChanging && _tabController.index == 1) {
        context.read<CrawlerProvider>().fetchChromaStatus();
      }
    });

    WidgetsBinding.instance.addPostFrameCallback((_) {
      final provider = context.read<CrawlerProvider>();
      provider.fetchSources();
      provider.fetchChromaStatus();
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    _queryController.dispose();
    _authorController.dispose();
    _subjectController.dispose();
    _isbnController.dispose();
    _yearFromController.dispose();
    _yearToController.dispose();
    super.dispose();
  }

  void _onSearch() {
    final query = _queryController.text.trim();
    final author = _authorController.text.trim();
    final subject = _subjectController.text.trim();
    final isbn = _isbnController.text.trim();

    if (query.isEmpty && author.isEmpty && subject.isEmpty && isbn.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          backgroundColor: AppColors.error,
          content: Text(
            '⚠️ Vui lòng nhập ít nhất một từ khóa, tên tác giả, chủ đề hoặc mã ISBN.',
          ),
        ),
      );
      return;
    }

    FocusScope.of(context).unfocus();
    final yFrom = int.tryParse(_yearFromController.text.trim()) ?? 0;
    final yTo = int.tryParse(_yearToController.text.trim()) ?? 0;

    context.read<CrawlerProvider>().search(
          query: query,
          author: author,
          subject: subject,
          isbn: isbn,
          language: _selectedLanguage,
          yearFrom: yFrom > 1800 ? yFrom : 0,
          yearTo: yTo < 2030 ? yTo : 0,
          limit: _selectedLimit,
        );
  }

  void _resetFilters() {
    setState(() {
      _queryController.clear();
      _authorController.clear();
      _subjectController.clear();
      _isbnController.clear();
      _yearFromController.text = '1900';
      _yearToController.text = '2026';
      _selectedLanguage = '';
      _selectedLimit = 20;
    });
  }

  void _confirmAndBatchImport() {
    final provider = context.read<CrawlerProvider>();
    final selected = provider.selectedBooks;
    if (selected.isEmpty) return;

    final hasDuplicate = selected.any((b) => b.isDuplicate);

    showDialog(
      context: context,
      builder: (dialogCtx) {
        return AlertDialog(
          backgroundColor: const Color(0xFF1B263B),
          title: const Row(
            children: [
              Icon(Icons.cloud_download_outlined, color: AppColors.gold),
              SizedBox(width: 8),
              Text(
                'Xác nhận nhập sách',
                style: TextStyle(color: Colors.white, fontSize: 18),
              ),
            ],
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Bạn chuẩn bị nhập ${selected.length} cuốn sách đã chọn vào Thư viện số AI.',
                  style: const TextStyle(color: Colors.white70),
                ),
                const SizedBox(height: 12),
                if (hasDuplicate)
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: Colors.amber.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.amber.shade700),
                    ),
                    child: const Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(Icons.warning_amber_rounded,
                            color: Colors.amber, size: 20),
                        SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            'Lưu ý: Sách có dấu hiệu trùng lặp sẽ tự động được hệ thống bỏ qua để bảo vệ dữ liệu.',
                            style: TextStyle(color: Colors.amber, fontSize: 12),
                          ),
                        ),
                      ],
                    ),
                  ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Icon(
                      _upsertChroma
                          ? Icons.check_circle
                          : Icons.radio_button_unchecked,
                      color: AppColors.gold,
                      size: 18,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _upsertChroma
                            ? 'Tự động lập vector embedding ChromaDB (gemini-embedding-2)'
                            : 'Không lập vector embedding',
                        style: const TextStyle(
                            color: Colors.white70, fontSize: 13),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogCtx),
              child: const Text('Hủy bỏ',
                  style: TextStyle(color: Colors.white54)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.gold,
                foregroundColor: AppColors.navyDark,
              ),
              onPressed: () {
                Navigator.pop(dialogCtx);
                _executeBatchImport();
              },
              child: const Text('Bắt đầu nhập',
                  style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ],
        );
      },
    );
  }

  Future<void> _executeBatchImport() async {
    final provider = context.read<CrawlerProvider>();

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) {
        return const WillPopScope(
          onWillPop: _preventPop,
          child: AlertDialog(
            backgroundColor: Color(0xFF1B263B),
            content: Row(
              children: [
                CircularProgressIndicator(color: AppColors.gold),
                SizedBox(width: 20),
                Expanded(
                  child: Text(
                    'Đang tiến hành nhập và lập chỉ mục...',
                    style: TextStyle(color: Colors.white),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );

    final response =
        await provider.importSelectedBooks(upsertChroma: _upsertChroma);

    if (mounted) {
      Navigator.pop(context); // Close loading dialog
      _showImportResultDialog(response);
    }
  }

  static Future<bool> _preventPop() async => false;

  void _showImportResultDialog(CrawlerBatchImportResponse resp) {
    showDialog(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          backgroundColor: const Color(0xFF1B263B),
          title: const Row(
            children: [
              Icon(Icons.fact_check_outlined, color: AppColors.gold),
              SizedBox(width: 8),
              Text('Kết quả nhập sách',
                  style: TextStyle(color: Colors.white, fontSize: 18)),
            ],
          ),
          content: SizedBox(
            width: 500,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0D1B2A),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      _buildSummaryStat(
                          'Tổng số', '${resp.totalRequested}', Colors.white70),
                      _buildSummaryStat('Thành công', '${resp.importedCount}',
                          Colors.greenAccent),
                      _buildSummaryStat('Bỏ qua/Trùng', '${resp.skippedCount}',
                          Colors.orangeAccent),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                const Text(
                  'Chi tiết từng cuốn:',
                  style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 13),
                ),
                const SizedBox(height: 8),
                ConstrainedBox(
                  constraints: const BoxConstraints(maxHeight: 250),
                  child: ListView.separated(
                    shrinkWrap: true,
                    itemCount: resp.results.length,
                    separatorBuilder: (_, __) =>
                        const Divider(color: Colors.white12, height: 1),
                    itemBuilder: (c, idx) {
                      final item = resp.results[idx];
                      return ListTile(
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                        leading: Icon(
                          item.success
                              ? Icons.check_circle
                              : Icons.cancel_outlined,
                          color: item.success
                              ? Colors.greenAccent
                              : Colors.orangeAccent,
                          size: 20,
                        ),
                        title: Text(
                          item.title,
                          style: const TextStyle(
                              color: Colors.white, fontSize: 13),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        subtitle: Text(
                          item.message,
                          style: TextStyle(
                            color: item.success
                                ? Colors.white60
                                : Colors.orange.shade200,
                            fontSize: 11,
                          ),
                        ),
                        trailing: item.vectorIndexed
                            ? const Tooltip(
                                message: 'Đã lập vector ChromaDB',
                                child: Icon(Icons.bolt,
                                    color: AppColors.gold, size: 16),
                              )
                            : null,
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
          actions: [
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.gold,
                foregroundColor: AppColors.navyDark,
              ),
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Đóng'),
            ),
          ],
        );
      },
    );
  }

  Widget _buildSummaryStat(String label, String value, Color color) {
    return Column(
      children: [
        Text(value,
            style: TextStyle(
                color: color, fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 2),
        Text(label,
            style: const TextStyle(color: Colors.white54, fontSize: 11)),
      ],
    );
  }

  void _showBookDetailsDialog(CrawlerBookCandidate book) {
    showDialog(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          backgroundColor: const Color(0xFF1B263B),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: Row(
            children: [
              const Icon(Icons.menu_book_rounded, color: AppColors.gold),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  book.title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: Colors.white, fontSize: 16),
                ),
              ),
            ],
          ),
          content: SizedBox(
            width: 550,
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: book.coverUrl.isNotEmpty
                            ? Image.network(
                                book.coverUrl,
                                width: 90,
                                height: 130,
                                fit: BoxFit.cover,
                                errorBuilder: (_, __, ___) =>
                                    _buildCoverPlaceholder(width: 90, height: 130),
                              )
                            : _buildCoverPlaceholder(width: 90, height: 130),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              book.title,
                              style: const TextStyle(
                                color: AppColors.gold,
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text('Tác giả: ${book.author}',
                                style: const TextStyle(color: Colors.white70)),
                            const SizedBox(height: 4),
                            Text('Năm: ${book.year ?? "N/A"} · Thể loại: ${book.genre.isEmpty ? "Tổng hợp" : book.genre}',
                                style: const TextStyle(
                                    color: Colors.white54, fontSize: 12)),
                            const SizedBox(height: 8),
                            Wrap(
                              spacing: 6,
                              children: [
                                _buildBadge(book.source, Colors.blueGrey),
                                if (book.isDuplicate)
                                  _buildBadge(
                                      'Trùng: ${book.matchReason}', Colors.red)
                                else if (book.isUncertain)
                                  _buildBadge('Nghi trùng', Colors.orange)
                                else
                                  _buildBadge('Sách mới', Colors.green),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const Divider(color: Colors.white24, height: 24),
                  _buildDetailRow('Nguồn thu thập', book.source),
                  _buildDetailRow('ISBN', book.isbn.isEmpty ? 'Không có' : book.isbn),
                  _buildDetailRow('Nhà xuất bản',
                      book.publisher.isEmpty ? 'Không rõ' : book.publisher),
                  _buildDetailRow('Số trang', '${book.pages ?? "Không rõ"}'),
                  _buildDetailRow('Ngôn ngữ',
                      book.language.isEmpty ? 'Không rõ' : book.language),
                  _buildDetailRow(
                    'Trạng thái đọc số',
                    book.readingAvailable
                        ? 'Có tài liệu số (${book.readingType})'
                        : 'Không có tệp trực tiếp',
                  ),
                  if (book.readingUrl.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8.0),
                      child: Row(
                        children: [
                          const SizedBox(
                            width: 130,
                            child: Text('Tài liệu trực tuyến',
                                style: TextStyle(
                                    color: Colors.white54, fontSize: 12)),
                          ),
                          Expanded(
                            child: InkWell(
                              onTap: () => UrlLauncherHelper.launchUrlString(
                                  book.readingUrl),
                              child: Text(
                                book.readingUrl,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                    color: AppColors.gold,
                                    fontSize: 12,
                                    decoration: TextDecoration.underline),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  const SizedBox(height: 12),
                  const Text('Mô tả / Tóm tắt:',
                      style: TextStyle(
                          color: Colors.white70, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 6),
                  Text(
                    book.description.isEmpty
                        ? 'Không có mô tả chi tiết'
                        : book.description,
                    style: const TextStyle(
                        color: Colors.white60, fontSize: 13, height: 1.4),
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Đóng',
                  style: TextStyle(color: Colors.white54)),
            ),
            ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.gold,
                foregroundColor: AppColors.navyDark,
              ),
              icon: const Icon(Icons.download_rounded, size: 16),
              label: const Text('Nhập sách này',
                  style: TextStyle(fontWeight: FontWeight.bold)),
              onPressed: () async {
                Navigator.pop(ctx);
                final res = await context
                    .read<CrawlerProvider>()
                    .importSingleBook(book, upsertChroma: _upsertChroma);
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      backgroundColor: res.success
                          ? Colors.green.shade800
                          : Colors.red.shade800,
                      content: Text(res.message),
                    ),
                  );
                }
              },
            ),
          ],
        );
      },
    );
  }

  Widget _buildDetailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 130,
            child: Text(label,
                style: const TextStyle(color: Colors.white54, fontSize: 12)),
          ),
          Expanded(
            child: Text(value,
                style: const TextStyle(color: Colors.white, fontSize: 12)),
          ),
        ],
      ),
    );
  }

  void _confirmAndSyncChroma() {
    final provider = context.read<CrawlerProvider>();
    final unindexed = provider.chromaStatus?.unindexedCount ?? 0;

    showDialog(
      context: context,
      builder: (dialogCtx) {
        return AlertDialog(
          backgroundColor: const Color(0xFF1B263B),
          title: const Row(
            children: [
              Icon(Icons.bolt_rounded, color: AppColors.gold),
              SizedBox(width: 8),
              Text('Đồng bộ ChromaDB',
                  style: TextStyle(color: Colors.white, fontSize: 18)),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Hệ thống sẽ tiến hành tạo vector embedding bằng mô hình "gemini-embedding-2" cho $unindexed cuốn sách chưa được lập chỉ mục trong ChromaDB.',
                style: const TextStyle(color: Colors.white70, fontSize: 13),
              ),
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: const Color(0xFF0D1B2A),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppColors.gold.withOpacity(0.3)),
                ),
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('🛡️ Nguyên tắc an toàn dữ liệu:',
                        style: TextStyle(
                            color: AppColors.gold,
                            fontSize: 12,
                            fontWeight: FontWeight.bold)),
                    SizedBox(height: 4),
                    Text('• Giữ nguyên toàn bộ vector sách cũ trong books_collection.',
                        style: TextStyle(color: Colors.white60, fontSize: 11)),
                    Text('• Dùng book_id ổn định, không tạo vector trùng.',
                        style: TextStyle(color: Colors.white60, fontSize: 11)),
                    Text('• Xử lý từng sách độc lập, không làm đứt đoạn cả lô.',
                        style: TextStyle(color: Colors.white60, fontSize: 11)),
                  ],
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogCtx),
              child: const Text('Hủy bỏ',
                  style: TextStyle(color: Colors.white54)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.gold,
                foregroundColor: AppColors.navyDark,
              ),
              onPressed: () async {
                Navigator.pop(dialogCtx);
                _executeSyncChroma();
              },
              child: const Text('Bắt đầu đồng bộ',
                  style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ],
        );
      },
    );
  }

  Future<void> _executeSyncChroma() async {
    final provider = context.read<CrawlerProvider>();

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) {
        return const WillPopScope(
          onWillPop: _preventPop,
          child: AlertDialog(
            backgroundColor: Color(0xFF1B263B),
            content: Row(
              children: [
                CircularProgressIndicator(color: AppColors.gold),
                SizedBox(width: 20),
                Expanded(
                  child: Text(
                    'Đang đồng bộ vector vào ChromaDB...\nQuá trình có thể mất từ vài giây đến một phút.',
                    style: TextStyle(color: Colors.white, fontSize: 13),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );

    final res = await provider.syncChroma();

    if (mounted) {
      Navigator.pop(context); // Close loading dialog
      _showSyncResultDialog(res);
    }
  }

  void _showSyncResultDialog(SyncChromaResult res) {
    showDialog(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          backgroundColor: const Color(0xFF1B263B),
          title: Row(
            children: [
              Icon(
                res.success ? Icons.task_alt_rounded : Icons.error_outline,
                color: res.success ? Colors.greenAccent : Colors.redAccent,
              ),
              const SizedBox(width: 8),
              const Text('Kết quả đồng bộ Vector',
                  style: TextStyle(color: Colors.white, fontSize: 18)),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                res.message,
                style: const TextStyle(color: Colors.white70, fontSize: 13),
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF0D1B2A),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: [
                    _buildSummaryStat(
                        'Cần đồng bộ', '${res.totalUnindexed}', Colors.white70),
                    _buildSummaryStat('Thành công', '${res.syncedCount}',
                        Colors.greenAccent),
                    _buildSummaryStat('Thất bại', '${res.failedCount}',
                        Colors.redAccent),
                  ],
                ),
              ),
            ],
          ),
          actions: [
            if (res.failedCount > 0)
              TextButton(
                onPressed: () {
                  Navigator.pop(ctx);
                  _confirmAndSyncChroma();
                },
                child: const Text('Thử lại sách lỗi',
                    style: TextStyle(color: AppColors.gold)),
              ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.gold,
                foregroundColor: AppColors.navyDark,
              ),
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Đóng'),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final authProvider = context.watch<AuthProvider>();
    final crawlerProvider = context.watch<CrawlerProvider>();

    // Guard: Only admins allowed
    if (!authProvider.isAdmin) {
      return Scaffold(
        backgroundColor: const Color(0xFF0D1B2A),
        appBar: AppBar(
          title: const Text('AI Book Crawler & ChromaDB'),
          backgroundColor: const Color(0xFF1B263B),
        ),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.gpp_bad_outlined,
                    size: 72, color: Colors.redAccent),
                const SizedBox(height: 16),
                const Text(
                  'Truy cập bị từ chối',
                  style: TextStyle(
                      color: Colors.white,
                      fontSize: 20,
                      fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Chức năng Quản trị AI Crawler & Đồng bộ ChromaDB chỉ dành riêng cho Quản trị viên thư viện (Admin).',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.white70),
                ),
                const SizedBox(height: 24),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.gold,
                    foregroundColor: AppColors.navyDark,
                  ),
                  onPressed: () {
                    if (Navigator.canPop(context)) {
                      Navigator.pop(context);
                    }
                  },
                  child: const Text('Quay lại'),
                ),
              ],
            ),
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: const Color(0xFF0D1B2A),
      appBar: AppBar(
        title: const Text(
          'Trung tâm AI Crawler & ChromaDB Vector Sync',
          style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
        backgroundColor: const Color(0xFF1B263B),
        foregroundColor: Colors.white,
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: AppColors.gold,
          indicatorWeight: 3,
          labelColor: AppColors.gold,
          unselectedLabelColor: Colors.white60,
          labelStyle: const TextStyle(fontWeight: FontWeight.bold),
          tabs: [
            Tab(
              icon: const Icon(Icons.travel_explore_rounded),
              text: 'AI Book Crawler (${crawlerProvider.results.length})',
            ),
            Tab(
              icon: const Icon(Icons.hub_rounded),
              text:
                  'ChromaDB Vector Sync (${crawlerProvider.chromaStatus?.unindexedCount ?? 0} chưa index)',
            ),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildCrawlerTab(crawlerProvider),
          _buildChromaSyncTab(crawlerProvider),
        ],
      ),
    );
  }

  // =========================================================================
  // TAB 1: AI BOOK CRAWLER
  // =========================================================================
  Widget _buildCrawlerTab(CrawlerProvider provider) {
    return Column(
      children: [
        _buildSearchFilterHeader(provider),
        if (provider.results.isNotEmpty) _buildResultsToolBar(provider),
        Expanded(
          child: provider.isLoading
              ? const Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      CircularProgressIndicator(color: AppColors.gold),
                      SizedBox(height: 16),
                      Text('Đang truy vấn các nguồn dữ liệu số...',
                          style: TextStyle(color: Colors.white70)),
                    ],
                  ),
                )
              : provider.errorMessage != null
                  ? Center(
                      child: Padding(
                        padding: const EdgeInsets.all(24.0),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.error_outline,
                                size: 48, color: Colors.redAccent),
                            const SizedBox(height: 12),
                            Text(
                              provider.errorMessage!,
                              textAlign: TextAlign.center,
                              style: const TextStyle(color: Colors.white70),
                            ),
                            const SizedBox(height: 16),
                            ElevatedButton(
                              style: ElevatedButton.styleFrom(
                                backgroundColor: AppColors.gold,
                                foregroundColor: AppColors.navyDark,
                              ),
                              onPressed: _onSearch,
                              child: const Text('Thử lại'),
                            ),
                          ],
                        ),
                      ),
                    )
                  : provider.results.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: const [
                              Icon(Icons.manage_search,
                                  size: 64, color: Colors.white24),
                              SizedBox(height: 12),
                              Text(
                                'Nhập từ khóa và bấm tìm kiếm để thu thập sách từ 6 nguồn mở chính thống',
                                style: TextStyle(color: Colors.white38),
                              ),
                            ],
                          ),
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.all(12),
                          itemCount: provider.results.length,
                          itemBuilder: (ctx, index) {
                            final book = provider.results[index];
                            return _buildBookCard(book, index, provider);
                          },
                        ),
        ),
      ],
    );
  }

  Widget _buildSearchFilterHeader(CrawlerProvider provider) {
    return Container(
      padding: const EdgeInsets.all(16.0),
      color: const Color(0xFF1B263B),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                flex: 2,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0D1B2A),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.white24),
                  ),
                  child: DropdownButtonHideUnderline(
                    child: DropdownButton<String>(
                      value: provider.selectedSource,
                      isExpanded: true,
                      dropdownColor: const Color(0xFF1B263B),
                      style: const TextStyle(color: Colors.white, fontSize: 13),
                      items: provider.sources.map((src) {
                        return DropdownMenuItem<String>(
                          value: src.id,
                          child: Text(src.name, overflow: TextOverflow.ellipsis),
                        );
                      }).toList(),
                      onChanged: (val) {
                        if (val != null) {
                          provider.setSelectedSource(val);
                        }
                      },
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                flex: 3,
                child: TextField(
                  controller: _queryController,
                  style: const TextStyle(color: Colors.white),
                  decoration: InputDecoration(
                    hintText: 'Từ khóa / Tên sách...',
                    hintStyle: const TextStyle(color: Colors.white38),
                    filled: true,
                    fillColor: const Color(0xFF0D1B2A),
                    contentPadding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 12),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: const BorderSide(color: AppColors.gold),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide:
                          const BorderSide(color: AppColors.gold, width: 2),
                    ),
                  ),
                  onSubmitted: (_) => _onSearch(),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                flex: 2,
                child: TextField(
                  controller: _authorController,
                  style: const TextStyle(color: Colors.white),
                  decoration: InputDecoration(
                    hintText: 'Tác giả...',
                    hintStyle: const TextStyle(color: Colors.white38),
                    filled: true,
                    fillColor: const Color(0xFF0D1B2A),
                    contentPadding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 12),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: const BorderSide(color: Colors.white24),
                    ),
                  ),
                  onSubmitted: (_) => _onSearch(),
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.gold,
                  foregroundColor: AppColors.navyDark,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                ),
                icon: const Icon(Icons.rocket_launch_rounded, size: 18),
                label: const Text('Thu thập',
                    style: TextStyle(fontWeight: FontWeight.bold)),
                onPressed: provider.isLoading ? null : _onSearch,
              ),
              const SizedBox(width: 8),
              IconButton(
                tooltip: _showAdvancedFilters ? 'Ẩn bộ lọc mở rộng' : 'Hiện bộ lọc mở rộng',
                icon: Icon(
                  _showAdvancedFilters
                      ? Icons.filter_list_off
                      : Icons.tune_rounded,
                  color: AppColors.gold,
                ),
                onPressed: () {
                  setState(() => _showAdvancedFilters = !_showAdvancedFilters);
                },
              ),
            ],
          ),
          if (_showAdvancedFilters) ...[
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _subjectController,
                    style: const TextStyle(color: Colors.white, fontSize: 13),
                    decoration: InputDecoration(
                      hintText: 'Chủ đề / Thể loại...',
                      hintStyle: const TextStyle(color: Colors.white38),
                      filled: true,
                      fillColor: const Color(0xFF0D1B2A),
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 12, vertical: 10),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                        borderSide: const BorderSide(color: Colors.white24),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: TextField(
                    controller: _isbnController,
                    style: const TextStyle(color: Colors.white, fontSize: 13),
                    decoration: InputDecoration(
                      hintText: 'Mã ISBN...',
                      hintStyle: const TextStyle(color: Colors.white38),
                      filled: true,
                      fillColor: const Color(0xFF0D1B2A),
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 12, vertical: 10),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                        borderSide: const BorderSide(color: Colors.white24),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10),
                    decoration: BoxDecoration(
                      color: const Color(0xFF0D1B2A),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.white24),
                    ),
                    child: DropdownButtonHideUnderline(
                      child: DropdownButton<String>(
                        value: _selectedLanguage,
                        isExpanded: true,
                        dropdownColor: const Color(0xFF1B263B),
                        style: const TextStyle(
                            color: Colors.white, fontSize: 12),
                        items: _languages.map((l) {
                          return DropdownMenuItem<String>(
                            value: l['value']!,
                            child: Text(l['label']!),
                          );
                        }).toList(),
                        onChanged: (val) {
                          if (val != null) {
                            setState(() => _selectedLanguage = val);
                          }
                        },
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                SizedBox(
                  width: 90,
                  child: TextField(
                    controller: _yearFromController,
                    keyboardType: TextInputType.number,
                    style: const TextStyle(color: Colors.white, fontSize: 13),
                    decoration: InputDecoration(
                      labelText: 'Từ năm',
                      labelStyle: const TextStyle(color: Colors.white54, fontSize: 11),
                      filled: true,
                      fillColor: const Color(0xFF0D1B2A),
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 8),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                        borderSide: const BorderSide(color: Colors.white24),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                SizedBox(
                  width: 90,
                  child: TextField(
                    controller: _yearToController,
                    keyboardType: TextInputType.number,
                    style: const TextStyle(color: Colors.white, fontSize: 13),
                    decoration: InputDecoration(
                      labelText: 'Đến năm',
                      labelStyle: const TextStyle(color: Colors.white54, fontSize: 11),
                      filled: true,
                      fillColor: const Color(0xFF0D1B2A),
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 8),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                        borderSide: const BorderSide(color: Colors.white24),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                TextButton.icon(
                  onPressed: _resetFilters,
                  icon: const Icon(Icons.refresh, size: 16, color: Colors.white54),
                  label: const Text('Đặt lại',
                      style: TextStyle(color: Colors.white54, fontSize: 12)),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildResultsToolBar(CrawlerProvider provider) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: const BoxDecoration(
        color: Color(0xFF14213D),
        border: Border(bottom: BorderSide(color: Colors.white12)),
      ),
      child: Column(
        children: [
          // 5 Colorful metric summary boxes (matching Web)
          Row(
            children: [
              _buildMetricChip(
                  'Tổng kết quả', '${provider.totalCount}', const Color(0xFF0B1F3A), Colors.white),
              const SizedBox(width: 8),
              _buildMetricChip(
                  'Sách mới', '${provider.newCount}', const Color(0xFF1B5E20), Colors.greenAccent),
              const SizedBox(width: 8),
              _buildMetricChip(
                  'Trùng lặp', '${provider.duplicateCount}', const Color(0xFFBF360C), Colors.orangeAccent),
              const SizedBox(width: 8),
              _buildMetricChip(
                  'Cần xem xét', '${provider.uncertainCount}', const Color(0xFFE65100), Colors.amberAccent),
              const SizedBox(width: 8),
              _buildMetricChip(
                  'Thiếu mô tả', '${provider.noDescCount}', const Color(0xFF880E4F), Colors.pinkAccent),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.greenAccent,
                  side: const BorderSide(color: Colors.greenAccent),
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                ),
                icon: const Icon(Icons.select_all_rounded, size: 16),
                label: const Text('Chọn tất cả mới', style: TextStyle(fontSize: 12)),
                onPressed: provider.selectAllNew,
              ),
              const SizedBox(width: 8),
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.white54,
                  side: const BorderSide(color: Colors.white24),
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                ),
                icon: const Icon(Icons.deselect_rounded, size: 16),
                label: const Text('Bỏ chọn tất cả', style: TextStyle(fontSize: 12)),
                onPressed: provider.deselectAll,
              ),
              const Spacer(),
              Row(
                children: [
                  const Text('Lập Vector ChromaDB',
                      style: TextStyle(color: Colors.white70, fontSize: 12)),
                  Switch(
                    value: _upsertChroma,
                    activeColor: AppColors.gold,
                    onChanged: (v) => setState(() => _upsertChroma = v),
                  ),
                ],
              ),
              const SizedBox(width: 12),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.gold,
                  foregroundColor: AppColors.navyDark,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                ),
                icon: const Icon(Icons.download_rounded, size: 16),
                label: Text(
                  'Nhập (${provider.selectedCount}) sách',
                  style: const TextStyle(
                      fontWeight: FontWeight.bold, fontSize: 13),
                ),
                onPressed: provider.selectedCount > 0
                    ? _confirmAndBatchImport
                    : null,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMetricChip(
      String label, String value, Color bgColor, Color textColor) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 8),
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: BorderRadius.circular(6),
        ),
        child: Column(
          children: [
            Text(value,
                style: TextStyle(
                    color: textColor,
                    fontSize: 15,
                    fontWeight: FontWeight.bold)),
            Text(label,
                style: const TextStyle(color: Colors.white70, fontSize: 10)),
          ],
        ),
      ),
    );
  }

  Widget _buildBookCard(
    CrawlerBookCandidate book,
    int index,
    CrawlerProvider provider,
  ) {
    return Card(
      color: const Color(0xFF1B263B),
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: BorderSide(
          color: book.isSelected ? AppColors.gold : Colors.white12,
          width: book.isSelected ? 1.5 : 1,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Checkbox(
              value: book.isSelected,
              activeColor: AppColors.gold,
              checkColor: AppColors.navyDark,
              onChanged: (val) => provider.toggleSelectBook(index, val),
            ),
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: book.coverUrl.isNotEmpty
                  ? Image.network(
                      book.coverUrl,
                      width: 60,
                      height: 90,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => _buildCoverPlaceholder(),
                    )
                  : _buildCoverPlaceholder(),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    book.title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 14,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Tác giả: ${book.author}',
                    style: const TextStyle(color: Colors.white70, fontSize: 12),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    'Năm: ${book.year ?? "N/A"} · NXB: ${book.publisher.isNotEmpty ? book.publisher : "N/A"} · ISBN: ${book.isbn.isNotEmpty ? book.isbn : "N/A"}',
                    style: const TextStyle(color: Colors.white54, fontSize: 11),
                  ),
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 6,
                    runSpacing: 4,
                    children: [
                      _buildBadge(book.source, Colors.blueGrey),
                      if (book.readingAvailable)
                        _buildBadge('Đọc tự do (${book.readingType})', Colors.green),
                      if (book.isDuplicate)
                        _buildBadge('Trùng: ${book.matchReason}', Colors.red)
                      else if (book.isUncertain)
                        _buildBadge('Nghi trùng', Colors.orange)
                      else
                        _buildBadge('Sách mới', Colors.teal),
                      if (book.hasNoDescription)
                        _buildBadge('Thiếu mô tả', Colors.pinkAccent),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      TextButton.icon(
                        icon: const Icon(Icons.info_outline, size: 14),
                        label: const Text('Chi tiết', style: TextStyle(fontSize: 12)),
                        style: TextButton.styleFrom(foregroundColor: AppColors.gold),
                        onPressed: () => _showBookDetailsDialog(book),
                      ),
                      const SizedBox(width: 8),
                      OutlinedButton.icon(
                        icon: const Icon(Icons.download_rounded, size: 14),
                        label: const Text('Nhập ngay', style: TextStyle(fontSize: 12)),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: Colors.white,
                          side: const BorderSide(color: AppColors.gold),
                          padding: const EdgeInsets.symmetric(
                              horizontal: 10, vertical: 4),
                        ),
                        onPressed: () async {
                          final res = await provider.importSingleBook(book,
                              upsertChroma: _upsertChroma);
                          if (mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                backgroundColor: res.success
                                    ? Colors.green.shade800
                                    : Colors.red.shade800,
                                content: Text(res.message),
                              ),
                            );
                          }
                        },
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCoverPlaceholder({double width = 60, double height = 90}) {
    return Container(
      width: width,
      height: height,
      color: const Color(0xFF0D1B2A),
      child: const Icon(Icons.book, color: Colors.white24, size: 28),
    );
  }

  Widget _buildBadge(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.2),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withOpacity(0.6), width: 0.8),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.bold),
      ),
    );
  }

  // =========================================================================
  // TAB 2: CHROMADB VECTOR SYNC
  // =========================================================================
  Widget _buildChromaSyncTab(CrawlerProvider provider) {
    if (provider.isLoadingChromaStatus) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(color: AppColors.gold),
            SizedBox(height: 16),
            Text('Đang nạp trạng thái vector ChromaDB...',
                style: TextStyle(color: Colors.white70)),
          ],
        ),
      );
    }

    final status = provider.chromaStatus;
    final unindexedCount = status?.unindexedCount ?? 0;
    final totalBooks = status?.totalBooks ?? 0;
    final indexedCount = status?.indexedCount ?? 0;
    final failedCount = status?.failedCount ?? 0;
    final lastSyncedAt = status?.lastSyncedAt;
    final unindexedBooks = status?.unindexedBooks ?? [];

    return RefreshIndicator(
      color: AppColors.gold,
      backgroundColor: const Color(0xFF1B263B),
      onRefresh: () async => await provider.fetchChromaStatus(),
      child: ListView(
        padding: const EdgeInsets.all(20.0),
        children: [
          // Collection Info Banner
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF0B1F3A), Color(0xFF123B66)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.gold.withOpacity(0.4)),
            ),
            child: Row(
              children: [
                const Icon(Icons.hub_rounded, size: 40, color: AppColors.gold),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'QUẢN LÝ VÀ ĐỒNG BỘ VECTOR CHROMADB',
                        style: TextStyle(
                          color: AppColors.gold,
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 0.8,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Collection: ${status?.collectionName ?? "books_collection"} · Metric: cosine · Embedding Model: ${status?.embeddingModel ?? "gemini-embedding-2"}',
                        style: const TextStyle(
                            color: Colors.white70, fontSize: 12),
                      ),
                      if (lastSyncedAt != null && lastSyncedAt.isNotEmpty) ...[
                        const SizedBox(height: 2),
                        Text('Lần đồng bộ gần nhất: $lastSyncedAt',
                            style: const TextStyle(
                                color: AppColors.goldLight, fontSize: 11)),
                      ],
                    ],
                  ),
                ),
                IconButton(
                  tooltip: 'Làm mới trạng thái',
                  icon: const Icon(Icons.refresh, color: AppColors.gold),
                  onPressed: () => provider.fetchChromaStatus(),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // 4 Big Metric Stat Cards
          Row(
            children: [
              _buildChromaStatCard(
                'Tổng sách trong CSV',
                '$totalBooks',
                Icons.menu_book_rounded,
                Colors.white,
                const Color(0xFF1B263B),
              ),
              const SizedBox(width: 12),
              _buildChromaStatCard(
                'Đã lập Vector',
                '$indexedCount',
                Icons.bolt_rounded,
                Colors.greenAccent,
                const Color(0xFF1B263B),
              ),
              const SizedBox(width: 12),
              _buildChromaStatCard(
                'Chưa lập Vector',
                '$unindexedCount',
                Icons.warning_amber_rounded,
                unindexedCount > 0 ? Colors.orangeAccent : Colors.white60,
                const Color(0xFF1B263B),
              ),
              const SizedBox(width: 12),
              _buildChromaStatCard(
                'Thất bại lần trước',
                '$failedCount',
                Icons.error_outline,
                failedCount > 0 ? Colors.redAccent : Colors.white60,
                const Color(0xFF1B263B),
              ),
            ],
          ),
          const SizedBox(height: 20),

          // Recovery & Synchronization Status Section
          if (unindexedCount == 0) ...[
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: const Color(0xFF142D1F),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.greenAccent.withOpacity(0.5)),
              ),
              child: const Row(
                children: [
                  Icon(Icons.check_circle_rounded,
                      color: Colors.greenAccent, size: 36),
                  SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Tất cả sách đều đã được đồng bộ Vector!',
                          style: TextStyle(
                            color: Colors.greenAccent,
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        SizedBox(height: 4),
                        Text(
                          'ChromaDB và kho sách CSV hoàn toàn đồng bộ 100%. Cơ chế truy xuất RAG và gợi ý ngữ nghĩa đang hoạt động tối ưu.',
                          style: TextStyle(color: Colors.white70, fontSize: 13),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ] else ...[
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: const Color(0xFF33200B),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.amber.shade700),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.warning_amber_rounded,
                          color: Colors.amber, size: 36),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Phát hiện $unindexedCount sách chưa lập Vector trong ChromaDB!',
                              style: const TextStyle(
                                color: Colors.amber,
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 4),
                            const Text(
                              'Các sách này có trong thư viện CSV nhưng chưa được tính toán embedding ngữ nghĩa (do lỗi mạng hoặc bước embedding trước bị gián đoạn).',
                              style: TextStyle(
                                  color: Colors.white70, fontSize: 13),
                            ),
                          ],
                        ),
                      ),
                      ElevatedButton.icon(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.gold,
                          foregroundColor: AppColors.navyDark,
                          padding: const EdgeInsets.symmetric(
                              horizontal: 18, vertical: 14),
                        ),
                        icon: const Icon(Icons.sync_rounded),
                        label: const Text(
                          'Đồng bộ lại vào ChromaDB',
                          style: TextStyle(fontWeight: FontWeight.bold),
                        ),
                        onPressed: provider.isSyncingChroma
                            ? null
                            : _confirmAndSyncChroma,
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Table of unindexed books
            const Text(
              'Danh sách sách chờ lập chỉ mục Vector:',
              style: TextStyle(
                color: Colors.white,
                fontSize: 15,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Container(
              decoration: BoxDecoration(
                color: const Color(0xFF1B263B),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Colors.white12),
              ),
              child: ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: unindexedBooks.length,
                separatorBuilder: (_, __) =>
                    const Divider(color: Colors.white12, height: 1),
                itemBuilder: (ctx, idx) {
                  final b = unindexedBooks[idx];
                  return ListTile(
                    dense: true,
                    leading: Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: const Color(0xFF0D1B2A),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        '${b['book_id'] ?? "N/A"}',
                        style: const TextStyle(
                            color: AppColors.gold,
                            fontSize: 11,
                            fontWeight: FontWeight.bold),
                      ),
                    ),
                    title: Text(
                      '${b['title'] ?? "Chưa rõ tiêu đề"}',
                      style: const TextStyle(
                          color: Colors.white,
                          fontSize: 13,
                          fontWeight: FontWeight.w600),
                    ),
                    subtitle: Text(
                      'Tác giả: ${b['author'] ?? "N/A"} · Thể loại: ${b['genre'] ?? "N/A"} · Năm: ${b['year'] ?? "N/A"}',
                      style: const TextStyle(
                          color: Colors.white60, fontSize: 11),
                    ),
                    trailing: const Tooltip(
                      message: 'Chưa có vector embedding trong ChromaDB',
                      child: Icon(Icons.cloud_off_rounded,
                          color: Colors.orangeAccent, size: 18),
                    ),
                  );
                },
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildChromaStatCard(
    String label,
    String value,
    IconData icon,
    Color valueColor,
    Color bgColor,
  ) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: Colors.white12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: valueColor, size: 20),
                const Spacer(),
                Text(
                  value,
                  style: TextStyle(
                    color: valueColor,
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              label,
              style: const TextStyle(color: Colors.white54, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }
}
