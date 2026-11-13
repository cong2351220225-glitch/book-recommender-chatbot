import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../models/user_model.dart';

class AuthStorage {
  static const String _keyToken = 'auth_token';
  static const String _keyUser = 'auth_user';
  static const String _keyBaseUrl = 'custom_base_url';

  final FlutterSecureStorage _secureStorage = const FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
    wOptions: WindowsOptions(),
  );

  bool _useFallback = false;

  Future<void> saveToken(String token) async {
    try {
      if (!_useFallback) {
        await _secureStorage.write(key: _keyToken, value: token);
        return;
      }
    } catch (_) {
      _useFallback = true;
    }
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyToken, token);
  }

  Future<String?> getToken() async {
    try {
      if (!_useFallback) {
        final token = await _secureStorage.read(key: _keyToken);
        if (token != null) return token;
      }
    } catch (_) {
      _useFallback = true;
    }
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyToken);
  }

  Future<void> saveUser(UserModel user) async {
    final jsonStr = jsonEncode(user.toJson());
    try {
      if (!_useFallback) {
        await _secureStorage.write(key: _keyUser, value: jsonStr);
        return;
      }
    } catch (_) {
      _useFallback = true;
    }
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyUser, jsonStr);
  }

  Future<UserModel?> getUser() async {
    try {
      if (!_useFallback) {
        final jsonStr = await _secureStorage.read(key: _keyUser);
        if (jsonStr != null && jsonStr.isNotEmpty) {
          return UserModel.fromJson(jsonDecode(jsonStr));
        }
      }
    } catch (_) {
      _useFallback = true;
    }
    final prefs = await SharedPreferences.getInstance();
    final jsonStr = prefs.getString(_keyUser);
    if (jsonStr != null && jsonStr.isNotEmpty) {
      try {
        return UserModel.fromJson(jsonDecode(jsonStr));
      } catch (_) {}
    }
    return null;
  }

  Future<void> saveCustomBaseUrl(String url) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyBaseUrl, url);
  }

  Future<String?> getCustomBaseUrl() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyBaseUrl);
  }

  Future<void> clear() async {
    try {
      await _secureStorage.delete(key: _keyToken);
      await _secureStorage.delete(key: _keyUser);
    } catch (_) {}
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_keyToken);
    await prefs.remove(_keyUser);
  }
}

