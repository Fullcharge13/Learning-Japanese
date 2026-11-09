#!/usr/bin/env python3
"""단어 표(data/words.csv) → 레슨 표(data/lessons/chN.js) + 단어 이름표(data/concepts.js).

    python3 tools/make_lessons.py

- 장 = words.csv의 chapter. 1 히라가나, 2 가타카나, 3~14 = 1~12과(NHK 「일본말 첫걸음」 주제 순서만 참고).
- 레슨 = 단원(unit) 하나를 표 순서대로 8개씩(남는 4개 이하는 앞 레슨에 붙임), 장 끝에 장 평가.
- 문제: 일→한·한→일(choice), 가나 카드 순서(order, 가나 장 제외). 일반 레슨 터치 max(6, 단어 수) + check 1, 장 평가 8 + check 1.
- jp 칸은 「学生{がくせい}」처럼 한자 뒤 {읽기}. 화면이 <ruby>로 그린다(src/ruby.js).
- 무작위는 random.Random(문자열 시드)만 써서 같은 입력이면 같은 출력.
- 결과물은 CC BY-SA 4.0 (data/LICENSE-data.md).
"""
import csv
import json
import os
import random
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHUNK, TAIL = 8, 4
TOUCH, EXAM_TOUCH, MIN_ITEMS = 6, 8, 4
WORD_KINDS, KANA_KINDS = ("j2k", "k2j", "order"), ("j2k", "k2j")
STATUS = {"ok", "hold"}

CHAPTER_TITLES = {
    1: "히라가나", 2: "가타카나",
    3: "1과 · 장소 묻기", 4: "2과 · 자기소개", 5: "3과 · 출신 말하기", 6: "4과 · 하는 일·공부",
    7: "5과 · 지난 일 말하기", 8: "6과 · 전철 타기", 9: "7과 · 부탁하기", 10: "8과 · 친구 소개",
    11: "9과 · 물건 이름 묻기", 12: "10과 · 값 묻기", 13: "11과 · 있는지 묻기", 14: "12과 · 느낌 말하기",
}

RUBY = re.compile(r"([㐀-鿿々〆ヶ]+)\{([^{}]+)\}")
KANA = re.compile(r"^[ぁ-ゟ゠-ヿー]+$")
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
            if st == "hold":
                continue
            out.append({"id": r["id"], "chapter": int(r["chapter"]), "unit": int(r["unit"]), "seq": n,
                        "jp": jp, "ko": ko, "pos": r["pos"].strip(), "note": (r.get("note") or "").strip()})
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
    return sound_key(a["ko"]) == sound_key(b["ko"]) or plain(a["jp"]) == plain(b["jp"]) or kana(a["jp"]) == kana(b["jp"])


def _options(w, pool, field, seed):
    """정답 + 같은 품사 오답 3개(모자라면 같은 장 아무 품사). 못 채우면 None"""
    used, picked = {w[field]}, []
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


def _item(w, kind, pool, is_kana):
    seed = w["id"] + ":" + kind
    if kind == "order":
        r = kana(w["jp"])
        units = kana_units(r) if KANA.match(r) else []
        if not 2 <= len(units) <= 6:
            return None
        return {"type": "order", "concept": w["id"], "q": "가나 카드를 순서대로: 「%s」" % w["ko"],
                "lines": units, "explain": _explain(w)}
    if kind == "j2k":
        field, q = "ko", ("「%s」 어떻게 읽을까요?" if is_kana else "「%s」 무슨 뜻일까요?") % w["jp"]
    else:
        field, q = "jp", ("「%s」 소리는 어느 글자일까요?" if is_kana else "「%s」 일본어로 뭘까요?") % w["ko"]
    opts = _options(w, pool, field, seed)
    if not opts:
        return None
    return {"type": "choice", "concept": w["id"], "q": q, "options": opts, "answer": 0, "explain": _explain(w)}


def _items(words, pool, n, seed, is_kana):
    """단어마다 문제 종류를 돌려 쓰고, 안 맞는 종류는 다음 종류로. 단어가 모자라면 다른 종류로 한 바퀴 더"""
    kinds_all = KANA_KINDS if is_kana else WORD_KINDS
    items, done = [], set()
    for rnd in range(len(kinds_all)):
        for i, w in enumerate(words):
            if len(items) == n:
                break
            for k in range(len(kinds_all)):
                kind = kinds_all[(i + rnd + k) % len(kinds_all)]
                if (w["id"], kind) in done:
                    continue
                it = _item(w, kind, pool, is_kana)
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


def build_chapter(words, chapter):
    pool = sorted((w for w in words if w["chapter"] == chapter), key=lambda w: (w["unit"], w["seq"]))
    is_kana = all(w["pos"] == "kana" for w in pool)
    title = CHAPTER_TITLES.get(chapter, "%d장" % chapter)
    noun = "글자" if is_kana else "단어"
    lessons = []
    for u in sorted({w["unit"] for w in pool}):
        parts = _chunks([w for w in pool if w["unit"] == u])
        for k, part in enumerate(parts, 1):
            lid = "%d-%d" % (chapter, len(lessons) + 1)
            lessons.append({"id": lid, "chapter": chapter, "title": "%d단원" % u + (" (%d)" % k if len(parts) > 1 else ""),
                            "goal": "새 %s %d개 알기" % (noun, len(part)),
                            "summary": ["%s = %s" % (w["jp"], w["ko"]) for w in part[:4]],
                            "cards": _cards(part), "items": _items(part, pool, max(TOUCH, len(part)), lid, is_kana)})
    eid = "%d-%d" % (chapter, len(lessons) + 1)
    exam_words = random.Random("exam:%d" % chapter).sample(pool, min(len(pool), EXAM_TOUCH))
    lessons.append({"id": eid, "chapter": chapter, "title": title + " 평가", "goal": "이 장 %s 복습" % noun,
                    "summary": [], "isExam": True, "cards": [], "items": _items(exam_words, pool, EXAM_TOUCH, eid, is_kana)})
    return {"CHAPTER": {"id": chapter, "title": title}, "LESSONS": lessons}


HEADER = "// 자동 생성: tools/make_lessons.py — 고치지 말고 다시 만드세요. 데이터 라이선스 CC BY-SA 4.0 (data/LICENSE-data.md)\n"


def main(out_dir=None, words_file=None, concepts_file=None):
    out_dir = out_dir or os.path.join(ROOT, "data", "lessons")
    concepts_file = concepts_file or os.path.join(ROOT, "data", "concepts.js")
    words = load_words(words_file or os.path.join(ROOT, "data", "words.csv"))
    os.makedirs(out_dir, exist_ok=True)
    total = 0
    for ch in sorted({w["chapter"] for w in words}):
        data = build_chapter(words, ch)
        total += len(data["LESSONS"])
        with open(os.path.join(out_dir, "ch%d.js" % ch), "w", encoding="utf-8") as f:
            f.write(HEADER)
            f.write("export const CHAPTER = %s;\n\n" % json.dumps(data["CHAPTER"], ensure_ascii=False))
            f.write("export const LESSONS = %s;\n" % json.dumps(data["LESSONS"], ensure_ascii=False, indent=1))
    # 복습·취약 단어 이름표(홈·배지 화면): concept id = 단어 id
    with open(concepts_file, "w", encoding="utf-8") as f:
        f.write(HEADER.replace("레슨", "단어 이름표"))
        f.write("export const CONCEPTS = [\n%s\n];\n" % ",\n".join(
            "  " + json.dumps({"id": w["id"], "name": "%s · %s" % (w["jp"], w["ko"]), "chapter": w["chapter"]}, ensure_ascii=False)
            for w in words))
    print("%d words, %d lessons" % (len(words), total))


if __name__ == "__main__":
    main()
