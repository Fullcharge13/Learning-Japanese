import { test } from "node:test";
import assert from "node:assert/strict";
import { buy, place } from "../../src/shop.js";
import { ITEMS } from "../../data/items.js";
import { newSave } from "../../src/save.js";

const mk = (over = {}) => ({ ...newSave(), ...over });

test("ITEMS table: empty hand + 34 Japanese items, kadomatsu is the 30-day reward", () => {
  assert.equal(ITEMS.length, 35);
  assert.equal(new Set(ITEMS.map((x) => x.id)).size, 35);
  assert.equal(ITEMS[0].id, "none");
  assert.equal(ITEMS[0].unlock, "start");
  const k = ITEMS.find((x) => x.id === "kadomatsu");
  assert.equal(k.unlock, "streak30");
  assert.equal(k.price, null);
  for (const x of ITEMS.slice(1)) {
    assert.ok(x.ko && x.jp, x.id);
    if (x.id !== "kadomatsu") assert.ok([60, 120, 180, 240, 300].includes(x.price), x.id);
  }
  assert.equal(ITEMS.find((x) => x.id === "kimono").jp, "着物{きもの}");
});

test("buy: needs enough coins, adds the item, takes the price", () => {
  assert.ok(buy(mk({ bytes: 59 }), "dango") instanceof Error);
  const s = buy(mk({ bytes: 80 }), "dango");
  assert.deepEqual(s.items, ["none", "dango"]);
  assert.equal(s.bytes, 20);
  assert.ok(buy(s, "dango") instanceof Error, "already owned");
  assert.ok(buy(mk({ bytes: 999 }), "kadomatsu") instanceof Error, "not for sale");
  assert.ok(buy(mk({ bytes: 999 }), "pirate") instanceof Error, "unknown");
});

test("place: only an owned item can sit beside Yuki", () => {
  assert.ok(place(mk(), "kimono") instanceof Error);
  assert.equal(place(mk({ items: ["none", "kimono"] }), "kimono").item, "kimono");
  assert.equal(place(mk({ items: ["none", "kimono"], item: "kimono" }), "none").item, "none");
});
