// 개발자 모드: 켜면 학습 기록과 따로 둔 저장 칸(DEV_SAVE_KEY)을 쓰고, 끄면 학습 기록으로 돌아간다.
import { SAVE_KEY, loadEx, store } from "./save.js";
import { RESUME_KEY } from "./resume.js";
import { DEV_MARK } from "./devgate.js";

export const DEV_FLAG_KEY = "sanada-japanese.dev";
export const DEV_SAVE_KEY = "sanada-japanese.dev.save";
export const DEV_RESUME_KEY = "sanada-japanese.dev.resume";

export const keysFor = (dev) => (dev ? { save: DEV_SAVE_KEY, resume: DEV_RESUME_KEY } : { save: SAVE_KEY, resume: RESUME_KEY });

export function readDevFlag(storage) {
  try { return storage.getItem(DEV_FLAG_KEY) === "1"; } catch { return false; }
}
export function writeDevFlag(storage, on) {
  try { on ? storage.setItem(DEV_FLAG_KEY, "1") : storage.removeItem(DEV_FLAG_KEY); return true; } catch { return false; }
}
export function markDev(save, on) {
  const { [DEV_MARK]: _, ...rest } = save;
  return on ? { ...rest, [DEV_MARK]: true } : rest;
}
export function loadSlot(storage, dev) {
  const r = loadEx(storage, keysFor(dev).save);
  return { ...r, save: markDev(r.save, dev) };
}
export const storeSlot = (storage, save, dev) => store(storage, save, keysFor(dev).save);
export function setDevMode(storage, on) {
  writeDevFlag(storage, on);
  return loadSlot(storage, on);
}
