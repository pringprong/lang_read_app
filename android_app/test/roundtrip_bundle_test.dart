import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:langread/data/export_service.dart';
import 'package:langread/data/import_service.dart';
import 'package:langread/state/review_session.dart';

import 'test_db.dart';

/// Full-circle round-trip (A5/A6 acceptance, plan §8):
/// real desktop `sync-v1.zip` → Android import → review session → complete
/// → Android results bundle written to `build/results-roundtrip.zip`.
///
/// The companion check on the desktop side:
///   /home/pringprong/lang_read_app/.venv/bin/python \
///       tool/verify_results_bundle.py build/results-roundtrip.zip
void main() {
  test('desktop bundle → review → results bundle', () async {
    final fixture =
        File('${Directory.current.path}/test/fixtures/sync-v1.zip');
    expect(fixture.existsSync(), isTrue,
        reason: 'run tool/make_fixture.py first');

    final dir = tempDir();
    final db = testFileDb(dir);
    addTearDown(db.close);

    await ImportService(db, dir).importBundle(fixture.path);

    final topics = await db.watchTopics().first;
    final cooking = topics.firstWhere((t) => t.name == 'Cooking');
    final lessons = await db.lessonsForTopic(cooking.id);
    final first = lessons.firstWhere((l) => l.status == 'complete');

    final session = ReviewSession(db, first);
    await session.load();
    // Rate one word easy (rest stay standard); promote an unlisted word
    // from the text to the New list, as from a popup (§8.3).
    session.setRating(session.reviewWords.first, ReviewRating.easy);
    await session.applyWordAction('很', 'add_new');
    await session.complete();

    final out = await ExportService(db, dir).exportResults();
    expect(out, isNotNull);
    // One rating per learned word + lesson_reviewed + word_action.
    expect(await db.allPendingEvents(), hasLength(4));

    final build = Directory('${Directory.current.path}/build')
      ..createSync(recursive: true);
    final target = File('${build.path}/results-roundtrip.zip');
    out!.copySync(target.path);
    expect(target.existsSync(), isTrue);
  });
}
