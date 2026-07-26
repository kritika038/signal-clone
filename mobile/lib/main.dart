import 'package:flutter/material.dart';
import 'services/fcm_service.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const SignalCloneApp());
}

class SignalCloneApp extends StatelessWidget {
  const SignalCloneApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Signal Clone',
      theme: ThemeData(
        brightness: Brightness.dark,
        primarySwatch: Colors.blue,
      ),
      home: const HomeScreen(),
    );
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  String _activeConversationId = '';
  String _status = 'Initializing...';

  @override
  void initState() {
    super.initState();
    _initFCM();
  }

  Future<void> _initFCM() async {
    // The authenticated app shell supplies the FastAPI-issued JWT. Firebase is
    // only used for push delivery; it is never used for authentication.
    const jwtToken = String.fromEnvironment('SIGNAL_JWT');
    if (jwtToken.isEmpty) {
      setState(() => _status = 'Sign in to enable push notifications');
      return;
    }
    try {
      await FCMService().initialize(
        jwtToken: jwtToken,
        onOpenChat: (conversationId) {
          setState(() {
            _activeConversationId = conversationId;
          });
          print('Navigating to Conversation: $conversationId');
        },
      );
      setState(() {
        _status = 'FCM Initialized & Device Registered';
      });
    } catch (e) {
      setState(() {
        _status = 'FCM Init Note: Running in environment stub mode';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Signal Messenger'),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(_status, style: const TextStyle(fontSize: 16)),
            const SizedBox(height: 20),
            if (_activeConversationId.isNotEmpty)
              Text(
                'Opened Conversation ID: $_activeConversationId',
                style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.blueAccent),
              ),
          ],
        ),
      ),
    );
  }
}
