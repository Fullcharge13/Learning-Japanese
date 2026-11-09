"""N5 완성: 문법(115~117)·한자(118~119)·모의고사(120) 데이터와 생성물 점검 (N5 완성 설계 §4~§6)"""
import json, os, re, sys
import pytest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from make_lessons import RUBY, BARE_KANJI, main, plain  # noqa: E402

GRAMMAR = os.path.join(ROOT, "data", "jlpt-n5-grammar.json")


def _bare(s):
    return BARE_KANJI.search(RUBY.sub("", s))


def _js_const(path, name):
    text = open(path, encoding="utf-8").read()
    return json.loads(text.split("export const %s = " % name, 1)[1].split(";\n", 1)[0])


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    d = tmp_path_factory.mktemp("extra")
    main(out_dir=str(d), concepts_file=str(d / "concepts.js"), jlpt_file=str(d / "jlpt.js"))
    return d


# ---- 문법 ----
def test_grammar_points():
    from make_lessons import load_grammar
    ps = load_grammar(GRAMMAR)
    assert [p["id"] for p in ps] == ["g5-%02d" % i for i in range(1, 19)]
    assert [p["chapter"] for p in ps] == [115] * 6 + [116] * 6 + [117] * 6


def test_grammar_items():
    from make_lessons import load_grammar
    for p in load_grammar(GRAMMAR):
        assert len(p["items"]) >= 5, p["id"]
        assert not _bare(p["explain"]), p["id"]
        for it in p["items"]:
            if it["type"] == "fill":
                opts = [it["answer"]] + it["wrong"]
                assert len(opts) == 4 and len({plain(o) for o in opts}) == 4, (p["id"], opts)
                for s in [it["pre"], it["post"]] + opts:
                    assert not _bare(s), (p["id"], s)
                assert it["ko"]
            else:
                assert 3 <= len(it["lines"]) <= 6 and len(set(it["lines"])) == len(it["lines"]), (p["id"], it)
                assert not any(_bare(x) for x in it["lines"]), it


def test_grammar_built(built):
    for n in (115, 116, 117):
        ch = _js_const(built / ("ch%d.js" % n), "CHAPTER")
        ls = _js_const(built / ("ch%d.js" % n), "LESSONS")
        assert ch["title"] == "N5 · %d장 문법 %d" % (n - 100, n - 114)
        assert len(ls) == 7 and ls[-1].get("isExam")
        for l in ls:
            for it in l["items"]:
                assert it.get("kind") in ("grammar", "build"), it
                if it["type"] == "order":
                    assert "".join(it["lines"]) == it["say"]
                else:
                    assert it["sentence"]["jp"].count("＿＿") == 1 and it["options"][it["answer"]]
    ls = _js_const(built / "ch115.js", "LESSONS")
    assert ls[0]["id"] == "115-1" and ls[0]["title"] == "명사문 です" and ls[0]["cards"]
    cs = {c["id"]: c for c in _js_const(built / "concepts.js", "CONCEPTS")}
    assert cs["g5-01"]["chapter"] == 115 and cs["g5-01"]["name"].startswith("문법 · ")


# ---- 한자 ----
def test_kanji_all_79():
    from make_lessons import load_kanji
    ks = load_kanji()
    v = json.load(open(os.path.join(ROOT, "vendor", "kanji", "n5.json"), encoding="utf-8"))
    assert sorted(k["kanji"] for k in ks) == sorted(v) and len(ks) == 79
    assert all(k["ko"].strip() and k["chapter"] in (118, 119) for k in ks)


def test_kanji_words_found():
    from make_lessons import load_kanji, kanji_words
    ws = kanji_words()
    for k in load_kanji():
        assert ws.get(k["kanji"]), k["kanji"]


def test_kanji_built(built):
    seen = set()
    for n in (118, 119):
        ch = _js_const(built / ("ch%d.js" % n), "CHAPTER")
        assert ch["title"] == "N5 · %d장 한자 %d" % (n - 100, n - 117)
        for l in _js_const(built / ("ch%d.js" % n), "LESSONS"):
            for it in l["items"]:
                assert it["kind"] in ("kanji-read", "kanji-write"), it
                o = it["options"]
                assert len(o) == 4 and len(set(o)) == 4 and it["answer"] == 0, it  # distinct readings / spellings
                if it["kind"] == "kanji-read":
                    assert all(not BARE_KANJI.search(x) for x in o), o
                seen.add(it["concept"])
    assert len({c for c in seen if c.startswith("k5-")}) == 79
    cs = {c["id"]: c for c in _js_const(built / "concepts.js", "CONCEPTS")}
    assert cs["k5-日"]["name"] == "한자 · 日 날 일" and cs["k5-日"]["chapter"] == 118


# ---- 모의고사 ----
MOCK_MIX = {"kanji-read": 4, "kanji-write": 3, None: 4, "grammar": 4, "build": 2, "reading": 2, "listen": 6}


def test_mock_three_25(built):
    ch = _js_const(built / "ch120.js", "CHAPTER")
    assert ch["title"] == "N5 · 20장 모의고사"
    ls = _js_const(built / "ch120.js", "LESSONS")
    assert [l["title"] for l in ls] == ["모의고사 1", "모의고사 2", "모의고사 3"]
    seen = []
    for l in ls:
        assert l["isExam"] and len(l["items"]) == 25, (l["id"], len(l["items"]))
        mix = {}
        for it in l["items"]:
            mix[it.get("kind")] = mix.get(it.get("kind"), 0) + 1
        assert mix == MOCK_MIX, mix
        assert all(it.get("sentence") for it in l["items"] if it.get("kind") is None)  # 문맥 = 예문 빈칸
        seen.append(tuple(json.dumps([it["q"], it.get("sentence"), it.get("say"), it["options"] if "options" in it else it["lines"]], ensure_ascii=False) for it in l["items"]))
    for a, b in ((0, 1), (0, 2), (1, 2)):
        assert not set(seen[a]) & set(seen[b]), "회마다 다른 문제"  # 시드가 달라 겹치지 않음
    cs = {c["id"] for c in _js_const(built / "concepts.js", "CONCEPTS")}
    assert {it["concept"] for l in ls for it in l["items"]} <= cs


def test_mock_listen_no_japanese_in_q(built):
    ja = re.compile(r"[ぁ-ゟ゠-ヿ㐀-鿿]")
    n = 0
    for l in _js_const(built / "ch120.js", "LESSONS"):
        for it in l["items"]:
            if it.get("kind") == "listen":
                n += 1
                assert it["qSay"] and it["say"] and not ja.search(it["q"]) and "sentence" not in it, it
    assert n == 18


def test_build_accepts_free_order(built):
    """조사로 역할이 정해진 덩어리는 순서를 바꿔도 맞음: accept는 카드의 순열이고 생성물에 실림"""
    from make_lessons import load_grammar
    acc = {p["id"]: it.get("accept", []) for p in load_grammar(GRAMMAR) for it in p["items"] if it["type"] == "build"}
    assert ["電車{でんしゃ}で", "毎日{まいにち}", "会社{かいしゃ}へ", "行{い}きます。"] in acc["g5-05"]
    assert ["手紙{てがみ}を", "友達{ともだち}に", "書{か}きます。"] in acc["g5-04"]
    for p in load_grammar(GRAMMAR):
        for it in p["items"]:
            for a in it.get("accept", []):
                assert sorted(a) == sorted(it["lines"]) and a != it["lines"], (p["id"], a)
    ls = _js_const(built / "ch115.js", "LESSONS")
    assert any(it.get("accept") for l in ls for it in l["items"] if it["type"] == "order")


def test_kanji_readings_handwritten(built):
    """한자 카드 읽기는 손으로 고른 N5 읽기(음 가타카나, 훈 오쿠리가나 괄호). 음은 KANJIDIC에 있는 것만"""
    import csv
    rows = {r["kanji"]: r for r in csv.DictReader(open(os.path.join(ROOT, "data", "jlpt-n5-kanji.csv"), encoding="utf-8"))}
    kd = json.load(open(os.path.join(ROOT, "vendor", "kanji", "n5.json"), encoding="utf-8"))
    hira = lambda s: "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)
    assert len(rows) == 79
    for k, r in rows.items():
        on = [x for x in r["on"].split("·") if x != "-"]
        kun = [x for x in r["kun"].split("·") if x != "-"]
        assert on or kun, k
        assert len(set(on)) == len(on) and len(set(kun)) == len(kun), k
        assert all(re.fullmatch(r"[ァ-ヶー]+", x) for x in on), (k, on)
        assert all(re.fullmatch(r"[ぁ-ゖ]+(\([ぁ-ゖ]+\))?", x) for x in kun), (k, kun)
        assert all(hira(x) in [y.replace(".", "").replace("-", "") for y in kd[k]["on"]] for x in on), (k, on, kd[k]["on"])
    assert rows["三"]["kun"] == "みっ(つ)" and "た(べる)" in rows["食"]["kun"] and "あと" in rows["後"]["kun"]
    cards = [w for l in _js_const(built / "ch118.js", "LESSONS") for c in l["cards"] for w in c["words"]]
    three = next(w for w in cards if w["jp"] == "三")
    assert "음 サン · 훈 みっ(つ)" in three["ko"], three



# ---- 손질(N5 손질 2) ----
def _lessons(built, n):
    return _js_const(built / ("ch%d.js" % n), "LESSONS")


def test_maitsuki_not_in_kanji_questions(built):
    """毎月은 まいつき·まいげつ 둘 다 흔해서 한자 문제 단어로 쓰지 않음(원본 목록은 まいげつ)"""
    for n in (118, 119):
        for l in _lessons(built, n):
            assert all(plain(it["say"]) != "毎月" for it in l["items"]), l["id"]


def test_kanji_words_one_kanji_each(built):
    """한 장 안에서 문제 단어 하나는 한자 하나에만(天気를 天·気가 같이 쓰지 않음), 当て字 沢山 안 씀"""
    for n in (118, 119):
        owner = {}
        for l in _lessons(built, n):
            for it in l["items"]:
                if it["kind"].startswith("kanji"):
                    w = plain(it["say"])
                    assert w != "沢山"
                    assert owner.setdefault(w, it["concept"]) == it["concept"], (w, owner[w], it["concept"])


def test_kanji_reads_before_writes(built):
    """레슨 안에서 읽기 문제를 먼저 다 내고 표기 문제는 뒤에(같은 단어 읽기→표기가 바로 붙지 않게)"""
    for n in (118, 119):
        for l in _lessons(built, n)[:-1]:
            ks = [it["kind"] for it in l["items"]]
            assert ks == sorted(ks, key=lambda k: k != "kanji-read"), (l["id"], ks)


def test_kanji_write_no_same_reading(built):
    """표기 문제 오답의 읽기가 질문 읽기와 같으면 정답이 둘(같은 소리 다른 표기)"""
    from make_lessons import jlpt_words, load_words, kana
    rd = {}
    for w in jlpt_words(load_words(os.path.join(ROOT, "data", "words.csv"))):
        rd.setdefault(plain(w["jp"]), set()).add(kana(w["jp"]))
    for n in (118, 119):
        for l in _lessons(built, n):
            for it in l["items"]:
                if it["kind"] == "kanji-write":
                    q = it["q"][1:it["q"].index("」")]
                    for o in it["options"][1:]:
                        assert q not in rd.get(o, set()), (it["q"], o)


def test_kanji_summary_and_titles(built):
    n = 0
    for ch in (118, 119):
        for l in _lessons(built, ch)[:-1]:
            n += 1
            assert l["title"] == "한자 %d" % n
            assert len(l["summary"]) == len({it["concept"] for it in l["items"]}), l["summary"]


def test_mock_listen_mixed(built):
    for l in _lessons(built, 120):
        qs = [it["q"] for it in l["items"] if it.get("kind") == "listen"]
        assert sum("뜻" in q for q in qs) == 4 and sum("대답" in q for q in qs) == 2, qs


def test_polish_texts():
    d = json.load(open(os.path.join(ROOT, "data", "jlpt-n5-mock.json"), encoding="utf-8"))
    assert "ことができ" not in json.dumps(d, ensure_ascii=False)
    from make_lessons import load_grammar
    ps = {p["id"]: p for p in load_grammar(GRAMMAR)}
    fills = lambda pid: {it["pre"] + "＿" + it["post"]: it["wrong"] for it in ps[pid]["items"] if it["type"] == "fill"}
    assert "まで" not in fills("g5-15")["授業{じゅぎょう}は九{く}時{じ}＿です。"]
    assert "から" not in fills("g5-15")["駅{えき}＿歩{ある}きます。"]
    assert "よく" not in fills("g5-17")["＿昼{ひる}ご飯{はん}を食{た}べましたか。"]
    assert "もう" not in fills("g5-17")["弟{おとうと}は＿寝{ね}ています。"]
    assert all("兄{あに}は料理" not in k for k in fills("g5-08"))
    b14 = [it for it in ps["g5-14"]["items"] if it["type"] == "build"][0]
    assert b14["ko"] == "같이 공원을 산책합시다."
