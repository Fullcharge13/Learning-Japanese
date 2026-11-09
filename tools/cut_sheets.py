#!/usr/bin/env python3
"""참고 그림 시트 → 앱 그림 PNG (한 번 실행해 결과를 커밋).

    python3 tools/cut_sheets.py

- docs/img/ref/yuki-sheet.jpg     → src/img/yuki/<표정>.png (15컷)
- docs/img/ref/items-sheet-1·2.jpg → src/img/items/<물건>.png
- 시트에 그려진 이름표 글씨(「기쁨」「하카마」 …)는 LABELS 상자를 배경색으로 덮어 지운다.
  그림 속 효과 글씨(「파이팅!」「아하!」「휴~」)는 그림의 일부라 남긴다.
- 칸 좌표는 이름표를 지운 시트에서 배경과 다른 덩어리를 찾아 정한 값(2576×1438). 정사각형 캔버스에 가운데 맞춰 256px.
- 하치마키(시트 1의 1행 3칸)는 욱일 무늬라 자르지 않는다(설계서 §6).
- 배경(흰색)에 가까운 픽셀은 투명하게(가장자리는 반투명).
- 미리보기: docs/img/yuki-preview.png
"""
import os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIZE, PAD = 256, 10
BG = (255, 255, 255)
NEAR, FAR = 24, 70   # 배경과의 색 거리: NEAR 이하 투명, FAR 이상 불투명

LABELS = {
    "yuki-sheet.jpg": [(405, 400, 505, 470), (940, 400, 1005, 470), (1450, 400, 1535, 470), (1940, 400, 2035, 470), (2428, 398, 2570, 476),
                       (412, 882, 552, 942), (925, 875, 1065, 945), (1440, 875, 1705, 945), (1935, 875, 2140, 945), (2418, 872, 2512, 948),
                       (398, 1292, 512, 1354), (398, 1358, 512, 1420), (585, 1350, 675, 1415), (1050, 1350, 1220, 1415), (1605, 1350, 1700, 1415), (2018, 1360, 2244, 1422)],
    "items-sheet-1.jpg": [(440, 412, 596, 490), (860, 412, 1080, 490), (1370, 412, 1580, 490), (1880, 412, 2036, 490), (2420, 412, 2530, 490),
                          (260, 880, 556, 955), (800, 880, 1050, 955), (1318, 880, 1580, 955), (1888, 880, 2056, 955), (2414, 880, 2526, 955),
                          (0, 1348, 2576, 1438)],
    "items-sheet-2.jpg": [(438, 412, 590, 490), (920, 412, 1076, 490), (1418, 412, 1580, 490), (1934, 412, 2042, 490), (2420, 412, 2526, 490),
                          (434, 880, 542, 955), (940, 880, 1050, 955), (1428, 880, 1536, 955), (1884, 880, 2042, 955), (2364, 880, 2526, 955),
                          (0, 1348, 2576, 1438), (1466, 988, 1644, 1118)],
}

YUKI = {  # (x0, y0, x1, y1)
    "joy": (100, 38, 479, 476), "angry": (613, 38, 993, 480), "sad": (1075, 38, 1537, 477),
    "surprise": (1587, 38, 2037, 476), "worry": (2117, 38, 2498, 477),
    "smile": (104, 502, 491, 956), "sleepy": (600, 516, 1043, 955), "done": (1122, 505, 1498, 953),
    "think": (1579, 506, 2075, 961), "sparkle": (2089, 500, 2526, 954),
    "pout": (113, 969, 500, 1427), "cheer": (526, 969, 1121, 1427), "shy": (1141, 970, 1500, 1427),
    "wink": (1652, 970, 2014, 1426), "hello": (2040, 969, 2512, 1427),
}
ITEMS = {
    "items-sheet-1.jpg": {
        "hakama": (104, 28, 512, 468), "jikatabi": (616, 49, 1018, 434), "kanzashi": (1624, 38, 2025, 453),
        "happi": (2086, 62, 2537, 453), "kiyomizu": (65, 538, 564, 885), "koinobori": (617, 507, 1041, 914),
        "kabuki": (1168, 516, 1481, 903), "noh": (1682, 509, 1992, 916), "tako": (2157, 506, 2472, 960),
        "osechi": (60, 980, 482, 1349), "dango": (518, 993, 778, 1353), "takoyaki": (803, 990, 1129, 1331),
        "taiyaki": (1133, 1045, 1464, 1301), "taiko": (1459, 1011, 1742, 1340), "kendama": (1745, 972, 1978, 1353),
        "koma": (1980, 1010, 2269, 1337), "kadomatsu": (2280, 972, 2533, 1353),
    },
    "items-sheet-2.jpg": {
        "kimono": (43, 9, 524, 503), "yukata": (612, 32, 1014, 501), "haori": (1073, 39, 1560, 454),
        "geta": (1585, 84, 2060, 440), "zori": (2084, 73, 2536, 454), "tabi": (90, 524, 497, 935),
        "obi": (609, 532, 1023, 908), "sensu": (1068, 546, 1573, 893), "uchiwa": (1659, 499, 2016, 967),
        "wagasa": (2084, 496, 2542, 958), "daruma": (107, 979, 450, 1346), "manekineko": (524, 979, 806, 1342),
        "omamori": (861, 974, 1112, 1347), "koto": (1262, 975, 1636, 1353), "torii": (1640, 994, 1973, 1343),
        "hannya": (1993, 1007, 2244, 1345), "furin": (2303, 972, 2492, 1353),
    },
}


def load(name):
    im = Image.open(os.path.join(ROOT, "docs", "img", "ref", name)).convert("RGB")
    d = ImageDraw.Draw(im)
    for r in LABELS.get(name, []):
        d.rectangle(r, fill=BG)
    return im


def cut(sheet, box):
    x0, y0, x1, y1 = box
    part = sheet.crop((x0 - PAD, y0 - PAD, x1 + PAD, y1 + PAD))
    side = max(part.size)
    canvas = Image.new("RGB", (side, side), BG)
    canvas.paste(part, ((side - part.width) // 2, (side - part.height) // 2))
    im = canvas.resize((SIZE, SIZE), Image.LANCZOS).convert("RGBA")
    px = im.load()
    for y in range(SIZE):
        for x in range(SIZE):
            r, g, b, _ = px[x, y]
            dist = abs(r - BG[0]) + abs(g - BG[1]) + abs(b - BG[2])
            if dist < FAR:
                px[x, y] = (r, g, b, 0 if dist <= NEAR else round(255 * (dist - NEAR) / (FAR - NEAR)))
    return im


def main():
    out = []
    jobs = [("yuki-sheet.jpg", YUKI, "yuki")] + [(n, t, "items") for n, t in ITEMS.items()]
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
    print("%d pictures" % len(out))


if __name__ == "__main__":
    main()
