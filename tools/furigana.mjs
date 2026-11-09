// 개발 도구: 일본어 문장 → 「漢字{よみ}」 후리가나 표기 (kuroshiro MIT + kuromoji Apache-2.0). 앱에는 들어가지 않는다.
//   node tools/furigana.mjs "毎朝六時に起きる。" [문장 …]
// 형태소 분석 결과라 읽기가 틀릴 수 있다(숫자+조수사, 같은 표기 다른 읽기) — 예문에 넣기 전에 사람이 확인한다.
import Kuroshiro from "kuroshiro";
import KuromojiAnalyzer from "kuroshiro-analyzer-kuromoji";

const k = new (Kuroshiro.default || Kuroshiro)();
await k.init(new (KuromojiAnalyzer.default || KuromojiAnalyzer)());
for (const s of process.argv.slice(2)) {
  const html = await k.convert(s, { mode: "furigana", to: "hiragana" });
  // <ruby>漢<rp>(</rp><rt>かん</rt><rp>)</rp></ruby> → 漢{かん}
  console.log(html.replace(/<ruby>([^<]*)<rp>\(<\/rp><rt>([^<]*)<\/rt><rp>\)<\/rp><\/ruby>/g, "$1{$2}"));
}
