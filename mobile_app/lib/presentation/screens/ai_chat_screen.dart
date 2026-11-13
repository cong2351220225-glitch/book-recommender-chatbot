import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants/app_colors.dart';
import '../../models/chat_session_model.dart';
import '../../providers/chat_provider.dart';
import '../../services/audio_service.dart';
import '../widgets/chat_bubble.dart';
import '../widgets/book_vision_dialog.dart';

class AiChatScreen extends StatefulWidget {
  const AiChatScreen({super.key});

  @override
  State<AiChatScreen> createState() => _AiChatScreenState();
}

class _AiChatScreenState extends State<AiChatScreen> {
  final TextEditingController _inputController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final FocusNode _focusNode = FocusNode();

  final AudioService _audioService = AudioService();
  bool _isRecordingVoice = false;
  bool _isTranscribingVoice = false;

  void _openVisionDialog() {
    showDialog(
      context: context,
      builder: (_) => BookVisionDialog(
        onSelectBookForChat: (query) {
          _inputController.text = query;
          _handleSend();
        },
      ),
    );
  }

  Future<void> _toggleVoiceRecording() async {
    if (_isTranscribingVoice) return;

    if (!_isRecordingVoice) {
      final started = await _audioService.startRecording();
      if (started) {
        setState(() {
          _isRecordingVoice = true;
        });
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Không thể truy cập microphone. Vui lòng kiểm tra quyền trên Windows.'),
              backgroundColor: AppColors.error,
            ),
          );
        }
      }
    } else {
      setState(() {
        _isRecordingVoice = false;
        _isTranscribingVoice = true;
      });

      final transcript = await _audioService.stopRecordingAndTranscribe();

      setState(() {
        _isTranscribingVoice = false;
      });

      if (transcript != null && transcript.isNotEmpty) {
        final currentText = _inputController.text.trim();
        _inputController.text = currentText.isEmpty ? transcript : '$currentText $transcript';
        _inputController.selection = TextSelection.fromPosition(
          TextPosition(offset: _inputController.text.length),
        );
        _focusNode.requestFocus();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Đã nhận diện giọng nói! Bạn có thể chỉnh sửa trước khi gửi.'),
              backgroundColor: AppColors.success,
              duration: Duration(seconds: 3),
            ),
          );
        }
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Không nhận diện được giọng nói hoặc âm thanh quá nhỏ.'),
              duration: Duration(seconds: 2),
            ),
          );
        }
      }
    }
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final chatProvider = context.read<ChatProvider>();
      chatProvider.loadSessions();
      chatProvider.fetchRagConfig();
    });
  }

  @override
  void dispose() {
    _inputController.dispose();
    _scrollController.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _handleSend() {
    final text = _inputController.text.trim();
    if (text.isEmpty) return;

    _inputController.clear();
    final chatProvider = context.read<ChatProvider>();
    chatProvider.sendMessage(text);
    _scrollToBottom();
  }

  @override
  Widget build(BuildContext context) {
    final chatProvider = context.watch<ChatProvider>();
    final messages = chatProvider.messages;
    final isStreaming = chatProvider.isStreaming;

    // Auto-scroll when new content arrives
    if (isStreaming) {
      _scrollToBottom();
    }

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Row(
          children: [
            const Icon(Icons.smart_toy_rounded, size: 20, color: AppColors.gold),
            const SizedBox(width: 8),
            const Text('Trợ Lý AI Thư Viện'),
            const SizedBox(width: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: AppColors.navyLight,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.gold.withValues(alpha: 0.3)),
              ),
              child: Text(
                'Top-K: ${chatProvider.topK}',
                style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.bold,
                  color: AppColors.navyDark,
                ),
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.tune_rounded),
            tooltip: 'Cấu hình AI RAG (Top-K)',
            onPressed: () => _showRagConfigDialog(context, chatProvider),
          ),
          IconButton(
            icon: const Icon(Icons.add_comment_rounded),
            tooltip: 'Đoạn chat mới',
            onPressed: () {
              chatProvider.startNewSession();
            },
          ),
          Builder(
            builder: (ctx) => IconButton(
              icon: const Icon(Icons.history_rounded),
              tooltip: 'Lịch sử trò chuyện',
              onPressed: () {
                chatProvider.loadSessions();
                Scaffold.of(ctx).openEndDrawer();
              },
            ),
          ),
        ],
      ),
      endDrawer: _buildHistoryDrawer(context, chatProvider),
      body: Column(
        children: [
          // Main Messages Area
          Expanded(
            child: chatProvider.isLoadingHistory
                ? const Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        CircularProgressIndicator(strokeWidth: 2.5),
                        SizedBox(height: 12),
                        Text(
                          'Đang tải lại đoạn hội thoại...',
                          style: TextStyle(fontSize: 13, color: AppColors.textSecondary),
                        ),
                      ],
                    ),
                  )
                : messages.isEmpty
                    ? _buildEmptyWelcome(context, chatProvider)
                    : Center(
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 900),
                          child: ListView.builder(
                            controller: _scrollController,
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
                            itemCount: messages.length,
                            itemBuilder: (context, index) {
                              return ChatBubble(message: messages[index]);
                            },
                          ),
                        ),
                      ),
          ),

          // Stop Generation Button Banner
          if (isStreaming)
            Padding(
              padding: const EdgeInsets.only(bottom: 8.0),
              child: Center(
                child: OutlinedButton.icon(
                  icon: const Icon(Icons.stop_circle_outlined, size: 16, color: AppColors.error),
                  label: const Text(
                    'Dừng phản hồi',
                    style: TextStyle(fontSize: 12, color: AppColors.error, fontWeight: FontWeight.bold),
                  ),
                  onPressed: () => chatProvider.stopResponse(),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: AppColors.error),
                    backgroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                  ),
                ),
              ),
            ),

          // Error Banner if present
          if (chatProvider.errorMessage != null && !isStreaming)
            Container(
              color: AppColors.error.withValues(alpha: 0.08),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: Row(
                children: [
                  const Icon(Icons.error_outline_rounded, size: 16, color: AppColors.error),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      chatProvider.errorMessage!,
                      style: const TextStyle(fontSize: 12, color: AppColors.error),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close_rounded, size: 16, color: AppColors.error),
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(),
                    tooltip: 'Đóng thông báo',
                    onPressed: () => chatProvider.clearError(),
                  ),
                ],
              ),
            ),

          // Bottom Input Bar
          _buildInputBar(context, isStreaming),
        ],
      ),
    );
  }

  Widget _buildEmptyWelcome(BuildContext context, ChatProvider chatProvider) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24.0),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 700),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const SizedBox(height: 20),
              Container(
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: AppColors.navyDark,
                  borderRadius: BorderRadius.circular(16),
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.gold.withValues(alpha: 0.15),
                      blurRadius: 16,
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.auto_awesome,
                  size: 40,
                  color: AppColors.gold,
                ),
              ),
              const SizedBox(height: 18),
              const Text(
                'Xin chào! Tôi có thể giúp gì cho bạn?',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: AppColors.navyDark,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Hỏi đáp về ${chatProvider.vectorCount ?? 208} đầu sách, nội dung tác phẩm, tác giả hoặc nhận gợi ý đọc sách cá nhân hóa dựa trên RAG.',
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 13,
                  color: AppColors.textSecondary,
                  height: 1.4,
                ),
              ),
              const SizedBox(height: 28),

              // Suggested Prompt Chips
              const Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  'GỢI Ý CÂU HỎI NHANH:',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                    color: AppColors.goldDark,
                    letterSpacing: 0.5,
                  ),
                ),
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: chatProvider.suggestedPrompts.map((prompt) {
                  return ActionChip(
                    label: Text(prompt),
                    avatar: const Icon(Icons.help_outline_rounded, size: 14, color: AppColors.navy),
                    backgroundColor: Colors.white,
                    side: const BorderSide(color: AppColors.border),
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                    onPressed: () {
                      _inputController.text = prompt;
                      _handleSend();
                    },
                  );
                }).toList(),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildInputBar(BuildContext context, bool isStreaming) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: AppColors.border)),
      ),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 900),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Voice Recording Indicator Bar
              if (_isRecordingVoice)
                Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  decoration: BoxDecoration(
                    color: AppColors.error.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: AppColors.error.withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: 10,
                        height: 10,
                        decoration: const BoxDecoration(
                          color: AppColors.error,
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 8),
                      const Text(
                        'Đang lắng nghe giọng nói tiếng Việt... Bấm biểu tượng mic để hoàn tất.',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: AppColors.error,
                        ),
                      ),
                      const SizedBox(width: 8),
                      InkWell(
                        onTap: () {
                          _audioService.cancelRecording();
                          setState(() => _isRecordingVoice = false);
                        },
                        child: const Icon(Icons.close_rounded, size: 16, color: AppColors.error),
                      ),
                    ],
                  ),
                ),

              // Main Input Row
              Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  // Book Cover Vision Button
                  Container(
                    height: 46,
                    width: 46,
                    margin: const EdgeInsets.only(right: 8),
                    decoration: BoxDecoration(
                      color: AppColors.surfaceVariant,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppColors.border),
                    ),
                    child: IconButton(
                      icon: const Icon(Icons.document_scanner_rounded, color: AppColors.navy, size: 22),
                      tooltip: 'Tìm sách bằng ảnh bìa (AI Vision)',
                      onPressed: isStreaming ? null : _openVisionDialog,
                    ),
                  ),

                  // Microphone Button (Voice STT)
                  Container(
                    height: 46,
                    width: 46,
                    margin: const EdgeInsets.only(right: 8),
                    decoration: BoxDecoration(
                      color: _isRecordingVoice
                          ? AppColors.error
                          : AppColors.surfaceVariant,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: _isRecordingVoice ? AppColors.error : AppColors.border,
                      ),
                    ),
                    child: _isTranscribingVoice
                        ? const Center(
                            child: SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.navy),
                            ),
                          )
                        : IconButton(
                            icon: Icon(
                              _isRecordingVoice ? Icons.mic_rounded : Icons.mic_none_rounded,
                              color: _isRecordingVoice ? Colors.white : AppColors.navy,
                              size: 22,
                            ),
                            tooltip: _isRecordingVoice
                                ? 'Đang ghi âm... Bấm để dừng và nhận diện'
                                : 'Nhập câu hỏi bằng giọng nói (Tiếng Việt)',
                            onPressed: isStreaming ? null : _toggleVoiceRecording,
                          ),
                  ),

                  // Text Field
                  Expanded(
                    child: Container(
                      decoration: BoxDecoration(
                        color: AppColors.surfaceVariant,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: AppColors.border),
                      ),
                      child: TextField(
                        controller: _inputController,
                        focusNode: _focusNode,
                        minLines: 1,
                        maxLines: 4,
                        textInputAction: TextInputAction.send,
                        onSubmitted: (_) => _handleSend(),
                        decoration: const InputDecoration(
                          hintText: 'Hỏi về sách, so sánh sách, tìm thư viện hoặc nói vào mic...',
                          hintStyle: TextStyle(fontSize: 13, color: AppColors.textMuted),
                          border: InputBorder.none,
                          enabledBorder: InputBorder.none,
                          focusedBorder: InputBorder.none,
                          contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),

                  // Send Button
                  Container(
                    height: 46,
                    width: 46,
                    decoration: BoxDecoration(
                      color: isStreaming ? AppColors.textMuted : AppColors.navy,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: IconButton(
                      icon: const Icon(Icons.send_rounded, color: Colors.white, size: 20),
                      onPressed: isStreaming ? null : _handleSend,
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

  Widget _buildHistoryDrawer(BuildContext context, ChatProvider chatProvider) {
    final sessions = chatProvider.sessions;
    final currentSessionId = chatProvider.sessionId;

    return Drawer(
      width: 360,
      backgroundColor: Colors.white,
      child: SafeArea(
        child: Column(
          children: [
            // Header
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 8, 12),
              child: Row(
                children: [
                  const Icon(Icons.history_rounded, color: AppColors.navyDark, size: 22),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: Text(
                      'Lịch sử trò chuyện',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: AppColors.navyDark,
                      ),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close_rounded, size: 20),
                    tooltip: 'Đóng',
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
            ),

            // New Chat Button
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              child: SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  icon: const Icon(Icons.add_rounded, size: 18, color: AppColors.navy),
                  label: const Text(
                    'Tạo phiên chat mới',
                    style: TextStyle(fontWeight: FontWeight.bold, color: AppColors.navy),
                  ),
                  onPressed: () {
                    chatProvider.startNewSession();
                    Navigator.pop(context);
                  },
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: AppColors.navy),
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                ),
              ),
            ),

            const Divider(height: 20, color: AppColors.border),

            // Session List
            Expanded(
              child: chatProvider.isLoadingSessions
                  ? const Center(child: CircularProgressIndicator(strokeWidth: 2))
                  : sessions.isEmpty
                      ? Center(
                          child: Padding(
                            padding: const EdgeInsets.all(24.0),
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.forum_outlined, size: 48, color: AppColors.textMuted.withValues(alpha: 0.5)),
                                const SizedBox(height: 12),
                                const Text(
                                  'Chưa có lịch sử trò chuyện',
                                  style: TextStyle(
                                    fontWeight: FontWeight.bold,
                                    fontSize: 14,
                                    color: AppColors.textSecondary,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                const Text(
                                  'Các câu hỏi của bạn sẽ tự động lưu lại ở đây.',
                                  textAlign: TextAlign.center,
                                  style: TextStyle(fontSize: 12, color: AppColors.textMuted),
                                ),
                              ],
                            ),
                          ),
                        )
                      : ListView.separated(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          itemCount: sessions.length,
                          separatorBuilder: (_, __) => const SizedBox(height: 8),
                          itemBuilder: (context, index) {
                            final session = sessions[index];
                            final isCurrent = currentSessionId == session.id;

                            return Container(
                              decoration: BoxDecoration(
                                color: isCurrent ? AppColors.goldLight.withValues(alpha: 0.15) : Colors.white,
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(
                                  color: isCurrent ? AppColors.gold : AppColors.border,
                                  width: isCurrent ? 1.5 : 1,
                                ),
                              ),
                              child: InkWell(
                                borderRadius: BorderRadius.circular(10),
                                onTap: () {
                                  chatProvider.selectSession(session.id);
                                  Navigator.pop(context);
                                },
                                child: Padding(
                                  padding: const EdgeInsets.all(12),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        children: [
                                          Icon(
                                            isCurrent ? Icons.chat_rounded : Icons.chat_bubble_outline_rounded,
                                            size: 16,
                                            color: isCurrent ? AppColors.goldDark : AppColors.navy,
                                          ),
                                          const SizedBox(width: 8),
                                          Expanded(
                                            child: Text(
                                              session.title,
                                              maxLines: 1,
                                              overflow: TextOverflow.ellipsis,
                                              style: TextStyle(
                                                fontWeight: FontWeight.bold,
                                                fontSize: 13,
                                                color: isCurrent ? AppColors.navyDark : AppColors.textPrimary,
                                              ),
                                            ),
                                          ),
                                          IconButton(
                                            icon: const Icon(Icons.delete_outline_rounded, size: 18, color: AppColors.error),
                                            tooltip: 'Xóa đoạn chat',
                                            padding: EdgeInsets.zero,
                                            constraints: const BoxConstraints(),
                                            onPressed: () => _confirmDeleteSession(context, chatProvider, session),
                                          ),
                                        ],
                                      ),
                                      const SizedBox(height: 6),
                                      Text(
                                        session.lastMessage.isNotEmpty ? session.lastMessage : 'Chưa có nội dung',
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: const TextStyle(
                                          fontSize: 11,
                                          color: AppColors.textSecondary,
                                        ),
                                      ),
                                      const SizedBox(height: 8),
                                      Row(
                                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                        children: [
                                          Text(
                                            '🕒 ${session.timestamp}',
                                            style: const TextStyle(
                                              fontSize: 10,
                                              color: AppColors.textMuted,
                                            ),
                                          ),
                                          Container(
                                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                            decoration: BoxDecoration(
                                              color: AppColors.navyLight,
                                              borderRadius: BorderRadius.circular(10),
                                            ),
                                            child: Text(
                                              '${session.messageCount} tin nhắn',
                                              style: const TextStyle(
                                                fontSize: 9,
                                                fontWeight: FontWeight.bold,
                                                color: AppColors.navy,
                                              ),
                                            ),
                                          ),
                                        ],
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            );
                          },
                        ),
            ),
          ],
        ),
      ),
    );
  }

  void _confirmDeleteSession(BuildContext context, ChatProvider chatProvider, ChatSessionModel session) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.warning_amber_rounded, color: AppColors.error, size: 22),
            SizedBox(width: 8),
            Text('Xóa đoạn chat?'),
          ],
        ),
        content: Text(
          'Bạn có chắc chắn muốn xóa đoạn chat "${session.title}" không? Thao tác này sẽ xóa vĩnh viễn tệp hội thoại và không thể hoàn tác.',
          style: const TextStyle(fontSize: 13, height: 1.4),
        ),
        actions: [
          TextButton(
            child: const Text('Hủy'),
            onPressed: () => Navigator.pop(ctx),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.error,
              foregroundColor: Colors.white,
            ),
            onPressed: () async {
              final messenger = ScaffoldMessenger.of(context);
              Navigator.pop(ctx);
              final ok = await chatProvider.deleteSession(session.id);
              messenger.showSnackBar(
                SnackBar(
                  content: Text(ok ? 'Đã xóa đoạn chat thành công.' : 'Không thể xóa đoạn chat.'),
                  backgroundColor: ok ? AppColors.navy : AppColors.error,
                ),
              );
            },
            child: const Text('Xóa vĩnh viễn'),
          ),
        ],
      ),
    );
  }

  void _showRagConfigDialog(BuildContext context, ChatProvider chatProvider) {
    // Refresh real ChromaDB vector count upon dialog open
    chatProvider.fetchRagConfig();

    int tempTopK = chatProvider.topK;

    showDialog(
      context: context,
      builder: (dialogCtx) => StatefulBuilder(
        builder: (context, setDialogState) {
          final isConfigLoading = chatProvider.isLoadingConfig;
          final configError = chatProvider.configError;
          final vectorCount = chatProvider.vectorCount;

          return AlertDialog(
            title: const Row(
              children: [
                Icon(Icons.tune_rounded, color: AppColors.navyDark),
                SizedBox(width: 8),
                Text('Cấu hình AI RAG & Grounding'),
              ],
            ),
            content: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Vector Database Info Card
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: configError != null
                          ? AppColors.error.withValues(alpha: 0.08)
                          : AppColors.surfaceVariant,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: configError != null
                            ? AppColors.error.withValues(alpha: 0.4)
                            : AppColors.gold.withValues(alpha: 0.5),
                      ),
                    ),
                    child: isConfigLoading
                        ? const Row(
                            children: [
                              SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              ),
                              SizedBox(width: 10),
                              Text(
                                'Đang kiểm tra Vector Database...',
                                style: TextStyle(fontSize: 12, color: AppColors.textSecondary),
                              ),
                            ],
                          )
                        : configError != null
                            ? Row(
                                children: [
                                  const Icon(Icons.cloud_off_rounded, color: AppColors.error, size: 20),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      configError,
                                      style: const TextStyle(fontSize: 11, color: AppColors.error),
                                    ),
                                  ),
                                  IconButton(
                                    icon: const Icon(Icons.refresh_rounded, size: 18),
                                    onPressed: () {
                                      chatProvider.fetchRagConfig();
                                      setDialogState(() {});
                                    },
                                  ),
                                ],
                              )
                            : Row(
                                children: [
                                  const Icon(Icons.storage_rounded, color: AppColors.goldDark, size: 24),
                                  const SizedBox(width: 10),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          'Vector Database: $vectorCount bản ghi ChromaDB',
                                          style: const TextStyle(
                                            fontWeight: FontWeight.bold,
                                            fontSize: 13,
                                            color: AppColors.navyDark,
                                          ),
                                        ),
                                        const SizedBox(height: 2),
                                        const Text(
                                          'Collection: books_collection (Thư viện số)',
                                          style: TextStyle(fontSize: 11, color: AppColors.textSecondary),
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                  ),

                  const SizedBox(height: 20),

                  // Top-K Slider
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Số sách Top-K truy xuất:',
                        style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                        decoration: BoxDecoration(
                          color: AppColors.navyDark,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          '$tempTopK',
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                            fontSize: 14,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Slider(
                    value: tempTopK.toDouble(),
                    min: 1,
                    max: 10,
                    divisions: 9,
                    label: '$tempTopK',
                    activeColor: AppColors.gold,
                    inactiveColor: AppColors.border,
                    onChanged: (val) {
                      setDialogState(() {
                        tempTopK = val.round();
                      });
                    },
                  ),
                  const Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('1 (Chính xác cao)', style: TextStyle(fontSize: 10, color: AppColors.textMuted)),
                      Text('10 (Bao quát ngữ cảnh)', style: TextStyle(fontSize: 10, color: AppColors.textMuted)),
                    ],
                  ),

                  const SizedBox(height: 12),
                  const Text(
                    'Tham số Top-K xác định số lượng tài liệu sách phù hợp nhất được RAG Engine truy xuất từ ChromaDB để làm ngữ cảnh trả lời.',
                    style: TextStyle(fontSize: 11, color: AppColors.textSecondary, height: 1.4),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogCtx),
                child: const Text('Hủy'),
              ),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.navy,
                  foregroundColor: Colors.white,
                ),
                onPressed: () {
                  chatProvider.setTopK(tempTopK);
                  Navigator.pop(dialogCtx);
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text('Đã cập nhật cấu hình RAG: Top-K = $tempTopK'),
                      backgroundColor: AppColors.navy,
                    ),
                  );
                },
                child: const Text('Lưu cấu hình'),
              ),
            ],
          );
        },
      ),
    );
  }
}
