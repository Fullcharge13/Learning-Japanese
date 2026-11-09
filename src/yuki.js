// 사나다 유키 선생님 그림: 참고 시트를 자른 PNG(tools/cut_sheets.py). 의상을 입었으면 표정 대신 그 의상 그림.
import { ITEMS } from "../data/items.js";
// 그림 주소는 index.html 기준 상대 주소(배포판·개발판 모두 img/ 폴더를 둠).

export const FACE_IDS = Object.freeze(["smile", "joy", "sparkle", "think", "surprise", "worry", "cheer", "wink", "hello", "done", "sleepy",
  "angry", "pout", "sad", "shy"]);

export function yukiImg({ face = "smile", item = "none", size = 160 } = {}) {
  const f = FACE_IDS.includes(face) ? face : "smile";
  const px = Number.isFinite(+size) && +size > 0 ? Math.round(+size) : 160;
  const o = item !== "none" && ITEMS.find((x) => x.id === item);
  if (o) return `<span class="yuki"><img class="yuki-img yuki-outfit" src="img/outfits/${o.id}.png" width="${px}" height="${px}" alt="${o.ko} 의상을 입은 유키 선생님"></span>`;
  return `<span class="yuki"><img class="yuki-img" src="img/yuki/${f}.png" width="${px}" height="${px}" alt="유키 선생님"></span>`;
}

// 홈 인사 때 무작위로 고르는 밝은 표정(화남·삐짐·슬픔·졸림은 인사로 어색해서 뺌)
export const GREET_FACES = Object.freeze(["smile", "joy", "sparkle", "wink", "hello", "cheer", "shy", "done", "surprise"]);

export function greetFace(rng = Math.random) {
  const v = Number(rng());
  const i = Number.isFinite(v) && v > 0 ? Math.min(GREET_FACES.length - 1, Math.floor(v * GREET_FACES.length)) : 0;
  return GREET_FACES[i];
}
