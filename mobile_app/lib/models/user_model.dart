class UserModel {
  final String username;
  final String role;
  final String? token;

  UserModel({
    required this.username,
    required this.role,
    this.token,
  });

  bool get isAdmin => role.toLowerCase() == 'admin';

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      username: json['username']?.toString() ?? '',
      role: json['role']?.toString() ?? 'user',
      token: json['access_token']?.toString() ?? json['token']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'username': username,
      'role': role,
      if (token != null) 'access_token': token,
    };
  }
}

