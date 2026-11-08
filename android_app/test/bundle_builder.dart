import 'dart:convert';
import 'dart:io';

import 'package:archive/archive.dart';
import 'package:crypto/crypto.dart';

/// Builds content/results bundles in tests, mirroring the desktop's writer
/// (`SyncService.export_bundle` / `write_results_bundle`).
File buildBundle(
  String path, {
  Map<String, dynamic>? content,
  String? eventsJsonl,
  Map<String, List<int>> extraFiles = const {},
  int schemaVersion = 1,
  String bundleType = 'content',
  bool omitManifest = false,
  Map<String, String>? hashOverrides,
  List<String>? manifestExtraFiles,
}) {
  final files = <String, List<int>>{};
  if (content != null) {
    files['content.json'] = utf8.encode(jsonEncode(content));
  }
  if (eventsJsonl != null) {
    files['events.jsonl'] = utf8.encode(eventsJsonl);
  }
  files.addAll(extraFiles);

  final hashes = {
    for (final e in files.entries)
      e.key: sha256.convert(e.value).toString(),
  };
  if (hashOverrides != null) hashes.addAll(hashOverrides);
  if (manifestExtraFiles != null) {
    for (final f in manifestExtraFiles) {
      hashes.putIfAbsent(f, () => '00' * 32);
    }
  }

  final manifest = {
    'schema_version': schemaVersion,
    'bundle_type': bundleType,
    'created_at': '2026-11-07T00:00:00+00:00',
    'counts': bundleType == 'results'
        ? {
            'events': (eventsJsonl ?? '')
                .split('\n')
                .where((l) => l.trim().isNotEmpty)
                .length,
          }
        : {'files': files.length},
    'files': hashes,
  };

  final archive = Archive();
  for (final e in files.entries) {
    archive.addFile(ArchiveFile(e.key, e.value.length, e.value));
  }
  if (!omitManifest) {
    final m = utf8.encode(jsonEncode(manifest));
    archive.addFile(ArchiveFile('manifest.json', m.length, m));
  }
  final f = File(path)..createSync(recursive: true);
  f.writeAsBytesSync(ZipEncoder().encode(archive)!);
  return f;
}

/// A small content payload matching the desktop `build_content` shape.
Map<String, dynamic> sampleContent({String? exportedAt}) => {
      'schema_version': 1,
      'exported_at': exportedAt ?? '2026-11-07T00:00:00+00:00',
      'topics': [
        {
          'id': 1,
          'name': 'Cooking',
          'order_index': 1,
          'created_at': '2026-11-01T00:00:00+00:00',
        },
      ],
      'lessons': [
        {
          'id': 10,
          'topic_id': 1,
          'order_index': 1,
          'title': 'First meal',
          'status': 'complete',
          'audio_path': 'lesson_10.mp3',
          'created_at': '2026-11-01T00:00:00+00:00',
          'last_reviewed_at': null,
        },
      ],
      'sentences': [
        {
          'id': 100,
          'lesson_id': 10,
          'para_index': 0,
          'sent_index': 0,
          'text': '我用锅做饭。',
          'segmentation': '["我","用","锅","做","饭","。"]',
          'translation': 'I cook rice with the pot.',
        },
        {
          'id': 101,
          'lesson_id': 10,
          'para_index': 0,
          'sent_index': 1,
          'text': '锅很热。',
          'segmentation': '["锅","很","热","。"]',
          'translation': 'The pot is hot.',
        },
      ],
      'words': [
        {
          'id': 1,
          'text': '我',
          'pinyin': 'wǒ',
          'definition': 'I; me',
          'list_state': 'basic',
          'hsk_word_id': null,
          'source': 'manual',
          'added_at': '2026-11-01T00:00:00+00:00',
          'ease': 2.5,
          'interval_days': null,
          'due_at': null,
          'reps': 0,
          'lapses': 0,
          'last_rated_at': null,
        },
        {
          'id': 2,
          'text': '锅',
          'pinyin': 'guō',
          'definition': 'pot',
          'list_state': 'new',
          'hsk_word_id': null,
          'source': 'manual',
          'added_at': '2026-11-01T00:00:00+00:00',
          'ease': 2.5,
          'interval_days': null,
          'due_at': null,
          'reps': 0,
          'lapses': 0,
          'last_rated_at': null,
        },
        {
          'id': 3,
          'text': '饭',
          'pinyin': 'fàn',
          'definition': 'cooked rice; food',
          'list_state': 'learned',
          'hsk_word_id': 7,
          'source': 'manual',
          'added_at': '2026-11-01T00:00:00+00:00',
          'ease': 2.5,
          'interval_days': 3,
          'due_at': '2026-11-10T00:00:00+00:00',
          'reps': 1,
          'lapses': 0,
          'last_rated_at': '2026-11-04T00:00:00+00:00',
        },
      ],
      'lesson_words': [
        {'lesson_id': 10, 'word_id': 2, 'role': 'new'},
        {'lesson_id': 10, 'word_id': 3, 'role': 'review'},
      ],
      'hsk_words': [
        {
          'id': 7,
          'text': '饭',
          'pinyin': 'fàn',
          'definition': 'rice; food',
          'level': 1,
          'app_state': 'learned',
        },
      ],
    };

const fakeMp3 = [0x49, 0x44, 0x33, 1, 2, 3, 4, 5];
