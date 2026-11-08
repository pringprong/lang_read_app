import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:provider/provider.dart';

import 'app.dart';
import 'data/db.dart';
import 'state/sync_provider.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final db = AppDb();
  final dir = await getApplicationDocumentsDirectory();
  runApp(
    MultiProvider(
      providers: [
        Provider<AppDb>.value(value: db),
        ChangeNotifierProvider(create: (_) => SyncState(db, dir)),
      ],
      child: const LangReadApp(),
    ),
  );
}
