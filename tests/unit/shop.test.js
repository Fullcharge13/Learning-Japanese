import { test } from "node:test";
import assert from "node:assert/strict";
import { buy, place } from "../../src/shop.js";
import { ITEMS, OUTFIT_IDS } from "../../data/items.js";
import { newSave } from "../../src/save.js";

const mk = (over = {}) => ({ ...newSave(), ...over });

test("ITEMS table: plain clothes + 15 festival outfits, nebuta is the 30-day reward", () => {
  assert.equal(ITEMS.length, 16);
  assert.equal(new Set(ITEMS.map((x) => x.id)).size, 16);
  assert.deepEqual({ ...ITEMS[0] }, { id: "none", ko: "평소 옷", jp: "いつもの服{ふく}", price: null, unlock: "start" });
  const k = ITEMS.find((x) => x.id === "nebuta");
  assert.equal(k.unlock, "streak30");
  assert.equal(k.price, null);
  const prices = ITEMS.slice(1).filter((x) => x.id !== "nebuta").map((x) => x.price).sort((a, b) => a - b);
  assert.deepEqual(prices, [120, 120, 120, 180, 180, 180, 180, 240, 240, 240, 240, 300, 300, 300]);
  const t = ITEMS.find((x) => x.id === "tenjin");
  assert.deepEqual([t.ko, t.jp, t.price], ["오사카 덴진 마쓰리", "天神祭{てんじんまつり}", 120]);
  assert.deepEqual(OUTFIT_IDS, ITEMS.slice(1).map((x) => x.id));
  const bare = /[\u4e00-\u9fff々](?![\u4e00-\u9fff々]*\{)/; // 후리가나 없는 한자
  for (const x of ITEMS) assert.ok(!bare.test(x.jp), x.id);
});

test("buy: needs enough yen, adds the outfit, takes the price", () => {
  assert.ok(buy(mk({ bytes: 119 }), "tenjin") instanceof Error);
  const s = buy(mk({ bytes: 130 }), "tenjin");
  assert.deepEqual(s.items, ["none", "tenjin"]);
  assert.equal(s.bytes, 10);
  assert.ok(buy(s, "tenjin") instanceof Error, "already owned");
  assert.ok(buy(mk({ bytes: 999 }), "nebuta") instanceof Error, "not for sale");
  assert.ok(buy(mk({ bytes: 999 }), "kimono") instanceof Error, "old item gone");
});

test("place: only an owned outfit can be worn", () => {
  assert.ok(place(mk(), "gion") instanceof Error);
  assert.equal(place(mk({ items: ["none", "gion"] }), "gion").item, "gion");
  assert.equal(place(mk({ items: ["none", "gion"], item: "gion" }), "none").item, "none");
});
