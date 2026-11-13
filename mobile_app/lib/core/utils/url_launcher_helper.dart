import 'dart:io';
import 'package:flutter/foundation.dart';

class UrlLauncherHelper {
  static Future<bool> launchUrlString(String url) async {
    final trimmed = url.trim();
    if (trimmed.isEmpty) return false;

    try {
      if (Platform.isWindows) {
        final result = await Process.run('cmd', ['/c', 'start', '', trimmed]);
        return result.exitCode == 0;
      } else if (Platform.isMacOS) {
        final result = await Process.run('open', [trimmed]);
        return result.exitCode == 0;
      } else if (Platform.isLinux) {
        final result = await Process.run('xdg-open', [trimmed]);
        return result.exitCode == 0;
      }
    } catch (e) {
      debugPrint('Error launching URL: $e');
    }
    return false;
  }
}

