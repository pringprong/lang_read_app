import 'dart:convert';
import 'dart:io';

import 'package:archive/archive.dart';
import 'package:crypto/crypto.dart';
import 'package:path/path.dart' as p;

import 'bundle_reader.dart';
import 'db.dart';

/// Builds the results bundle (plan §4.3): `pending_events` → `events.jsonl`
/// + `manifest.json` → `exports/results-<stamp>.zip`.
///
/// Events are NOT removed from the queue here — only a successful content
/// import confirms them (§3.3), so a lost bundle never loses review data.
class ExportService {
  final AppDb db;
  final Directory baseDir;

  ExportService(this.db, this.baseDir);

  /// Returns null when there is nothing to sync back.
  Future<File?> exportResults() async {
    final events = await db.allPendingEvents();
    if (events.isEmpty) return null;

    final payload =
        events.map((e) => e.payload).join('\n');
    final payloadBytes = utf8.encode(payload);
    final manifest = <String, dynamic>{
      'schema_version': bundleSchemaVersion,
      'bundle_type': 'results',
      'created_at': utcnowIso(),
      'counts': {'events': events.length},
      'files': {
        'events.jsonl': sha256.convert(payloadBytes).toString(),
      },
    };
    final manifestBytes = utf8.encode(jsonEncode(manifest));

    final archive = Archive()
      ..addFile(ArchiveFile('events.jsonl', payloadBytes.length, payloadBytes))
      ..addFile(
          ArchiveFile('manifest.json', manifestBytes.length, manifestBytes));
    final zipBytes = ZipEncoder().encode(archive)!;

    final stamp = utcnowIso().replaceAll(RegExp(r'[:+]'), '');
    final outDir = Directory(p.join(baseDir.path, 'exports'))
      ..createSync(recursive: true);
    final out = File(p.join(outDir.path, 'results-$stamp.zip'));
    await out.writeAsBytes(zipBytes, flush: true);
    return out;
  }
}
