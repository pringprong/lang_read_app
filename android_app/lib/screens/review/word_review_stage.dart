import 'package:flutter/material.dart';

import '../../data/db.dart';
import '../../state/review_session.dart';

/// Word review stage (§8.6): this lesson's Learned words, each with the
/// 4-way rating (default standard), multi-select + select-all + bulk apply,
/// then "Mark review complete" (§8.7).
class WordReviewStage extends StatefulWidget {
  final ReviewSession session;

  const WordReviewStage({super.key, required this.session});

  @override
  State<WordReviewStage> createState() => _WordReviewStageState();
}

class _WordReviewStageState extends State<WordReviewStage> {
  final Set<int> _selected = {};

  @override
  Widget build(BuildContext context) {
    final session = widget.session;
    return ListenableBuilder(
      listenable: session,
      builder: (context, _) {
        final words = session.reviewWords;
        return Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      'Rate the words you just read',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ),
                  TextButton.icon(
                    icon: Icon(
                      _selected.length == words.length && words.isNotEmpty
                          ? Icons.check_box
                          : Icons.check_box_outline_blank,
                    ),
                    label: const Text('All'),
                    onPressed: words.isEmpty
                        ? null
                        : () => setState(() {
                              _selected.length == words.length
                                  ? _selected.clear()
                                  : _selected
                                      .addAll(words.map((w) => w.id));
                            }),
                  ),
                ],
              ),
            ),
            if (_selected.isNotEmpty)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                child: _BulkBar(
                  session: session,
                  selectedIds: _selected,
                  onApplied: () => setState(() => _selected.clear()),
                ),
              ),
            Expanded(
              child: words.isEmpty
                  ? const Center(
                      child: Padding(
                        padding: EdgeInsets.all(24),
                        child: Text(
                            'No Learned words in this lesson.\n'
                            'You can mark the review complete.'),
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.only(bottom: 16),
                      itemCount: words.length,
                      itemBuilder: (context, i) {
                        final w = words[i];
                        return _WordRow(
                          word: w,
                          rating: session.ratingFor(w),
                          selected: _selected.contains(w.id),
                          onToggleSelect: () => setState(() {
                            _selected.contains(w.id)
                                ? _selected.remove(w.id)
                                : _selected.add(w.id);
                          }),
                          onRating: (r) => session.setRating(w, r),
                        );
                      },
                    ),
            ),
            SafeArea(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
                child: Row(
                  children: [
                    TextButton(
                      onPressed: () => session.goToStage(ReviewStage.reading),
                      child: const Text('Back to text'),
                    ),
                    const Spacer(),
                    FilledButton.icon(
                      icon: const Icon(Icons.done_all),
                      label: session.completing
                          ? const Text('Completing…')
                          : const Text('Mark review complete'),
                      onPressed: session.completing
                          ? null
                          : () => session.complete(),
                    ),
                  ],
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}

class _BulkBar extends StatelessWidget {
  final ReviewSession session;
  final Set<int> selectedIds;
  final VoidCallback onApplied;

  const _BulkBar(
      {required this.session,
      required this.selectedIds,
      required this.onApplied});

  @override
  Widget build(BuildContext context) {
    final selected = session.reviewWords
        .where((w) => selectedIds.contains(w.id))
        .toList();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Apply to ${selected.length} selected:',
                style: Theme.of(context).textTheme.labelMedium),
            const SizedBox(height: 4),
            Wrap(
              spacing: 8,
              children: [
                for (final r in ReviewRating.values)
                  ActionChip(
                    label: Text(r.wire),
                    onPressed: () {
                      session.setRatingBulk(selected, r);
                      onApplied();
                    },
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _WordRow extends StatelessWidget {
  final Word word;
  final ReviewRating rating;
  final bool selected;
  final VoidCallback onToggleSelect;
  final void Function(ReviewRating) onRating;

  const _WordRow({
    required this.word,
    required this.rating,
    required this.selected,
    required this.onToggleSelect,
    required this.onRating,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return ListTile(
      dense: true,
      leading: Checkbox(
        value: selected,
        onChanged: (_) => onToggleSelect(),
      ),
      title: Text(word.word,
          style: theme.textTheme.titleMedium!
              .copyWith(fontWeight: FontWeight.w600)),
      subtitle: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (word.pinyin != null && word.pinyin!.isNotEmpty)
            Text(word.pinyin!,
                style: TextStyle(color: theme.colorScheme.primary)),
          if (word.definition != null && word.definition!.isNotEmpty)
            Text(word.definition!),
          const SizedBox(height: 4),
          Wrap(
            spacing: 6,
            children: [
              for (final r in ReviewRating.values)
                ChoiceChip(
                  label: Text(r.wire),
                  selected: rating == r,
                  onSelected: (_) => onRating(r),
                  visualDensity: VisualDensity.compact,
                ),
            ],
          ),
        ],
      ),
    );
  }
}
