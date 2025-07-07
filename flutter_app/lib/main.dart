import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  runApp(const WhisPadApp());
}

class WhisPadApp extends StatelessWidget {
  const WhisPadApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'WhisPad',
      theme: ThemeData(primarySwatch: Colors.blue),
      home: const ConnectionScreen(),
    );
  }
}

class ConnectionScreen extends StatefulWidget {
  const ConnectionScreen({super.key});

  @override
  State<ConnectionScreen> createState() => _ConnectionScreenState();
}

class _ConnectionScreenState extends State<ConnectionScreen> {
  final TextEditingController _urlController = TextEditingController();
  final TextEditingController _userController = TextEditingController();
  final TextEditingController _passController = TextEditingController();

  bool _connected = false;
  WebViewController? _webViewController;

  @override
  void initState() {
    super.initState();
    _loadPrefs();
  }

  Future<void> _loadPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    _urlController.text = prefs.getString('url') ?? '';
    _userController.text = prefs.getString('user') ?? '';
    _passController.text = prefs.getString('pass') ?? '';
  }

  Future<void> _savePrefs() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('url', _urlController.text);
    await prefs.setString('user', _userController.text);
    await prefs.setString('pass', _passController.text);
  }

  void _connect() async {
    await _savePrefs();
    setState(() {
      _connected = true;
    });
  }

  Widget _buildForm() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: ListView(
        children: [
          TextField(
            controller: _urlController,
            decoration: const InputDecoration(labelText: 'URL del servidor'),
          ),
          TextField(
            controller: _userController,
            decoration: const InputDecoration(labelText: 'Usuario (opcional)'),
          ),
          TextField(
            controller: _passController,
            decoration: const InputDecoration(labelText: 'Contraseña (opcional)'),
            obscureText: true,
          ),
          const SizedBox(height: 20),
          ElevatedButton(onPressed: _connect, child: const Text('Conectar')),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (!_connected) {
      return Scaffold(appBar: AppBar(title: const Text('WhisPad')), body: _buildForm());
    }
    return WebViewWidget(controller: _createController());
  }

  WebViewController _createController() {
    final controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted);
    final url = _urlController.text;
    if (_userController.text.isNotEmpty || _passController.text.isNotEmpty) {
      final auth = base64Encode(utf8.encode('${_userController.text}:${_passController.text}'));
      controller.loadRequest(Uri.parse(url), headers: {'Authorization': 'Basic $auth'});
    } else {
      controller.loadRequest(Uri.parse(url));
    }
    _webViewController = controller;
    return controller;
  }
}
