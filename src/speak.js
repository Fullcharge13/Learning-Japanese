// 🔊 발음: 기기 내장 음성(Web Speech API)으로 일본어 읽기를 읽는다. 없거나 실패하면 조용히 false.
import { kana } from "./ruby.js";

export function canSpeak(win = globalThis) {
  return !!(win && win.speechSynthesis && win.SpeechSynthesisUtterance);
}

/** text(「学生{がくせい}」 꼴 가능)의 읽기를 ja-JP로 읽는다. 앞 소리는 멈춘다 */
export function speak(text, win = globalThis) {
  const t = kana(text).trim();
  if (!t || !canSpeak(win)) return false;
  try {
    const u = new win.SpeechSynthesisUtterance(t);
    u.lang = "ja-JP";
    u.rate = 0.9;
    win.speechSynthesis.cancel();
    win.speechSynthesis.speak(u);
    return true;
  } catch {
    return false;
  }
}
