import 'dart:convert';
import 'dart:io';

import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import 'tables.dart';

part 'db.g.dart';

@DriftDatabase(tables: [
  Topics,
  Lessons,
  Sentences,
  Words,
  LessonWords,
  HskWords,
  PendingEvents,
  SyncMeta,
])
class AppDb extends _$AppDb {
  /// Production database: `<documents dir>/langread.db` (plan §4.1).
  AppDb() : super(_openAppConnection());

  /// Tests / tools: any executor (e.g. `NativeDatabase.memory()`).
  AppDb.withExecutor(super.executor);

  @override
  int get schemaVersion => 1;

  // ---------- content queries ----------

  Stream<List<Topic>> watchTopics() {
    final q = select(topics)
      ..orderBy([
        (t) => OrderingTerm.asc(t.orderIndex),
        (t) => OrderingTerm.asc(t.id),
      ]);
    return q.watch();
  }

  Future<List<Lesson>> lessonsForTopic(int topicId) async {
    final q = select(lessons)
      ..where((l) => l.topicId.equals(topicId))
      ..orderBy([
        (l) => OrderingTerm.asc(l.orderIndex),
        (l) => OrderingTerm.asc(l.id),
      ]);
    return q.get();
  }

  Future<Lesson?> lessonById(int id) =>
      (select(lessons)..where((l) => l.id.equals(id))).getSingleOrNull();

  Future<List<Sentence>> sentencesForLesson(int lessonId) {
    final q = select(sentences)
      ..where((s) => s.lessonId.equals(lessonId))
      ..orderBy([
        (s) => OrderingTerm.asc(s.paraIndex),
        (s) => OrderingTerm.asc(s.sentIndex),
        (s) => OrderingTerm.asc(s.id),
      ]);
    return q.get();
  }

  Future<List<LessonWord>> lessonWordsForLesson(int lessonId) =>
      (select(lessonWords)..where((lw) => lw.lessonId.equals(lessonId))).get();

  /// This lesson's words that are on the Learned list (§8.6 word review).
  Future<List<Word>> learnedWordsForLesson(int lessonId) async {
    final rows = await lessonWordsForLesson(lessonId);
    final out = <Word>[];
    for (final row in rows) {
      final w = await wordById(row.wordId);
      if (w != null && w.listState == 'learned') out.add(w);
    }
    return out;
  }

  Future<Word?> wordById(int id) =>
      (select(words)..where((w) => w.id.equals(id))).getSingleOrNull();

  Future<Word?> wordByText(String text) =>
      (select(words)..where((w) => w.word.equals(text))).getSingleOrNull();

  Future<List<Word>> allWords() => select(words).get();

  Future<void> setWordListState(int wordId, String state) async {
    await (update(words)..where((w) => w.id.equals(wordId)))
        .write(WordsCompanion(listState: Value(state)));
  }

  /// Creates a local word row (unlisted word promoted from a popup, §8.3).
  /// The id is local-only; the desktop reconciles by text.
  Future<Word> createLocalWord(String text, String listState) async {
    final id = await into(words).insert(WordsCompanion.insert(
      word: text,
      listState: listState,
      source: 'lesson',
      addedAt: _nowIso,
    ));
    return (await wordById(id))!;
  }

  Future<void> markLessonReviewedAt(int lessonId, String iso) async {
    await (update(lessons)..where((l) => l.id.equals(lessonId)))
        .write(LessonsCompanion(lastReviewedAt: Value(iso)));
  }

  Future<void> deleteWord(int wordId) =>
      (delete(words)..where((w) => w.id.equals(wordId))).go();

  // ---------- pending events (§3.3 / §4) ----------

  Stream<int> watchPendingCount() {
    final count = countAll();
    final q = selectOnly(pendingEvents)..addColumns([count]);
    return q.watch().map((rows) => rows.first.read(count) ?? 0);
  }

  Future<List<PendingEvent>> allPendingEvents() => select(pendingEvents).get();

  Future<int> insertPendingEvent(String type, Map<String, dynamic> payload) =>
      into(pendingEvents).insert(PendingEventsCompanion.insert(
        type: type,
        payload: jsonEncode(payload),
        createdAt: _nowIso,
      ));

  Future<void> deletePendingEvent(int id) =>
      (delete(pendingEvents)..where((e) => e.id.equals(id))).go();

  // ---------- sync meta ----------

  Future<String?> getMeta(String key) async {
    final row = await (select(syncMeta)..where((m) => m.key.equals(key)))
        .getSingleOrNull();
    return row?.value;
  }

  Future<void> setMeta(String key, String value) =>
      into(syncMeta).insertOnConflictUpdate(SyncMetaEntry(key: key, value: value));

  static String get _nowIso {
    final now = DateTime.now().toUtc();
    String two(int n) => n.toString().padLeft(2, '0');
    return '${now.year}-${two(now.month)}-${two(now.day)}'
        'T${two(now.hour)}:${two(now.minute)}:${two(now.second)}+00:00';
  }
}

LazyDatabase _openAppConnection() {
  return LazyDatabase(() async {
    final dir = await getApplicationDocumentsDirectory();
    return NativeDatabase(File(p.join(dir.path, 'langread.db')));
  });
}
