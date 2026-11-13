import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:cached_network_image/cached_network_image.dart';

import '../../core/constants/app_colors.dart';
import '../../models/book_model.dart';
import '../../models/book_vision_model.dart';
import '../../services/vision_service.dart';
import '../screens/book_detail_screen.dart';

class BookVisionDialog extends StatefulWidget {
  final Function(String query) onSelectBookForChat;

  const BookVisionDialog({
    super.key,
    required this.onSelectBookForChat,
  });

  @override
  State<BookVisionDialog> createState() => _BookVisionDialogState();
}

class _BookVisionDialogState extends State<BookVisionDialog> {
  final VisionService _visionService = VisionService();

  String? _selectedFilePath;
  Uint8List? _selectedFileBytes;
  String? _selectedFileName;

  bool _isAnalyzing = false;
  bool _isSearchingLibrary = false;
  String? _errorMessage;

  BookVisionResult? _visionResult;
  List<BookModel> _matchedBooks = [];

  Future<void> _pickImage() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['jpg', 'jpeg', 'png'],
        withData: true,
      );

      if (result != null && result.files.isNotEmpty) {
        final file = result.files.first;
        setState(() {
          _selectedFilePath = file.path;
          _selectedFileBytes = file.bytes;
          _selectedFileName = file.name;
          _visionResult = null;
          _matchedBooks = [];
          _errorMessage = null;
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Không thể mở hộp thoại chọn tệp: $e';
      });
    }
  }

  void _clearImage() {
    setState(() {
      _selectedFilePath = null;
      _selectedFileBytes = null;
      _selectedFileName = null;
      _visionResult = null;
      _matchedBooks = [];
      _errorMessage = null;
    });
  }

  Future<void> _recognizeAndSearch() async {
    if (_selectedFilePath == null && _selectedFileBytes == null) return;

    setState(() {
      _isAnalyzing = true;
      _errorMessage = null;
      _visionResult = null;
      _matchedBooks = [];
    });

    final result = await _visionService.recognizeCover(
      filePath: _selectedFilePath,
      fileBytes: _selectedFileBytes,
      fileName: _selectedFileName,
    );

    setState(() {
      _isAnalyzing = false;
      _visionResult = result;
    });

    if (result.success && result.isBookCover && result.title != null && result.title!.isNotEmpty) {
      setState(() {
        _isSearchingLibrary = true;
      });

      final books = await _visionService.searchLibraryBooks(result.title!);

      setState(() {
        _isSearchingLibrary = false;
        _matchedBooks = books;
      });
    } else if (!result.success) {
      setState(() {
        _errorMessage = result.message;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 620, maxHeight: 680),
        child: Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: AppColors.navyLight,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.document_scanner_rounded, color: AppColors.navy, size: 22),
                  ),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Tìm Sách Bằng Ảnh Bìa (AI Vision)',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: AppColors.navyDark,
                          ),
                        ),
                        Text(
                          'AI Gemini Vision tự động đọc chữ trên bìa và tìm trong thư viện số.',
                          style: TextStyle(fontSize: 12, color: AppColors.textSecondary),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close_rounded, size: 20),
                    tooltip: 'Đóng',
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              const Divider(height: 1),
              const SizedBox(height: 16),

              // Content Area
              Expanded(
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Image Selector / Preview Area
                      if (_selectedFilePath == null && _selectedFileBytes == null)
                        _buildEmptyPicker()
                      else
                        _buildImagePreview(),

                      // Error message if any
                      if (_errorMessage != null) ...[
                        const SizedBox(height: 12),
                        Container(
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: AppColors.error.withValues(alpha: 0.08),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: AppColors.error.withValues(alpha: 0.3)),
                          ),
                          child: Row(
                            children: [
                              const Icon(Icons.error_outline_rounded, color: AppColors.error, size: 18),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  _errorMessage!,
                                  style: const TextStyle(color: AppColors.error, fontSize: 13),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],

                      // Vision Result Badge
                      if (_visionResult != null && _visionResult!.isBookCover) ...[
                        const SizedBox(height: 16),
                        _buildVisionResultCard(_visionResult!),
                      ],

                      // Matched Books in Library
                      if (_isSearchingLibrary) ...[
                        const SizedBox(height: 16),
                        const Center(
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
                              SizedBox(width: 10),
                              Text('Đang đối chiếu trong kho sách thư viện...', style: TextStyle(fontSize: 13)),
                            ],
                          ),
                        ),
                      ] else if (_visionResult != null && _visionResult!.isBookCover) ...[
                        const SizedBox(height: 16),
                        _buildMatchedBooksList(),
                      ],
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 16),
              const Divider(height: 1),
              const SizedBox(height: 12),

              // Footer Actions
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Đóng'),
                  ),
                  const SizedBox(width: 8),
                  if (_selectedFilePath != null || _selectedFileBytes != null)
                    ElevatedButton.icon(
                      icon: _isAnalyzing
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                            )
                          : const Icon(Icons.search_rounded, size: 18),
                      label: Text(_isAnalyzing ? 'Đang nhận diện...' : 'Nhận diện & tìm sách'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.navy,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                      onPressed: _isAnalyzing ? null : _recognizeAndSearch,
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildEmptyPicker() {
    return InkWell(
      onTap: _pickImage,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        width: double.infinity,
        height: 180,
        decoration: BoxDecoration(
          color: AppColors.surfaceVariant,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.border, style: BorderStyle.solid),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.white,
                shape: BoxShape.circle,
                border: Border.all(color: AppColors.border),
              ),
              child: const Icon(Icons.add_photo_alternate_rounded, size: 32, color: AppColors.navy),
            ),
            const SizedBox(height: 12),
            const Text(
              'Bấm để chọn ảnh bìa sách từ máy tính',
              style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.navyDark),
            ),
            const SizedBox(height: 4),
            const Text(
              'Hỗ trợ tệp định dạng JPG, JPEG hoặc PNG (Tối đa 8 MB)',
              style: TextStyle(fontSize: 12, color: AppColors.textSecondary),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildImagePreview() {
    Widget imageWidget;
    if (_selectedFileBytes != null) {
      imageWidget = Image.memory(_selectedFileBytes!, fit: BoxFit.contain);
    } else if (_selectedFilePath != null) {
      imageWidget = Image.file(File(_selectedFilePath!), fit: BoxFit.contain);
    } else {
      imageWidget = const SizedBox();
    }

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 100,
            height: 140,
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppColors.border),
            ),
            clipBehavior: Clip.antiAlias,
            child: imageWidget,
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _selectedFileName ?? 'Ảnh bìa đã chọn',
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: AppColors.navyDark),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Ảnh đã sẵn sàng. Nhấn "Nhận diện & tìm sách" để AI phân tích tên sách.',
                  style: TextStyle(fontSize: 12, color: AppColors.textSecondary),
                ),
                const SizedBox(height: 14),
                Row(
                  children: [
                    OutlinedButton.icon(
                      icon: const Icon(Icons.refresh_rounded, size: 14),
                      label: const Text('Chọn ảnh khác', style: TextStyle(fontSize: 12)),
                      onPressed: _pickImage,
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      ),
                    ),
                    const SizedBox(width: 8),
                    TextButton.icon(
                      icon: const Icon(Icons.delete_outline_rounded, size: 14, color: AppColors.error),
                      label: const Text('Xóa', style: TextStyle(fontSize: 12, color: AppColors.error)),
                      onPressed: _clearImage,
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildVisionResultCard(BookVisionResult result) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.navyDark,
        borderRadius: BorderRadius.circular(10),
        boxShadow: [
          BoxShadow(
            color: AppColors.gold.withValues(alpha: 0.15),
            blurRadius: 8,
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.auto_awesome, color: AppColors.gold, size: 16),
              const SizedBox(width: 6),
              const Text(
                'AI VISION ĐỌC ĐƯỢC TÊN SÁCH:',
                style: TextStyle(
                  color: AppColors.gold,
                  fontSize: 11,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 0.5,
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  'Độ tin cậy: ${(result.confidence * 100).toInt()}%',
                  style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            result.title ?? 'Không rõ',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
          if (result.author != null && result.author!.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              'Tác giả: ${result.author}',
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.8),
                fontSize: 13,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildMatchedBooksList() {
    if (_matchedBooks.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.amber.shade50,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.amber.shade300),
        ),
        child: Row(
          children: [
            Icon(Icons.info_outline_rounded, color: Colors.amber.shade800, size: 18),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                'Cuốn sách này hiện chưa có sẵn trong thư viện số, nhưng bạn vẫn có thể hỏi Trợ lý AI về tác phẩm này.',
                style: TextStyle(fontSize: 12, color: Colors.amber.shade900),
              ),
            ),
            const SizedBox(width: 8),
            ElevatedButton(
              onPressed: () {
                final title = _visionResult?.title ?? '';
                Navigator.of(context).pop();
                widget.onSelectBookForChat('Hãy tư vấn và tóm tắt cuốn sách: $title');
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.navy,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              ),
              child: const Text('Hỏi AI', style: TextStyle(fontSize: 12)),
            ),
          ],
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'SÁCH TÌM THẤY TRONG THƯ VIỆN (${_matchedBooks.length}):',
              style: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.bold,
                color: AppColors.navyDark,
                letterSpacing: 0.4,
              ),
            ),
            TextButton.icon(
              icon: const Icon(Icons.chat_bubble_outline_rounded, size: 14),
              label: const Text('Hỏi AI về cuốn này', style: TextStyle(fontSize: 11)),
              onPressed: () {
                final firstTitle = _matchedBooks.first.title;
                Navigator.of(context).pop();
                widget.onSelectBookForChat('Hãy giới thiệu chi tiết về cuốn sách $firstTitle trong thư viện.');
              },
            ),
          ],
        ),
        const SizedBox(height: 6),
        ListView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: _matchedBooks.length,
          itemBuilder: (context, index) {
            final book = _matchedBooks[index];
            return Card(
              margin: const EdgeInsets.only(bottom: 8),
              elevation: 0.5,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
                side: const BorderSide(color: AppColors.border),
              ),
              child: ListTile(
                dense: true,
                leading: Container(
                  width: 36,
                  height: 48,
                  decoration: BoxDecoration(
                    color: AppColors.surfaceVariant,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  clipBehavior: Clip.antiAlias,
                  child: book.coverUrl.isNotEmpty
                      ? CachedNetworkImage(
                          imageUrl: book.coverUrl,
                          fit: BoxFit.cover,
                          errorWidget: (_, __, ___) => const Icon(Icons.book_rounded, size: 16),
                        )
                      : const Icon(Icons.book_rounded, size: 16),
                ),
                title: Text(
                  book.title,
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                subtitle: Text(
                  '${book.author} • ${book.genre}',
                  style: const TextStyle(fontSize: 11, color: AppColors.textSecondary),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    IconButton(
                      icon: const Icon(Icons.visibility_rounded, size: 18, color: AppColors.navy),
                      tooltip: 'Xem chi tiết sách',
                      onPressed: () {
                        Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => BookDetailScreen(bookId: book.bookId),
                          ),
                        );
                      },
                    ),
                    IconButton(
                      icon: const Icon(Icons.send_rounded, size: 16, color: AppColors.goldDark),
                      tooltip: 'Tư vấn sách này trong chat',
                      onPressed: () {
                        Navigator.of(context).pop();
                        widget.onSelectBookForChat('Hãy tư vấn cho tôi cuốn sách: ${book.title}');
                      },
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ],
    );
  }
}
