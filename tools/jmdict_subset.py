#!/usr/bin/env python3
"""단어 표 읽기를 JMdict와 대조할 부분집합 만들기 (사전이 바뀌거나 단어 표가 바뀔 때 한 번 실행해 커밋).

    python3 tools/jmdict_subset.py /path/to/jamdict.db

- 사전: JMdict(EDRDG, CC BY-SA 4.0). jamdict-data(pip) 패키지의 jamdict.db(sqlite)를 쓴다.
- 가나 장(pos=kana)은 빼고, 단어마다 (표기, 읽기) 후보를 만들어 사전에 있는 쌍만 vendor/jmdict/subset.json에 담는다.
  「行{い}きます」처럼 ます꼴 동사는 사전형 후보(行く/いく, 行きる/いきる …)로 찾는다.
- 사전에서 못 찾은 단어는 이름을 찍고 1로 끝난다.
"""
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_lessons import load_words, kana, plain  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "vendor", "jmdict", "subset.json")
I_TO_U = dict(zip("いきぎしちにびみり", "うくぐすつぬぶむる"))
IRREGULAR = {("来", "き"): ("来る", "くる"), ("し", "し"): ("する", "する")}


def candidates(jp):
    """(표기, 읽기) 후보: 그대로, ます꼴이면 사전형들"""
    p, r = plain(jp), kana(jp)
    out = [(p, r)]
    for end in ("ましょう", "ました", "ません", "ます"):
        if p.endswith(end) and r.endswith(end):
            sp, sr = p[:-len(end)], r[:-len(end)]
            if (sp, sr) in IRREGULAR:
                out.append(IRREGULAR[(sp, sr)])
            out.append((sp + "る", sr + "る"))                       # 一段
            if sr and sr[-1] in I_TO_U:                              # 五段
                last = I_TO_U[sr[-1]]
                out.append(((sp[:-1] + last) if sp[-1] == sr[-1] else sp + last, sr[:-1] + last))
            if sp.endswith("し") and len(sp) > 1:                    # 명사 + する
                out.append((sp[:-1], sr[:-1]))
            break
    return out


def found(db, p, r):
    if p == r:
        return db.execute("select 1 from Kana where text=? limit 1", (p,)).fetchone() is not None
    return db.execute("select 1 from Kanji k join Kana n on k.idseq=n.idseq where k.text=? and n.text=? limit 1", (p, r)).fetchone() is not None


def main(db_path):
    db = sqlite3.connect(db_path)
    pairs, missing = set(), []
    for w in load_words(os.path.join(ROOT, "data", "words.csv")):
        if w["pos"] == "kana":
            continue
        hit = [c for c in candidates(w["jp"]) if found(db, *c)]
        if hit:
            pairs.add(hit[0])
        else:
            missing.append("%s %s" % (w["id"], w["jp"]))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"source": "JMdict via jamdict-data 1.5", "pairs": sorted(map(list, pairs))}, f, ensure_ascii=False, indent=0)
        f.write("\n")
    print("%d pairs, %d missing" % (len(pairs), len(missing)))
    for m in missing:
        print("MISSING", m)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
