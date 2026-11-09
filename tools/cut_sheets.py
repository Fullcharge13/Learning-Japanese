#!/usr/bin/env python3
"""참고 그림 시트 → 앱 그림 PNG (한 번 실행해 결과를 커밋).

    python3 tools/cut_sheets.py

- docs/img/ref/yuki-sheet.jpg     → src/img/yuki/<표정>.png (15컷)
- docs/img/ref/yuki-festival-sheet.jpg → src/img/outfits/<의상>.png (축제 의상 15벌, 크림색 배경을 투명하게)
- 시트에 그려진 이름표 글씨(「기쁨」 …)는 LABELS 상자를 배경색으로 덮어 지운다.
  그림 속 효과 글씨(「파이팅!」「아하!」「휴~」)는 그림의 일부라 남긴다.
- 칸 좌표는 이름표를 지운 시트에서 배경과 다른 덩어리를 찾아 정한 값(2576×1438). 정사각형 캔버스에 가운데 맞춰 256px.
- 배경(흰색)에 가까운 픽셀은 투명하게(가장자리는 반투명).
- docs/img/ref/shop-*-sheet.png → src/img/shop/flow-NN·story-NN·guest-<id>.png (가게 컷 45개)
- 미리보기: docs/img/yuki-preview.png, docs/img/outfits-preview.png, docs/img/shop-preview.png
"""
import os
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIZE, PAD = 256, 10
BG = (255, 255, 255)
NEAR, FAR = 24, 70   # 배경과의 색 거리: NEAR 이하 투명, FAR 이상 불투명

LABELS = {
    "yuki-sheet.jpg": [(405, 400, 505, 470), (940, 400, 1005, 470), (1450, 400, 1535, 470), (1940, 400, 2035, 470), (2428, 398, 2570, 476),
                       (412, 882, 552, 942), (925, 875, 1065, 945), (1440, 875, 1705, 945), (1935, 875, 2140, 945), (2418, 872, 2512, 948),
                       (398, 1292, 512, 1354), (398, 1358, 512, 1420), (585, 1350, 675, 1415), (1050, 1350, 1220, 1415), (1605, 1350, 1700, 1415), (2018, 1360, 2244, 1422)],
}

YUKI = {  # (x0, y0, x1, y1)
    "joy": (100, 38, 479, 476), "angry": (613, 38, 993, 480), "sad": (1075, 38, 1537, 477),
    "surprise": (1587, 38, 2037, 476), "worry": (2117, 38, 2498, 477),
    "smile": (104, 502, 491, 956), "sleepy": (600, 516, 1043, 955), "done": (1122, 505, 1498, 953),
    "think": (1579, 506, 2075, 961), "sparkle": (2089, 500, 2526, 954),
    "pout": (113, 969, 500, 1427), "cheer": (526, 969, 1121, 1427), "shy": (1141, 970, 1500, 1427),
    "wink": (1652, 970, 2014, 1426), "hello": (2040, 969, 2512, 1427),
}
# 축제 의상 시트(2576×1438, 5×3): 칸마다 그림 오른쪽에 이름표. 열 경계는 이웃 그림 사이 빈 곳(행마다 다름).
OUTFIT_SHEET = "yuki-festival-sheet.jpg"
OUTFIT_IDS = ["nebuta", "hanagasa", "awaodori", "yosakoi", "kanto", "tanabata", "gion", "tenjin", "yamakasa", "eisa",
              "hyakumangoku", "owara", "nishimonai", "yassa", "ohara"]
OUTFIT_ROWS = [(0, 505), (505, 963), (963, 1438)]
OUTFIT_SPLITS = [[520, 1050, 1560, 2065], [540, 1055, 1570, 2075], [541, 1090, 1590, 2050]]
OUTFIT_TITLE = (590, 0, 2075, 88)  # 맨 위 제목 줄: 그림과 겹치지 않아 통째로 덮는다
# 이름표 영역(쓰지 않는 니가타·나가노 포함). 상자 안에서 「작고 어두운 무채색 덩어리」(글자 획)만 지워 옷 가장자리는 남긴다
OUTFIT_LABELS = [(370, 405, 570, 510), (900, 405, 1140, 510), (1380, 400, 1600, 515), (1790, 400, 2110, 515), (2390, 405, 2570, 510),
                 (410, 860, 570, 965), (910, 860, 1080, 965), (1410, 860, 1600, 965), (1900, 840, 2110, 965), (2400, 860, 2570, 965),
                 (390, 1300, 570, 1438), (580, 1330, 700, 1438), (880, 1330, 1120, 1438), (1420, 1300, 1570, 1438),
                 (1600, 1300, 1745, 1438), (1920, 1300, 2110, 1438), (2410, 1300, 2576, 1438)]


def load(name):
    im = Image.open(os.path.join(ROOT, "docs", "img", "ref", name)).convert("RGB")
    d = ImageDraw.Draw(im)
    for r in LABELS.get(name, []):
        d.rectangle(r, fill=BG)
    return im


def cut(sheet, box, bg=BG):
    x0, y0, x1, y1 = box
    part = sheet.crop((x0 - PAD, y0 - PAD, x1 + PAD, y1 + PAD))
    side = max(part.size)
    canvas = Image.new("RGB", (side, side), bg)
    canvas.paste(part, ((side - part.width) // 2, (side - part.height) // 2))
    im = canvas.resize((SIZE, SIZE), Image.LANCZOS).convert("RGBA")
    px = im.load()
    for y in range(SIZE):
        for x in range(SIZE):
            r, g, b, _ = px[x, y]
            dist = abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2])
            if dist < FAR:
                px[x, y] = (r, g, b, 0 if dist <= NEAR else round(255 * (dist - NEAR) / (FAR - NEAR)))
    return im


# 가게 그림 시트(1024×572, 5×3 칸): 칸 = 흰 사이 띠로 나뉜 사각 그림. 흐름·이야기 컷은 이름표를 남기고(컷 제목),
# 손님은 칸 아래 이름표 띠를 빼고(3행은 위쪽 이름표 띠도) 자른다. 배경이 그림의 일부라 투명하게 하지 않는다.
SHOP_COLS = [(20, 217), (222, 415), (421, 614), (620, 813), (818, 1011)]
SHOP_ROWS = [(5, 190), (193, 378), (383, 562)]
GUEST_IDS = ["ojisan", "obaachan", "kinder", "joshi", "salary", "tokyo", "youtuber", "tourist", "family", "business",
             "mania", "dogwalk", "ensoku", "couple", "memory"]


# 흐름·이야기 컷은 2·3행 이름표가 칸 사이 띠에 걸쳐 있어 아래로 넓게 자른다
LABEL_ROWS = [(0, 194), (190, 394), (380, 572)]


def shop_cells(trim_labels=False):
    for r, (y0, y1) in enumerate(SHOP_ROWS if trim_labels else LABEL_ROWS):
        for x0, x1 in SHOP_COLS:
            yield (x0, y0 + (30 if trim_labels and r == 2 else 0), x1, y1 - (32 if trim_labels else 0))


def cut_panel(sheet, box):
    part = sheet.crop(box)
    side = max(part.size)
    canvas = Image.new("RGB", (side, side), BG)
    canvas.paste(part, ((side - part.width) // 2, (side - part.height) // 2))
    return canvas.resize((SIZE, SIZE), Image.LANCZOS)


def cut_shop():
    out = []
    folder = os.path.join(ROOT, "src", "img", "shop")
    os.makedirs(folder, exist_ok=True)
    jobs = [("shop-flow-sheet.png", ["flow-%02d" % i for i in range(1, 16)], False),
            ("shop-story-sheet.png", ["story-%02d" % i for i in range(1, 16)], False),
            ("shop-customers-sheet.png", ["guest-" + g for g in GUEST_IDS], True)]
    for sheet_name, names, trim in jobs:
        sheet = Image.open(os.path.join(ROOT, "docs", "img", "ref", sheet_name)).convert("RGB")
        for name, box in zip(names, shop_cells(trim)):
            im = cut_panel(sheet, box)
            im.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(os.path.join(folder, name + ".png"), optimize=True)
            out.append(im)
    cols = 10
    prev = Image.new("RGB", (cols * SIZE, ((len(out) + cols - 1) // cols) * SIZE), (210, 225, 235))
    for i, im in enumerate(out):
        prev.paste(im, ((i % cols) * SIZE, (i // cols) * SIZE))
    prev.save(os.path.join(ROOT, "docs", "img", "shop-preview.png"), optimize=True)
    return len(out)


def cut_outfits():
    """의상 시트 → src/img/outfits/<id>.png 15장 + 미리보기. 배경색은 시트 모서리의 중앙값(크림색)"""
    src = np.asarray(Image.open(os.path.join(ROOT, "docs", "img", "ref", OUTFIT_SHEET)).convert("RGB")).astype(int)
    bg = np.median(np.concatenate([src[:20, :20].reshape(-1, 3), src[-20:, -20:].reshape(-1, 3)]), axis=0).astype(int)
    x0, y0, x1, y1 = OUTFIT_TITLE
    src[y0:y1, x0:x1] = bg
    for x0, y0, x1, y1 in OUTFIT_LABELS:
        r = src[y0:y1, x0:x1]
        dark = (r.sum(2) < 330) & ((r.max(2) - r.min(2)) < 70)
        lab, _ = ndimage.label(dark)
        glyphs = np.zeros_like(dark)
        for i, sl in enumerate(ndimage.find_objects(lab), 1):
            touches = sl[0].start == 0 or sl[1].start == 0 or sl[0].stop == r.shape[0] or sl[1].stop == r.shape[1]
            if sl[0].stop - sl[0].start < 60 and sl[1].stop - sl[1].start < 60 and not touches:
                glyphs |= lab == i
        r[ndimage.binary_dilation(glyphs, iterations=3)] = bg
    sheet = Image.fromarray(src.astype("uint8"))
    fg = np.abs(src - bg).sum(2) > 60
    folder = os.path.join(ROOT, "src", "img", "outfits")
    os.makedirs(folder, exist_ok=True)
    out, ids = [], iter(OUTFIT_IDS)
    for (ry0, ry1), splits in zip(OUTFIT_ROWS, OUTFIT_SPLITS):
        edges = [0] + splits + [src.shape[1]]
        for cx0, cx1 in zip(edges, edges[1:]):
            ys, xs = np.nonzero(fg[ry0:ry1, cx0:cx1])
            h, w = fg.shape  # cut()이 PAD만큼 넓혀 자르므로 시트 밖(검은 띠)으로 나가지 않게 줄인다
            box = (max(PAD, cx0 + xs.min()), max(PAD, ry0 + ys.min()), min(w - PAD, cx0 + xs.max()), min(h - PAD, ry0 + ys.max()))
            im = cut(sheet, box, tuple(int(v) for v in bg))
            im.quantize(256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).save(os.path.join(folder, next(ids) + ".png"), optimize=True)
            out.append(im)
    prev = Image.new("RGB", (5 * SIZE, 3 * SIZE), (210, 225, 235))
    for i, im in enumerate(out):
        prev.paste(im, ((i % 5) * SIZE, (i // 5) * SIZE), im)
    prev.save(os.path.join(ROOT, "docs", "img", "outfits-preview.png"), optimize=True)
    return len(out)


def main():
    out = []
    jobs = [("yuki-sheet.jpg", YUKI, "yuki")]
    for sheet_name, table, folder in jobs:
        sheet = load(sheet_name)
        os.makedirs(os.path.join(ROOT, "src", "img", folder), exist_ok=True)
        for name, box in table.items():
            im = cut(sheet, box)
            im.quantize(256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).save(
                os.path.join(ROOT, "src", "img", folder, name + ".png"), optimize=True)
            out.append(im)
    cols = 8
    prev = Image.new("RGB", (cols * SIZE, ((len(out) + cols - 1) // cols) * SIZE), (210, 225, 235))
    for i, im in enumerate(out):
        prev.paste(im, ((i % cols) * SIZE, (i // cols) * SIZE), im)
    prev.save(os.path.join(ROOT, "docs", "img", "yuki-preview.png"), optimize=True)
    print("%d pictures, %d outfits, %d shop pictures" % (len(out), cut_outfits(), cut_shop()))


if __name__ == "__main__":
    main()
