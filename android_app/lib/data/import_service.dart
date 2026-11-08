import 'dart:convert';
import 'dart:io';

import 'package:drift/drift.dart';
import 'package:path/path.dart' as p;

import 'bundle_reader.dart';
import 'db.dart';

class ImportStats {
  final int topics;
  final int lessons;
  final int sentences;
  final int words;
  final int audioFiles;
  final int pendingKept;
  final String? backupPath;

  const ImportStats({
    required this.topics,
    required this.lessons,
    required this.sentences,
    required this.words,
    required this.audioFiles,
    required this.pendingKept,
    this.backupPath,
  });

  @override
  String toString() =>
      'ImportStats(topics: $topics, lessons: $lessons, sentences: $sentences, '
      'words: $words, audio: $audioFiles, pending kept: $pendingKept)';
}

/// ISO-8601 strings don't support `>=` in Dart — compare via compareTo.
bool _ge(String a, String b) => a.compareTo(b) >= 0;

/// Applies a verified content bundle to the local database (plan §4.2):
/// verify → backup → replace content tables in one transaction → write audio
/// → update sync meta. Pending events survive; superseded ones are pruned.
class ImportService {
  final AppDb db;
  /// The app's documents directory (holds `langread.db`, `audio/`, `backups/`).
  final Directory baseDir;

  ImportService(this.db, this.baseDir);

  Future<ImportStats> importBundle(String zipPath) async {
    // 1-2. Verify before anything is applied (D-3).
    final reader = BundleReader.load(zipPath, expectedType: 'content');
    final content = _parseContent(reader);

    // 3. Backup the current database.
    final backupPath = await _backupCurrentDb();

    // 4a. Replace content tables in one transaction.
    await db.transaction(() async {
      await db.delete(db.topics).go();
      await db.delete(db.sentences).go();
      await db.delete(db.lessonWords).go();
      await db.delete(db.words).go();
      await db.delete(db.hskWords).go();
      await db.delete(db.lessons).go();

      await db.batch((b) {
        b.insertAll(db.topics, content.topics);
        b.insertAll(db.lessons, content.lessons);
        b.insertAll(db.sentences, content.sentences);
        b.insertAll(db.words, content.words);
        b.insertAll(db.lessonWords, content.lessonWords);
        b.insertAll(db.hskWords, content.hskWords);
      });
    });

    // 4b. Audio files (skip ones already present with the same size).
    final audioDir = Directory(p.join(baseDir.path, 'audio'))
      ..createSync(recursive: true);
    final audioNames = _manifestAudioFiles(reader);
    for (final name in audioNames) {
      final local = File(p.join(audioDir.path, p.basename(name)));
      final bytes = reader.read(name);
      if (!local.existsSync() || local.lengthSync() != bytes.length) {
        await local.writeAsBytes(bytes, flush: true);
      }
    }

    // 4c. Prune superseded pending events (§4.2 step 4).
    final pendingBefore = await db.allPendingEvents();
    final desktopEvents = reader.has('events.jsonl')
        ? reader.readJsonLines('events.jsonl')
        : <Map<String, dynamic>>[];
    final lessonLastReviewed = <int, String?>{};
    for (final l in content.lessonRows) {
      lessonLastReviewed[l['id'] as int] = l['last_reviewed_at'] as String?;
    }
    final wordStateByText = <String, String>{};
    for (final w in content.wordRows) {
      wordStateByText[w['text'] as String] = w['list_state'] as String;
    }
    for (final e in pendingBefore) {
      if (_isSuperseded(e, content.exportedAt, desktopEvents,
          lessonLastReviewed, wordStateByText)) {
        await db.deletePendingEvent(e.id);
      }
    }
    final pendingKept = (await db.allPendingEvents()).length;

    // 4d. Record the import.
    await db.setMeta('last_import_at', utcnowIso());

    return ImportStats(
      topics: content.topics.length,
      lessons: content.lessons.length,
      sentences: content.sentences.length,
      words: content.words.length,
      audioFiles: audioNames.length,
      pendingKept: pendingKept,
      backupPath: backupPath,
    );
  }

  // ---------- helpers ----------

  List<String> _manifestAudioFiles(BundleReader reader) {
    final files = (reader.manifest['files'] ?? const {}) as Map<String, dynamic>;
    final names = files.keys.where((k) => k.startsWith('audio/')).toList()
      ..sort();
    return names;
  }

  _ParsedContent _parseContent(BundleReader reader) {
    final raw = reader.readJson('content.json') as Map<String, dynamic>;

    List<Map<String, dynamic>> list(String key) =>
        (raw[key] as List? ?? []).cast<Map<String, dynamic>>();

    final topics = list('topics')
        .map((t) => TopicsCompanion.insert(
              id: Value(t['id'] as int),
              name: t['name'] as String,
              orderIndex: (t['order_index'] as num).toInt(),
              createdAt: t['created_at'] as String? ?? '',
            ))
        .toList();

    final lessonRows = list('lessons');
    final lessons = lessonRows
        .map((l) => LessonsCompanion.insert(
              id: Value(l['id'] as int),
              topicId: l['topic_id'] as int,
              orderIndex: (l['order_index'] as num).toInt(),
              title: Value(l['title'] as String?),
              status: l['status'] as String,
              audioPath: Value(l['audio_path'] as String?),
              createdAt: l['created_at'] as String? ?? '',
              lastReviewedAt: Value(l['last_reviewed_at'] as String?),
            ))
        .toList();

    final sentences = list('sentences')
        .map((s) {
          // The desktop exports segmentation as a JSON array (its dataclass
          // decodes the DB string before export); accept both forms and
          // normalize to the stored JSON-string column.
          final seg = s['segmentation'];
          final segmentation = seg is String ? seg : jsonEncode(seg ?? []);
          return SentencesCompanion.insert(
            id: Value(s['id'] as int),
            lessonId: s['lesson_id'] as int,
            paraIndex: (s['para_index'] as num).toInt(),
            sentIndex: (s['sent_index'] as num).toInt(),
            content: s['text'] as String,
            segmentation: segmentation,
            translation: Value(s['translation'] as String?),
          );
        })
        .toList();

    final wordRows = list('words');
    final words = wordRows
        .map((w) => WordsCompanion.insert(
              id: Value(w['id'] as int),
              word: w['text'] as String,
              listState: w['list_state'] as String,
              source: w['source'] as String? ?? 'lesson',
              addedAt: w['added_at'] as String? ?? '',
              pinyin: Value(w['pinyin'] as String?),
              definition: Value(w['definition'] as String?),
              hskWordId: Value(w['hsk_word_id'] as int?),
              ease: Value((w['ease'] as num?)?.toDouble() ?? 2.5),
              intervalDays: Value((w['interval_days'] as num?)?.toDouble()),
              dueAt: Value(w['due_at'] as String?),
              reps: Value((w['reps'] as num?)?.toInt() ?? 0),
              lapses: Value((w['lapses'] as num?)?.toInt() ?? 0),
              lastRatedAt: Value(w['last_rated_at'] as String?),
            ))
        .toList();

    final lessonWords = list('lesson_words')
        .map((lw) => LessonWordsCompanion.insert(
              lessonId: lw['lesson_id'] as int,
              wordId: lw['word_id'] as int,
              role: lw['role'] as String,
            ))
        .toList();

    final hskWords = list('hsk_words')
        .map((h) => HskWordsCompanion.insert(
              id: Value(h['id'] as int),
              word: h['text'] as String,
              level: (h['level'] as num).toInt(),
              appState: h['app_state'] as String,
              pinyin: Value(h['pinyin'] as String?),
              definition: Value(h['definition'] as String?),
            ))
        .toList();

    return _ParsedContent(
      exportedAt: raw['exported_at'] as String? ?? '',
      topics: topics,
      lessons: lessons,
      lessonRows: lessonRows,
      sentences: sentences,
      words: words,
      wordRows: wordRows,
      lessonWords: lessonWords,
      hskWords: hskWords,
    );
  }

  Future<String?> _backupCurrentDb() async {
    final dbFile = File(p.join(baseDir.path, 'langread.db'));
    if (!dbFile.existsSync()) return null;
    // Flush the WAL so the copied file is complete.
    await db.customStatement('PRAGMA wal_checkpoint(TRUNCATE)');
    final backups = Directory(p.join(baseDir.path, 'backups'))
      ..createSync(recursive: true);
    final stamp = utcnowIso().replaceAll(':', '');
    final target = File(p.join(backups.path, 'pre-import-$stamp.db'));
    await dbFile.copy(target.path);
    _pruneBackups(backups);
    return target.path;
  }

  void _pruneBackups(Directory backups) {
    final files = backups
        .listSync()
        .whereType<File>()
        .where((f) => p.basename(f.path).startsWith('pre-import-'))
        .toList()
      ..sort((a, b) => p.basename(a.path).compareTo(p.basename(b.path)));
    while (files.length > 5) {
      files.removeAt(0).deleteSync();
    }
  }

  /// Conservative pruning (§4.2): an event is dropped only when the bundle
  /// proves the desktop already has something at least as recent.
  bool _isSuperseded(
    PendingEvent e,
    String exportedAt,
    List<Map<String, dynamic>> desktopEvents,
    Map<int, String?> lessonLastReviewed,
    Map<String, String> wordStateByText,
  ) {
    Map<String, dynamic> payload;
    try {
      payload = jsonDecode(e.payload) as Map<String, dynamic>;
    } catch (_) {
      return false; // keep malformed records for manual inspection
    }
    final ts = (payload['reviewed_at'] ?? payload['acted_at'] ?? '') as String;
    if (ts.isNotEmpty && exportedAt.isNotEmpty && _ge(ts, exportedAt)) {
      return false; // desktop export predates this event — not confirmed yet
    }
    switch (e.type) {
      case 'rating':
        final wordId = payload['word_id'] as int?;
        final lessonId = payload['lesson_id'] as int?;
        return desktopEvents.any((ev) =>
            ev['type'] == 'rating' &&
            ev['word_id'] == wordId &&
            (ev['lesson_id'] as int?) == lessonId &&
            _ge((ev['reviewed_at'] ?? '') as String, ts));
      case 'lesson_reviewed':
        final lessonId = payload['lesson_id'] as int?;
        final confirmed = desktopEvents.any((ev) =>
            ev['type'] == 'lesson_reviewed' &&
            (ev['lesson_id'] as int?) == lessonId &&
            _ge((ev['reviewed_at'] ?? '') as String, ts));
        if (confirmed) return true;
        final last = lessonLastReviewed[lessonId];
        return last != null && _ge(last, ts);
      case 'word_action':
        final text = payload['word_text'] as String? ?? '';
        final action = payload['action'] as String? ?? '';
        final expected = switch (action) {
          'add_new' => 'new',
          'add_basic' => 'basic',
          'basic_to_new' => 'new',
          _ => null,
        };
        return expected != null && wordStateByText[text] == expected;
      default:
        return false;
    }
  }
}

class _ParsedContent {
  final String exportedAt;
  final List<TopicsCompanion> topics;
  final List<LessonsCompanion> lessons;
  final List<Map<String, dynamic>> lessonRows;
  final List<SentencesCompanion> sentences;
  final List<WordsCompanion> words;
  final List<Map<String, dynamic>> wordRows;
  final List<LessonWordsCompanion> lessonWords;
  final List<HskWordsCompanion> hskWords;

  _ParsedContent({
    required this.exportedAt,
    required this.topics,
    required this.lessons,
    required this.lessonRows,
    required this.sentences,
    required this.words,
    required this.wordRows,
    required this.lessonWords,
    required this.hskWords,
  });
}
