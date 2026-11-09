"""축제 의상 그림 점검 (설계서 §3): 15장, 256px RGBA, 모서리 투명, 가운데 그림 있음, 옛 물건 그림 없음"""
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "src", "img", "outfits")
IDS = ["nebuta", "hanagasa", "awaodori", "yosakoi", "kanto", "tanabata", "gion", "tenjin", "yamakasa", "eisa",
       "hyakumangoku", "owara", "nishimonai", "yassa", "ohara"]


def _open(i):
    return Image.open(os.path.join(OUT, i + ".png")).convert("RGBA")


def test_outfits_exist():
    for i in IDS:
        im = Image.open(os.path.join(OUT, i + ".png"))
        assert im.size == (256, 256), i


def test_outfits_transparent_edges():
    for i in IDS:
        im = _open(i)
        for xy in [(0, 0), (255, 0), (0, 255), (255, 255)]:
            assert im.getpixel(xy)[3] == 0, (i, xy)
        mid = im.crop((96, 96, 160, 160))
        solid = sum(1 for p in mid.getdata() if p[3] > 200)
        assert solid >= 64 * 64 * 0.2, (i, solid)


def test_items_gone():
    assert not os.path.exists(os.path.join(ROOT, "src", "img", "items"))


def test_outfits_no_border_lines():
    """가장자리 2px 띠에 불투명 픽셀이 거의 없음(시트 밖을 잘라 생긴 검은 줄 막기)"""
    for i in IDS:
        im = _open(i)
        px = im.load()
        band = [(x, y) for x in range(256) for y in (0, 1, 254, 255)] + [(x, y) for y in range(256) for x in (0, 1, 254, 255)]
        solid = sum(1 for xy in band if px[xy][3] > 200)
        assert solid < len(band) * 0.05, (i, solid)
