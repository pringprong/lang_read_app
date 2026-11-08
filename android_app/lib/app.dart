import 'package:flutter/material.dart';

import 'screens/home_screen.dart';
import 'screens/sync_screen.dart';

/// Two top-level destinations per §12.2: Review (home) and Sync.
class LangReadApp extends StatefulWidget {
  const LangReadApp({super.key});

  @override
  State<LangReadApp> createState() => _LangReadAppState();
}

class _LangReadAppState extends State<LangReadApp> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'LangRead',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF00695C)),
        useMaterial3: true,
      ),
      darkTheme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF00695C),
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      home: Scaffold(
        body: IndexedStack(
          index: _index,
          children: [
            HomeScreen(onGoToSync: () => setState(() => _index = 1)),
            const SyncScreen(),
          ],
        ),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _index,
          onDestinationSelected: (i) => setState(() => _index = i),
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.menu_book_outlined),
              selectedIcon: Icon(Icons.menu_book),
              label: 'Review',
            ),
            NavigationDestination(
              icon: Icon(Icons.sync_outlined),
              selectedIcon: Icon(Icons.sync),
              label: 'Sync',
            ),
          ],
        ),
      ),
    );
  }
}
