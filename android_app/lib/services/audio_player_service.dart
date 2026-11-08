import 'package:flutter/foundation.dart';
import 'package:just_audio/just_audio.dart';

/// Thin, testable wrapper around `just_audio` for the audio bar (§8.5).
/// Caches player state and notifies listeners; the UI reads plain fields.
class AudioPlayerService extends ChangeNotifier {
  final AudioPlayer _player = AudioPlayer();

  bool loaded = false;
  bool playing = false;
  bool completed = false;
  Duration position = Duration.zero;
  Duration? duration;
  double speed = 1.0;

  AudioPlayerService() {
    _player.playingStream.listen((v) {
      playing = v;
      notifyListeners();
    });
    _player.positionStream.listen((p) {
      position = p;
      notifyListeners();
    });
    _player.durationStream.listen((d) {
      duration = d;
      notifyListeners();
    });
    _player.processingStateStream.listen((s) {
      if (s == ProcessingState.completed) {
        completed = true;
        playing = false;
      } else if (s == ProcessingState.ready) {
        completed = false;
      }
      notifyListeners();
    });
  }

  /// Loads a local MP3 (app-storage path). Safe to call repeatedly.
  Future<void> loadFile(String path) async {
    if (loaded && _path == path) return;
    _path = path;
    await _player.stop();
    await _player.setFilePath(path);
    await _player.setSpeed(speed);
    loaded = true;
    completed = false;
    notifyListeners();
  }

  String? _path;

  Future<void> play() async {
    if (completed) {
      await seekToStart();
    }
    await _player.play();
  }

  Future<void> pause() => _player.pause();

  Future<void> restart() async {
    await seekToStart();
    await _player.play();
  }

  Future<void> seekToStart() async {
    await _player.seek(Duration.zero);
    completed = false;
  }

  /// ±15 s jumps (§8.5), clamped to the audio bounds.
  Future<void> seekBy(Duration delta) async {
    final d = duration ?? Duration.zero;
    var target = position + delta;
    if (target < Duration.zero) target = Duration.zero;
    if (target > d) target = d;
    await _player.seek(target);
    completed = false;
  }

  /// 0.5×–2.0× (§8.5).
  Future<void> setSpeed(double value) async {
    speed = value;
    await _player.setSpeed(value);
    notifyListeners();
  }

  @override
  void dispose() {
    _player.dispose();
    super.dispose();
  }
}
