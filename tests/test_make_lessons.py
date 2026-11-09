import json, os, sys
import pytest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from make_lessons import load_words, build_chapter, kana_units, kana, plain, sound_key, main

FX = os.path.join(ROOT, "tests", "fixtures")
WORDS = os.path.join(FX, "words-mini.csv")
HEAD = "id,chapter,unit,jp,ko,pos,status,note\n"


def _ch(n):
    return build_chapter(load_words(WORDS), n)


def _items(ch):
    return [it for l in ch["LESSONS"] for it in l["items"]]


def _bad_csv(tmp_path, row):
    p = tmp_path / "w.csv"
    p.write_text(HEAD + "c3-001,3,1,どこ,어디,noun,ok,\n" + row + "\n", encoding="utf-8")
    return str(p)


@pytest.mark.parametrize("row, msg", [
    ("c3-002,3,1,学生{がくせい,학생,noun,ok,", "line 3: unpaired braces"),
    ("c3-002,3,1,,학생,noun,ok,", "line 3: empty jp"),
    ("c3-002,3,1,学生{がくせい},,noun,ok,", "line 3: empty ko"),
    ("c3-002,3,1,学生{がくせい},학생,noun,maybe,", "line 3: unknown status"),
    ("c3-001,3,1,学生{がくせい},학생,noun,ok,", "line 3: duplicate id c3-001"),
    ("c3-002,3,1,学生{학생},학생,noun,ok,", "line 3: reading must be kana"),
])
def test_parse_errors(tmp_path, row, msg):
    with pytest.raises(ValueError, match=msg):
        load_words(_bad_csv(tmp_path, row))


def test_hold_excluded():
    words = {w["id"] for w in load_words(WORDS)}
    assert "c3-015" not in words
    assert "先生" not in json.dumps(_ch(3), ensure_ascii=False)


def test_kana_and_plain():
    assert kana("行{い}きます") == "いきます" and plain("行{い}きます") == "行きます"


def test_kana_units():
    assert kana_units("きょう") == ["きょ", "う"]
    assert kana_units("がっこう") == ["が", "っ", "こ", "う"]
    assert kana_units("コーヒー") == ["コ", "ー", "ヒ", "ー"]
    assert kana_units("ジュース") == ["ジュ", "ー", "ス"]


def test_order_items_use_kana_units_2_to_6():
    for it in _items(_ch(3)):
        if it["type"] == "order":
            assert 2 <= len(it["lines"]) <= 6
            assert all(len(x) <= 2 for x in it["lines"])
    lines = {it["concept"]: it["lines"] for it in _items(_ch(3)) if it["type"] == "order"}
    assert "c3-014" not in lines  # ありがとうございます: 10단위라 order 없음
    if "c3-005" in lines:
        assert lines["c3-005"] == ["きょ", "う"]


def test_kana_chapter_has_no_order_items():
    assert {it["type"] for it in _items(_ch(1))} <= {"choice", "check"}


def test_no_twin_options():
    """같은 소리(あ/ア, お/を)나 같은 뜻(トイレ/お手洗い = 화장실)이 정답과 함께 보기에 나오지 않음"""
    words = load_words(WORDS)
    by_jp = {w["jp"]: w for w in words}
    by_ko = {}
    for w in words:
        by_ko.setdefault(sound_key(w["ko"]), set()).add(w["jp"])
    for n in (1, 3):
        for it in _items(_ch(n)):
            if it["type"] == "order":
                continue
            w = next(x for x in words if x["id"] == it["concept"])
            opts = it["options"]
            assert opts[it["answer"]] in (w["jp"], w["ko"])
            for d in opts[1:]:
                if d in by_jp:  # 일본어 보기: 정답과 같은 뜻이면 안 됨
                    assert sound_key(by_jp[d]["ko"]) != sound_key(w["ko"]), (it["q"], opts)
                else:           # 한국어 보기: 같은 소리·뜻이면 안 됨
                    assert sound_key(d) != sound_key(w["ko"]), (it["q"], opts)


def test_questions_are_korean_with_furigana():
    ch = _ch(3)
    qs = [it["q"] for it in _items(ch)]
    assert any("駅{えき}" in q for q in qs) or any("学校{がっこう}" in q for q in qs)
    j2k = [it for it in _items(ch) if it["type"] == "choice" and it["q"].endswith("무슨 뜻일까요?")]
    assert j2k
    k = [it for it in _items(_ch(1)) if it["q"].endswith("어떻게 읽을까요?")]
    assert k


def test_chunks_and_exam():
    ch = _ch(3)
    *normal, exam = ch["LESSONS"]
    sizes = [sum(len(c["words"]) for c in l["cards"]) for l in normal]
    assert sizes == [10, 5], sizes  # 단원1 10개(8+2 → 붙임), 단원2 6개 중 보류 1 → 5
    assert exam["isExam"] is True and exam["id"] == "3-3"
    for l in normal:
        n_words = sum(len(c["words"]) for c in l["cards"])
        assert l["items"][-1]["type"] == "check"
        assert len([it for it in l["items"] if it["type"] != "check"]) == max(6, n_words)
    assert len([it for it in exam["items"] if it["type"] != "check"]) == 8
    assert ch["CHAPTER"] == {"id": 3, "title": "1과 · 장소 묻기"}
    assert _ch(1)["CHAPTER"]["title"] == "히라가나"


def test_cards_carry_jp_and_ko():
    w = _ch(3)["LESSONS"][0]["cards"][0]["words"][0]
    assert set(w) == {"jp", "ko"} and w["jp"] == "すみません"


def test_deterministic():
    assert json.dumps(_ch(3), ensure_ascii=False) == json.dumps(_ch(3), ensure_ascii=False)


def test_every_word_used():
    for n in (1, 3):
        used = {it["concept"] for it in _items(_ch(n))}
        want = {w["id"] for w in load_words(WORDS) if w["chapter"] == n}
        assert want <= used, want - used


def test_main_writes_files(tmp_path):
    out = tmp_path / "lessons"
    concepts = tmp_path / "concepts.js"
    main(out_dir=str(out), words_file=WORDS, concepts_file=str(concepts))
    assert sorted(os.listdir(out)) == ["ch1.js", "ch3.js"]
    c = concepts.read_text(encoding="utf-8")
    assert '"name": "駅{えき} · 역"' in c and "c3-015" not in c


def test_items_carry_the_japanese_to_speak():
    words = {w["id"]: w for w in load_words(WORDS)}
    for n in (1, 3):
        for it in _items(_ch(n)):
            assert it["say"] == words[it["concept"]]["jp"]
    # 질문 옆 🔊는 듣고도 답이 드러나지 않는 일→한(단어 장)만. 가나 장은 소리가 곧 답이라 없음
    for it in _items(_ch(3)):
        assert it.get("qSay", False) == it["q"].endswith("무슨 뜻일까요?"), it["q"]
    assert not any(it.get("qSay") for it in _items(_ch(1)))


def test_twin_column_keeps_confusable_words_apart(tmp_path):
    """twin 칸이 같은 단어끼리는 뜻이 달라도 서로 오답 보기로 나오지 않음(かわいい↔きれい 등)"""
    rows = [HEAD.strip() + ",twin"] + ["c3-%03d,3,1,%s,%s,adj,ok,,%s" % (i + 1, jp, ko, tw) for i, (jp, ko, tw) in enumerate([
        ("かわいい", "귀여워요", "a"), ("きれい", "예뻐요", "a"), ("高{たか}い", "비싸요", ""), ("安{やす}い", "싸요", ""),
        ("寒{さむ}い", "추워요", ""), ("暑{あつ}い", "더워요", ""), ("楽{たの}しい", "즐거워요", "b"), ("おもしろい", "재미있어요", "b")])]
    p = tmp_path / "w.csv"
    p.write_text("\n".join(rows) + "\n", encoding="utf-8")
    words = load_words(str(p))
    for it in [it for l in build_chapter(words, 3)["LESSONS"] for it in l["items"] if it["type"] != "order"]:
        o = set(it["options"])
        assert not ({"귀여워요", "예뻐요"} <= o or {"かわいい", "きれい"} <= o), it
        assert not ({"즐거워요", "재미있어요"} <= o or {"楽{たの}しい", "おもしろい"} <= o), it


@pytest.mark.parametrize("row, msg", [
    ("c3-002,,1,学生{がくせい},학생,noun,ok,", "line 3: chapter and unit must be numbers"),
    ("c3-002,3,1,学生{がくせい},학생,,ok,", "line 3: empty pos"),
    ("c3-002,3,1,学生{がくせい},학생,noun,ok,学校の話", "line 3: kanji without furigana in note"),
    ("c3-002,3,1,学生,학생,noun,ok,", "line 3: kanji without furigana in jp"),
])
def test_more_parse_errors(tmp_path, row, msg):
    with pytest.raises(ValueError, match=msg):
        load_words(_bad_csv(tmp_path, row))
