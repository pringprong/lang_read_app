"""Dictionary service tests: CC-CEDICT parsing, lookup, pinyin conversion."""

from __future__ import annotations

import gzip

from langread.services.dictionary import (
    CEDICT_GZ,
    DictEntry,
    DictionaryService,
    get_dictionary,
    pinyin_tone_marks,
)

CEDICT_SAMPLE = "\n".join(
    [
        "# CC-CEDICT sample fixture",
        "#! cedict_b52_1_0_ts_utf-8_mdbg",
        "廚房 厨房 [chu2 fang2] /kitchen/CL:間|间[jian1]/",
        "學習 学习 [xue2 xi2] /to learn; to study/",
        "你好 你好 [ni3 hao3] /hello/hi/goodbye/see you/",
        "北京 北京 [Bei3 jing1] /Beijing, capital of China/",
        "女 女 [nu:3] /female/woman/",
        "的 的 [de5] /of/particle/",
        "覆 覆 [fu4] /variant of 復|复[fu4]/",
        "覆 覆 [fu4] /to cover/",
        "多 多 [duo1] /many/much/more/most/excessive/",
        "長 长 [chang2] /long/length/",
    ]
) + "\n"


def _write_fixture(tmp_path, name="cedict.txt", content=CEDICT_SAMPLE):
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


# ---- pinyin tone marks ----


def test_tone_mark_placement():
    assert pinyin_tone_marks("chu2 fang2") == "chú fáng"
    assert pinyin_tone_marks("Bei3 jing1") == "Běi jīng"  # proper noun caps
    assert pinyin_tone_marks("nu:3") == "nǚ"              # u: → ü
    assert pinyin_tone_marks("de5") == "de"               # neutral tone
    assert pinyin_tone_marks("ni3 hao3 ma5") == "nǐ hǎo ma"
    assert pinyin_tone_marks("liu2") == "liú"             # iu → mark the u
    assert pinyin_tone_marks("gui1") == "guī"             # ui → mark the i
    assert pinyin_tone_marks("hao3") == "hǎo"             # a takes the mark
    assert pinyin_tone_marks("lei2") == "léi"             # e takes the mark
    assert pinyin_tone_marks("") is None


# ---- parsing and lookup ----


def test_lookup_by_simplified_headword(tmp_path):
    service = DictionaryService(_write_fixture(tmp_path))
    entry = service.lookup("厨房")
    assert entry == DictEntry(headword="厨房", pinyin="chú fáng",
                              definition="kitchen")
    # traditional form is not an index key
    assert service.lookup("廚房") is None
    assert service.lookup("不存在") is None
    assert service.lookup("") is None


def test_classifier_references_are_stripped(tmp_path):
    service = DictionaryService(_write_fixture(tmp_path))
    entry = service.lookup("厨房")
    assert "CL" not in entry.definition


def test_senses_are_capped_at_three(tmp_path):
    service = DictionaryService(_write_fixture(tmp_path))
    entry = service.lookup("多")
    assert entry.definition == "many; much; more"
    entry = service.lookup("你好")
    assert entry.definition == "hello; hi; goodbye"


def test_variant_entry_is_deprioritized(tmp_path):
    service = DictionaryService(_write_fixture(tmp_path))
    entry = service.lookup("覆")
    assert entry.definition == "to cover"


def test_proper_noun_sense_is_deprioritized(tmp_path):
    """CC-CEDICT lists name senses first for some words; the everyday
    sense wins when one exists, and a proper-noun-only word still resolves."""
    content = (
        "獅子 狮子 [Shi1 zi5] /Leo (star sign)/Shihtzu township in Pingtung/\n"
        "獅子 狮子 [shi1 zi5] /lion/\n"
        "北京 北京 [Bei3 jing1] /Beijing, capital of China/\n"
    )
    service = DictionaryService(_write_fixture(tmp_path, "proper.txt", content))
    lion = service.lookup("狮子")
    assert lion.pinyin == "shī zi"
    assert lion.definition == "lion"
    beijing = service.lookup("北京")  # only a proper-noun entry exists
    assert beijing.definition == "Beijing, capital of China"


def test_definition_length_is_capped(tmp_path):
    long_sense = "x" * 250
    path = _write_fixture(
        tmp_path, "long.txt",
        f"長 长 [chang2] /{long_sense}/\n",
    )
    service = DictionaryService(path)
    entry = service.lookup("长")
    assert len(entry.definition) == 200
    assert entry.definition.endswith("…")


def test_gzipped_file_is_supported(tmp_path):
    path = tmp_path / "cedict.txt.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(CEDICT_SAMPLE)
    service = DictionaryService(path)
    assert service.lookup("学习").definition == "to learn; to study"


def test_missing_file_disables_the_service(tmp_path):
    service = DictionaryService(tmp_path / "nope.txt")
    assert service.available is False
    assert service.lookup("厨房") is None


def test_corrupt_file_disables_the_service(tmp_path):
    path = tmp_path / "broken.txt.gz"
    path.write_bytes(b"not gzip at all")
    service = DictionaryService(path)
    assert service.available is False


# ---- get_dictionary() configuration ----


def test_get_dictionary_disabled(monkeypatch):
    monkeypatch.setenv("LANGREAD_CEDICT", "off")
    assert get_dictionary() is None


def test_get_dictionary_env_override(tmp_path, monkeypatch):
    path = _write_fixture(tmp_path)
    monkeypatch.setenv("LANGREAD_CEDICT", str(path))
    service = get_dictionary()
    assert service is not None
    assert service.lookup("厨房").definition == "kitchen"
    # cached per path: the same object is returned on the next call
    assert get_dictionary() is service


def test_get_dictionary_default_uses_bundled_resource(monkeypatch):
    monkeypatch.delenv("LANGREAD_CEDICT", raising=False)
    service = get_dictionary()
    assert service is not None
    assert service.lookup("厨房") == DictEntry(
        headword="厨房", pinyin="chú fáng", definition="kitchen"
    )
    assert CEDICT_GZ.is_file()
