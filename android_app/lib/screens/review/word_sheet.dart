import 'package:flutter/material.dart';

import '../../data/db.dart';
import '../../state/review_session.dart';

/// Word popup (§8.3): modal bottom sheet with word, pinyin, definition, list
/// status, and the allowed actions — which commit immediately (§8.7 note)
/// and queue a `word_action` event for the desktop.
Future<void> showWordSheet(
    BuildContext context, ReviewSession session, String token) async {
  final word = session.lookup(token);
  final theme = Theme.of(context);

  await showModalBottomSheet<void>(
    context: context,
    showDragHandle: true,
    builder: (sheetContext) => SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(token,
                style: theme.textTheme.headlineMedium!
                    .copyWith(fontWeight: FontWeight.w600)),
            const SizedBox(height: 4),
            Text(word?.pinyin ?? '',
                style: theme.textTheme.titleMedium
                    ?.copyWith(color: theme.colorScheme.primary)),
            const SizedBox(height: 8),
            Text(word?.definition ?? 'No definition available.'),
            const SizedBox(height: 8),
            Text(_statusLine(session, word),
                style: theme.textTheme.labelMedium
                    ?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
            const SizedBox(height: 16),
            ..._actions(context, sheetContext, session, token, word),
          ],
        ),
      ),
    ),
  );
}

String _statusLine(ReviewSession session, Word? word) {
  if (word == null) return 'Not on any list';
  switch (word.listState) {
    case 'learned':
      return 'Learned${word.dueAt != null ? ' · due ${word.dueAt!.substring(0, 10)}' : ''}';
    case 'new':
      return 'New (acquiring)';
    case 'basic':
      return 'Basic (known)';
    default:
      return word.listState;
  }
}

List<Widget> _actions(
    BuildContext context,
    BuildContext sheetContext,
    ReviewSession session,
    String token,
    Word? word) {
  final theme = Theme.of(context);
  Future<void> run(String action, String message) async {
    final handle = await session.applyWordAction(token, action);
    if (!sheetContext.mounted) return;
    Navigator.pop(sheetContext);
    if (handle == null) return;
    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(message),
      action: SnackBarAction(
        label: 'Undo',
        onPressed: () => session.undoWordAction(handle),
      ),
    ));
  }

  final buttons = <Widget>[];
  if (word == null) {
    buttons.add(FilledButton.tonalIcon(
      icon: const Icon(Icons.playlist_add),
      label: const Text('Add to Basic list'),
      onPressed: () => run('add_basic', 'Added "$token" to the Basic list.'),
    ));
    buttons.add(const SizedBox(height: 8));
    buttons.add(FilledButton.tonalIcon(
      icon: const Icon(Icons.lightbulb_outline),
      label: const Text('Add to New list'),
      onPressed: () => run('add_new', 'Added "$token" to the New list.'),
    ));
  } else if (word.listState == 'basic') {
    buttons.add(FilledButton.tonalIcon(
      icon: const Icon(Icons.lightbulb_outline),
      label: const Text('Move to New list'),
      onPressed: () => run('basic_to_new', 'Moved "$token" to the New list.'),
    ));
  } else {
    buttons.add(Text(
      'No list actions available for this word.',
      style: theme.textTheme.bodySmall
          ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
    ));
  }
  return buttons;
}
