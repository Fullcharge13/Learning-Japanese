// 저장: localStorage 한 칸에 JSON 하나. 옛 저장은 migrate로 새 형식에 맞춘다.
// 리아와 파이썬·해치와 한국어와 같은 주소(github.io)에 올라가므로 저장 키를 따로 둔다(다른 앱 저장은 읽지도 지우지도 않음).
// 해치 앱 저장 파일은 모양이 같아서, 가져오기는 app 표시로 가린다(isOwnSave).
import { ITEMS } from "../data/items.js";
import { OLD_ITEM_PRICES } from "../data/old-items.js";
import { cleanSeenUpdates } from "./newcontent.js";
import { CONCEPTS } from "../data/concepts.js";
import { defaultShop, cleanShop } from "./shop/rules.js";

const WORD_IDS = new Set(CONCEPTS.map((c) => c.id));

export const SAVE_KEY = "sanada-japanese.save";
export const SAVE_VER = 2;
const LOG_CAP = 50;
const BROKEN_SLOTS = 5; // .broken 다음 .broken.1 ~ .broken.5
const BAD_KEYS = new Set(["__proto__", "constructor", "prototype"]);

export function newSave() {
  return {
    app: "sanada-japanese",
    saveVer: SAVE_VER,
    current_chapter: 1, current_lesson: "1-1",
    completed_lessons: [],
    submission_logs: [],
    grading_results: {},
    weak_concepts: {},
    review_queue: [],
    last_active_at: null,
    xp: 0, bytes: 0,
    streak: { days: 0, best: 0, lastGoalDate: null, todayDate: null, todayXp: 0 },
    freezes: 0,
    quests: { date: null, ids: [], progress: {}, done: [], chest: false },
    badges: [], items: ["none"], item: "none",
    stats: { lessons: 0, perfect: 0, review_items: 0 },
    settings: { sound: true, dailyGoal: 20, name: "" },
    shop: defaultShop(), // 다코야키 가게(src/shop/rules.js). 없거나 망가지면 migrate가 cleanShop으로
    seen_updates: {},  // v0.7.1 「새 내용」 점: { 레슨 id: 끝까지 다시 본 판 "v0.7.1" }. saveVer 그대로, 없으면 {}
  };
}

const isPlainObject = (v) =>
  v !== null && typeof v === "object" && !Array.isArray(v) &&
  (Object.getPrototypeOf(v) === Object.prototype || Object.getPrototypeOf(v) === null);

// 위험한 키를 빼고 얕게 복사한다.
function safeCopy(obj) {
  const out = {};
  for (const key of Object.keys(obj)) if (!BAD_KEYS.has(key)) out[key] = obj[key];
  return out;
}

// 기본값의 종류에 맞는 옛 값만 받아들이고, 아니면 기본값을 쓴다.
function coerce(d, v) {
  if (d === null) return v;                                   // null 기본: 무엇이든 받음
  if (Array.isArray(d)) return Array.isArray(v) ? v : d;
  if (typeof d === "number") {
    if (typeof v === "number") return Number.isFinite(v) ? v : d;
    if (typeof v === "string" && v.trim() !== "") {
      const n = Number(v);
      return Number.isFinite(n) ? n : d;
    }
    return d;
  }
  if (typeof d === "boolean") return typeof v === "boolean" ? v : d;
  if (typeof d === "string") return typeof v === "string" ? v : d;
  if (isPlainObject(d)) {
    if (!isPlainObject(v)) return d;
    return Object.keys(d).length > 0 ? fill(d, v) : safeCopy(v);
  }
  return v;
}

// 기본값 위에 옛 값을 덮는다. 기본값에 없는 칸은 그대로 남긴다.
function fill(defaults, raw) {
  const out = { ...defaults };
  for (const key of Object.keys(raw)) {
    if (BAD_KEYS.has(key)) continue;
    out[key] = Object.hasOwn(defaults, key) ? coerce(defaults[key], raw[key]) : raw[key];
  }
  return out;
}

const MAX_FREEZES = 2;
const nonNegInt = (v) => Math.max(0, Math.floor(v));

// 값의 범위를 맞춘다(타입은 fill에서 이미 숫자로 맞춰져 있음).
function clampRanges(s) {
  s.freezes = Math.min(MAX_FREEZES, nonNegInt(s.freezes));
  s.xp = nonNegInt(s.xp);
  s.bytes = nonNegInt(s.bytes);
  s.streak.days = nonNegInt(s.streak.days);
  s.streak.best = nonNegInt(s.streak.best);
  for (const k of Object.keys(s.stats)) {
    if (typeof s.stats[k] === "number") s.stats[k] = nonNegInt(s.stats[k]);
  }
  const wc = {};
  for (const [k, v] of Object.entries(s.weak_concepts)) {
    if (typeof v === "number" && Number.isFinite(v) && v >= 0) wc[k] = v;
  }
  s.weak_concepts = wc;
  s.seen_updates = cleanSeenUpdates(s.seen_updates);
  return s;
}

const ITEM_ORDER = ITEMS.map((o) => o.id);
const REFUND_MAX = 1e6; // 옛 물건을 다 사도 6,060엔. 이보다 큰 값은 깨진 값

// 옛 물건(축제 의상 전) 처리: 산 값은 엔으로(같은 id는 한 번), 30일 보상 가도마츠는 네부타 의상으로.
// 옛 id는 뒤의 cleanItems가 버리므로 다시 불러와도 또 돌려주지 않는다. 돌려준 엔은 item_refund에 쌓아 앱이 한 번 알린다.
function refundOldItems(s) {
  const prev = s.item_refund;
  let refund = Number.isInteger(prev) && prev > 0 && prev <= REFUND_MAX ? prev : 0;
  const owned = new Set(s.items.filter((x) => typeof x === "string"));
  for (const id of owned) if (Object.hasOwn(OLD_ITEM_PRICES, id)) { refund += OLD_ITEM_PRICES[id]; s.bytes += OLD_ITEM_PRICES[id]; }
  if (owned.has("kadomatsu")) s.items.push("nebuta");
  if (refund > 0) s.item_refund = refund; else delete s.item_refund;
  return s;
}

/** 돌려준 엔 안내를 한 번만: { save: item_refund를 뺀 저장, refund: 알릴 엔(없으면 0) } */
export function takeRefund(save) {
  const { item_refund: refund = 0, ...rest } = save;
  return { save: rest, refund };
}

// 가진 의상·입은 의상 정리: 의상 표 순서, 중복 없음, none 항상 포함, 표에 없는 id는 버림. 입은 의상이 가진 것이 아니면 none.
function cleanItems(s) {
  const owned = new Set(["none", ...s.items.filter((x) => typeof x === "string")]);
  s.items = ITEM_ORDER.filter((id) => owned.has(id));
  if (!s.items.includes(s.item)) s.item = "none";
  return s;
}

export function migrate(raw) {
  if (!isPlainObject(raw)) return newSave();
  const oldVer = raw.saveVer;
  const ver = typeof oldVer === "number" && Number.isFinite(oldVer) ? oldVer : 1; // saveVer 없음 = 첫 판(1)
  const s = clampRanges(fill(newSave(), structuredClone(raw)));
  refundOldItems(s);
  cleanItems(s);
  s.app = "sanada-japanese";
  s.shop = cleanShop(raw.shop);
  // 이 앱에 없는 단어(다른 앱 저장·지운 단어)는 복습·약한 단어에서 뺀다 — 복습 카드가 빈 채로 남지 않게
  s.review_queue = s.review_queue.filter((id) => WORD_IDS.has(id));
  s.weak_concepts = Object.fromEntries(Object.entries(s.weak_concepts).filter(([id]) => WORD_IDS.has(id)));
  s.saveVer = ver > SAVE_VER ? ver : SAVE_VER;
  return s;
}

// 깨진 원본을 남긴다. 이미 남긴 것은 덮지 않고 .broken.1 ~ .broken.5 중 빈 칸에 쓴다(모두 차면 .broken.5를 덮음).
function keepBroken(storage, text) {
  const keys = [SAVE_KEY + ".broken"];
  for (let i = 1; i <= BROKEN_SLOTS; i++) keys.push(`${SAVE_KEY}.broken.${i}`);
  try {
    const free = keys.find((k) => storage.getItem(k) === null);
    storage.setItem(free ?? keys[keys.length - 1], text);
  } catch { /* 남기지 못해도 새 저장으로 시작 */ }
}

export function loadEx(storage, key = SAVE_KEY) {
  let text;
  try {
    text = storage.getItem(key);
  } catch {
    return { save: newSave(), readFailed: true };
  }
  if (text === null || text === undefined) return { save: newSave(), readFailed: false };
  let raw;
  try {
    raw = JSON.parse(text);
  } catch {
    keepBroken(storage, text);
    return { save: newSave(), readFailed: false };
  }
  if (!isPlainObject(raw)) {
    keepBroken(storage, text);
    return { save: newSave(), readFailed: false };
  }
  return { save: migrate(raw), readFailed: false };
}

/** 가져온 파일이 이 앱의 저장인지: app 표시가 이 앱(해치 앱 저장은 모양이 같아 표시로 가림), 물건 칸이 있고 리아의 의상 칸이 없음 */
export function isOwnSave(raw) {
  return isPlainObject(raw) && raw.app === "sanada-japanese" && Array.isArray(raw.items) && typeof raw.item === "string" && !("outfits" in raw);
}

export function load(storage) {
  return loadEx(storage).save;
}

export function store(storage, save, key = SAVE_KEY) {
  const logs = Array.isArray(save.submission_logs) ? save.submission_logs.slice(-LOG_CAP) : [];
  try {
    storage.setItem(key, JSON.stringify({ ...save, submission_logs: logs }));
    return true;
  } catch {
    return false;
  }
}
