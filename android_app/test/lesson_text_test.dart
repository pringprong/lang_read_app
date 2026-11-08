import 'package:flutter_test/flutter_test.dart';
import 'package:langread/domain/lesson_text.dart';

void main() {
  test('parses the nested segmentation JSON string', () {
    final tokens = parseSegmentation('["我","用","锅","做","饭","。"]');
    expect(tokens, hasLength(6));
    expect(tokens.first.text, '我');
    expect(tokens.first.isWord, isTrue);
    expect(tokens.last.text, '。');
    expect(tokens.last.isWord, isFalse);
  });

  test('falls back to character tokens on malformed JSON', () {
    final tokens = parseSegmentation('not json');
    expect(tokens, hasLength(8));
    expect(tokens.every((t) => t.text.length == 1), isTrue);
  });

  test('latin tokens are not tappable words', () {
    final tokens = parseSegmentation('["abc","我"]');
    expect(tokens.first.isWord, isFalse);
    expect(tokens.last.isWord, isTrue);
  });

  test('new-word tracker highlights only the first occurrence', () {
    final tracker = NewWordTracker(['锅']);
    final first = tracker.styleFor('锅', false);
    expect(first.isNewWordFirstUse, isTrue);
    final second = tracker.styleFor('锅', false);
    expect(second.isNewWordFirstUse, isFalse);
    // Other words never highlighted
    expect(tracker.styleFor('饭', false).isNewWordFirstUse, isFalse);
  });

  test('acquiring words (New list) are underlined', () {
    final tracker = NewWordTracker(const []);
    expect(tracker.styleFor('锅', true).isAcquiring, isTrue);
    expect(tracker.styleFor('锅', false).isAcquiring, isFalse);
  });
}
