import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:langread/data/db.dart';
import 'package:langread/data/import_service.dart';
import 'package:langread/state/review_session.dart';

import 'bundle_builder.dart';
import 'test_db.dart';

void main() {
  late Directory dir;
  late AppDb db;
  late Lesson lesson;

  setUp(() async {
    dir = tempDir();
    db = testFileDb(dir);
    final zip = buildBundle('${dir.path}/sync.zip',
        content: sampleContent(),
        extraFiles: {'audio/lesson_10.mp3': fakeMp3});
    await ImportService(db, dir).importBundle(zip.path);
    lesson = (await db.lessonsForTopic(1)).single;
  });

  tearDown(() => db.close());

  test('load() reads sentences, words and the learned list', () async {
    final session = ReviewSession(db, lesson);
    await session.load();
    expect(session.sentences, hasLength(2));
    expect(session.newWordTexts, {'锅'});
    expect(session.reviewWords.map((w) => w.word), ['饭']);
    expect(session.lookup('锅')!.listState, 'new');
    expect(session.lookup('我')!.listState, 'basic');
    expect(session.lookup('用'), isNull); // unlisted
  });

  test('complete() queues one rating per learned word + lesson_reviewed',
      () async {
    final session = ReviewSession(db, lesson);
    await session.load();
    session.setRating(session.reviewWords.single, ReviewRating.easy);
    await session.complete();

    final events = await db.allPendingEvents();
    expect(events, hasLength(2));
    final rating = jsonDecode(events[0].payload) as Map<String, dynamic>;
    expect(rating['type'], 'rating');
    expect(rating['word_id'], 3);
    expect(rating['lesson_id'], 10);
    expect(rating['rating'], 'easy');
    final reviewed = jsonDecode(events[1].payload) as Map<String, dynamic>;
    expect(reviewed['type'], 'lesson_reviewed');
    expect(reviewed['lesson_id'], 10);

    // Local last-reviewed timestamp is set (§8.7).
    final updated = await db.lessonById(10);
    expect(updated!.lastReviewedAt, isNotNull);
    expect(session.stage, ReviewStage.done);
  });

  test('cancel() writes nothing (§8.7)', () async {
    final session = ReviewSession(db, lesson);
    await session.load();
    session.setRating(session.reviewWords.single, ReviewRating.difficult);
    session.cancel();
    expect(await db.allPendingEvents(), isEmpty);
    final unchanged = await db.lessonById(10);
    expect(unchanged!.lastReviewedAt, isNull);
  });

  test('word actions apply locally immediately and queue an event; undo works',
      () async {
    final session = ReviewSession(db, lesson);
    await session.load();

    // Unlisted word → add to New list (creates a local row).
    final handle = await session.applyWordAction('用', 'add_new');
    expect(handle, isNotNull);
    expect(session.lookup('用')!.listState, 'new');
    final queued = await db.allPendingEvents();
    expect(queued, hasLength(1));
    final payload = jsonDecode(queued.single.payload) as Map<String, dynamic>;
    expect(payload['type'], 'word_action');
    expect(payload['action'], 'add_new');
    expect(payload['word_text'], '用');

    // Undo removes the event and the local word.
    await session.undoWordAction(handle!);
    expect(await db.allPendingEvents(), isEmpty);
    expect(session.lookup('用'), isNull);

    // Basic word → move to New list (no local row created).
    final handle2 = await session.applyWordAction('我', 'basic_to_new');
    expect(handle2, isNotNull);
    expect(session.lookup('我')!.listState, 'new');
    await session.undoWordAction(handle2!);
    expect(session.lookup('我')!.listState, 'basic');
    expect(await db.allPendingEvents(), isEmpty);
  });

  test('cancel does not undo already-confirmed word actions (§8.7)', () async {
    final session = ReviewSession(db, lesson);
    await session.load();
    await session.applyWordAction('用', 'add_new');
    session.cancel();
    expect(await db.allPendingEvents(), hasLength(1));
    expect(session.lookup('用')!.listState, 'new');
  });
}
