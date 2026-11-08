import 'dart:convert';
import 'dart:io';

import 'package:archive/archive.dart';
import 'package:crypto/crypto.dart';

/// Thrown for any bundle-verification failure (plan §3.4). The message is
/// shown to the user verbatim, mirroring the desktop's wording.
class BundleException implements Exception {
  final String message;
  const BundleException(this.message);

  @override
  String toString() => message;
}

const int bundleSchemaVersion = 1;

/// Current UTC time as a sortable ISO-8601 string, formatted exactly like
/// the desktop's `utcnow_iso()` (seconds precision, `+00:00` suffix) so
/// timestamp string comparisons agree on both sides.
String utcnowIso() {
  final now = DateTime.now().toUtc();
  String two(int n) => n.toString().padLeft(2, '0');
  return '${now.year}-${two(now.month)}-${two(now.day)}'
      'T${two(now.hour)}:${two(now.minute)}:${two(now.second)}+00:00';
}

/// A verified, opened bundle archive (plan §3).
///
/// [load] performs the full §3.4 verification — valid zip, manifest present,
/// schema version, bundle type, and SHA-256 of every listed file — and
/// throws [BundleException] before anything is applied.
class BundleReader {
  final Archive archive;
  final Map<String, dynamic> manifest;

  BundleReader._(this.archive, this.manifest);

  static BundleReader load(String zipPath, {String? expectedType}) {
    final file = File(zipPath);
    if (!file.existsSync()) {
      throw BundleException('bundle does not exist: $zipPath');
    }
    Archive archive;
    try {
      archive = ZipDecoder().decodeBytes(file.readAsBytesSync());
    } catch (e) {
      throw BundleException('not a valid zip bundle: $e');
    }
    final manifestFile = archive.findFile('manifest.json');
    if (manifestFile == null) {
      throw BundleException('bundle has no manifest.json');
    }
    Map<String, dynamic> manifest;
    try {
      manifest =
          jsonDecode(utf8.decode(_contentOf(manifestFile))) as Map<String, dynamic>;
    } catch (e) {
      throw BundleException('manifest.json is not valid JSON: $e');
    }
    if (manifest['schema_version'] != bundleSchemaVersion) {
      throw BundleException(
          'unsupported bundle schema version ${manifest['schema_version']} '
          '(expected $bundleSchemaVersion) — update the desktop app and re-export');
    }
    if (expectedType != null && manifest['bundle_type'] != expectedType) {
      throw BundleException(
          "expected a '$expectedType' bundle, got '${manifest['bundle_type']}'");
    }
    final files = (manifest['files'] ?? const {}) as Map<String, dynamic>;
    for (final entry in files.entries) {
      final f = archive.findFile(entry.key);
      if (f == null) {
        throw BundleException('manifest lists missing file: ${entry.key}');
      }
      final digest = sha256.convert(_contentOf(f)).toString();
      if (digest != entry.value) {
        throw BundleException('checksum mismatch for ${entry.key}');
      }
    }
    return BundleReader._(archive, manifest);
  }

  /// Whether the archive contains a given file.
  bool has(String name) => archive.findFile(name) != null;

  /// Reads and returns a verified file's bytes.
  List<int> read(String name) {
    final f = archive.findFile(name);
    if (f == null) {
      throw BundleException('bundle has no file: $name');
    }
    return _contentOf(f);
  }

  /// Reads a verified file as decoded UTF-8 JSON.
  dynamic readJson(String name) => jsonDecode(utf8.decode(read(name)));

  /// Reads a verified file's text, one JSON object per line (events.jsonl).
  List<Map<String, dynamic>> readJsonLines(String name) {
    final text = utf8.decode(read(name));
    return text
        .split('\n')
        .where((line) => line.trim().isNotEmpty)
        .map((line) => jsonDecode(line) as Map<String, dynamic>)
        .toList();
  }

  static List<int> _contentOf(ArchiveFile f) => f.content as List<int>;
}
