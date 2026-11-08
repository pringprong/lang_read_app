import 'package:flutter/material.dart';

import '../../services/audio_player_service.dart';

const _speeds = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0];

/// Pinned audio bar (§8.5): play/pause, restart, speed chips, ±15 s,
/// progress slider, jump-to-end.
class AudioBar extends StatelessWidget {
  final AudioPlayerService audio;
  final VoidCallback onJumpToEnd;

  const AudioBar({super.key, required this.audio, required this.onJumpToEnd});

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: audio,
      builder: (context, _) {
        if (!audio.loaded) {
          return const Padding(
            padding: EdgeInsets.all(12),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.volume_off, size: 16),
                SizedBox(width: 8),
                Text('no audio in this bundle'),
              ],
            ),
          );
        }
        final total = audio.duration ?? Duration.zero;
        final pos = audio.position;
        return Material(
          elevation: 4,
          child: SafeArea(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    IconButton(
                      tooltip: 'Back 15 s',
                      icon: const Icon(Icons.replay_10),
                      onPressed: () => audio.seekBy(const Duration(seconds: -15)),
                    ),
                    IconButton.filled(
                      tooltip: audio.playing ? 'Pause' : 'Play',
                      icon: Icon(audio.playing
                          ? Icons.pause
                          : Icons.play_arrow),
                      onPressed: audio.playing ? audio.pause : audio.play,
                    ),
                    IconButton(
                      tooltip: 'Forward 15 s',
                      icon: const Icon(Icons.forward_10),
                      onPressed: () => audio.seekBy(const Duration(seconds: 15)),
                    ),
                    IconButton(
                      tooltip: 'Restart',
                      icon: const Icon(Icons.restart_alt),
                      onPressed: audio.restart,
                    ),
                    Expanded(
                      child: Text(
                        '${_fmt(pos)} / ${_fmt(total)}',
                        textAlign: TextAlign.center,
                      ),
                    ),
                    IconButton(
                      tooltip: 'Jump to word review',
                      icon: const Icon(Icons.skip_next),
                      onPressed: onJumpToEnd,
                    ),
                  ],
                ),
                Slider(
                  value: total.inMilliseconds == 0
                      ? 0
                      : (pos.inMilliseconds.clamp(0, total.inMilliseconds) /
                          total.inMilliseconds),
                  onChanged: (v) =>
                      audio.seekBy(Duration(milliseconds: (v * total.inMilliseconds).round() - pos.inMilliseconds)),
                ),
                SizedBox(
                  height: 36,
                  child: ListView(
                    scrollDirection: Axis.horizontal,
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    children: [
                          for (final s in _speeds)
                            Padding(
                              padding: const EdgeInsets.only(right: 8),
                              child: ChoiceChip(
                                label: Text('$s×'),
                                selected: audio.speed == s,
                                onSelected: (_) => audio.setSpeed(s),
                              ),
                            ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  static String _fmt(Duration d) {
    final m = d.inMinutes.remainder(60).toString().padLeft(2, '0');
    final s = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '$m:$s';
  }
}
