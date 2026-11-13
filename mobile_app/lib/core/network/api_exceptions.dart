import 'package:dio/dio.dart';

class ApiException implements Exception {
  final String message;
  final int? statusCode;
  final dynamic details;

  ApiException({
    required this.message,
    this.statusCode,
    this.details,
  });

  factory ApiException.fromDioException(DioException dioException) {
    switch (dioException.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return ApiException(
          message: 'Hết thời gian chờ kết nối máy chủ. Vui lòng thử lại sau.',
          statusCode: 408,
        );

      case DioExceptionType.badResponse:
        final status = dioException.response?.statusCode;
        final responseData = dioException.response?.data;
        String errorMessage = 'Lỗi máy chủ ($status).';

        if (responseData is Map && responseData.containsKey('detail')) {
          errorMessage = responseData['detail'].toString();
        } else if (responseData is String && responseData.isNotEmpty) {
          errorMessage = responseData;
        }

        switch (status) {
          case 400:
            return ApiException(message: errorMessage, statusCode: 400);
          case 401:
            return ApiException(
              message: 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.',
              statusCode: 401,
            );
          case 403:
            return ApiException(
              message: 'Bạn không có quyền thực hiện thao tác này.',
              statusCode: 403,
            );
          case 404:
            return ApiException(message: errorMessage, statusCode: 404);
          case 500:
            return ApiException(
              message: 'Máy chủ backend gặp lỗi xử lý. Vui lòng thử lại.',
              statusCode: 500,
            );
          default:
            return ApiException(message: errorMessage, statusCode: status);
        }

      case DioExceptionType.connectionError:
        return ApiException(
          message:
              'Không thể kết nối đến máy chủ backend. Vui lòng kiểm tra kết nối mạng hoặc đảm bảo backend FastAPI đang chạy.',
          statusCode: 0,
        );

      case DioExceptionType.cancel:
        return ApiException(message: 'Yêu cầu mạng đã bị hủy.');

      default:
        return ApiException(
          message: dioException.message ?? 'Đã xảy ra lỗi mạng không xác định.',
        );
    }
  }

  @override
  String toString() => message;
}

