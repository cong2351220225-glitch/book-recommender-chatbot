import '../models/location_item_model.dart';
import '../services/api_service.dart';

class LocationRepository {
  final ApiService _apiService;

  LocationRepository({ApiService? apiService})
      : _apiService = apiService ?? ApiService();

  Future<LocationSearchResponseModel> searchLocations({
    required String location,
    String kind = 'all',
    int limit = 10,
  }) async {
    return await _apiService.searchLocations(
      location: location,
      kind: kind,
      limit: limit,
    );
  }
}

