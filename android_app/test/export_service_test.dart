import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:langread/data/bundle_reader.dart';
import 'package:langread/data/export_service.dart';

import 'bundle_builder.dart';
import 'test_db.dart';

void main() {
  test('returns null when nothing is pending', () async {
    final db = testDb();
    addTearDown(db.close);
    final dir = tempDir();
    final out = await ExportService(db, dir).exportResults();
    expect(out, isNull);
  });

  test('exports pending events as a verifiable results bundle', () async {
    final db = testDb();
    addTearDown(db.close);
    final dir = tempDir();

    await db.insertPendingEvent('rating', {
      'type': 'rating',
      'word_id': 3,
      'lesson_id': 10,
      'rating': 'standard',
      'reviewed_at': '2026-11-07T09:00:00+00:00',
    });
    await db.insertPendingEvent('lesson_reviewed', {
      'type': 'lesson_reviewed',
      'lesson_id': 10,
      'reviewed_at': '2026-11-07T09:01:00+00:00',
    });
    await db.insertPendingEvent('word_action', {
      'type': 'word_action',
      'action': 'add_new',
      'word_text': '锅',
      'acted_at': '2026-11-07T09:02:00+00:00',
    });

    final result = await ExportService(db, dir).exportResults();
    expect(result, isNotNull);
    final out = result!;
    expect(out.path, contains('results-'));

    // The §3.4 verifier (expectedType results) must accept it.
    final reader = BundleReader.load(out.path, expectedType: 'results');
    expect(reader.manifest['counts']['events'], 3);

    final events = reader.readJsonLines('events.jsonl');
    expect(events, hasLength(3));
    expect(events[0]['type'], 'rating');
    expect(events[0]['rating'], 'standard');
    expect(events[1]['type'], 'lesson_reviewed');
    expect(events[2]['type'], 'word_action');
    expect(events[2]['word_text'], '锅');
    // Non-ASCII must be preserved as real UTF-8 (no \u escapes).
    expect(utf8.decode(reader.read('events.jsonl')), contains('锅'));

    // Events are NOT removed at export time (§3.3).
    expect(await db.allPendingEvents(), hasLength(3));
  });

  test('exported bundle is byte-compatible with the desktop spec', () async {
    final db = testDb();
    addTearDown(db.close);
    final dir = tempDir();
    await db.insertPendingEvent('rating', {
      'type': 'rating',
      'word_id': 3,
      'lesson_id': 10,
      'rating': 'easy',
      'reviewed_at': '2026-11-07T09:00:00+00:00',
    });
    final result2 = await ExportService(db, dir).exportResults();
    expect(result2, isNotNull);
    final out = result2!;

    // Compare against a bundle built by the test's reference writer,
    // which mirrors the desktop's write_results_bundle byte-for-byte
    // (same archive entries, same manifest fields).
    final reference = buildBundle('${dir.path}/reference.zip',
        bundleType: 'results',
        eventsJsonl:
            '{"type":"rating","word_id":3,"lesson_id":10,"rating":"easy",'
            '"reviewed_at":"2026-11-07T09:00:00+00:00"}');
    final a = BundleReader.load(out.path);
    final b = BundleReader.load(reference.path);
    expect(a.read('events.jsonl'), b.read('events.jsonl'));
    expect(a.manifest['files'], b.manifest['files']);
    expect(a.manifest['bundle_type'], b.manifest['bundle_type']);
    expect(a.manifest['counts'], b.manifest['counts']);
    expect(File(out.path).lengthSync(), greaterThan(0));
  });
}
