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
