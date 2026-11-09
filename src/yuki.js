// 사나다 유키 선생님 그림: 참고 시트를 자른 PNG(tools/cut_sheets.py). 물건은 유키 옆에 한 개.
// 그림 주소는 index.html 기준 상대 주소(배포판·개발판 모두 img/ 폴더를 둠).

export const FACE_IDS = Object.freeze(["smile", "joy", "sparkle", "think", "surprise", "worry", "cheer", "wink", "hello", "done", "sleepy",
  "angry", "pout", "sad", "shy"]);
const ITEM_ID = /^[a-z]+$/;

export function yukiImg({ face = "smile", item = "none", size = 160 } = {}) {
  const f = FACE_IDS.includes(face) ? face : "smile";
  const px = Number.isFinite(+size) && +size > 0 ? Math.round(+size) : 160;
  const thing = typeof item === "string" && item !== "none" && ITEM_ID.test(item)
    ? `<img class="yuki-item" src="img/items/${item}.png" width="${Math.round(px * 0.45)}" height="${Math.round(px * 0.45)}" alt="" aria-hidden="true">` : "";
  return `<span class="yuki"><img class="yuki-img" src="img/yuki/${f}.png" width="${px}" height="${px}" alt="유키 선생님">${thing}</span>`;
}
