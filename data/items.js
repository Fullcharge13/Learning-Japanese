// 보관함 의상: 「평소 옷」 + 일본 지역 축제 의상 15벌(설계서 2026-11-09-축제-의상 §2).
// 그림: src/img/outfits/<id>.png (tools/cut_sheets.py). price: null = 판매 안 함, unlock: 판매 외 얻는 방법. jp는 후리가나 표기(src/ruby.js)
export const ITEMS = [
  { id: "none", ko: "평소 옷", jp: "いつもの服{ふく}", price: null, unlock: "start" },
  { id: "nebuta", ko: "아오모리 네부타 마쓰리", jp: "青森{あおもり}ねぶた祭{まつ}り", price: null, unlock: "streak30" },
  { id: "hanagasa", ko: "야마가타 하나가사 마쓰리", jp: "山形{やまがた}花笠{はながさ}まつり", price: 240 },
  { id: "awaodori", ko: "도쿠시마 아와오도리", jp: "阿波{あわ}おどり", price: 180 },
  { id: "yosakoi", ko: "고치 요사코이 마쓰리", jp: "よさこい祭{まつ}り", price: 240 },
  { id: "kanto", ko: "아키타 간토 마쓰리", jp: "秋田{あきた}竿燈{かんとう}まつり", price: 180 },
  { id: "tanabata", ko: "센다이 다나바타 마쓰리", jp: "仙台{せんだい}七夕{たなばた}まつり", price: 180 },
  { id: "gion", ko: "교토 기온 마쓰리", jp: "祇園祭{ぎおんまつり}", price: 300 },
  { id: "tenjin", ko: "오사카 덴진 마쓰리", jp: "天神祭{てんじんまつり}", price: 120 },
  { id: "yamakasa", ko: "후쿠오카 하카타 기온 야마카사", jp: "博多{はかた}祇園山笠{ぎおんやまかさ}", price: 120 },
  { id: "eisa", ko: "오키나와 에이사", jp: "エイサー", price: 240 },
  { id: "hyakumangoku", ko: "이시카와 햐쿠만고쿠 마쓰리", jp: "百万石{ひゃくまんごく}まつり", price: 300 },
  { id: "owara", ko: "도야마 오와라 가제노본", jp: "おわら風{かぜ}の盆{ぼん}", price: 240 },
  { id: "nishimonai", ko: "아키타 니시모나이 본오도리", jp: "西馬音内{にしもない}盆踊{ぼんおど}り", price: 180 },
  { id: "yassa", ko: "히로시마 미하라 얏사 마쓰리", jp: "三原{みはら}やっさ祭{まつ}り", price: 120 },
  { id: "ohara", ko: "가고시마 오하라 마쓰리", jp: "おはら祭{まつり}", price: 300 },
];

export const OUTFIT_IDS = ITEMS.filter((o) => o.id !== "none").map((o) => o.id);
