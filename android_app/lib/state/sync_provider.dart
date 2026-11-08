import 'dart:io';

import 'package:flutter/foundation.dart';

import '../data/bundle_reader.dart';
import '../data/db.dart';
import '../data/export_service.dart';
import '../data/import_service.dart';

/// Import/export status for the Sync tab (§6.4). Methods throw
/// [BundleException] with user-presentable messages on verification
/// failures; the screen catches and shows them.
class SyncState extends ChangeNotifier {
  final AppDb db;
  final Directory baseDir;

  late final ImportService importer = ImportService(db, baseDir);
  late final ExportService exporter = ExportService(db, baseDir);

  bool importing = false;
  bool exporting = false;
  ImportStats? lastImportStats;
  String? lastError;

  SyncState(this.db, this.baseDir);

  Future<ImportStats> importBundle(String zipPath) async {
    importing = true;
    lastError = null;
    notifyListeners();
    try {
      final stats = await importer.importBundle(zipPath);
      lastImportStats = stats;
      return stats;
    } on BundleException catch (e) {
      lastError = e.message;
      rethrow;
    } finally {
      importing = false;
      notifyListeners();
    }
  }

  /// Returns the exported bundle file, or null when nothing is pending.
  Future<File?> exportResults() async {
    exporting = true;
    lastError = null;
    notifyListeners();
    try {
      return await exporter.exportResults();
    } on BundleException catch (e) {
      lastError = e.message;
      rethrow;
    } finally {
      exporting = false;
      notifyListeners();
    }
  }
}
