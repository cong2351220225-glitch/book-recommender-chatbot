import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../../core/constants/app_colors.dart';
import '../../core/utils/url_launcher_helper.dart';
import '../../models/chat_message_model.dart';
import '../../models/location_item_model.dart';
import '../../services/audio_service.dart';
import '../screens/book_detail_screen.dart';
import 'markdown_table_view.dart';

class ChatBubble extends StatelessWidget {
  final ChatMessageModel message;

  const ChatBubble({super.key, required this.message});

  @override
  Widget build(BuildContext context) {
    final isUser = message.isUser;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!isUser) ...[
            Container(
              padding: const EdgeInsets.all(7),
              decoration: const BoxDecoration(
                color: AppColors.navyDark,
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.auto_awesome,
                size: 16,
                color: AppColors.gold,
              ),
            ),
            const SizedBox(width: 8),
          ],
          Flexible(
            child: Column(
              crossAxisAlignment: isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
              children: [
                // Sender label & time
                Padding(
                  padding: const EdgeInsets.only(bottom: 4.0),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        isUser ? 'Bạn' : 'Trợ lý Thư viện AI',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: isUser ? AppColors.navy : AppColors.goldDark,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        message.timestamp,
                        style: const TextStyle(
                          fontSize: 10,
                          color: AppColors.textMuted,
                        ),
                      ),
                    ],
                  ),
                ),

                // Main Message Content Box
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  decoration: BoxDecoration(
                    color: isUser ? AppColors.navy : Colors.white,
                    borderRadius: BorderRadius.only(
                      topLeft: const Radius.circular(14),
                      topRight: const Radius.circular(14),
                      bottomLeft: Radius.circular(isUser ? 14 : 2),
                      bottomRight: Radius.circular(isUser ? 2 : 14),
                    ),
                    border: Border.all(
                      color: isUser
                          ? AppColors.navy
                          : (message.hasError ? AppColors.error.withOpacity(0.4) : AppColors.border),
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.04),
                        blurRadius: 4,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Thinking indicator
                      if (!isUser && message.isStreaming && message.content.isEmpty)
                        const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            SizedBox(
                              width: 14,
                              height: 14,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                valueColor: AlwaysStoppedAnimation<Color>(AppColors.gold),
                              ),
                            ),
                            SizedBox(width: 8),
                            Text(
                              'Đang suy nghĩ & tìm kiếm...',
                              style: TextStyle(
                                fontSize: 13,
                                fontStyle: FontStyle.italic,
                                color: AppColors.textSecondary,
                              ),
                            ),
                          ],
                        )
                      else
                        MarkdownTableView(
                          content: message.content,
                          isUser: isUser,
                        ),

                      // Streaming typing indicator dot
                      if (!isUser && message.isStreaming && message.content.isNotEmpty) ...[
                        const SizedBox(height: 6),
                        Container(
                          width: 8,
                          height: 8,
                          decoration: const BoxDecoration(
                            color: AppColors.gold,
                            shape: BoxShape.circle,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),

                // TTS Audio Controls (Assistant messages only)
                if (!isUser && !message.isStreaming && message.content.isNotEmpty && !message.hasError) ...[
                  const SizedBox(height: 6),
                  _buildTtsControlBar(context),
                ],

                // Retrieved Sources (RAG Books)
                if (message.sources.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  _buildSourcesList(context, message.sources),
                ],

                // Retrieved Locations (Bookstores & Libraries on Google Maps)
                if (message.locations.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  _buildLocationsList(context, message.locations),
                ],
              ],
            ),
          ),
          if (isUser) ...[
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.all(7),
              decoration: BoxDecoration(
                color: AppColors.navy.withOpacity(0.12),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.person_rounded,
                size: 16,
                color: AppColors.navy,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildTtsControlBar(BuildContext context) {
    final audioService = AudioService();

    return ListenableBuilder(
      listenable: audioService,
      builder: (context, _) {
        final isSpeakingThis = audioService.currentSpeakingMessageId == message.id;
        final status = isSpeakingThis ? audioService.ttsStatus : TtsPlaybackStatus.stopped;

        if (status == TtsPlaybackStatus.loading) {
          return Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: AppColors.surfaceVariant,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppColors.border),
            ),
            child: const Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                SizedBox(
                  width: 12,
                  height: 12,
                  child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.goldDark),
                ),
                SizedBox(width: 8),
                Text(
                  'Đang chuẩn bị giọng đọc...',
                  style: TextStyle(fontSize: 11, color: AppColors.textSecondary),
                ),
              ],
            ),
          );
        }

        if (status == TtsPlaybackStatus.playing || status == TtsPlaybackStatus.paused) {
          final isPlaying = status == TtsPlaybackStatus.playing;
          return Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: AppColors.navyLight,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppColors.gold.withValues(alpha: 0.3)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  isPlaying ? Icons.graphic_eq_rounded : Icons.pause_circle_outline_rounded,
                  size: 16,
                  color: AppColors.navy,
                ),
                const SizedBox(width: 6),
                Text(
                  isPlaying ? 'Đang đọc...' : 'Đã tạm dừng',
                  style: const TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                    color: AppColors.navyDark,
                  ),
                ),
                const SizedBox(width: 8),
                // Pause / Resume button
                InkWell(
                  onTap: () {
                    if (isPlaying) {
                      audioService.pauseTts();
                    } else {
                      audioService.resumeTts();
                    }
                  },
                  borderRadius: BorderRadius.circular(12),
                  child: Padding(
                    padding: const EdgeInsets.all(2.0),
                    child: Icon(
                      isPlaying ? Icons.pause_rounded : Icons.play_arrow_rounded,
                      size: 18,
                      color: AppColors.navy,
                    ),
                  ),
                ),
                const SizedBox(width: 4),
                // Stop button
                InkWell(
                  onTap: () => audioService.stopTts(),
                  borderRadius: BorderRadius.circular(12),
                  child: Padding(
                    padding: const EdgeInsets.all(2.0),
                    child: const Icon(
                      Icons.stop_rounded,
                      size: 18,
                      color: AppColors.error,
                    ),
                  ),
                ),
              ],
            ),
          );
        }

        // Idle state: Play button
        return InkWell(
          onTap: () => audioService.playTts(message.id, message.content),
          borderRadius: BorderRadius.circular(14),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: AppColors.border),
            ),
            child: const Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.volume_up_rounded, size: 14, color: AppColors.navy),
                SizedBox(width: 4),
                Text(
                  'Đọc câu trả lời',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: AppColors.navy,
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildSourcesList(BuildContext context, List<ChatSourceBook> sources) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Row(
          children: [
            Icon(Icons.auto_stories_rounded, size: 13, color: AppColors.goldDark),
            SizedBox(width: 4),
            Text(
              'TÀI LIỆU THAM KHẢO TRONG KHO (RAG):',
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w800,
                color: AppColors.goldDark,
                letterSpacing: 0.4,
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        SizedBox(
          height: 100,
          child: ListView.builder(
            scrollDirection: Axis.horizontal,
            itemCount: sources.length,
            itemBuilder: (context, index) {
              final book = sources[index];
              return Container(
                width: 220,
                margin: const EdgeInsets.only(right: 8),
                child: Card(
                  elevation: 1,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                    side: const BorderSide(color: AppColors.border),
                  ),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(8),
                    onTap: () {
                      if (book.id.isNotEmpty) {
                        Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => BookDetailScreen(bookId: book.id),
                          ),
                        );
                      }
                    },
                    child: Padding(
                      padding: const EdgeInsets.all(8.0),
                      child: Row(
                        children: [
                          Container(
                            width: 50,
                            height: 75,
                            decoration: BoxDecoration(
                              color: AppColors.surfaceVariant,
                              borderRadius: BorderRadius.circular(4),
                            ),
                            clipBehavior: Clip.antiAlias,
                            child: book.coverUrl.isNotEmpty
                                ? CachedNetworkImage(
                                    imageUrl: book.coverUrl,
                                    fit: BoxFit.cover,
                                    errorWidget: (_, __, ___) => const Icon(
                                      Icons.book_rounded,
                                      size: 20,
                                      color: AppColors.navy,
                                    ),
                                  )
                                : const Icon(
                                    Icons.book_rounded,
                                    size: 20,
                                    color: AppColors.navy,
                                  ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Text(
                                  book.title,
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                    color: AppColors.navyDark,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  book.author,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                    fontSize: 10,
                                    color: AppColors.textSecondary,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                if (book.genre.isNotEmpty)
                                  Text(
                                    book.genre,
                                    style: const TextStyle(
                                      fontSize: 9,
                                      fontWeight: FontWeight.w600,
                                      color: AppColors.navy,
                                    ),
                                  ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _buildLocationsList(BuildContext context, List<LocationItemModel> locations) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Row(
          children: [
            Icon(Icons.location_on_rounded, size: 14, color: AppColors.goldDark),
            SizedBox(width: 4),
            Text(
              'ĐỊA ĐIỂM TÌM THẤY TRÊN GOOGLE MAPS:',
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w800,
                color: AppColors.goldDark,
                letterSpacing: 0.4,
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        SizedBox(
          height: 185,
          child: ListView.builder(
            scrollDirection: Axis.horizontal,
            itemCount: locations.length,
            itemBuilder: (context, index) {
              final loc = locations[index];
              return Container(
                width: 295,
                margin: const EdgeInsets.only(right: 10),
                child: Card(
                  elevation: 1.5,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10),
                    side: const BorderSide(color: AppColors.border),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(10.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        // Details Section
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            // Title
                            Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Icon(
                                  Icons.store_mall_directory_rounded,
                                  size: 16,
                                  color: AppColors.navy,
                                ),
                                const SizedBox(width: 6),
                                Expanded(
                                  child: Text(
                                    loc.title,
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                      fontSize: 12,
                                      fontWeight: FontWeight.bold,
                                      color: AppColors.navyDark,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 3),
                            // Address
                            if (loc.address.isNotEmpty)
                              Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Icon(
                                    Icons.place_outlined,
                                    size: 13,
                                    color: AppColors.textMuted,
                                  ),
                                  const SizedBox(width: 4),
                                  Expanded(
                                    child: Text(
                                      loc.address,
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(
                                        fontSize: 10,
                                        color: AppColors.textSecondary,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            const SizedBox(height: 3),
                            // Rating & Open state
                            Row(
                              children: [
                                if (loc.rating > 0) ...[
                                  const Icon(Icons.star_rounded, size: 14, color: AppColors.goldDark),
                                  const SizedBox(width: 2),
                                  Text(
                                    '${loc.rating}',
                                    style: const TextStyle(
                                      fontSize: 11,
                                      fontWeight: FontWeight.bold,
                                      color: AppColors.navyDark,
                                    ),
                                  ),
                                  if (loc.reviews > 0)
                                    Text(
                                      ' (${loc.reviews})',
                                      style: const TextStyle(
                                        fontSize: 10,
                                        color: AppColors.textMuted,
                                      ),
                                    ),
                                  const SizedBox(width: 8),
                                ],
                                if (loc.openState.isNotEmpty)
                                  Expanded(
                                    child: Text(
                                      loc.openState,
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: TextStyle(
                                        fontSize: 10,
                                        fontWeight: FontWeight.w600,
                                        color: loc.openState.toLowerCase().contains('mở')
                                            ? Colors.green[700]
                                            : AppColors.textSecondary,
                                      ),
                                    ),
                                  ),
                              ],
                            ),
                            // Phone (identical to Web)
                            if (loc.phone.isNotEmpty) ...[
                              const SizedBox(height: 3),
                              Row(
                                children: [
                                  const Icon(
                                    Icons.phone_outlined,
                                    size: 12,
                                    color: AppColors.textMuted,
                                  ),
                                  const SizedBox(width: 4),
                                  Expanded(
                                    child: Text(
                                      loc.phone,
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(
                                        fontSize: 10,
                                        color: AppColors.navy,
                                        fontWeight: FontWeight.w500,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ],
                        ),
                        // Action buttons
                        Row(
                          children: [
                            if (loc.googleMapsUrl.isNotEmpty)
                              Expanded(
                                child: OutlinedButton.icon(
                                  onPressed: () {
                                    UrlLauncherHelper.launchUrlString(loc.googleMapsUrl);
                                  },
                                  icon: const Icon(Icons.map_rounded, size: 13),
                                  label: const Text(
                                    'Maps',
                                    style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold),
                                  ),
                                  style: OutlinedButton.styleFrom(
                                    padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
                                    minimumSize: const Size(0, 28),
                                    foregroundColor: AppColors.navy,
                                    side: const BorderSide(color: AppColors.navy, width: 0.8),
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(6),
                                    ),
                                  ),
                                ),
                              ),
                            if (loc.directionsUrl.isNotEmpty) ...[
                              const SizedBox(width: 4),
                              Expanded(
                                child: ElevatedButton.icon(
                                  onPressed: () {
                                    UrlLauncherHelper.launchUrlString(loc.directionsUrl);
                                  },
                                  icon: const Icon(Icons.directions_rounded, size: 13),
                                  label: const Text(
                                    'Chỉ đường',
                                    style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold),
                                  ),
                                  style: ElevatedButton.styleFrom(
                                    padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
                                    minimumSize: const Size(0, 28),
                                    backgroundColor: AppColors.navy,
                                    foregroundColor: Colors.white,
                                    elevation: 0,
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(6),
                                    ),
                                  ),
                                ),
                              ),
                            ],
                            if (loc.website.isNotEmpty) ...[
                              const SizedBox(width: 4),
                              IconButton(
                                onPressed: () {
                                  UrlLauncherHelper.launchUrlString(loc.website);
                                },
                                icon: const Icon(Icons.language_rounded, size: 14),
                                tooltip: 'Website',
                                style: IconButton.styleFrom(
                                  padding: const EdgeInsets.all(4),
                                  minimumSize: const Size(28, 28),
                                  foregroundColor: AppColors.navy,
                                  backgroundColor: AppColors.navy.withOpacity(0.08),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(6),
                                  ),
                                ),
                              ),
                            ],
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
    );
  }
}
