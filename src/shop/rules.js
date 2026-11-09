// 유키의 다코야키 가게 규칙 — 순수 함수(화면 없음). 설계: docs/superpowers/specs/2026-11-09-다코야키-가게-설계.md
// 저장 save.shop: { v, day, money, upgrades, stories, xpToday: {date, n}, run }
// run은 하루를 시작할 때의 맥락(끝낸 장·메뉴·손님 수)을 담아, 장사 중에 레슨을 끝내거나 날짜가 바뀌어도 손님이 그대로다.
import {
  MENU, TEMPLATES, COUNTS, GREETINGS, GUESTS, UPGRADES, STORIES, FLOW,
  SHOP_TIP, BASE_GUESTS, MAX_GUESTS, DAY_XP, XP_RUNS_PER_DAY,
} from "../../data/shop.js";
import { mulberry32 } from "../shuffle.js";
import { earnXp } from "../rules.js";
import { ensureQuests, tick } from "../quests.js";

const MENU_BY = Object.fromEntries(MENU.map((m) => [m.id, m]));
const UP_BY = Object.fromEntries(UPGRADES.map((u) => [u.id, u]));
const STORY_IDS = new Set(STORIES.map((s) => s.id));
const STEPS = ["greet", "order", "bye"];
const MONEY_MAX = 1e9;
const DATE = /^\d{4}-\d{2}-\d{2}$/;

export function defaultShop() {
  return { v: 1, day: 0, money: 0, upgrades: [], stories: [], xpToday: { date: null, n: 0 }, run: null };
}

function rngFrom(text) {
  let h = 2166136261; // FNV-1a
  for (const ch of String(text)) { h ^= ch.codePointAt(0); h = Math.imul(h, 16777619); }
  return mulberry32(h >>> 0);
}

function shuffled(list, rng) {
  const a = list.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

/** 평가를 통과한 장 가운데 가장 높은 번호(없으면 0) */
export function doneChapter(examIds, completed) {
  const done = new Set(completed || []);
  let max = 0;
  for (const [ch, id] of Object.entries(examIds || {})) if (done.has(id) && +ch > max) max = +ch;
  return max;
}

/** 히라가나(1장)·가타카나(2장) 평가를 모두 통과하면 열림 */
export function shopOpen(examIds, completed) {
  const done = new Set(completed || []);
  return [1, 2].every((ch) => examIds && examIds[ch] && done.has(examIds[ch]));
}

export function ownedMenus(shop) {
  const ups = new Set(shop.upgrades);
  return MENU.filter((m) => m.start || UPGRADES.some((u) => ups.has(u.id) && u.effect.menu === m.id)).map((m) => m.id);
}

export function guestCount(shop) {
  const extra = shop.upgrades.reduce((n, id) => n + ((UP_BY[id] && UP_BY[id].effect.guests) || 0), 0);
  return Math.min(MAX_GUESTS, BASE_GUESTS + extra);
}

/** 하루를 시작한다. 진행 중인 하루가 있으면 그대로 */
export function startRun(shop, { date, doneCh }) {
  if (shop.run) return shop;
  const dayNo = shop.day + 1;
  return { ...shop, run: { date, dayNo, seed: date + ":" + dayNo, ctx: { doneCh, menus: ownedMenus(shop), n: guestCount(shop) },
    idx: 0, step: "greet", results: [] } };
}

/** 그날 손님 목록: run.seed·run.ctx만 본다 */
export function dayCustomers(run) {
  const rng = rngFrom(run.seed);
  const { doneCh, menus, n } = run.ctx;
  const tpls = TEMPLATES.filter((t) => t.need <= doneCh);
  return shuffled(GUESTS, rng).slice(0, n).map((g) => {
    const liked = g.likes.filter((id) => menus.includes(id));
    const menu = liked.length && rng() < 0.5 ? liked[Math.floor(rng() * liked.length)] : menus[Math.floor(rng() * menus.length)];
    const tpl = tpls[Math.floor(rng() * tpls.length)];
    return { who: g.id, menu, count: tpl.count ? 1 + Math.floor(rng() * 3) : 1, tpl: tpl.id };
  });
}

/** 손님 말풍선: 일본어와(아직 배우지 않은 틀이면) 한국어 힌트 */
export function orderLine(c, doneCh) {
  const t = TEMPLATES.find((x) => x.id === c.tpl);
  const m = MENU_BY[c.menu], k = COUNTS[c.count - 1];
  const fill = (s, menu, count) => s.replace("{menu}", menu).replace("{count}", count);
  return { jp: fill(t.jp, m.jp, k.jp), hint: doneCh < t.learn ? fill(t.ko.replace("{menu_ko}", "{menu}").replace("{count_ko}", "{count}"), m.ko, k.ko) : null };
}

/** 인사 카드 3장(정답 1 + 오답 2), 씨앗이 같으면 같은 순서 */
export function greetCards(kind, seed) {
  const g = GREETINGS[kind];
  const rng = rngFrom(kind + ":" + seed);
  const cards = shuffled([g.answer, ...shuffled(g.wrong, rng).slice(0, 2)], rng);
  return { cards, answer: cards.indexOf(g.answer) };
}

export function judgeOrder(c, menuId, count) {
  return c.menu === menuId && c.count === count;
}

/** 손님 한 명 값: 메뉴 값 × 개수, 세 단계를 모두 맞히면 팁(마네키네코 +5%p), 1円 아래 버림 */
export function payFor(c, allRight, shop) {
  const base = MENU_BY[c.menu].price * c.count;
  if (!allRight) return base;
  const rate = SHOP_TIP + shop.upgrades.reduce((r, id) => r + ((UP_BY[id] && UP_BY[id].effect.tip) || 0), 0);
  return base + Math.floor(base * rate + 1e-9);
}

export function runDone(shop) {
  return !!shop.run && shop.run.idx >= shop.run.ctx.n;
}

/** 지금 단계의 결과를 남기고 다음 단계(손님)로 */
export function recordStep(shop, ok) {
  if (!shop.run || runDone(shop)) return shop;
  const run = { ...shop.run, results: shop.run.results.slice() };
  const r = { greet: null, order: null, bye: null, paid: 0, ...run.results[run.idx] };
  r[run.step] = !!ok;
  if (run.step === "bye") {
    r.paid = payFor(dayCustomers(run)[run.idx], r.greet && r.order && r.bye, shop);
    run.results[run.idx] = r;
    run.idx += 1;
    run.step = "greet";
  } else {
    run.results[run.idx] = r;
    run.step = STEPS[STEPS.indexOf(run.step) + 1];
  }
  return { ...shop, run };
}

/** 정산: 진행 중인 하루를 끝낸다. 돈·일수·이야기 컷, 앱 XP는 정산하는 날짜마다 2번까지 */
export function finishDay(save, today) {
  const shop = save.shop;
  if (!shop || !shop.run) return new Error("진행 중인 장사가 없어요");
  if (!runDone(shop)) return new Error("아직 손님이 남았어요");
  const res = shop.run.results;
  const money = res.reduce((n, r) => n + r.paid, 0);
  const day = shop.day + 1;
  const st = STORIES.find((s) => s.day === day && !shop.stories.includes(s.id));
  const used = shop.xpToday.date === today ? shop.xpToday.n : 0;
  const xp = used < XP_RUNS_PER_DAY ? DAY_XP : 0;
  let s = { ...save, shop: { ...shop, day, money: Math.min(MONEY_MAX, shop.money + money),
    stories: st ? [...shop.stories, st.id] : shop.stories, xpToday: { date: today, n: used + (xp ? 1 : 0) }, run: null } };
  let milestone = null, finished = [], chest = false;
  if (xp) {
    const e = earnXp(s, xp, today);
    milestone = e.milestone;
    const t = tick(ensureQuests(e.save, today), "xp", today, xp);
    ({ save: s, finished, chest } = t);
  }
  // milestone·finished·chest: 정산 화면이 레슨 완료처럼 축하 창·끝낸 퀘스트를 보여 준다
  return { save: s, report: { money, right: res.filter((r) => r.greet && r.order && r.bye).length, total: res.length, xp, story: st ? st.id : null,
    milestone, finished, chest } };
}

export function buyUpgrade(shop, id) {
  const u = UP_BY[id];
  if (!u) return new Error("없는 업그레이드예요: " + id);
  if (shop.upgrades.includes(id)) return new Error("이미 샀어요");
  if (shop.money < u.price) return new Error(`가게 금고가 모자라요 (${shop.money}/${u.price})`);
  return { ...shop, money: shop.money - u.price, upgrades: [...shop.upgrades, id] };
}

const int = (v, lo, hi) => (typeof v === "number" && Number.isFinite(v) ? Math.min(hi, Math.max(lo, Math.floor(v))) : lo);
const isObj = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
const uniq = (list, ok) => (Array.isArray(list) ? [...new Set(list.filter((x) => typeof x === "string" && ok(x)))] : []);

function cleanRun(r) {
  if (!isObj(r) || !isObj(r.ctx) || typeof r.date !== "string" || !DATE.test(r.date) || typeof r.seed !== "string") return null;
  const { doneCh, menus, n } = r.ctx;
  // 가게는 2장(가타카나) 평가 뒤에 열린다: 그 전 장으로는 쓸 수 있는 주문 틀이 없어 손님을 만들 수 없음
  if (!Number.isInteger(doneCh) || doneCh < 2 || !Number.isInteger(n) || n < 1 || n > MAX_GUESTS) return null;
  if (!Array.isArray(menus) || !menus.length || !menus.every((m) => MENU_BY[m])) return null;
  if (!Number.isInteger(r.dayNo) || r.dayNo < 1 || !Number.isInteger(r.idx) || r.idx < 0 || r.idx > n || !STEPS.includes(r.step)) return null;
  if (!Array.isArray(r.results) || r.results.length > n || !r.results.every(isObj)) return null;
  return { date: r.date, dayNo: r.dayNo, seed: r.seed, ctx: { doneCh, menus: menus.slice(), n }, idx: r.idx, step: r.step,
    results: r.results.map((x) => ({ greet: x.greet ?? null, order: x.order ?? null, bye: x.bye ?? null, paid: int(x.paid, 0, MONEY_MAX) })) };
}

/** 망가진 저장을 기본값으로 정리 */
export function cleanShop(raw) {
  if (!isObj(raw)) return defaultShop();
  const xp = isObj(raw.xpToday) ? raw.xpToday : {};
  return {
    v: 1,
    day: int(raw.day, 0, 1e6),
    money: int(raw.money, 0, MONEY_MAX),
    upgrades: uniq(raw.upgrades, (x) => UP_BY[x]),
    stories: uniq(raw.stories, (x) => STORY_IDS.has(x)),
    xpToday: { date: typeof xp.date === "string" && DATE.test(xp.date) ? xp.date : null, n: int(xp.n, 0, XP_RUNS_PER_DAY) },
    run: cleanRun(raw.run),
  };
}

/** 손님 passed명을 보낸 뒤 보여 줄 흐름 컷 id(없으면 null). 하루 컷 수 = floor((n-1)/2), 가운데 13컷(flow-02..14)을 날마다 이어서 돌림 */
export function flowCut(run, passed) {
  const n = run.ctx.n, k = Math.floor((n - 1) / 2);
  if (passed % 2 !== 0 || passed >= n || k < 1) return null;
  const mid = FLOW.length - 2;
  return FLOW[1 + (((run.dayNo - 1) * k + passed / 2 - 1) % mid)].id;
}
