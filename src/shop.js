// 축제 의상 사기·입기. 성공하면 새 Save, 실패하면 Error
import { ITEMS } from "../data/items.js";

export function buy(save, id) {
  const o = ITEMS.find((x) => x.id === id);
  if (!o) return new Error(`없는 의상이에요: ${id}`);
  if ((save.items || []).includes(id)) return new Error("이미 가진 의상이에요");
  if (o.price == null) return new Error("팔지 않는 의상이에요");
  const bytes = save.bytes || 0;
  if (bytes < o.price) return new Error(`엔이 모자라요 (${bytes}/${o.price})`);
  return { ...save, bytes: bytes - o.price, items: [...(save.items || []), id] };
}

/** 가진 의상 하나를 입는다("none"은 평소 옷) */
export function place(save, id) {
  if (!(save.items || []).includes(id)) return new Error("아직 없는 의상이에요");
  return { ...save, item: id };
}
