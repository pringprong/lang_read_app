import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';

import '../../data/db.dart';
import '../../domain/lesson_text.dart';
import '../../state/review_session.dart';

/// The lesson text (§8.2–8.4): paragraphs of flowing rich text where every
/// Chinese word token is tappable, new words are highlighted on first use
/// (static, D-1), acquiring (New-list) words are underlined, and each
/// sentence ends with a translation toggle chip that reveals the stored
/// translation inline.
class LessonTextView extends StatefulWidget {
  final ReviewSession session;
  final void Function(String token) onWordTap;

  const LessonTextView(
      {super.key, required this.session, required this.onWordTap});

  @override
  State<LessonTextView> createState() => _LessonTextViewState();
}

class _LessonTextViewState extends State<LessonTextView> {
  final Set<int> _shownTranslations = {};
  final List<TapGestureRecognizer> _recognizers = [];
  late final NewWordTracker _tracker;

  @override
  void initState() {
    super.initState();
    _tracker = NewWordTracker(widget.session.newWordTexts);
  }

  @override
  void dispose() {
    _disposeRecognizers();
    super.dispose();
  }

  void _disposeRecognizers() {
    for (final r in _recognizers) {
      r.dispose();
    }
    _recognizers.clear();
  }

  @override
  Widget build(BuildContext context) {
    _disposeRecognizers();
    final session = widget.session;
    if (!session.loaded) {
      return const Center(child: CircularProgressIndicator());
    }
    final theme = Theme.of(context);

    // Group sentences into paragraphs.
    final paragraphs = <int, List<Sentence>>{};
    for (final s in session.sentences) {
      paragraphs.putIfAbsent(s.paraIndex, () => []).add(s);
    }
    final paraIndexes = paragraphs.keys.toList()..sort();

    return ListenableBuilder(
      listenable: session,
      builder: (context, _) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          for (final pi in paraIndexes) ...[
            if (pi != paraIndexes.first) const SizedBox(height: 16),
            Text.rich(
              TextSpan(
                children: [
                  for (final s in paragraphs[pi]!)
                    ..._sentenceSpans(s, session, theme),
                ],
              ),
              style: theme.textTheme.bodyLarge!.copyWith(
                height: 1.7,
                fontSize: 20,
              ),
            ),
          ],
        ],
      ),
    );
  }

  List<InlineSpan> _sentenceSpans(
      Sentence s, ReviewSession session, ThemeData theme) {
    final spans = <InlineSpan>[];
    for (final token in parseSegmentation(s.segmentation)) {
      spans.add(_tokenSpan(token, session, theme));
    }
    if (s.translation != null && s.translation!.isNotEmpty) {
      spans.add(_translationChip(s, theme));
      if (_shownTranslations.contains(s.id)) {
        spans.add(const WidgetSpan(child: SizedBox(width: 6)));
        spans.add(TextSpan(
          text: s.translation,
          style: theme.textTheme.bodyMedium!.copyWith(
            fontStyle: FontStyle.italic,
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ));
      }
    }
    spans.add(const TextSpan(text: ' '));
    return spans;
  }

  InlineSpan _tokenSpan(
      LessonTextToken token, ReviewSession session, ThemeData theme) {
    if (!token.isWord) {
      return TextSpan(text: token.text);
    }
    final word = session.lookup(token.text);
    final style = _tracker.styleFor(
        token.text, word != null && word.listState == 'new');
    final base = theme.textTheme.bodyLarge!.copyWith(
      fontSize: 20,
      color: word != null
          ? theme.colorScheme.onSurface
          : theme.colorScheme.onSurfaceVariant,
      fontWeight: style.isNewWordFirstUse ? FontWeight.w700 : null,
      decoration: style.isAcquiring ? TextDecoration.underline : null,
      background: style.isNewWordFirstUse
          ? (Paint()
            ..color = theme.colorScheme.primaryContainer
            ..style = PaintingStyle.fill)
          : null,
    );
    final recognizer = TapGestureRecognizer()
      ..onTap = () => widget.onWordTap(token.text);
    _recognizers.add(recognizer);
    return TextSpan(
      text: token.text,
      style: base,
      recognizer: recognizer,
    );
  }

  InlineSpan _translationChip(Sentence s, ThemeData theme) {
    final shown = _shownTranslations.contains(s.id);
    return WidgetSpan(
      alignment: PlaceholderAlignment.middle,
      child: GestureDetector(
        onTap: () => setState(() {
          if (shown) {
            _shownTranslations.remove(s.id);
          } else {
            _shownTranslations.add(s.id);
          }
        }),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
          margin: const EdgeInsets.symmetric(horizontal: 2),
          decoration: BoxDecoration(
            color: theme.colorScheme.secondaryContainer,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            shown ? '▾译' : '▸译',
            style: theme.textTheme.bodySmall!.copyWith(
              color: theme.colorScheme.onSecondaryContainer,
            ),
          ),
        ),
      ),
    );
  }
}
