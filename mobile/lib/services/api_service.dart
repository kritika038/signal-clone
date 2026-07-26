import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  final String baseUrl;
  String? _jwtToken;

  ApiService({this.baseUrl = const String.fromEnvironment(
    'SIGNAL_API_URL',
    defaultValue: 'http://10.0.2.2:8000',
  )});

  void setJwtToken(String token) {
    _jwtToken = token;
  }

  Future<bool> registerDeviceToken({
    required String deviceId,
    required String platform,
    required String fcmToken,
  }) async {
    if (_jwtToken == null) {
      print('[ApiService] Cannot register device token: JWT token not set');
      return false;
    }

    final url = Uri.parse('$baseUrl/api/v1/devices/register');
    final response = await http.post(
      url,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $_jwtToken',
      },
      body: jsonEncode({
        'device_id': deviceId,
        'platform': platform,
        'fcm_token': fcmToken,
      }),
    );

    if (response.statusCode == 200) {
      print('[ApiService] Successfully registered device token');
      return true;
    } else {
      print('[ApiService] Failed to register device token: ${response.statusCode} ${response.body}');
      return false;
    }
  }

  Future<bool> deleteDeviceToken(String deviceId) async {
    if (_jwtToken == null) return false;

    final url = Uri.parse('$baseUrl/api/v1/devices/$deviceId');
    final response = await http.delete(
      url,
      headers: {
        'Authorization': 'Bearer $_jwtToken',
      },
    );

    return response.statusCode == 200;
  }
}
