import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SAVE_KEY } from "../../src/save.js";
import { RESUME_KEY } from "../../src/resume.js";
import { INSTALL_HINT_KEY } from "../../src/install.js";

test("every storage key is this app's own (Haechi Korean and Ria apps share the github.io origin)", () => {
  for (const k of [SAVE_KEY, RESUME_KEY, INSTALL_HINT_KEY]) assert.ok(k.startsWith("sanada-japanese."), k);
  assert.ok(!/(ria-python|haechi-korean)\./.test(readFileSync(new URL("../../src/app.js", import.meta.url), "utf8")));
});
