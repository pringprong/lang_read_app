import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../data/db.dart';
import 'lesson_list_screen.dart';

/// Home: topic list (§8.1 / §6.1). Empty states guide to the Sync tab.
class HomeScreen extends StatelessWidget {
  final VoidCallback onGoToSync;

  const HomeScreen({super.key, required this.onGoToSync});

  @override
  Widget build(BuildContext context) {
    final db = context.read<AppDb>();
    return Scaffold(
      appBar: AppBar(title: const Text('LangRead')),
      body: StreamBuilder<List<Topic>>(
        stream: db.watchTopics(),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting &&
              !snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          final topics = snapshot.data ?? const [];
          if (topics.isEmpty) {
            return Center(
              child: Card(
                margin: const EdgeInsets.all(24),
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.cloud_download, size: 48),
                      const SizedBox(height: 12),
                      const Text('No content yet',
                          style: TextStyle(
                              fontSize: 18, fontWeight: FontWeight.w600)),
                      const SizedBox(height: 8),
                      const Text(
                          'Sync with the desktop app to copy your\n'
                          'topics, lessons and audio to this phone.',
                          textAlign: TextAlign.center),
                      const SizedBox(height: 16),
                      FilledButton.icon(
                        icon: const Icon(Icons.sync),
                        label: const Text('Go to Sync'),
                        onPressed: onGoToSync,
                      ),
                    ],
                  ),
                ),
              ),
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.symmetric(vertical: 8),
            itemCount: topics.length,
            separatorBuilder: (_, _) => const SizedBox(height: 4),
            itemBuilder: (context, i) {
              final t = topics[i];
              return FutureBuilder<List<Lesson>>(
                future: db.lessonsForTopic(t.id),
                builder: (context, snapshot) {
                  final lessons = snapshot.data ?? const [];
                  final complete =
                      lessons.where((l) => l.status == 'complete').length;
                  final reviewed = lessons
                      .where((l) =>
                          l.status == 'complete' &&
                          l.lastReviewedAt != null)
                      .length;
                  return ListTile(
                    leading: const Icon(Icons.folder_outlined),
                    title: Text(t.name),
                    subtitle: complete == 0
                        ? null
                        : Text('$reviewed / $complete lessons reviewed'),
                    trailing: const Icon(Icons.chevron_right),
                    enabled: complete > 0,
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => LessonListScreen(topic: t),
                      ),
                    ),
                  );
                },
              );
            },
          );
        },
      ),
    );
  }
}
