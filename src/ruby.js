// 후리가나 표기: 단어 표·대사는 「学生{がくせい}」처럼 한자 바로 뒤 {읽기}로 적는다.
// 덮는 범위는 {} 바로 앞의 한자 덩어리뿐(「お茶{ちゃ}」 → お + 茶에 ちゃ).
import { esc } from "./ui/dom.js";

const RUBY = /([㐀-鿿々〆ヶ]+)\{([^{}]+)\}/g;

/** 이스케이프한 HTML. 한자{읽기} → <ruby>한자<rt>읽기</rt></ruby> */
export function ruby(text) {
  const s = String(text ?? "");
  let out = "", last = 0;
  for (const m of s.matchAll(RUBY)) {
    out += esc(s.slice(last, m.index)) + `<ruby>${esc(m[1])}<rt>${esc(m[2])}</rt></ruby>`;
    last = m.index + m[0].length;
  }
  return out + esc(s.slice(last));
}

/** 읽기(가나): 한자{읽기} → 읽기 */
export const kana = (text) => String(text ?? "").replace(RUBY, "$2");

/** 표기: {읽기}를 지운 글자 */
export const plain = (text) => String(text ?? "").replace(RUBY, "$1");
