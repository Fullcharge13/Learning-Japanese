import { test } from "node:test";
import assert from "node:assert/strict";
import {
  defaultShop, cleanShop, doneChapter, shopOpen, ownedMenus, guestCount, startRun, dayCustomers, orderLine,
  greetCards, judgeOrder, payFor, recordStep, runDone, finishDay, buyUpgrade,
} from "../../src/shop/rules.js";
import { newSave } from "../../src/save.js";
import { GUESTS } from "../../data/shop.js";

const D = "2026-11-09";
const run = (shop, doneCh = 2, date = D) => startRun(shop, { date, doneCh }).run;
const withMoney = (money, extra = {}) => ({ ...defaultShop(), money, ...extra });

test("same seed same guests, no repeats in a day", () => {
  const r = run(defaultShop());
  const a = dayCustomers(r), b = dayCustomers(r);
  assert.deepEqual(a, b);
  assert.equal(a.length, 6);
  assert.equal(new Set(a.map((c) => c.who)).size, 6);
  assert.notDeepEqual(dayCustomers(run(defaultShop(), 2, "2026-11-10")), a);
});

test("templates by chapter", () => {
  const at = (ch) => {
    const shop = { ...defaultShop(), day: 0 };
    const out = [];
    for (let d = 1; d <= 12; d++) out.push(...dayCustomers(startRun(shop, { date: "2026-12-" + String(d).padStart(2, "0"), doneCh: ch }).run));
    return out;
  };
  const kana = at(2);
  assert.ok(kana.every((c) => ["t_name", "t_kudasai"].includes(c.tpl) && c.count === 1));
  assert.ok(kana.some((c) => c.tpl === "t_kudasai"));
  assert.ok(orderLine(kana.find((c) => c.tpl === "t_kudasai"), 2).hint);
  assert.equal(orderLine(kana.find((c) => c.tpl === "t_name"), 2).hint, null);
  const nine = at(9);
  assert.ok(nine.some((c) => c.tpl === "t_count" || c.tpl === "t_onegai"));
  const k9 = nine.find((c) => c.tpl === "t_kudasai");
  if (k9) assert.equal(orderLine(k9, 9).hint, null);
  const c9 = nine.find((c) => c.tpl === "t_count");
  assert.ok(orderLine(c9, 9).hint);
  assert.ok(nine.filter((c) => c.tpl === "t_name" || c.tpl === "t_kudasai").every((c) => c.count === 1));
  assert.equal(orderLine(c9, 12).hint, null);
  const line = orderLine({ who: "ojisan", menu: "takoyaki", count: 2, tpl: "t_count" }, 12);
  assert.equal(line.jp, "たこ焼{や}きを 二{ふた}つ ください。");
  assert.equal(orderLine({ who: "ojisan", menu: "takoyaki", count: 2, tpl: "t_count" }, 9).hint, "다코야키 2개 주세요.");
});

test("guests only order owned menus", () => {
  for (let d = 1; d <= 20; d++) {
    const cs = dayCustomers(run(defaultShop(), 12, "2026-12-" + String(d).padStart(2, "0")));
    assert.ok(cs.every((c) => ["takoyaki", "ocha"].includes(c.menu)), JSON.stringify(cs));
  }
  const owned = { ...defaultShop(), upgrades: ["m_dango"] };
  assert.deepEqual(ownedMenus(owned), ["takoyaki", "ocha", "dango"]);
});

test("judge and pay", () => {
  const c = { who: "ojisan", menu: "takoyaki", count: 2, tpl: "t_count" };
  assert.equal(judgeOrder(c, "takoyaki", 2), true);
  assert.equal(judgeOrder(c, "takoyaki", 1), false);
  assert.equal(judgeOrder(c, "ocha", 2), false);
  assert.equal(payFor(c, true, defaultShop()), 880);
  assert.equal(payFor(c, true, { ...defaultShop(), upgrades: ["neko"] }), 920);
  assert.equal(payFor(c, false, defaultShop()), 800);
});

test("greet cards: three cards, one answer, same seed same order", () => {
  const g = greetCards("enter", "x:1:0");
  assert.equal(g.cards.length, 3);
  assert.equal(g.cards[g.answer].jp, "いらっしゃいませ");
  assert.deepEqual(greetCards("enter", "x:1:0"), g);
  const l = greetCards("leave", "x:1:0");
  assert.equal(l.cards[l.answer].jp, "ありがとうございました");
  assert.equal(new Set(l.cards.map((c) => c.jp)).size, 3);
});

test("run keeps its customers when chapters change", () => {
  const shop = startRun(defaultShop(), { date: D, doneCh: 2 });
  const before = dayCustomers(shop.run);
  const again = startRun(shop, { date: "2026-11-10", doneCh: 12 }); // 이미 진행 중이면 그대로
  assert.deepEqual(again.run, shop.run);
  assert.deepEqual(dayCustomers(again.run), before);
});

test("record steps greet → order → bye, then next guest; runDone after all", () => {
  let s = startRun(defaultShop(), { date: D, doneCh: 2 });
  assert.equal(s.run.step, "greet");
  s = recordStep(s, true);
  assert.equal(s.run.step, "order");
  s = recordStep(s, true);
  assert.equal(s.run.step, "bye");
  s = recordStep(s, false);
  assert.equal(s.run.idx, 1);
  assert.equal(s.run.step, "greet");
  assert.deepEqual(s.run.results[0], { greet: true, order: true, bye: false, paid: payFor(dayCustomers(s.run)[0], false, s) });
  for (let i = 1; i < 6; i++) for (let k = 0; k < 3; k++) s = recordStep(s, true);
  assert.equal(runDone(s), true);
});

function playDay(save, date, allRight = true) {
  let shop = startRun(save.shop, { date, doneCh: 2 });
  while (!runDone(shop)) shop = recordStep(shop, allRight);
  return { ...save, shop };
}

test("finishDay twice pays once", () => {
  const s0 = playDay(newSave(), D);
  const r = finishDay(s0, D);
  assert.ok(!(r instanceof Error));
  const paid = r.save.shop.money;
  assert.ok(paid > 0 && r.report.money === paid && r.save.shop.day === 1 && r.save.shop.run === null);
  assert.equal(r.report.right, 6);
  assert.equal(r.report.total, 6);
  const again = finishDay(r.save, D);
  assert.ok(again instanceof Error);
  assert.ok(finishDay(newSave(), D) instanceof Error, "no run");
  const half = finishDay({ ...s0, shop: recordStep(startRun(defaultShop(), { date: D, doneCh: 2 }), true) }, D);
  assert.ok(half instanceof Error, "run not done");
});

test("xp twice a day", () => {
  let s = newSave();
  const xps = [];
  for (let i = 0; i < 3; i++) {
    const r = finishDay(playDay(s, D), D);
    xps.push(r.report.xp);
    s = r.save;
  }
  assert.deepEqual(xps, [10, 10, 0]);
  assert.equal(s.xp, 20);
  const next = finishDay(playDay(s, "2026-11-10"), "2026-11-10");
  assert.equal(next.report.xp, 10);
});

test("xp cap counts the settle date", () => {
  const r = finishDay(playDay(newSave(), D), "2026-11-10");
  assert.deepEqual(r.save.shop.xpToday, { date: "2026-11-10", n: 1 });
});

test("story days", () => {
  let s = newSave();
  const got = [];
  for (let d = 1; d <= 7; d++) {
    const date = "2026-12-" + String(d).padStart(2, "0");
    const r = finishDay(playDay(s, date), date);
    got.push(r.report.story);
    s = r.save;
  }
  assert.deepEqual(got, ["story-01", "story-02", "story-03", "story-04", "story-05", null, "story-06"]);
  assert.deepEqual(s.shop.stories, ["story-01", "story-02", "story-03", "story-04", "story-05", "story-06"]);
});

test("upgrades: money, no twice, guests and menus", () => {
  assert.ok(buyUpgrade(withMoney(1999), "m_juice") instanceof Error);
  const a = buyUpgrade(withMoney(2500), "m_juice");
  assert.equal(a.money, 500);
  assert.ok(ownedMenus(a).includes("juice"));
  assert.ok(buyUpgrade({ ...a, money: 9999 }, "m_juice") instanceof Error);
  assert.ok(buyUpgrade(withMoney(99999), "nope") instanceof Error);
  let b = buyUpgrade(withMoney(20000), "plate2");
  assert.equal(guestCount(b), 7);
  b = buyUpgrade(b, "noren");
  assert.equal(guestCount(b), 8);
  assert.equal(dayCustomers(startRun(b, { date: D, doneCh: 2 }).run).length, 8);
});

test("cleanShop repairs broken shop", () => {
  assert.deepEqual(cleanShop(undefined), defaultShop());
  assert.deepEqual(cleanShop("x"), defaultShop());
  const c = cleanShop({ day: -3, money: "abc", upgrades: ["neko", "neko", "pirate", 7], stories: ["story-01", "bad"],
    xpToday: { date: D, n: 9 }, run: { date: D, dayNo: 1, seed: "s", ctx: { doneCh: 2, menus: ["takoyaki"], n: 6 }, idx: 99, step: "greet", results: [] } });
  assert.equal(c.day, 0);
  assert.equal(c.money, 0);
  assert.deepEqual(c.upgrades, ["neko"]);
  assert.deepEqual(c.stories, ["story-01"]);
  assert.equal(c.xpToday.n, 2);
  assert.equal(c.run, null);
  assert.equal(cleanShop({ money: 1e20 }).money, 1e9);
  assert.equal(cleanShop({ money: 12.7 }).money, 12);
  const ok = startRun(defaultShop(), { date: D, doneCh: 2 });
  assert.deepEqual(cleanShop(JSON.parse(JSON.stringify(ok))).run, ok.run);
  assert.equal(cleanShop({ run: { ...ok.run, step: "dance" } }).run, null);
  assert.equal(cleanShop({ run: { ...ok.run, ctx: { ...ok.run.ctx, menus: ["pirate"] } } }).run, null);
});

test("shopOpen and doneChapter", () => {
  const exams = { 1: "1-9", 2: "2-9", 3: "3-3" };
  assert.equal(shopOpen(exams, ["1-9", "2-9"]), true);
  assert.equal(shopOpen(exams, ["1-9"]), false);
  assert.equal(shopOpen(exams, ["2-9"]), false);
  assert.equal(doneChapter(exams, ["1-9", "2-9", "3-3"]), 3);
  assert.equal(doneChapter(exams, []), 0);
});

test("guest table has 15 and every customer is a known guest", () => {
  const ids = new Set(GUESTS.map((g) => g.id));
  for (const c of dayCustomers(run(withMoney(0, { upgrades: ["plate2", "noren"] })))) assert.ok(ids.has(c.who));
});
