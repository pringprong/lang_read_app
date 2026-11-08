import 'dart:io';

import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:langread/data/db.dart';

/// In-memory test database (the sqlite3 native asset is resolved by the
/// build hook when running `flutter test` / `flutter run`).
AppDb testDb() {
  return AppDb.withExecutor(NativeDatabase.memory());
}

/// File-backed test database at `<dir>/langread.db` (the app's convention,
/// needed for backup logic).
AppDb testFileDb(Directory dir) {
  return AppDb.withExecutor(NativeDatabase(File('${dir.path}/langread.db')));
}

Directory tempDir() {
  final d = Directory.systemTemp.createTempSync('langread_test');
  addTearDown(() => d.deleteSync(recursive: true));
  return d;
}
