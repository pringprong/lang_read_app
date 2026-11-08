import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:langread/data/bundle_reader.dart';

import 'bundle_builder.dart';

void main() {
  late Directory dir;

  setUp(() {
    dir = Directory.systemTemp.createTempSync('bundle_reader_test');
    addTearDown(() => dir.deleteSync(recursive: true));
  });

  test('valid content bundle verifies and reads', () {
    final zip = buildBundle('${dir.path}/good.zip',
        content: sampleContent(),
        extraFiles: {'audio/lesson_10.mp3': fakeMp3});
    final reader = BundleReader.load(zip.path, expectedType: 'content');
    expect(reader.manifest['bundle_type'], 'content');
    final content = reader.readJson('content.json') as Map<String, dynamic>;
    expect(content['topics'], hasLength(1));
    expect(reader.has('audio/lesson_10.mp3'), isTrue);
  });

  test('missing manifest throws BundleException', () {
    final zip = buildBundle('${dir.path}/missing.zip', omitManifest: true);
    expect(
      () => BundleReader.load(zip.path),
      throwsA(isA<BundleException>()),
    );
  });

  test('non-zip bytes throw "not a valid zip bundle"', () {
    final f = File('${dir.path}/garbage.zip')
      ..writeAsBytesSync([1, 2, 3, 4, 5, 6, 7, 8]);
    expect(
      () => BundleReader.load(f.path),
      throwsA(predicate(
          (BundleException e) => e.message.contains('not a valid zip'))),
    );
  });

  test('wrong schema version is rejected', () {
    final zip = buildBundle('${dir.path}/old.zip',
        content: sampleContent(), schemaVersion: 99);
    expect(
      () => BundleReader.load(zip.path),
      throwsA(predicate((BundleException e) =>
          e.message.contains('unsupported bundle schema version'))),
    );
  });

  test('wrong bundle type is rejected', () {
    final zip = buildBundle('${dir.path}/type.zip',
        content: sampleContent(), bundleType: 'results');
    expect(
      () => BundleReader.load(zip.path, expectedType: 'content'),
      throwsA(predicate(
          (BundleException e) => e.message.contains("expected a 'content'"))),
    );
  });

  test('manifest lists a file that is not in the archive', () {
    final zip = buildBundle('${dir.path}/phantom.zip',
        content: sampleContent(), manifestExtraFiles: ['audio/lesson_99.mp3']);
    expect(
      () => BundleReader.load(zip.path),
      throwsA(predicate((BundleException e) =>
          e.message.contains('manifest lists missing file'))),
    );
  });

  test('checksum mismatch is rejected', () {
    final zip = buildBundle('${dir.path}/tampered.zip',
        content: sampleContent(),
        hashOverrides: {'content.json': '00' * 32});
    expect(
      () => BundleReader.load(zip.path),
      throwsA(predicate(
          (BundleException e) => e.message.contains('checksum mismatch'))),
    );
  });

  test('readJsonLines parses one object per line', () {
    final events =
        '{"type":"rating","word_id":3,"lesson_id":10,"rating":"easy",'
        '"reviewed_at":"2026-11-06T10:00:00+00:00"}\n'
        '{"type":"lesson_reviewed","lesson_id":10,'
        '"reviewed_at":"2026-11-06T10:05:00+00:00"}';
    final zip =
        buildBundle('${dir.path}/events.zip', eventsJsonl: events);
    final reader = BundleReader.load(zip.path);
    final lines = reader.readJsonLines('events.jsonl');
    expect(lines, hasLength(2));
    expect(lines[0]['rating'], 'easy');
    expect(lines[1]['type'], 'lesson_reviewed');
  });
}
