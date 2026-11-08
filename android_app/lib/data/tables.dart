import 'package:drift/drift.dart';

/// Local schema — mirrors the desktop app's tables 1:1 so `content.json`
/// maps directly and desktop word/lesson ids stay stable (plan §4.1).
///
/// All timestamps are ISO-8601 UTC strings (same format as the desktop's
/// `utcnow_iso`), so string comparison matches the desktop's
/// most-recent-wins reconciliation.

class Topics extends Table {
  IntColumn get id => integer()();
  TextColumn get name => text()();
  IntColumn get orderIndex => integer().named('order_index')();
  TextColumn get createdAt => text().named('created_at')();

  @override
  Set<Column> get primaryKey => {id};
}

class Lessons extends Table {
  IntColumn get id => integer()();
  IntColumn get topicId => integer().named('topic_id')();
  IntColumn get orderIndex => integer().named('order_index')();
  TextColumn get title => text().nullable()();
  TextColumn get status => text()();
  /// File name only, e.g. `lesson_3.mp3` (same convention as the desktop).
  TextColumn get audioPath => text().nullable().named('audio_path')();
  TextColumn get createdAt => text().named('created_at')();
  TextColumn get lastReviewedAt => text().nullable().named('last_reviewed_at')();

  @override
  Set<Column> get primaryKey => {id};
}

class Sentences extends Table {
  IntColumn get id => integer()();
  IntColumn get lessonId => integer().named('lesson_id')();
  IntColumn get paraIndex => integer().named('para_index')();
  IntColumn get sentIndex => integer().named('sent_index')();
  /// Unsegmented Chinese sentence text. (Getter is `content`, not `text`,
  /// because `text` would shadow drift's `text()` column builder.)
  TextColumn get content => text().named('text')();
  /// JSON array of word tokens, imported as-is from the desktop bundle.
  TextColumn get segmentation => text()();
  TextColumn get translation => text().nullable()();

  @override
  Set<Column> get primaryKey => {id};
}

class Words extends Table {
  /// Desktop word ids on import; locally created words (unlisted words the
  /// user added from a popup) get fresh auto ids — replaced on next import.
  IntColumn get id => integer().autoIncrement()();
  /// The word's written form (SQL column `text`; getter is `word` because
  /// `text` would shadow drift's `text()` column builder).
  TextColumn get word => text().named('text')();
  TextColumn get pinyin => text().nullable()();
  TextColumn get definition => text().nullable()();
  /// new | learned | basic
  TextColumn get listState => text().named('list_state')();
  IntColumn get hskWordId => integer().nullable().named('hsk_word_id')();
  TextColumn get source => text()();
  TextColumn get addedAt => text().named('added_at')();
  // SRS fields (valid when list_state == 'learned'); received, never computed.
  RealColumn get ease => real().withDefault(const Constant(2.5))();
  RealColumn get intervalDays => real().nullable().named('interval_days')();
  TextColumn get dueAt => text().nullable().named('due_at')();
  IntColumn get reps => integer().withDefault(const Constant(0))();
  IntColumn get lapses => integer().withDefault(const Constant(0))();
  TextColumn get lastRatedAt => text().nullable().named('last_rated_at')();
}

class LessonWords extends Table {
  IntColumn get lessonId => integer().named('lesson_id')();
  IntColumn get wordId => integer().named('word_id')();
  /// new | review
  TextColumn get role => text()();

  @override
  Set<Column> get primaryKey => {lessonId, wordId};
}

class HskWords extends Table {
  IntColumn get id => integer()();
  /// The word's written form (SQL column `text`; getter is `word` because
  /// `text` would shadow drift's `text()` column builder).
  TextColumn get word => text().named('text')();
  TextColumn get pinyin => text().nullable()();
  TextColumn get definition => text().nullable()();
  IntColumn get level => integer()();
  /// unused | new | basic | learned
  TextColumn get appState => text().named('app_state')();

  @override
  Set<Column> get primaryKey => {id};
}

/// Local-only: queued events destined for the results bundle (§3.3).
class PendingEvents extends Table {
  IntColumn get id => integer().autoIncrement()();
  /// rating | lesson_reviewed | word_action
  TextColumn get type => text()();
  /// The full event record as JSON (exactly what goes into events.jsonl).
  TextColumn get payload => text()();
  TextColumn get createdAt => text().named('created_at')();
}

/// Local-only: small key/value state (last_import_at, device_id, history log).
@DataClassName('SyncMetaEntry')
class SyncMeta extends Table {
  TextColumn get key => text()();
  TextColumn get value => text()();

  @override
  Set<Column> get primaryKey => {key};
}
