import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:langread/data/bundle_reader.dart';
import 'package:langread/data/db.dart';
import 'package:langread/data/import_service.dart';

import 'bundle_builder.dart';
import 'test_db.dart';

void main() {
  late Directory dir;
  late AppDb db;

  setUp(() {
    dir = tempDir();
    db = testFileDb(dir);
    addTearDown(db.close);
  });

  ImportService importer() => ImportService(db, dir);

  test('imports a valid bundle end-to-end', () async {
    final zip = buildBundle('${dir.path}/sync.zip',
        content: sampleContent(),
        extraFiles: {'audio/lesson_10.mp3': fakeMp3});
    final stats = await importer().importBundle(zip.path);

    expect(stats.topics, 1);
    expect(stats.lessons, 1);
    expect(stats.sentences, 2);
    expect(stats.words, 3);
    expect(stats.audioFiles, 1);

    final topics = await db.watchTopics().first;
    expect(topics.single.name, 'Cooking');
    final lessons = await db.lessonsForTopic(1);
    expect(lessons.single.title, 'First meal');
    final sentences = await db.sentencesForLesson(10);
    expect(sentences, hasLength(2));
    expect(sentences.first.content, '我用锅做饭。');
    expect(sentences.first.translation, 'I cook rice with the pot.');
    final word = await db.wordByText('锅');
    expect(word!.listState, 'new');
    expect(word.pinyin, 'guō');
    final learned = await db.learnedWordsForLesson(10);
    expect(learned.map((w) => w.word), contains('饭'));

    // audio written
    final audio = File('${dir.path}/audio/lesson_10.mp3');
    expect(audio.existsSync(), isTrue);
    expect(audio.readAsBytesSync(), fakeMp3);

    // sync meta recorded
    expect(await db.getMeta('last_import_at'), isNotNull);
  });

  test('re-import creates a backup and is idempotent', () async {
    final zip = buildBundle('${dir.path}/sync.zip',
        content: sampleContent(),
        extraFiles: {'audio/lesson_10.mp3': fakeMp3});
    await importer().importBundle(zip.path);
    final stats = await importer().importBundle(zip.path);
    expect(stats.topics, 1);
    final backups =
        Directory('${dir.path}/backups').listSync().whereType<File>();
    expect(backups, hasLength(1));
    // audio skipped, not rewritten (same size)
    final audio = File('${dir.path}/audio/lesson_10.mp3');
    final before = audio.lastModifiedSync();
    await Future.delayed(const Duration(milliseconds: 20));
    await importer().importBundle(zip.path);
    expect(audio.lastModifiedSync(), before);
  });

  test('pending events survive an import', () async {
    await db.insertPendingEvent('rating', {
      'type': 'rating',
      'word_id': 3,
      'lesson_id': 10,
      'rating': 'easy',
      'reviewed_at': '2026-11-08T00:00:00+00:00',
    });
    final zip = buildBundle('${dir.path}/sync.zip', content: sampleContent());
    final stats = await importer().importBundle(zip.path);
    expect(stats.pendingKept, 1);
    expect(await db.allPendingEvents(), hasLength(1));
  });

  test('superseded pending events are pruned conservatively', () async {
    // Older than the export AND the desktop's events.jsonl confirms it.
    await db.insertPendingEvent('rating', {
      'type': 'rating',
      'word_id': 3,
      'lesson_id': 10,
      'rating': 'easy',
      'reviewed_at': '2026-11-05T00:00:00+00:00',
    });
    // Older than the export, but word 2 rating is NOT in desktop events.
    await db.insertPendingEvent('rating', {
      'type': 'rating',
      'word_id': 2,
      'lesson_id': 10,
      'rating': 'difficult',
      'reviewed_at': '2026-11-05T00:00:00+00:00',
    });
    // Newer than the export — must be kept.
    await db.insertPendingEvent('lesson_reviewed', {
      'type': 'lesson_reviewed',
      'lesson_id': 10,
      'reviewed_at': '2026-11-08T00:00:00+00:00',
    });
    // Word action now reflected in the imported content (锅 is 'new').
    await db.insertPendingEvent('word_action', {
      'type': 'word_action',
      'action': 'add_new',
      'word_text': '锅',
      'acted_at': '2026-11-05T00:00:00+00:00',
    });

    final events = jsonEncode({
      'type': 'rating',
      'word_id': 3,
      'lesson_id': 10,
      'rating': 'easy',
      'reviewed_at': '2026-11-06T00:00:00+00:00',
    });
    final zip = buildBundle('${dir.path}/sync.zip',
        content: sampleContent(), eventsJsonl: events);
    final stats = await importer().importBundle(zip.path);

    expect(stats.pendingKept, 2); // word 2 rating + newer lesson_reviewed
    final remaining = await db.allPendingEvents();
    expect(remaining.map((e) => jsonDecode(e.payload)['word_id']),
        containsAll([2, null]));
  });

  test('corrupt bundle is rejected and leaves data untouched', () async {
    final good = buildBundle('${dir.path}/good.zip', content: sampleContent());
    await importer().importBundle(good.path);
    final bad = buildBundle('${dir.path}/bad.zip',
        content: sampleContent(), hashOverrides: {'content.json': '00' * 32});
    expect(
      () => importer().importBundle(bad.path),
      throwsA(isA<BundleException>()),
    );
    // old content still present
    final topics = await db.watchTopics().first;
    expect(topics, hasLength(1));
    expect(await db.getMeta('last_import_at'), isNotNull);
  });
}
