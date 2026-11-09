#!/usr/bin/env python3
"""단어 표(data/words.csv) → 레슨 표(data/lessons/chN.js) + 단어 이름표(data/concepts.js).

    python3 tools/make_lessons.py

- 장 = words.csv의 chapter. 1 히라가나, 2 가타카나, 3~26 = 1~24과(NHK 「일본말 첫걸음」 주제 순서만 참고).
- 101~114 = JLPT N5 (data/jlpt-n5.csv, tools/jlpt_n5.py). 겹치는 단어는 같은 id로 JLPT 장에도 나온다. data/jlpt.js에 N5_IDS.
- 레슨 = 단원(unit) 하나를 표 순서대로 8개씩(남는 4개 이하는 앞 레슨에 붙임), 장 끝에 장 평가.
- 문제: 일→한·한→일(choice), 가나 카드 순서(order, 가나 장 제외), 예문 빈칸(choice + sentence, data/examples.csv에 예문 있는 단어). 일반 레슨 터치 max(6, 단어 수) + check 1, 장 평가 8 + check 1.
- jp 칸은 「学生{がくせい}」처럼 한자 뒤 {읽기}. 화면이 <ruby>로 그린다(src/ruby.js).
- 무작위는 random.Random(문자열 시드)만 써서 같은 입력이면 같은 출력.
- 결과물은 CC BY-SA 4.0 (data/LICENSE-data.md).
"""
import csv
import json
import os
import random
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # jlpt_n5
CHUNK, TAIL = 8, 4
TOUCH, EXAM_TOUCH, MIN_ITEMS = 6, 8, 4
WORD_KINDS, KANA_KINDS = ("j2k", "k2j", "order"), ("j2k", "k2j")
STATUS = {"ok", "hold"}

CHAPTER_TITLES = {
    1: "히라가나", 2: "가타카나",
    3: "1과 · 장소 묻기", 4: "2과 · 자기소개", 5: "3과 · 출신 말하기", 6: "4과 · 하는 일·공부",
    7: "5과 · 지난 일 말하기", 8: "6과 · 전철 타기", 9: "7과 · 부탁하기", 10: "8과 · 친구 소개",
    11: "9과 · 물건 이름 묻기", 12: "10과 · 값 묻기", 13: "11과 · 있는지 묻기", 14: "12과 · 느낌 말하기",
    15: "13과 · 하고 싶은 것", 16: "14과 · 가 보고 싶은 곳", 17: "15과 · 택시 타기", 18: "16과 · 관광지 소개",
    19: "17과 · 지금 하는 일", 20: "18과 · 여행 소감", 21: "19과 · 쇼핑하기", 22: "20과 · 음식 주문",
    23: "21과 · 위치 말하기", 24: "22과 · 같이 하자고 하기", 25: "23과 · 좋아하는 것", 26: "24과 · 못 하는 것",
}
# JLPT 길(장 번호 100 이상, JLPT 설계 §2-3): 장 = (긴 주제, 레슨 이름에 붙는 짧은 주제)
JLPT_TITLES = {101: ("숫자·조수사", "숫자"), 102: ("날짜·요일·시간", "날짜"), 103: ("사람·가족", "가족"), 104: ("몸·건강", "몸"),
               105: ("집·물건", "물건"), 106: ("음식·식사", "음식"), 107: ("거리·교통·장소", "거리"), 108: ("학교·일", "학교"),
               109: ("날씨·계절·자연", "날씨"), 110: ("い형용사 반대말", "い형용사"), 111: ("な형용사·색", "な형용사"),
               112: ("동사 1", "동사"), 113: ("동사 2", "동사"), 114: ("지시어·의문사·부사·인사말", "기본 말"),
               115: ("문법 1", "문법"), 116: ("문법 2", "문법"), 117: ("문법 3", "문법"),
               118: ("한자 1", "한자"), 119: ("한자 2", "한자"), 120: ("모의고사", "모의고사")}
for _n, (_long, _short) in JLPT_TITLES.items():
    CHAPTER_TITLES[_n] = "N5 · %d장 %s" % (_n - 100, _long)

RUBY = re.compile(r"([㐀-鿿々〆ヶ]+)\{([^{}]+)\}")
KANA = re.compile(r"^[ぁ-ゟ゠-ヿー]+$")
BARE_KANJI = re.compile(r"[\u3400-\u9fff々]")
SMALL = set("ゃゅょぁぃぅぇぉゎャュョァィゥェォヮ")


def kana(s):
    return RUBY.sub(r"\2", s)


def plain(s):
    return RUBY.sub(r"\1", s)


def sound_key(ko):
    """같은 소리·뜻 비교용: 괄호 설명 앞부분(「오 (조사)」 → 「오」)"""
    return ko.split(" (")[0].strip()


def kana_units(reading):
    """가나 카드 단위: 작은 ゃゅょ 등은 앞 글자에 붙인다(きょ). っ·ー는 한 장"""
    out = []
    for c in reading:
        if c in SMALL and out:
            out[-1] += c
        else:
            out.append(c)
    return out


def load_words(path):
    """단어 표 → 단어 목록(hold 제외). 표 오류는 줄 번호와 함께 ValueError"""
    out, ids = [], set()
    with open(path, encoding="utf-8", newline="") as f:
        for n, r in enumerate(csv.DictReader(f), start=2):
            at = "line %d" % n
            jp, ko, st = (r.get("jp") or "").strip(), (r.get("ko") or "").strip(), (r.get("status") or "").strip()
            if not jp:
                raise ValueError("%s: empty jp" % at)
            if not ko:
                raise ValueError("%s: empty ko" % at)
            if st not in STATUS:
                raise ValueError("%s: unknown status %r" % (at, st))
            if r["id"] in ids:
                raise ValueError("%s: duplicate id %s" % (at, r["id"]))
            ids.add(r["id"])
            for m in RUBY.finditer(jp):
                if not KANA.match(m.group(2)):
                    raise ValueError("%s: reading must be kana: %r" % (at, m.group(2)))
            if "{" in RUBY.sub("", jp) or "}" in RUBY.sub("", jp):
                raise ValueError("%s: unpaired braces in %r" % (at, jp))
            note = (r.get("note") or "").strip()
            for name, text in (("jp", jp), ("note", note)):
                if BARE_KANJI.search(RUBY.sub("", text)):
                    raise ValueError("%s: kanji without furigana in %s: %r" % (at, name, text))
            try:
                chapter, unit = int(r.get("chapter") or ""), int(r.get("unit") or "")
            except ValueError:
                raise ValueError("%s: chapter and unit must be numbers" % at) from None
            pos = (r.get("pos") or "").strip()
            if not pos:
                raise ValueError("%s: empty pos" % at)
            if st == "hold":
                continue
            out.append({"id": r["id"], "chapter": chapter, "unit": unit, "seq": n, "jp": jp, "ko": ko, "pos": pos,
                        "note": note, "twin": (r.get("twin") or "").strip()})
    return out


EX_STATUS = {"cross", "native", "hold"}


def load_examples(path, words):
    """예문 표(data/examples.csv) → {단어 id: {pre, post, ko, avoid}}. hold는 뺀다. 잘못된 줄은 줄 번호와 함께 ValueError.
    빈칸 [[…]] 안은 그 단어의 jp와 똑같아야 한다(보기 카드 = 단어 카드)."""
    by_id = {w["id"]: w for w in words}
    out = {}
    with open(path, encoding="utf-8", newline="") as f:
        for n, r in enumerate(csv.DictReader(f), start=2):
            at = "example line %d" % n
            eid, s, ko, st = r["id"], r["sentence_jp"], (r.get("ko") or "").strip(), (r.get("status") or "").strip()
            if st not in EX_STATUS:
                raise ValueError("%s: unknown status %r" % (at, st))
            if eid not in by_id:
                raise ValueError("%s: no such word %s" % (at, eid))
            parts = s.split("[[")
            if len(parts) != 2 or parts[1].count("]]") != 1 or "]]" in parts[0]:
                raise ValueError("%s: needs exactly one [[...]]" % at)
            form, post = parts[1].split("]]")
            if form != by_id[eid]["jp"]:
                raise ValueError("%s: blank %r must be the word %r" % (at, form, by_id[eid]["jp"]))
            if not ko:
                raise ValueError("%s: empty ko" % at)
            if BARE_KANJI.search(RUBY.sub("", parts[0] + post)):
                raise ValueError("%s: kanji without furigana in %r" % (at, s))
            if st == "hold":
                continue
            out[eid] = {"pre": parts[0], "post": post, "ko": ko, "avoid": [plain(x) for x in (r.get("avoid") or "").split("|") if x]}
    return out


def _chunks(words):
    parts = [words[i:i + CHUNK] for i in range(0, len(words), CHUNK)]
    if len(parts) > 1 and len(parts[-1]) <= TAIL:
        tail = parts.pop()
        parts[-1] += tail
    return parts


def _explain(w):
    return "%s = %s%s" % (w["jp"], w["ko"], " · " + w["note"] if w["note"] else "")


def _twins(a, b):
    """보기로 함께 나오면 정답이 둘로 보이는 짝: 뜻(소리)이 같거나 표기·읽기가 같음"""
    return (sound_key(a["ko"]) == sound_key(b["ko"]) or plain(a["jp"]) == plain(b["jp"]) or kana(a["jp"]) == kana(b["jp"])
            or (a["twin"] != "" and a["twin"] == b["twin"]))  # twin: 뜻은 달라도 학습자가 헷갈리는 짝(words.csv twin 칸)


def _options(w, pool, field, seed, avoid=()):
    """정답 + 같은 품사 오답 3개(모자라면 같은 장 아무 품사). 못 채우면 None. avoid: 빼야 할 표기(plain)"""
    used, picked = {w[field]}, []
    pool = [x for x in pool if plain(x["jp"]) not in avoid]
    rng = random.Random(seed)
    for same_pos in (True, False):
        cands = sorted({x[field] for x in pool if (not same_pos or x["pos"] == w["pos"]) and not _twins(x, w)} - used)
        rng.shuffle(cands)
        for c in cands:
            if len(picked) == 3:
                break
            # 고른 오답끼리도 쌍둥이면 안 됨(뜻 두 개가 같은 보기)
            cw = next(x for x in pool if x[field] == c)
            if any(_twins(cw, next(x for x in pool if x[field] == p)) for p in picked):
                continue
            picked.append(c)
            used.add(c)
    return [w[field]] + picked if len(picked) == 3 else None


def _item(w, kind, pool, is_kana, examples=None):
    seed = w["id"] + ":" + kind
    if kind == "fill":
        ex = (examples or {}).get(w["id"])
        opts = ex and _options(w, pool, "jp", seed, avoid=ex["avoid"])
        if not opts:
            return None
        full = ex["pre"] + w["jp"] + ex["post"]
        return {"type": "choice", "concept": w["id"], "q": "빈칸에 들어갈 말을 골라요",
                "sentence": {"jp": ex["pre"] + "＿＿" + ex["post"], "ko": ex["ko"]}, "options": opts, "answer": 0,
                "explain": "%s · %s" % (full, _explain(w)), "say": full}
    if kind == "order":
        r = kana(w["jp"])
        units = kana_units(r) if KANA.match(r) else []
        if not 2 <= len(units) <= 6:
            return None
        return {"type": "order", "concept": w["id"], "q": "가나 카드를 순서대로: 「%s」" % w["ko"],
                "lines": units, "explain": _explain(w), "say": w["jp"]}
    if kind == "j2k":
        field, q = "ko", ("「%s」 어떻게 읽을까요?" if is_kana else "「%s」 무슨 뜻일까요?") % w["jp"]
    else:
        field, q = "jp", ("「%s」 소리는 어느 글자일까요?" if is_kana else "「%s」 일본어로 뭘까요?") % w["ko"]
    opts = _options(w, pool, field, seed)
    if not opts:
        return None
    it = {"type": "choice", "concept": w["id"], "q": q, "options": opts, "answer": 0, "explain": _explain(w), "say": w["jp"]}
    if kind == "j2k" and not is_kana:
        it["qSay"] = True  # 질문 옆 🔊: 뜻을 묻는 문제라 들어도 답이 드러나지 않음
    return it


def _items(words, pool, n, seed, is_kana, examples=None):
    """단어마다 문제 종류를 돌려 쓰고, 안 맞는 종류는 다음 종류로. 단어가 모자라면 다른 종류로 한 바퀴 더.
    예문이 있는 단어는 첫 바퀴에서 빈칸 문제(fill)를 먼저 시도한다."""
    examples = examples or {}
    kinds_all = KANA_KINDS if is_kana else WORD_KINDS
    items, done = [], set()
    for rnd in range(len(kinds_all)):
        for i, w in enumerate(words):
            if len(items) == n:
                break
            kinds = [kinds_all[(i + rnd + k) % len(kinds_all)] for k in range(len(kinds_all))]
            if rnd == 0 and w["id"] in examples:
                kinds.insert(0, "fill")
            for kind in kinds:
                if (w["id"], kind) in done:
                    continue
                it = _item(w, kind, pool, is_kana, examples)
                if it:
                    done.add((w["id"], kind))
                    items.append(it)
                    break
    if len(items) < MIN_ITEMS:
        raise ValueError("too few items for lesson %s: %d" % (seed, len(items)))
    # 이해도 확인: 이 레슨에서 아직 안 낸 (단어, 종류) 중에서. 다 냈으면 이미 낸 것 중 하나
    order = random.Random(seed + ":check").sample(words, len(words))
    for fresh in (True, False):
        for w in order:
            for kind in ("j2k", "k2j"):
                if fresh and (w["id"], kind) in done:
                    continue
                check = _item(w, kind, pool, is_kana)
                if check:
                    return items + [dict(check, type="check")]
    return items


def _cards(words):
    return [{"say": "새 글자를 만나 봐요!" if words[0]["pos"] == "kana" else "새 단어를 만나 봐요!",
             "words": [{"jp": w["jp"], "ko": w["ko"]} for w in words[i:i + 4]]}
            for i in range(0, len(words), 4)]


def build_chapter(words, chapter, examples=None):
    pool = sorted((w for w in words if w["chapter"] == chapter), key=lambda w: (w["unit"], w["seq"]))
    is_kana = all(w["pos"] == "kana" for w in pool)
    title = CHAPTER_TITLES.get(chapter, "%d장" % chapter)
    noun = "글자" if is_kana else "단어"
    lessons = []
    for u in sorted({w["unit"] for w in pool}):
        parts = _chunks([w for w in pool if w["unit"] == u])
        for k, part in enumerate(parts, 1):
            lid = "%d-%d" % (chapter, len(lessons) + 1)
            name = "%s %d" % (JLPT_TITLES[chapter][1], u) if chapter in JLPT_TITLES else "%d단원" % u
            lessons.append({"id": lid, "chapter": chapter, "title": name + (" (%d)" % k if len(parts) > 1 else ""),
                            "goal": "새 %s %d개 알기" % (noun, len(part)),
                            "summary": ["%s = %s" % (w["jp"], w["ko"]) for w in part[:4]],
                            "cards": _cards(part), "items": _items(part, pool, max(TOUCH, len(part)), lid, is_kana, examples)})
    eid = "%d-%d" % (chapter, len(lessons) + 1)
    exam_words = random.Random("exam:%d" % chapter).sample(pool, min(len(pool), EXAM_TOUCH))
    lessons.append({"id": eid, "chapter": chapter, "title": title + " 평가", "goal": "이 장 %s 복습" % noun,
                    "summary": [], "isExam": True, "cards": [], "items": _items(exam_words, pool, EXAM_TOUCH, eid, is_kana, examples)})
    return {"CHAPTER": {"id": chapter, "title": title}, "LESSONS": lessons}


# ---- N5 문법(115~117장, N5 완성 설계 §4): 원본 data/jlpt-n5-grammar.json, 항목 하나 = 레슨 하나 ----
GRAMMAR_FILE = os.path.join(ROOT, "data", "jlpt-n5-grammar.json")


def load_grammar(path=GRAMMAR_FILE):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["points"]


def _grammar_items(p):
    out = []
    for it in p["items"]:
        if it["type"] == "fill":
            full = it["pre"] + it["answer"] + it["post"]
            out.append({"type": "choice", "kind": "grammar", "concept": p["id"], "q": "빈칸에 들어갈 말을 골라요",
                        "sentence": {"jp": it["pre"] + "＿＿" + it["post"], "ko": it["ko"]}, "options": [it["answer"]] + it["wrong"],
                        "answer": 0, "explain": "%s · %s" % (full, p["title"]), "say": full})
        else:
            full = "".join(it["lines"])
            out.append({"type": "order", "kind": "build", "concept": p["id"], "q": "카드를 순서대로 놓아 문장을 만들어요: 「%s」" % it["ko"],
                        "lines": it["lines"], "explain": "%s = %s" % (full, it["ko"]), "say": full})
    return out


def build_grammar_chapter(points, chapter):
    ps = [p for p in points if p["chapter"] == chapter]
    title = CHAPTER_TITLES[chapter]
    lessons, pool = [], []
    for p in ps:
        items = _grammar_items(p)
        pool += items
        ex = [i for i in items if i["type"] == "choice"][:3]
        lessons.append({"id": "%d-%d" % (chapter, len(lessons) + 1), "chapter": chapter, "title": p["title"],
                        "goal": "문법: %s" % p["title"], "summary": [p["explain"]],
                        "cards": [{"say": p["explain"], "words": [{"jp": i["say"], "ko": i["sentence"]["ko"]} for i in ex]}],
                        "items": items})
    exam = random.Random("exam:%d" % chapter).sample(pool, min(len(pool), EXAM_TOUCH))
    lessons.append({"id": "%d-%d" % (chapter, len(lessons) + 1), "chapter": chapter, "title": title + " 평가",
                    "goal": "이 장 문법 복습", "summary": [], "isExam": True, "cards": [], "items": exam})
    return {"CHAPTER": {"id": chapter, "title": title}, "LESSONS": lessons}


# ---- N5 한자(118~119장, N5 완성 설계 §5): 훈음 data/jlpt-n5-kanji.csv, 읽기 vendor/kanji/n5.json(KANJIDIC) ----
KANJI_FILE = os.path.join(ROOT, "data", "jlpt-n5-kanji.csv")
KANJI_READINGS = os.path.join(ROOT, "vendor", "kanji", "n5.json")


def load_kanji(path=KANJI_FILE):
    with open(path, encoding="utf-8", newline="") as f:
        return [{"kanji": r["kanji"], "ko": r["ko"], "chapter": int(r["chapter"]), "unit": int(r["unit"])} for r in csv.DictReader(f)]


def kanji_words(words=None):
    """한자 → 그 한자를 쓰는 JLPT 단어(짧은 것부터). 문제에 쓸 단어 후보"""
    if words is None:
        words = jlpt_words(load_words(os.path.join(ROOT, "data", "words.csv")))
    # 읽기가 둘인 표기(一日 いちにち/ついたち, 九 きゅう/く)와 흔한 읽기가 따로 있는 말(一月 いちがつ)은 읽기 문제에 쓰지 않는다
    readings = {}
    for w in words:
        readings.setdefault(plain(w["jp"]), set()).add(kana(w["jp"]))
    skip = {p for p, r in readings.items() if len(r) > 1} | {"一月"}
    out = {}
    for k in load_kanji():
        cands = [w for w in words if k["kanji"] in plain(w["jp"]) and w["pos"] != "kana" and KANA.match(kana(w["jp"]))
                 and plain(w["jp"]) not in skip]
        uniq = {}
        # 조수사 말(三時·二本 …)은 다른 단어가 없을 때만(二本 にほん은 日本과 읽기가 같음)
        for w in sorted(cands, key=lambda w: (w["pos"] == "num" and len(plain(w["jp"])) > 1, len(plain(w["jp"])), w["chapter"], w["seq"])):
            uniq.setdefault(plain(w["jp"]), w)
        out[k["kanji"]] = list(uniq.values())
    return out


def _kanji_readings(k):
    with open(KANJI_READINGS, encoding="utf-8") as f:
        r = json.load(f)[k]
    clean = lambda xs: [x.replace("-", "").replace(".", "") for x in xs[:2]]  # ひと.つ → ひとつ (보여 주기용)
    return clean(r["on"]), clean(r["kun"])


def _pick(answer, cands, seed):
    """정답과 다르고 서로 다른 오답 3개(길이가 비슷한 것부터)"""
    pool = sorted({c for c in cands if c != answer}, key=lambda c: (abs(len(c) - len(answer)), c))[:12]
    random.Random(seed).shuffle(pool)
    return [answer] + pool[:3] if len(pool) >= 3 else None


def build_kanji_chapter(chapter, words=None):
    ks = [k for k in load_kanji() if k["chapter"] == chapter]
    kw = kanji_words(words)
    title = CHAPTER_TITLES[chapter]
    used = [w for k in ks for w in kw[k["kanji"]][:2]]
    readings, spellings = [kana(w["jp"]) for w in used], [plain(w["jp"]) for w in used]
    lessons, pool = [], []
    for u in sorted({k["unit"] for k in ks}):
        unit_ks, items, cards = [k for k in ks if k["unit"] == u], [], []
        for k in unit_ks:
            ws = kw[k["kanji"]]
            a, b = ws[0], ws[1] if len(ws) > 1 else ws[0]
            cid = "k5-" + k["kanji"]
            why = lambda w: "%s = %s · %s %s" % (w["jp"], w["ko"], k["kanji"], k["ko"])
            ro = _pick(kana(a["jp"]), readings, cid + ":r")
            wo = _pick(plain(b["jp"]), spellings, cid + ":w")
            if ro:
                items.append({"type": "choice", "kind": "kanji-read", "concept": cid, "q": "「%s」 어떻게 읽을까요?" % plain(a["jp"]),
                              "options": ro, "answer": 0, "explain": why(a), "say": a["jp"]})
            if wo:
                items.append({"type": "choice", "kind": "kanji-write", "concept": cid, "q": "「%s」 한자로 쓰면?" % kana(b["jp"]),
                              "options": wo, "answer": 0, "explain": why(b), "say": b["jp"]})
            on, kun = _kanji_readings(k["kanji"])
            cards.append({"jp": k["kanji"], "ko": "%s · 음 %s · 훈 %s · 예: %s" % (k["ko"], "·".join(on) or "-", "·".join(kun) or "-", plain(a["jp"]))})
        pool += items
        lessons.append({"id": "%d-%d" % (chapter, len(lessons) + 1), "chapter": chapter, "title": "한자 %d" % (len(lessons) + 1 + (8 if chapter == 119 else 0)),
                        "goal": "새 한자 %d자" % len(unit_ks), "summary": ["%s %s" % (k["kanji"], k["ko"]) for k in unit_ks[:4]],
                        "cards": [{"say": "새 한자를 만나 봐요!", "words": cards[i:i + 4]} for i in range(0, len(cards), 4)], "items": items})
    exam = random.Random("exam:%d" % chapter).sample(pool, min(len(pool), EXAM_TOUCH))
    lessons.append({"id": "%d-%d" % (chapter, len(lessons) + 1), "chapter": chapter, "title": title + " 평가",
                    "goal": "이 장 한자 복습", "summary": [], "isExam": True, "cards": [], "items": exam})
    return {"CHAPTER": {"id": chapter, "title": title}, "LESSONS": lessons}


# ---- N5 모의고사(120장, N5 완성 설계 §6): 앞 장 문제에서 회마다 겹치지 않게 + 독해·청해 원본 data/jlpt-n5-mock.json ----
MOCK_FILE = os.path.join(ROOT, "data", "jlpt-n5-mock.json")
MOCK_MIX = (("kanji-read", 4), ("kanji-write", 3), ("context", 4), ("grammar", 4), ("build", 2))
MOCK_ROUNDS = 3


def load_mock(path=MOCK_FILE):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _mock_reading(p):
    return [{"type": "choice", "kind": "reading", "concept": p["id"], "q": q["q"], "sentence": {"jp": p["text"], "ko": ""},
             "options": q["options"], "answer": 0, "explain": p["ko"], "say": q["q"]} for q in p["questions"]]


def _mock_listen(n, it):
    meaning = it["ask"] == "meaning"
    return {"type": "choice", "kind": "listen", "concept": "m5-l%02d" % n, "qSay": True,
            "q": "잘 듣고 뜻을 골라요" if meaning else "잘 듣고 알맞은 대답을 골라요",
            "options": it["options"], "answer": 0, "explain": "%s %s %s" % (it["jp"], "=" if meaning else "→", it["options"][0]), "say": it["jp"]}


def mock_concepts(mock):
    return ([{"id": p["id"], "name": "모의고사 · 독해 %d" % n, "chapter": 120} for n, p in enumerate(mock["reading"], 1)]
            + [{"id": "m5-l%02d" % n, "name": "모의고사 · 청해 %d" % n, "chapter": 120} for n in range(1, len(mock["listening"]) + 1)])


def build_mock_chapter(built, mock, chapter=120):
    """built: 장 번호 → 만든 장(101~119). 꼴마다 문제를 한 번 섞어 회마다 다른 조각을 쓴다(겹침 없음)"""
    src = [it for ch, d in built.items() if 100 < ch < chapter for l in d["LESSONS"] if not l.get("isExam") for it in l["items"]]
    kind = lambda it: it.get("kind") or ("context" if it["type"] == "choice" and it.get("sentence") else None)
    pools = {k: random.Random("mock:" + k).sample([it for it in src if kind(it) == k], k=len([it for it in src if kind(it) == k]))
             for k, _ in MOCK_MIX}
    listen = [_mock_listen(n, it) for n, it in enumerate(mock["listening"], 1)]
    per = len(listen) // MOCK_ROUNDS
    title = CHAPTER_TITLES[chapter]
    lessons = []
    for r in range(MOCK_ROUNDS):
        items = [dict(it) for k, n in MOCK_MIX for it in pools[k][r * n:(r + 1) * n]]
        items += _mock_reading(mock["reading"][r]) + listen[r * per:(r + 1) * per]
        lessons.append({"id": "%d-%d" % (chapter, r + 1), "chapter": chapter, "title": "모의고사 %d" % (r + 1),
                        "goal": "N5 시험 꼴로 풀어 보기", "summary": [], "isExam": True, "cards": [], "items": items})
    return {"CHAPTER": {"id": chapter, "title": title}, "LESSONS": lessons}


HEADER = "// 자동 생성: tools/make_lessons.py — 고치지 말고 다시 만드세요. 데이터 라이선스 CC BY-SA 4.0 (data/LICENSE-data.md)\n"


def jlpt_words(base):
    """JLPT 단어 표(data/jlpt-n5.csv) → 생성기 단어 목록. 회화 길과 겹치는 단어는 같은 id·표기·뜻을 JLPT 장에 한 번 더 둔다."""
    from jlpt_n5 import load_jlpt
    by = {w["id"]: w for w in base}
    out = []
    for n, r in enumerate(load_jlpt(), start=1):
        w = dict(by[r["id"]]) if r["shared"] else {"id": r["id"], "jp": r["jp"], "ko": r["ko"], "pos": r["pos"], "note": r["note"], "twin": ""}
        w.update(chapter=r["chapter"], unit=r["unit"], seq=100000 + n, shared=r["shared"])
        out.append(w)
    return out


def main(out_dir=None, words_file=None, concepts_file=None, examples_file=None, jlpt_file=None):
    out_dir = out_dir or os.path.join(ROOT, "data", "lessons")
    concepts_file = concepts_file or os.path.join(ROOT, "data", "concepts.js")
    words = load_words(words_file or os.path.join(ROOT, "data", "words.csv"))
    # 실제 단어 표일 때만 JLPT 장을 합친다(시험이 단어 표를 바꾸면 회화 장만)
    jlpt = jlpt_words(words) if words_file is None else []
    words = words + jlpt
    # 예문 표는 실제 단어 표와 짝. 시험이 단어 표만 바꾸면 예문 없이 만든다
    if examples_file is None and words_file is None:
        examples_file = os.path.join(ROOT, "data", "examples.csv")
    examples = load_examples(examples_file, words) if examples_file and os.path.exists(examples_file) else {}
    os.makedirs(out_dir, exist_ok=True)
    total = 0
    grammar = load_grammar() if jlpt else []
    extra = {ch: (lambda ch=ch: build_grammar_chapter(grammar, ch)) for ch in sorted({p["chapter"] for p in grammar})}
    if jlpt:
        extra.update({ch: (lambda ch=ch: build_kanji_chapter(ch, words)) for ch in sorted({k["chapter"] for k in load_kanji()})})
    mock = load_mock() if jlpt else None
    if jlpt:
        extra[120] = lambda: build_mock_chapter(made, mock)  # 앞 장이 다 만들어진 뒤(정렬 순서상 마지막)
    made = {}
    for ch in sorted({w["chapter"] for w in words} | set(extra)):
        data = made[ch] = extra[ch]() if ch in extra else build_chapter(words, ch, examples)
        total += len(data["LESSONS"])
        with open(os.path.join(out_dir, "ch%d.js" % ch), "w", encoding="utf-8") as f:
            f.write(HEADER)
            f.write("export const CHAPTER = %s;\n\n" % json.dumps(data["CHAPTER"], ensure_ascii=False))
            f.write("export const LESSONS = %s;\n" % json.dumps(data["LESSONS"], ensure_ascii=False, indent=1))
    # 복습·취약 단어 이름표(홈·배지 화면): concept id = 단어 id
    with open(concepts_file, "w", encoding="utf-8") as f:
        f.write(HEADER.replace("레슨", "단어 이름표"))
        names = [{"id": w["id"], "name": "%s · %s" % (w["jp"], w["ko"]), "chapter": w["chapter"]}
                 for w in words if not w.get("shared")]  # 겹치는 단어는 회화 길의 원래 장으로 한 번만
        names += [{"id": p["id"], "name": "문법 · %s" % p["title"], "chapter": p["chapter"]} for p in grammar]
        if jlpt:
            names += [{"id": "k5-" + k["kanji"], "name": "한자 · %s %s" % (k["kanji"], k["ko"]), "chapter": k["chapter"]} for k in load_kanji()]
            names += mock_concepts(mock)
        f.write("export const CONCEPTS = [\n%s\n];\n" % ",\n".join("  " + json.dumps(n, ensure_ascii=False) for n in names))
    if jlpt:
        with open(jlpt_file or os.path.join(ROOT, "data", "jlpt.js"), "w", encoding="utf-8") as f:
            f.write(HEADER.replace("레슨", "JLPT 단어 목록"))
            f.write("// N5_IDS: JLPT N5 단어 표(data/jlpt-n5.csv)의 단어 id, 표 순서. 「N5 단어 N개 중 M개 배웠어요」의 기준\n")
            f.write("export const N5_IDS = %s;\n" % json.dumps([w["id"] for w in jlpt], ensure_ascii=False))
    print("%d words, %d lessons" % (len(words), total))


if __name__ == "__main__":
    main()
