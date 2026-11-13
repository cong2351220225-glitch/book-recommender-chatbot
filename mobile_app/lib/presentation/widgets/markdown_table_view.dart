import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import '../../core/constants/app_colors.dart';

class MarkdownTableView extends StatelessWidget {
  final String content;
  final bool isUser;

  const MarkdownTableView({
    super.key,
    required this.content,
    this.isUser = false,
  });

  bool _isTableLine(String line) {
    final trimmed = line.trim();
    return trimmed.startsWith('|') && trimmed.endsWith('|');
  }

  List<_ContentBlock> _parseBlocks(String text) {
    final blocks = <_ContentBlock>[];
    final lines = text.split('\n');

    final currentLines = <String>[];
    bool inTable = false;

    for (final line in lines) {
      final isTable = _isTableLine(line);
      if (isTable != inTable) {
        if (currentLines.isNotEmpty) {
          blocks.add(_ContentBlock(
            text: currentLines.join('\n'),
            isTable: inTable,
          ));
          currentLines.clear();
        }
        inTable = isTable;
      }
      currentLines.add(line);
    }

    if (currentLines.isNotEmpty) {
      blocks.add(_ContentBlock(
        text: currentLines.join('\n'),
        isTable: inTable,
      ));
    }

    return blocks;
  }

  @override
  Widget build(BuildContext context) {
    if (isUser) {
      return SelectableText(
        content,
        style: const TextStyle(
          fontSize: 14,
          height: 1.5,
          color: Colors.white,
        ),
      );
    }

    final blocks = _parseBlocks(content);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: blocks.map((block) {
        if (block.isTable) {
          return Container(
            margin: const EdgeInsets.symmetric(vertical: 8),
            decoration: BoxDecoration(
              color: Colors.grey.shade50,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppColors.border),
            ),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                child: MarkdownBody(
                  data: block.text,
                  selectable: true,
                  styleSheet: _buildStyleSheet(isTable: true),
                ),
              ),
            ),
          );
        } else {
          return Padding(
            padding: const EdgeInsets.only(bottom: 4.0),
            child: MarkdownBody(
              data: block.text,
              selectable: true,
              styleSheet: _buildStyleSheet(isTable: false),
            ),
          );
        }
      }).toList(),
    );
  }

  MarkdownStyleSheet _buildStyleSheet({required bool isTable}) {
    return MarkdownStyleSheet(
      p: const TextStyle(
        fontSize: 14,
        height: 1.5,
        color: AppColors.textPrimary,
      ),
      strong: const TextStyle(
        fontWeight: FontWeight.bold,
        color: AppColors.navyDark,
      ),
      h1: const TextStyle(
        fontSize: 18,
        fontWeight: FontWeight.bold,
        color: AppColors.navyDark,
      ),
      h2: const TextStyle(
        fontSize: 16,
        fontWeight: FontWeight.bold,
        color: AppColors.navyDark,
      ),
      h3: const TextStyle(
        fontSize: 15,
        fontWeight: FontWeight.bold,
        color: AppColors.navyDark,
      ),
      listBullet: const TextStyle(
        fontSize: 14,
        color: AppColors.goldDark,
      ),
      blockquote: const TextStyle(
        fontSize: 13,
        fontStyle: FontStyle.italic,
        color: AppColors.textSecondary,
      ),
      blockquoteDecoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        border: const Border(
          left: BorderSide(color: AppColors.gold, width: 3),
        ),
        borderRadius: BorderRadius.circular(4),
      ),
      tableBorder: TableBorder.all(
        color: AppColors.border,
        width: 1,
        borderRadius: BorderRadius.circular(6),
      ),
      tableHead: const TextStyle(
        fontSize: 13,
        fontWeight: FontWeight.bold,
        color: AppColors.navyDark,
      ),
      tableBody: const TextStyle(
        fontSize: 13,
        height: 1.4,
        color: AppColors.textPrimary,
      ),
      tableHeadAlign: TextAlign.center,
      tablePadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      tableColumnWidth: const IntrinsicColumnWidth(),
    );
  }
}

class _ContentBlock {
  final String text;
  final bool isTable;

  _ContentBlock({required this.text, required this.isTable});
}
