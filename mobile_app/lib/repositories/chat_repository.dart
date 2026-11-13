import 'package:dio/dio.dart';
import '../models/chat_message_model.dart';
import '../models/chat_session_model.dart';
import '../models/location_item_model.dart';
import '../models/rag_config_model.dart';
import '../services/api_service.dart';

class ChatRepository {
  final ApiService _apiService;

  ChatRepository({ApiService? apiService})
      : _apiService = apiService ?? ApiService();

  Future<Map<String, dynamic>> sendMessage({
    required String message,
    String? sessionId,
    int topK = 3,
    Map<String, dynamic>? readerProfile,
  }) async {
    return await _apiService.sendChatMessage(
      message: message,
      sessionId: sessionId,
      topK: topK,
      readerProfile: readerProfile,
    );
  }

  Future<void> streamMessage({
    required String message,
    String? sessionId,
    int topK = 3,
    Map<String, dynamic>? readerProfile,
    required Function(String chunk) onChunk,
    required Function(
      String fullAnswer,
      List<ChatSourceBook> sources,
      List<LocationItemModel> locations,
      String intent,
      String sessionId,
    ) onDone,
    required Function(String error) onError,
    CancelToken? cancelToken,
  }) async {
    await _apiService.sendChatMessageStream(
      message: message,
      sessionId: sessionId,
      topK: topK,
      readerProfile: readerProfile,
      onChunk: onChunk,
      onDone: onDone,
      onError: onError,
      cancelToken: cancelToken,
    );
  }

  Future<List<ChatMessageModel>> getHistory(String sessionId) async {
    return await _apiService.getChatHistory(sessionId);
  }

  Future<List<ChatSessionModel>> getSessions() async {
    return await _apiService.getChatSessions();
  }

  Future<bool> deleteSession(String sessionId) async {
    return await _apiService.deleteChatSession(sessionId);
  }

  Future<RagConfigModel> getRagConfig() async {
    return await _apiService.getRagConfig();
  }
}
