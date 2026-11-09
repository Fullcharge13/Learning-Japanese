import { test } from "node:test";
import assert from "node:assert/strict";
import { orderOk } from "../../src/ui/lesson.js";

test("orderOk: the stored order, or any order listed in accept (Japanese word order is free)", () => {
  const it = { lines: ["毎日", "電車で", "行きます"], accept: [["電車で", "毎日", "行きます"]] };
  assert.equal(orderOk(it, ["毎日", "電車で", "行きます"]), true);
  assert.equal(orderOk(it, ["電車で", "毎日", "行きます"]), true);
  assert.equal(orderOk(it, ["行きます", "毎日", "電車で"]), false);
  assert.equal(orderOk({ lines: ["を", "を"] }, ["を", "を"]), true); // 같은 카드 둘
});
