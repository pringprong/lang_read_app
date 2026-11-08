import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:provider/provider.dart';

import '../../data/db.dart';
import '../../services/audio_player_service.dart';
import '../../state/review_session.dart';
import 'audio_bar.dart';
import 'lesson_text_view.dart';
import 'word_review_stage.dart';
import 'word_sheet.dart';

/// Lesson review (§8.2–8.7): stage machine reading → wordReview → done.
class ReviewScreen extends StatefulWidget {
  final int lessonId;

  const ReviewScreen({super.key, required this.lessonId});

  @override
  State<ReviewScreen> createState() => _ReviewScreenState();
}

class _ReviewScreenState extends State<ReviewScreen>
    with WidgetsBindingObserver {
  AppDb? _db;
  ReviewSession? _session;
  AudioPlayerService? _audio;
  bool _autoAdvanced = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    // db is read in didChangeDependencies to avoid provider misuse.
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_session == null) {
      _db = context.read<AppDb>();
      _initSession();
    }
  }

  Future<void> _initSession() async {
    final db = _db!;
    final lesson = await db.lessonById(widget.lessonId);
    if (lesson == null || !mounted) return;
    final session = ReviewSession(db, lesson);
    await session.load();
    if (!mounted) return;
    final audio = AudioPlayerService();
    audio.addListener(_onAudioChanged);
    if (lesson.audioPath != null) {
      final docDir = await getApplicationDocumentsDirectory();
      final file =
          File(p.join(docDir.path, 'audio', lesson.audioPath!));
      if (file.existsSync()) {
        await audio.loadFile(file.path);
      }
    }
    if (!mounted) return;
    setState(() {
      _session = session;
      _audio = audio;
    });
  }

  void _onAudioChanged() {
    final a = _audio;
    final s = _session;
    if (a == null || s == null) return;
    if (a.completed && s.stage == ReviewStage.reading && !_autoAdvanced) {
      _autoAdvanced = true;
      s.goToStage(ReviewStage.wordReview);
    } else if (!a.completed) {
      _autoAdvanced = false;
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // Foreground-only audio (plan §2): pause when backgrounded.
    if (state == AppLifecycleState.paused ||
        state == AppLifecycleState.inactive) {
      _audio?.pause();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _audio?.removeListener(_onAudioChanged);
    _audio?.dispose();
    _session?.dispose();
    super.dispose();
  }

  Future<bool> _confirmCancel() async {
    final s = _session;
    if (s == null || s.stage == ReviewStage.done) return true;
    final result = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Cancel this review?'),
        content: const Text(
            'Word ratings and the review timestamp are discarded.\n'
            'Word-list changes you confirmed in popups are kept.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Keep reviewing')),
          FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Cancel review')),
        ],
      ),
    );
    return result ?? false;
  }

  @override
  Widget build(BuildContext context) {
    final session = _session;
    if (session == null) {
      return Scaffold(
        appBar: AppBar(),
        body: const Center(child: CircularProgressIndicator()),
      );
    }
    return PopScope(
      canPop: session.stage == ReviewStage.done,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        if (await _confirmCancel()) {
          session.cancel();
          if (context.mounted) Navigator.of(context).pop();
        }
      },
      child: ListenableBuilder(
        listenable: session,
        builder: (context, _) {
          return Scaffold(
            appBar: AppBar(
              title: Text(session.lesson.title ?? 'Lesson ${session.lesson.orderIndex}'),
              actions: [
                if (session.stage != ReviewStage.done)
                  IconButton(
                    tooltip: 'Cancel review',
                    icon: const Icon(Icons.close),
                    onPressed: () async {
                      if (await _confirmCancel()) {
                        session.cancel();
                        if (context.mounted) Navigator.of(context).pop();
                      }
                    },
                  ),
              ],
            ),
            body: switch (session.stage) {
              ReviewStage.reading => _readingStage(context, session),
              ReviewStage.wordReview => WordReviewStage(session: session),
              ReviewStage.done => _doneStage(context, session),
            },
          );
        },
      ),
    );
  }

  Widget _readingStage(BuildContext context, ReviewSession session) {
    final audio = _audio;
    return Column(
      children: [
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
            child: LessonTextView(
              session: session,
              onWordTap: (token) => showWordSheet(context, session, token),
            ),
          ),
        ),
        if (audio != null)
          AudioBar(
            audio: audio,
            onJumpToEnd: () =>
                session.goToStage(ReviewStage.wordReview),
          ),
      ],
    );
  }

  Widget _doneStage(BuildContext context, ReviewSession session) {
    return Center(
      child: Card(
        margin: const EdgeInsets.all(24),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.check_circle, size: 48, color: Colors.green),
              const SizedBox(height: 12),
              const Text('Review complete',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
              const SizedBox(height: 8),
              Text(
                  '${session.reviewWords.length} word ratings queued '
                  'for the desktop.'),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Back to lessons'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
