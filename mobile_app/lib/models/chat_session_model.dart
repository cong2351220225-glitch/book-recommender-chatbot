class ChatSessionModel {
  final String id;
  final String title;
  final String timestamp;
  final int messageCount;
  final String lastMessage;

  ChatSessionModel({
    required this.id,
    required this.title,
    required this.timestamp,
    this.messageCount = 0,
    this.lastMessage = '',
  });

  factory ChatSessionModel.fromJson(Map<String, dynamic> json) {
    return ChatSessionModel(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? 'Đoạn chat mới',
      timestamp: json['timestamp']?.toString() ?? '',
      messageCount: json['message_count'] as int? ?? 0,
      lastMessage: json['last_message']?.toString() ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'timestamp': timestamp,
      'message_count': messageCount,
      'last_message': lastMessage,
    };
  }
}

