import 'dart:typed_data';
import 'package:dio/dio.dart';
import '../core/constants/api_constants.dart';
import '../core/network/dio_client.dart';
import '../models/book_model.dart';
import '../models/book_list_response.dart';
import '../models/book_vision_model.dart';

class VisionService {
  final DioClient _dioClient;

  VisionService({DioClient? dioClient})
      : _dioClient = dioClient ?? DioClient();

  /// Gửi tệp ảnh bìa lên Backend để Gemini Vision nhận diện tên sách và tác giả
  Future<BookVisionResult> recognizeCover({
    String? filePath,
    Uint8List? fileBytes,
    String? fileName,
  }) async {
    MultipartFile multipartFile;
    final name = fileName ?? (filePath != null ? filePath.split(r'[\/]').last : 'cover.jpg');

    if (filePath != null && filePath.isNotEmpty) {
      multipartFile = await MultipartFile.fromFile(filePath, filename: name);
    } else if (fileBytes != null) {
      multipartFile = MultipartFile.fromBytes(fileBytes, filename: name);
    } else {
      return BookVisionResult(
        success: false,
        isBookCover: false,
        message: 'Không tìm thấy dữ liệu tệp ảnh.',
      );
    }

    final formData = FormData.fromMap({
      'file': multipartFile,
    });

    try {
      final response = await _dioClient.dio.post(
        ApiConstants.recognizeCover,
        data: formData,
        options: Options(
          contentType: 'multipart/form-data',
        ),
      );

      if (response.data is Map<String, dynamic>) {
        return BookVisionResult.fromJson(response.data as Map<String, dynamic>);
      }
      return BookVisionResult(
        success: false,
        isBookCover: false,
        message: 'Dữ liệu phản hồi từ máy chủ không hợp lệ.',
      );
    } catch (e) {
      return BookVisionResult(
        success: false,
        isBookCover: false,
        message: 'Lỗi kết nối khi quét ảnh bìa: ${e.toString()}',
      );
    }
  }

  /// Tìm sách trong thư viện dựa trên tên sách AI vừa nhận diện
  Future<List<BookModel>> searchLibraryBooks(String query) async {
    final cleanQuery = query.trim();
    if (cleanQuery.isEmpty) return [];

    try {
      final response = await _dioClient.get(
        ApiConstants.books,
        queryParameters: {
          'query': cleanQuery,
          'page': 1,
          'size': 6,
        },
      );

      if (response.data is Map<String, dynamic>) {
        final listResponse = BookListResponse.fromJson(response.data as Map<String, dynamic>);
        return listResponse.items;
      }
      return [];
    } catch (e) {
      return [];
    }
  }
}
