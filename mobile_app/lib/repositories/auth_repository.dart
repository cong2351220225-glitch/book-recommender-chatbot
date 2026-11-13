import '../core/storage/auth_storage.dart';
import '../models/user_model.dart';
import '../services/api_service.dart';

class AuthRepository {
  final ApiService _apiService;
  final AuthStorage _authStorage;

  AuthRepository({
    ApiService? apiService,
    AuthStorage? authStorage,
  })  : _apiService = apiService ?? ApiService(),
        _authStorage = authStorage ?? AuthStorage();

  Future<UserModel> register(String username, String password) async {
    final user = await _apiService.register(username, password);
    if (user.token != null && user.token!.isNotEmpty) {
      await _authStorage.saveToken(user.token!);
      await _authStorage.saveUser(user);
    }
    return user;
  }

  Future<UserModel> login(String username, String password) async {
    final user = await _apiService.login(username, password);
    if (user.token != null && user.token!.isNotEmpty) {
      await _authStorage.saveToken(user.token!);
      await _authStorage.saveUser(user);
    }
    return user;
  }

  Future<UserModel?> getCachedUser() async {
    return await _authStorage.getUser();
  }

  Future<UserModel?> checkAuthStatus() async {
    final token = await _authStorage.getToken();
    if (token == null || token.isEmpty) {
      return null;
    }
    try {
      final user = await _apiService.getMe();
      await _authStorage.saveUser(user);
      return user;
    } catch (_) {
      // Return cached user if offline, or null if token is completely invalid
      return await _authStorage.getUser();
    }
  }

  Future<void> logout() async {
    await _authStorage.clear();
  }
}

