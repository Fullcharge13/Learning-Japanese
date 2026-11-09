"""data/words.csv 점검: 읽기가 JMdict 부분집합과 맞음, 가나 장 짜임, 장 구성(설계 §3-1)"""
import json, os, sys
import pytest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from make_lessons import load_words, CHAPTER_TITLES  # noqa: E402
from jmdict_subset import candidates, OUT  # noqa: E402

WORDS = load_words(os.path.join(ROOT, "data", "words.csv"))


def test_readings_match_jmdict():
    if not os.path.exists(OUT):
        pytest.skip("vendor/jmdict/subset.json 없음: tools/jmdict_subset.py로 만드세요")
    pairs = {tuple(p) for p in json.load(open(OUT, encoding="utf-8"))["pairs"]}
    bad = [w["jp"] for w in WORDS if w["pos"] != "kana" and not any(c in pairs for c in candidates(w["jp"]))]
    assert not bad, "JMdict에 없는 표기·읽기(단어 표를 고쳤으면 subset을 다시 만드세요): %s" % bad


def test_kana_chapters():
    for ch, lo, hi in ((1, "ぁ", "ゟ"), (2, "゠", "ヿ")):
        ws = [w for w in WORDS if w["chapter"] == ch]
        assert len(ws) == 69 and all(w["pos"] == "kana" and len(w["jp"]) == 1 and lo <= w["jp"] <= hi for w in ws)
        assert not {"ぢ", "づ", "ヂ", "ヅ"} & {w["jp"] for w in ws}


def test_chapters_and_titles():
    chs = sorted({w["chapter"] for w in WORDS})
    assert chs == list(range(1, 27)) and {c for c in CHAPTER_TITLES if c < 100} == set(chs)  # 100 이상은 JLPT 장(test_jlpt_n5)
    for ch in range(3, 27):
        n = len([w for w in WORDS if w["chapter"] == ch])
        assert 10 <= n <= 15, (ch, n)


def test_no_romaji():
    assert not [w for w in WORDS if any("a" <= c.lower() <= "z" for c in w["jp"] + w["ko"] + w["note"])]


def test_no_duplicate_words_across_chapters():
    """같은 단어(표기)를 두 장에 두지 않음 — 복습·취약 단어 이름표가 겹치지 않게"""
    seen = {}
    for w in WORDS:
        if w["pos"] == "kana":
            continue
        assert w["jp"] not in seen, (w["jp"], seen.get(w["jp"]), w["id"])
        seen[w["jp"]] = w["id"]


def test_candidates_cover_polite_verb_forms():
    assert ("行く", "いく") in candidates("行{い}きましょう")
    assert ("食べる", "たべる") in candidates("食{た}べましょう")
    assert ("できる", "できる") in candidates("できません")
    assert ("疲れる", "つかれる") in candidates("疲{つか}れました")
