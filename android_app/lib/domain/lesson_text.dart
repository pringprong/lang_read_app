import 'dart:convert';

/// One token of a sentence's stored segmentation (§4.3 / D-5).
class LessonTextToken {
  final String text;
  /// Whether the token is tappable (contains CJK characters).
  final bool isWord;

  const LessonTextToken(this.text, this.isWord);
}

final RegExp _cjk = RegExp(r'[\u3400-\u4DBF\u4E00-\u9FFF]');

/// Parses a sentence's stored segmentation JSON (a JSON **string** containing
/// a JSON array of tokens — nested JSON, see plan §3.2) into tokens.
List<LessonTextToken> parseSegmentation(String segmentationJson) {
  List<dynamic> tokens;
  try {
    tokens = jsonDecode(segmentationJson) as List<dynamic>;
  } catch (_) {
    // Fallback: treat the raw text character-by-character.
    return segmentationJson.runes
        .map((r) => String.fromCharCode(r))
        .map((t) => LessonTextToken(t, _cjk.hasMatch(t)))
        .toList();
  }
  return tokens
      .whereType<String>()
      .map((t) => LessonTextToken(t, _cjk.hasMatch(t)))
      .toList();
}

/// The styling state for a word token in the reading view.
class TokenStyle {
  /// First occurrence of a lesson new word → highlight + bold (D-1).
  final bool isNewWordFirstUse;
  /// Word currently on the New list → underline.
  final bool isAcquiring;

  const TokenStyle({required this.isNewWordFirstUse, required this.isAcquiring});
}

/// Tracks first occurrences across the whole lesson (new-word highlighting).
class NewWordTracker {
  final Set<String> _newWordTexts;
  final Set<String> _seen = {};

  NewWordTracker(Iterable<String> newWordTexts)
      : _newWordTexts = newWordTexts.toSet();

  /// Marks the token as seen and returns whether this is its first use.
  TokenStyle styleFor(String token, bool onNewList) {
    final firstUse = _newWordTexts.contains(token) && !_seen.contains(token);
    _seen.add(token);
    return TokenStyle(isNewWordFirstUse: firstUse, isAcquiring: onNewList);
  }
}
