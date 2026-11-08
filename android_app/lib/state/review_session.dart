import 'package:flutter/foundation.dart';

import '../data/bundle_reader.dart';
import '../data/db.dart';

/// The four-way rating (§8.6 / D-2). Serialized by name.
enum ReviewRating {
  difficult('difficult'),
  easy('easy'),
  standard('standard'),
  unchanged('unchanged');

  final String wire;
  const ReviewRating(this.wire);

  static ReviewRating fromWire(String wire) => values
      .firstWhere((r) => r.wire == wire, orElse: () => ReviewRating.standard);
}

enum ReviewStage { reading, wordReview, done }

/// A word-action applied from a popup (§8.3) with enough state to undo it.
class WordActionHandle {
  final int pendingEventId;
  final String wordText;
  final String action;
  final int? wordId;
  final String? previousState;
  final bool createdLocally;

  const WordActionHandle({
    required this.pendingEventId,
    required this.wordText,
    required this.action,
    required this.wordId,
    required this.previousState,
    required this.createdLocally,
  });
}

/// Per-lesson review session (§8.2–8.7): loads all content once, holds the
/// stage machine, ratings, and word-list actions; knows the complete/cancel
/// semantics (§8.7) — ratings and the review timestamp are only written on
/// `complete()`, while word popup actions commit immediately.
class ReviewSession extends ChangeNotifier {
  final AppDb db;
  final Lesson lesson;

  ReviewStage stage = ReviewStage.reading;
  bool completing = false;

  List<Sentence> sentences = [];
  List<LessonWord> lessonWords = [];
  Map<String, Word> wordByText = {};
  final Map<int, Word> _wordById = {};
  List<Word> learnedWords = [];
  Set<String> newWordTexts = {};
  /// wordId → chosen rating (default standard for all listed words).
  final Map<int, ReviewRating> _ratings = {};
  bool _loaded = false;

  ReviewSession(this.db, this.lesson);

  bool get loaded => _loaded;
  List<Word> get reviewWords => learnedWords;

  ReviewRating ratingFor(Word w) => _ratings[w.id] ?? ReviewRating.standard;
  void setRating(Word w, ReviewRating r) {
    _ratings[w.id] = r;
    notifyListeners();
  }

  void setRatingBulk(List<Word> words, ReviewRating r) {
    for (final w in words) {
      _ratings[w.id] = r;
    }
    notifyListeners();
  }

  Word? wordById(int id) => _wordById[id];

  /// Word status for a tapped token (§8.3 popup).
  Word? lookup(String text) => wordByText[text];

  void goToStage(ReviewStage s) {
    stage = s;
    notifyListeners();
  }

  Future<void> load() async {
    if (_loaded) return;
    sentences = await db.sentencesForLesson(lesson.id);
    lessonWords = await db.lessonWordsForLesson(lesson.id);
    final allWords = await db.allWords();
    wordByText = {for (final w in allWords) w.word: w};
    _wordById.addAll({for (final w in allWords) w.id: w});
    newWordTexts = {
      for (final lw in lessonWords.where((l) => l.role == 'new'))
        if (wordById(lw.wordId) != null) wordById(lw.wordId)!.word,
    };
    learnedWords = await db.learnedWordsForLesson(lesson.id);
    for (final w in learnedWords) {
      _ratings.putIfAbsent(w.id, () => ReviewRating.standard);
    }
    _loaded = true;
    notifyListeners();
  }

  // ---------- word popup actions (commit immediately, §8.7) ----------

  /// `add_new` / `add_basic` / `basic_to_new` — returns a handle for Undo.
  Future<WordActionHandle?> applyWordAction(String text, String action) async {
    switch (action) {
      case 'add_new':
      case 'add_basic':
        final target = action == 'add_new' ? 'new' : 'basic';
        final existing = await db.wordByText(text);
        if (existing != null) {
          if (existing.listState == target) return null;
          await db.setWordListState(existing.id, target);
          return _queueAction(text, action, existing.id, existing.listState,
              createdLocally: false);
        }
        final created = await db.createLocalWord(text, target);
        wordByText[text] = created;
        _wordById[created.id] = created;
        return _queueAction(text, action, created.id, null,
            createdLocally: true);
      case 'basic_to_new':
        final existing = await db.wordByText(text);
        if (existing == null || existing.listState != 'basic') return null;
        await db.setWordListState(existing.id, 'new');
        return _queueAction(text, action, existing.id, 'basic',
            createdLocally: false);
      default:
        return null;
    }
  }

  Future<WordActionHandle> _queueAction(String text, String action, int wordId,
      String? previousState,
      {required bool createdLocally}) async {
    if (!createdLocally) await _refreshWord(wordId);
    final eventId = await db.insertPendingEvent('word_action', {
      'type': 'word_action',
      'action': action,
      'word_text': text,
      'acted_at': utcnowIso(),
    });
    notifyListeners();
    return WordActionHandle(
      pendingEventId: eventId,
      wordText: text,
      action: action,
      wordId: wordId,
      previousState: previousState,
      createdLocally: createdLocally,
    );
  }

  /// Re-reads the word row after a list-state change and updates both maps.
  Future<void> _refreshWord(int wordId) async {
    final old = _wordById[wordId];
    if (old != null) {
      wordByText.remove(old.word);
      _wordById.remove(wordId);
    }
    final w = await db.wordById(wordId);
    if (w != null) {
      wordByText[w.word] = w;
      _wordById[w.id] = w;
    }
  }

  /// Undo a popup action (snackbar action).
  Future<void> undoWordAction(WordActionHandle h) async {
    await db.deletePendingEvent(h.pendingEventId);
    if (h.createdLocally) {
      if (h.wordId != null) await db.deleteWord(h.wordId!);
      wordByText.remove(h.wordText);
      if (h.wordId != null) _wordById.remove(h.wordId);
    } else if (h.wordId != null && h.previousState != null) {
      await db.setWordListState(h.wordId!, h.previousState!);
      await _refreshWord(h.wordId!);
    }
    notifyListeners();
  }

  // ---------- completion (§8.7) ----------

  /// Marks the review complete: queues one rating event per listed word
  /// (every rating, including `unchanged`, is meaningful to the desktop's
  /// SRS reconciliation) + one lesson_reviewed event; sets the local
  /// last-reviewed timestamp.
  Future<void> complete() async {
    if (completing) return;
    completing = true;
    notifyListeners();
    final now = utcnowIso();
    for (final w in learnedWords) {
      await db.insertPendingEvent('rating', {
        'type': 'rating',
        'word_id': w.id,
        'lesson_id': lesson.id,
        'rating': ratingFor(w).wire,
        'reviewed_at': now,
      });
    }
    await db.insertPendingEvent('lesson_reviewed', {
      'type': 'lesson_reviewed',
      'lesson_id': lesson.id,
      'reviewed_at': now,
    });
    await db.markLessonReviewedAt(lesson.id, now);
    stage = ReviewStage.done;
    completing = false;
    notifyListeners();
  }

  /// Cancel (§8.7): writes nothing — ratings and the review timestamp are
  /// discarded; already-confirmed word popup actions stay (by design).
  void cancel() {
    _ratings.clear();
    stage = ReviewStage.reading;
    notifyListeners();
  }
}
