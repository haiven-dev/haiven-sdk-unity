import { chromium } from "playwright";
import { readFile, writeFile } from "node:fs/promises";
import assert from "node:assert/strict";
import { join } from "node:path";
const output = process.env.HAIVEN_WEBGL_OUTPUT;
const report = join(process.env.HAIVEN_UNITY_RESULTS, "browser.json");
const build = JSON.parse(await readFile(join(output, "haiven-build.json"), "utf8"));
assert.deepEqual(build, { unity:"2022.3.62f2", stripping:"High", result:"Succeeded" });
const origin = "http://127.0.0.1:18765";
const before = await (await fetch(origin + "/stats")).json();
const browser = await chromium.launch({headless:true, args:["--enable-unsafe-swiftshader"]});
const events = [];
let passed = false;
try {
  const page = await browser.newPage();
  page.on("console", message => {
    const text = message.text(); events.push(text); console.log(text);
    if (text.trim() === "HAIVEN_WEBGL_PASS") passed = true;
  });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto(origin, {timeout:30000});
  const deadline = Date.now() + 120000;
  while (!passed && Date.now() < deadline && !errors.length && !events.some(x => x.includes("HAIVEN_WEBGL_FAIL"))) await new Promise(r => setTimeout(r, 200));
  assert.equal(passed, true, "built player did not report completion");
  assert.deepEqual(errors, []);
  assert.equal(events.some(x => x.includes("HAIVEN_WEBGL_FAIL")), false);
  // Verify Dispose closes the real browser socket before closing the page.
  let after;
  for (let i=0; i<50; i++) {
    after = await (await fetch(origin + "/stats")).json();
    if (after.connections === 0 && after.closed > before.closed) break;
    await new Promise(r => setTimeout(r, 100));
  }
  assert.equal(after.connections, 0, "Dispose leaked the browser socket");
  assert.equal(after.roundTrips - before.roundTrips, 1);
  assert.equal(after.closed - before.closed, 1);
  assert.equal(after.exchanges - before.exchanges, 1);
  assert.deepEqual(after.lastExchange, {
    code:"webgl-code",
    integration_id:"webgl-smoke",
    redirect_uri:"http://127.0.0.1:18765/callback?mode=login",
    keys:["code", "code_verifier", "integration_id", "redirect_uri"],
  });
  await writeFile(report, JSON.stringify({result:"Passed",tests:1,build,before,after}, null, 2));
} finally { await browser.close(); }
