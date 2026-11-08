import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:langread/screens/home_screen.dart';
import 'package:provider/provider.dart';

import 'test_db.dart';
import 'package:langread/data/db.dart';

void main() {
  testWidgets('home shows the empty state before the first sync',
      (tester) async {
    final db = testDb();
    await tester.pumpWidget(
      MaterialApp(
        home: Provider<AppDb>.value(
          value: db,
          child: HomeScreen(onGoToSync: () {}),
        ),
      ),
    );
    // Let the topic stream emit.
    await tester.pumpAndSettle();
    expect(find.text('No content yet'), findsOneWidget);
    expect(find.text('Go to Sync'), findsOneWidget);
    // Close drift's stream queries so no timers remain pending.
    await db.close();
    await tester.pump();
  });
}
