import 'dart:async';
import 'dart:io';
import 'package:audioplayers/audioplayers.dart';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:record/record.dart';
import '../core/constants/api_constants.dart';
import '../core/network/dio_client.dart';

enum TtsPlaybackStatus { stopped, loading, playing, paused }

class AudioService extends ChangeNotifier {
  static final AudioService _instance = AudioService._internal();
  factory AudioService() => _instance;

  final DioClient _dioClient;
  final AudioPlayer _audioPlayer;
  final AudioRecorder _audioRecorder;

  // TTS State
  String? _currentSpeakingMessageId;
  TtsPlaybackStatus _ttsStatus = TtsPlaybackStatus.stopped;
  StreamSubscription? _playerStateSubscription;

  // STT State
  bool _isRecording = false;
  String? _lastRecordingPath;

  AudioService._internal({DioClient? dioClient})
      : _dioClient = dioClient ?? DioClient(),
        _audioPlayer = AudioPlayer(),
        _audioRecorder = AudioRecorder() {
    _initPlayerListeners();
  }

  String? get currentSpeakingMessageId => _currentSpeakingMessageId;
  TtsPlaybackStatus get ttsStatus => _ttsStatus;
  bool get isRecording => _isRecording;

  void _initPlayerListeners() {
    _playerStateSubscription = _audioPlayer.onPlayerStateChanged.listen((state) {
      switch (state) {
        case PlayerState.playing:
          _ttsStatus = TtsPlaybackStatus.playing;
          notifyListeners();
          break;
        case PlayerState.paused:
          _ttsStatus = TtsPlaybackStatus.paused;
          notifyListeners();
          break;
        case PlayerState.stopped:
        case PlayerState.completed:
          _ttsStatus = TtsPlaybackStatus.stopped;
          _currentSpeakingMessageId = null;
          notifyListeners();
          break;
        default:
          break;
      }
    });
  }

  // ===================== TEXT-TO-SPEECH (TTS) =====================

  /// Đọc câu trả lời bằng giọng nói tiếng Việt
  Future<void> playTts(String messageId, String text) async {
    // Nếu đang phát cùng một tin nhắn và bị tạm dừng, bấm tiếp sẽ resume
    if (_currentSpeakingMessageId == messageId && _ttsStatus == TtsPlaybackStatus.paused) {
      await resumeTts();
      return;
    }

    // Nếu đang phát tin nhắn khác, dừng tin nhắn đó trước
    if (_ttsStatus != TtsPlaybackStatus.stopped) {
      await stopTts();
    }

    _currentSpeakingMessageId = messageId;
    _ttsStatus = TtsPlaybackStatus.loading;
    notifyListeners();

    try {
      final response = await _dioClient.dio.post(
        ApiConstants.chatTts,
        data: {'text': text, 'lang': 'vi'},
        options: Options(responseType: ResponseType.bytes),
      );

      if (response.data != null && response.data is List<int>) {
        final audioBytes = Uint8List.fromList(response.data as List<int>);
        await _audioPlayer.play(BytesSource(audioBytes));
      } else {
        _ttsStatus = TtsPlaybackStatus.stopped;
        _currentSpeakingMessageId = null;
        notifyListeners();
      }
    } catch (e) {
      debugPrint('[TTS Error] Failed to play speech: $e');
      _ttsStatus = TtsPlaybackStatus.stopped;
      _currentSpeakingMessageId = null;
      notifyListeners();
    }
  }

  /// Tạm dừng đọc
  Future<void> pauseTts() async {
    try {
      await _audioPlayer.pause();
    } catch (e) {
      debugPrint('[TTS Error] Failed to pause: $e');
    }
  }

  /// Tiếp tục đọc
  Future<void> resumeTts() async {
    try {
      await _audioPlayer.resume();
    } catch (e) {
      debugPrint('[TTS Error] Failed to resume: $e');
    }
  }

  /// Dừng đọc hoàn toàn
  Future<void> stopTts() async {
    try {
      await _audioPlayer.stop();
    } catch (e) {
      debugPrint('[TTS Error] Failed to stop: $e');
    } finally {
      _ttsStatus = TtsPlaybackStatus.stopped;
      _currentSpeakingMessageId = null;
      notifyListeners();
    }
  }

  // ===================== SPEECH-TO-TEXT (STT) =====================

  /// Bắt đầu ghi âm từ microphone
  Future<bool> startRecording() async {
    try {
      if (await _audioRecorder.hasPermission()) {
        final tempDir = Directory.systemTemp;
        final filePath = '${tempDir.path}${Platform.pathSeparator}stt_${DateTime.now().millisecondsSinceEpoch}.wav';
        _lastRecordingPath = filePath;

        const config = RecordConfig(
          encoder: AudioEncoder.wav,
          sampleRate: 16000,
          numChannels: 1,
        );

        await _audioRecorder.start(config, path: filePath);
        _isRecording = true;
        notifyListeners();
        return true;
      }
      return false;
    } catch (e) {
      debugPrint('[STT Error] Failed to start recording: $e');
      _isRecording = false;
      notifyListeners();
      return false;
    }
  }

  /// Dừng ghi âm và gửi tệp lên Backend để nhận diện giọng nói tiếng Việt
  Future<String?> stopRecordingAndTranscribe() async {
    if (!_isRecording) return null;

    String? recordedPath;
    try {
      recordedPath = await _audioRecorder.stop();
      _isRecording = false;
      notifyListeners();
    } catch (e) {
      debugPrint('[STT Error] Failed to stop recording: $e');
      _isRecording = false;
      notifyListeners();
      return null;
    }

    final targetPath = recordedPath ?? _lastRecordingPath;
    if (targetPath == null || !File(targetPath).existsSync()) {
      return null;
    }

    try {
      final file = File(targetPath);
      final bytes = await file.readAsBytes();

      if (bytes.isEmpty) {
        return null;
      }

      final formData = FormData.fromMap({
        'file': MultipartFile.fromBytes(bytes, filename: 'recording.wav'),
      });

      final response = await _dioClient.dio.post(
        ApiConstants.transcribeAudio,
        data: formData,
        options: Options(contentType: 'multipart/form-data'),
      );

      // Clean up temporary audio file safely
      try {
        if (file.existsSync()) {
          file.deleteSync();
        }
      } catch (_) {}

      if (response.data is Map<String, dynamic>) {
        final success = response.data['success'] == true;
        final text = (response.data['text'] as String?)?.trim() ?? '';
        if (success && text.isNotEmpty) {
          return text;
        }
      }
      return null;
    } catch (e) {
      debugPrint('[STT Error] Failed to transcribe: $e');
      return null;
    }
  }

  /// Hủy ghi âm không nhận diện
  Future<void> cancelRecording() async {
    if (_isRecording) {
      try {
        final path = await _audioRecorder.stop();
        if (path != null && File(path).existsSync()) {
          File(path).deleteSync();
        }
      } catch (_) {}
      _isRecording = false;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _playerStateSubscription?.cancel();
    _audioPlayer.dispose();
    _audioRecorder.dispose();
    super.dispose();
  }
}
