import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/constants/app_colors.dart';
import '../../providers/reading_provider.dart';
import '../../providers/bookshelf_provider.dart';

class DigitalReaderScreen extends StatefulWidget {
  final String bookId;
  final String title;

  const DigitalReaderScreen({
    super.key,
    required this.bookId,
    required this.title,
  });

  @override
  State<DigitalReaderScreen> createState() => _DigitalReaderScreenState();
}

class _DigitalReaderScreenState extends State<DigitalReaderScreen> {
  final TransformationController _transformController = TransformationController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ReadingProvider>().loadDocument(widget.bookId);
    });
  }

  @override
  void dispose() {
    _transformController.dispose();
    super.dispose();
  }

  void _showJumpToPageDialog(BuildContext context, ReadingProvider provider) {
    final controller = TextEditingController(text: provider.currentPage.toString());
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Chuyển đến trang', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.number,
          autofocus: true,
          decoration: InputDecoration(
            labelText: 'Số trang (1 - ${provider.totalPages})',
            hintText: 'Nhập số trang',
            border: const OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Hủy'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.navy,
              foregroundColor: Colors.white,
            ),
            onPressed: () {
              final page = int.tryParse(controller.text.trim());
              if (page != null) {
                provider.jumpToPage(page);
                // Also update bookshelf provider
                context.read<BookshelfProvider>().loadBookshelf(silent: true);
              }
              Navigator.of(ctx).pop();
            },
            child: const Text('Đến trang'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<ReadingProvider>();
    final docInfo = provider.docInfo;

    return PopScope(
      onPopInvoked: (_) {
        provider.saveProgress();
        context.read<BookshelfProvider>().loadBookshelf(silent: true);
      },
      child: Scaffold(
        backgroundColor: const Color(0xFF2A2D34), // Reader dark backdrop
        appBar: AppBar(
          backgroundColor: AppColors.navyDark,
          elevation: 2,
          leading: IconButton(
            icon: const Icon(Icons.arrow_back_rounded, color: Colors.white),
            tooltip: 'Trở về',
            onPressed: () {
              provider.saveProgress();
              context.read<BookshelfProvider>().loadBookshelf(silent: true);
              Navigator.of(context).pop();
            },
          ),
          title: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                widget.title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              if (docInfo != null)
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                      decoration: BoxDecoration(
                        color: AppColors.gold,
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        docInfo.format.toUpperCase(),
                        style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w800, color: AppColors.navyDark),
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      docInfo.formattedFileSize,
                      style: const TextStyle(fontSize: 10, color: Colors.white70),
                    ),
                  ],
                ),
            ],
          ),
          actions: [
            IconButton(
              icon: const Icon(Icons.zoom_out_rounded, color: Colors.white, size: 20),
              tooltip: 'Thu nhỏ',
              onPressed: provider.zoomOut,
            ),
            IconButton(
              icon: const Icon(Icons.zoom_in_rounded, color: Colors.white, size: 20),
              tooltip: 'Phóng to',
              onPressed: provider.zoomIn,
            ),
            IconButton(
              icon: const Icon(Icons.pin_rounded, color: AppColors.gold, size: 20),
              tooltip: 'Đến trang...',
              onPressed: () => _showJumpToPageDialog(context, provider),
            ),
          ],
        ),
        body: Stack(
          children: [
            // Main Reader Canvas
            if (provider.isLoading)
              const Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    CircularProgressIndicator(color: AppColors.gold),
                    SizedBox(height: 16),
                    Text(
                      'Đang tải bản số hóa...',
                      style: TextStyle(color: Colors.white70, fontSize: 13),
                    ),
                  ],
                ),
              )
            else if (provider.errorMessage != null)
              Center(
                child: Padding(
                  padding: const EdgeInsets.all(24.0),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.error_outline_rounded, color: AppColors.error, size: 48),
                      const SizedBox(height: 12),
                      Text(
                        provider.errorMessage!,
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: Colors.white, fontSize: 14),
                      ),
                      const SizedBox(height: 16),
                      ElevatedButton.icon(
                        icon: const Icon(Icons.refresh_rounded, size: 16),
                        label: const Text('Thử lại'),
                        onPressed: () => provider.loadDocument(widget.bookId),
                      ),
                    ],
                  ),
                ),
              )
            else
              _buildDocumentViewer(context, provider),

            // Top Resume Reading Position Banner
            if (provider.hasResumePosition)
              Positioned(
                top: 12,
                left: 16,
                right: 16,
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 450),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                      decoration: BoxDecoration(
                        color: AppColors.navyDark,
                        borderRadius: BorderRadius.circular(24),
                        border: Border.all(color: AppColors.gold),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.3),
                            blurRadius: 8,
                            offset: const Offset(0, 3),
                          ),
                        ],
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.history_rounded, size: 16, color: AppColors.gold),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'Đọc tiếp từ trang ${provider.resumePage}?',
                              style: const TextStyle(color: Colors.white, fontSize: 12),
                            ),
                          ),
                          TextButton(
                            style: TextButton.styleFrom(
                              foregroundColor: AppColors.gold,
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            ),
                            onPressed: provider.resumeFromSavedPage,
                            child: const Text('Tiếp tục', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                          ),
                          IconButton(
                            icon: const Icon(Icons.close_rounded, size: 14, color: Colors.white70),
                            onPressed: provider.dismissResumePrompt,
                            padding: EdgeInsets.zero,
                            constraints: const BoxConstraints(),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),

            // Bottom Navigation & Progress Bar
            if (!provider.isLoading && provider.errorMessage == null)
              Positioned(
                bottom: 16,
                left: 16,
                right: 16,
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 600),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      decoration: BoxDecoration(
                        color: AppColors.navyDark.withOpacity(0.92),
                        borderRadius: BorderRadius.circular(30),
                        border: Border.all(color: AppColors.gold.withOpacity(0.4)),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.25),
                            blurRadius: 10,
                            offset: const Offset(0, 4),
                          ),
                        ],
                      ),
                      child: Row(
                        children: [
                          IconButton(
                            icon: const Icon(Icons.chevron_left_rounded, color: Colors.white, size: 24),
                            tooltip: 'Trang trước',
                            onPressed: provider.currentPage > 1 ? provider.prevPage : null,
                          ),
                          Expanded(
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                SliderTheme(
                                  data: SliderTheme.of(context).copyWith(
                                    thumbColor: AppColors.gold,
                                    activeTrackColor: AppColors.gold,
                                    inactiveTrackColor: Colors.white24,
                                    trackHeight: 3,
                                    thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 6),
                                  ),
                                  child: Slider(
                                    value: provider.currentPage.toDouble(),
                                    min: 1.0,
                                    max: provider.totalPages.toDouble(),
                                    divisions: provider.totalPages > 1 ? provider.totalPages - 1 : 1,
                                    onChanged: (val) {
                                      provider.jumpToPage(val.toInt());
                                    },
                                  ),
                                ),
                                Text(
                                  'Trang ${provider.currentPage} / ${provider.totalPages} (${(provider.progressPercentage * 100).toInt()}%)',
                                  style: const TextStyle(color: Colors.white70, fontSize: 11),
                                ),
                              ],
                            ),
                          ),
                          IconButton(
                            icon: const Icon(Icons.chevron_right_rounded, color: Colors.white, size: 24),
                            tooltip: 'Trang tiếp',
                            onPressed: provider.currentPage < provider.totalPages ? provider.nextPage : null,
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildDocumentViewer(BuildContext context, ReadingProvider provider) {
    return GestureDetector(
      onHorizontalDragEnd: (details) {
        if (details.primaryVelocity != null) {
          if (details.primaryVelocity! < -100) {
            // Swiped Left -> Next page
            provider.nextPage();
          } else if (details.primaryVelocity! > 100) {
            // Swiped Right -> Prev page
            provider.prevPage();
          }
        }
      },
      child: Center(
        child: InteractiveViewer(
          transformationController: _transformController,
          minScale: 0.5,
          maxScale: 3.0,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 40.0),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 680, maxHeight: 900),
              child: Container(
                decoration: BoxDecoration(
                  color: const Color(0xFFFBFBF8), // Paper off-white color
                  borderRadius: BorderRadius.circular(8),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.3),
                      blurRadius: 16,
                      offset: const Offset(0, 6),
                    ),
                  ],
                ),
                padding: const EdgeInsets.all(32.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Page Header
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          widget.title,
                          style: const TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: AppColors.textMuted,
                          ),
                        ),
                        Text(
                          'Trang ${provider.currentPage}',
                          style: const TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: AppColors.textMuted,
                          ),
                        ),
                      ],
                    ),
                    const Divider(color: AppColors.border, height: 20),

                    // Page Body Content
                    Expanded(
                      child: SingleChildScrollView(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const SizedBox(height: 12),
                            Text(
                              'Chương ${provider.currentPage}: Nội Dung Tác Phẩm',
                              style: const TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                                color: AppColors.navyDark,
                                height: 1.3,
                              ),
                            ),
                            const SizedBox(height: 16),
                            Text(
                              'Bạn đang đọc tác phẩm số hóa "${widget.title}" trong hệ thống Thư viện số AI (AI Digital Library).\n\n'
                              '• Trang số: ${provider.currentPage} / ${provider.totalPages}\n'
                              '• Định dạng tài liệu: ${provider.docInfo?.format.toUpperCase() ?? "PDF"}\n'
                              '• Kích thước tệp: ${provider.docInfo?.formattedFileSize ?? "N/A"}\n\n'
                              'Trình đọc sách số hỗ trợ điều hướng trang mượt mà, phóng to/thu nhỏ, tự động ghi nhớ trang bạn vừa dừng lại và đồng bộ với Tủ sách cá nhân của bạn.',
                              style: const TextStyle(
                                fontSize: 14,
                                height: 1.7,
                                color: AppColors.textPrimary,
                              ),
                            ),
                            const SizedBox(height: 24),
                            Container(
                              padding: const EdgeInsets.all(16),
                              decoration: BoxDecoration(
                                color: AppColors.surfaceVariant,
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: AppColors.border),
                              ),
                              child: const Row(
                                children: [
                                  Icon(Icons.bookmark_added_rounded, size: 20, color: AppColors.goldDark),
                                  SizedBox(width: 12),
                                  Expanded(
                                    child: Text(
                                      'Vị trí trang đọc này được tự động lưu trữ trên máy chủ và cập nhật vào mục "Đang đọc" trong Tủ sách của bạn.',
                                      style: TextStyle(fontSize: 12, color: AppColors.textSecondary, height: 1.4),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),

                    // Page Footer
                    const Divider(color: AppColors.border, height: 20),
                    Center(
                      child: Text(
                        '- ${provider.currentPage} -',
                        style: const TextStyle(fontSize: 11, color: AppColors.textMuted),
                      ),
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

