// 🔊 발음: 기기 내장 음성(Web Speech API)으로 일본어 읽기를 읽는다. 없거나 실패하면 조용히 false.
import { kana } from "./ruby.js";

export function canSpeak(win = globalThis) {
  return !!(win && win.speechSynthesis && win.SpeechSynthesisUtterance);
}

const PITCH = { 男: 0.8, 女: 1.25 }; // 목소리 하나로 두 사람처럼(청해 대화)

/** 대화 줄 나누기: 「男：…\n女：…」 → [{ who, text }]. 표시 없는 줄은 who "" */
export function dialogLines(text) {
  return String(text).split("\n").map((l) => l.trim()).filter(Boolean)
    .map((l) => { const m = l.match(/^([男女])：(.*)$/); return m ? { who: m[1], text: m[2] } : { who: "", text: l }; });
}

/** text(「学生{がくせい}」 꼴 가능)의 읽기를 ja-JP로 읽는다. 줄바꿈이 있으면 줄마다(男 낮게·女 높게). 앞 소리는 멈춘다 */
export function speak(text, win = globalThis) {
  const lines = dialogLines(text || "").map((l) => ({ ...l, text: kana(l.text).trim() })).filter((l) => l.text);
  if (!lines.length || !canSpeak(win)) return false;
  try {
    win.speechSynthesis.cancel();
    for (const l of lines) {
      const u = new win.SpeechSynthesisUtterance(l.text);
      u.lang = "ja-JP";
      u.rate = 0.9;
      if (PITCH[l.who]) u.pitch = PITCH[l.who];
      win.speechSynthesis.speak(u);
    }
    return true;
  } catch {
    return false;
  }
}
