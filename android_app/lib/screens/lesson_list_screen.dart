import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../data/db.dart';
import 'review/review_screen.dart';

/// Lesson list of one topic (§8.1 / §6.1): ordered rows with last-reviewed
/// state; only `complete` lessons are listed (§3.2 note).
class LessonListScreen extends StatelessWidget {
  final Topic topic;

  const LessonListScreen({super.key, required this.topic});

  @override
  Widget build(BuildContext context) {
    final db = context.read<AppDb>();
    return Scaffold(
      appBar: AppBar(title: Text(topic.name)),
      body: FutureBuilder<List<Lesson>>(
        future: db.lessonsForTopic(topic.id),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting &&
              !snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          final lessons =
              (snapshot.data ?? const []).where((l) => l.status == 'complete').toList();
          if (lessons.isEmpty) {
            return const Center(
                child: Text('This bundle has no completed lessons'));
          }
          return ListView.separated(
            padding: const EdgeInsets.symmetric(vertical: 8),
            itemCount: lessons.length,
            separatorBuilder: (_, _) => const SizedBox(height: 4),
            itemBuilder: (context, i) {
              final l = lessons[i];
              return ListTile(
                leading: CircleAvatar(
                  child: Text('${l.orderIndex}'),
                ),
                title: Text(l.title ?? 'Lesson ${l.orderIndex}'),
                subtitle: Text(l.lastReviewedAt != null
                    ? 'Last reviewed: ${_shortDate(l.lastReviewedAt!)}'
                    : 'Never reviewed'),
                trailing: l.lastReviewedAt == null
                    ? Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(
                          color: Theme.of(context)
                              .colorScheme
                              .secondaryContainer,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Text('new'),
                      )
                    : null,
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => ReviewScreen(lessonId: l.id),
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }

  static String _shortDate(String iso) {
    // "2026-11-07T05:00:00+00:00" → "2026-11-07"
    return iso.length >= 10 ? iso.substring(0, 10) : iso;
  }
}
