import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
// Read from source/version.py so a release cannot leave this behind.
const VERSION = readFileSync(new URL("version.py", import.meta.url), "utf8")
  .match(/^VERSION = "([^"]+)"/m)[1];
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createServer } from "node:http";
import { dirname, extname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import axe from "axe-core";

const project = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const output = `${project}/specimens`;
const axeSource = axe.source;
const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".md": "text/markdown; charset=utf-8",
  ".pdf": "application/pdf",
  ".png": "image/png",
  ".ttf": "font/ttf",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".zip": "application/zip",
};
const server = createServer(async (request, response) => {
  const pathname = decodeURIComponent(
    new URL(request.url, "http://127.0.0.1").pathname,
  );
  const filePath = resolve(project, `.${pathname}`);
  if (!filePath.startsWith(`${project}/`)) {
    response.writeHead(403).end("Forbidden");
    return;
  }
  try {
    const contents = await readFile(filePath);
    response.writeHead(200, {
      "Content-Type": contentTypes[extname(filePath)] ?? "application/octet-stream",
    });
    response.end(contents);
  } catch {
    response.writeHead(404).end("Not found");
  }
});
await new Promise((resolveListen) => {
  server.listen(0, "127.0.0.1", resolveListen);
});
server.unref();
const serverAddress = server.address();
const baseUrl = `http://127.0.0.1:${serverAddress.port}`;
const specimenUrl = `${baseUrl}/specimen.html`;
const browser = await chromium.launch({ headless: true });
const browserErrors = [];
const externalRequests = new Set();

function recordPageFailures(page, label) {
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      browserErrors.push(`${label} ${message.type()}: ${message.text()}`);
    }
  });
  page.on("pageerror", (error) => {
    browserErrors.push(`${label} pageerror: ${error.message}`);
  });
  page.on("request", (request) => {
    const url = request.url();
    if (!url.startsWith(baseUrl) && !url.startsWith("data:")) {
      externalRequests.add(url);
    }
  });
}

async function openSpecimen(page, label) {
  recordPageFailures(page, label);
  await page.goto(specimenUrl, { waitUntil: "load" });
  await page.waitForFunction(
    () =>
      document.body.dataset.specimenReady === "true" &&
      document.fonts.check('400 16px "Fractal Mono"'),
  );
}

const desktop = await browser.newPage({
  viewport: { width: 1440, height: 1000 },
  deviceScaleFactor: 1,
  colorScheme: "light",
});
await openSpecimen(desktop, "desktop");

const inventory = await desktop.evaluate(() => ({
  ready: document.body.dataset.specimenReady,
  featureCards: document.querySelectorAll(".feature-card").length,
  glyphCards: document.querySelectorAll(".glyph-card").length,
  unencodedGlyphs: document.querySelectorAll("#unencoded-glyphs li").length,
  languageRows: document.querySelectorAll(".language-list li").length,
  releaseFiles: document.querySelectorAll("#file-values tr").length,
  fontTables: document.querySelectorAll("#table-values tr").length,
  glyphTabStops: document.querySelectorAll('.glyph-card[tabindex="0"]').length,
  headings: {
    h1: document.querySelectorAll("h1").length,
    h2: document.querySelectorAll("h2").length,
  },
  landmarks: {
    header: document.querySelectorAll("body > header").length,
    main: document.querySelectorAll("main").length,
    footer: document.querySelectorAll("body > footer").length,
  },
  defaultCalt: document.querySelector('[data-feature="calt"] input').checked,
  defaultDlig: document.querySelector('[data-feature="dlig"] input').checked,
  specimenDlig: [...document.querySelectorAll(".ligature-toggle")].map(
    (input) => input.checked,
  ),
  optionalCount: document.querySelector("#active-feature-count").textContent,
  width: {
    scroll: document.documentElement.scrollWidth,
    viewport: window.innerWidth,
  },
}));

assert.equal(inventory.ready, "true");
assert.equal(inventory.featureCards, 39);
assert.equal(inventory.glyphCards, 1363);
assert.equal(inventory.unencodedGlyphs, 384);
assert.equal(inventory.languageRows, 363);
assert.equal(inventory.releaseFiles, 30);
assert.equal(inventory.fontTables, 18);
assert.equal(inventory.glyphTabStops, 1);
assert.deepEqual(inventory.headings, { h1: 1, h2: 10 });
assert.deepEqual(inventory.landmarks, { header: 1, main: 1, footer: 1 });
assert.equal(inventory.defaultCalt, true);
assert.equal(inventory.defaultDlig, false);
assert.equal(inventory.specimenDlig.every((value) => value === false), true);
assert.match(inventory.optionalCount, /^0 optional features active$/);
assert.ok(inventory.width.scroll <= inventory.width.viewport + 1);

const featureCards = await desktop.locator(".feature-card").all();
for (const card of featureCards) {
  const feature = await card.getAttribute("data-feature");
  const samples = card.locator(".feature-comparison p");
  const sampleCount = await samples.count();
  assert.ok(sampleCount >= 2, `${feature} needs a meaningful comparison`);
  const hashes = [];
  for (let index = 0; index < sampleCount; index += 1) {
    const screenshot = await samples.nth(index).screenshot({
      animations: "disabled",
    });
    hashes.push(createHash("sha256").update(screenshot).digest("hex"));
  }
  assert.equal(
    new Set(hashes).size,
    sampleCount,
    `${feature} comparison renders identical examples`,
  );
}

await desktop.addScriptTag({ content: axeSource });
const accessibility = {};
for (const theme of ["light", "dark"]) {
  await desktop.evaluate(
    (selectedTheme) => {
      document.documentElement.dataset.theme = selectedTheme;
    },
    theme,
  );
  await desktop.waitForTimeout(200);
  accessibility[theme] = await desktop.evaluate(async () => {
    const results = await window.axe.run(document, {
      runOnly: {
        type: "tag",
        values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"],
      },
    });
    return results.violations.map((violation) => ({
      id: violation.id,
      impact: violation.impact,
      nodes: violation.nodes.length,
    }));
  });
  assert.deepEqual(accessibility[theme], []);
}
await desktop.evaluate(() => {
  document.documentElement.dataset.theme = "light";
});

await desktop.emulateMedia({ reducedMotion: "reduce" });
const reducedMotion = await desktop.evaluate(() => ({
  scrollBehavior: getComputedStyle(document.documentElement).scrollBehavior,
  transitionDuration: getComputedStyle(
    document.querySelector(".theme-toggle"),
  ).transitionDuration,
}));
assert.equal(reducedMotion.scrollBehavior, "auto");
assert.match(reducedMotion.transitionDuration, /(?:0\.00001|1e-05)s/);
await desktop.emulateMedia({ reducedMotion: "no-preference" });

await desktop.evaluate(() => {
  document.documentElement.style.scrollBehavior = "auto";
  document.scrollingElement.scrollTop = 0;
});
await desktop.waitForFunction(() => window.scrollY === 0);
const lightScreenshot = await desktop.screenshot({
  path: `${output}/FractalMono-factsheet.png`,
  animations: "disabled",
});
assert.ok(lightScreenshot.length > 20_000, "light factsheet screenshot is blank");
await desktop.keyboard.press("Tab");
assert.equal(await desktop.locator(":focus").getAttribute("class"), "skip-link");
await desktop.locator(":focus").blur();

await desktop.locator(".theme-toggle").click();
await desktop.waitForFunction(
  () => document.documentElement.dataset.theme === "dark",
);
await desktop.evaluate(() => {
  document.scrollingElement.scrollTop = 0;
});
await desktop.waitForFunction(() => window.scrollY === 0);
const darkScreenshot = await desktop.screenshot({
  path: `${output}/FractalMono-factsheet-dark.png`,
  animations: "disabled",
});
assert.ok(darkScreenshot.length > 20_000, "dark factsheet screenshot is blank");
await desktop.locator(".theme-toggle").click();
await desktop.evaluate(() => {
  document.documentElement.style.removeProperty("scroll-behavior");
});

await desktop.locator('.glyph-card[tabindex="0"]').focus();
await desktop.keyboard.press("ArrowRight");
assert.match(
  await desktop.locator('.glyph-card[tabindex="0"]').getAttribute("aria-label"),
  /Latin Capital Letter B/,
);

await desktop.locator("#tester-weight").fill("137");
await desktop.locator("#tester-width").fill("113");
await desktop.locator("#tester-optical").fill("72");
await desktop.locator("#tester-size").fill("33");
await desktop.locator(".ligature-toggle").first().check();
const testerStyle = await desktop.locator("#tester-text").evaluate((element) => {
    const style = getComputedStyle(element);
    return {
      weight: style.fontWeight,
      size: style.fontSize,
      variations: style.fontVariationSettings,
    };
  });
assert.equal(testerStyle.weight, "137");
assert.equal(testerStyle.size, "33px");
assert.match(testerStyle.variations, /"opsz" 72/);
assert.match(testerStyle.variations, /"wdth" 113/);
assert.equal(
  await desktop.locator(".ligature-toggle").evaluateAll((inputs) =>
    inputs.every((input) => input.checked),
  ),
  true,
);

await desktop.locator('[data-feature="cv16"] input').check();
assert.match(
  await desktop
    .locator("#feature-preview")
    .evaluate((element) => element.style.fontFeatureSettings),
  /cv16/,
);
assert.match(
  await desktop.locator("#active-feature-count").textContent(),
  /^1 optional feature active$/,
);

await desktop.locator("#character-search").fill("U+0410");
assert.equal(await desktop.locator(".glyph-card:not([hidden])").count(), 1);
assert.match(
  await desktop
    .locator(".glyph-card:not([hidden])")
    .getAttribute("aria-label"),
  /Cyrillic Capital Letter A/,
);

await desktop.locator("#language-search").fill("Belarusian");
assert.equal(await desktop.locator(".language-list li").count(), 1);
assert.equal(
  await desktop.locator(".language-list b").textContent(),
  "Belarusian",
);

await desktop.locator(".theme-toggle").click();
assert.equal(
  await desktop.locator("html").getAttribute("data-theme"),
  "dark",
);
await desktop.locator(".theme-toggle").click();

await desktop.locator("#tester-reset").click();
await desktop.locator("#clear-features").click();
await desktop.locator("#character-search").fill("");
await desktop.locator("#language-search").fill("");
await desktop.evaluate(() => {
  document.scrollingElement.scrollTop =
    document.querySelector("#features").offsetTop;
});
await desktop.screenshot({
  path: `${output}/FractalMono-factsheet-features.png`,
  animations: "disabled",
});
await desktop.locator('[data-feature="case"]').screenshot({
  path: `${output}/FractalMono-case-feature.png`,
  animations: "disabled",
});

const mobile = await browser.newPage({
  viewport: { width: 390, height: 844 },
  deviceScaleFactor: 2,
  isMobile: true,
  hasTouch: true,
  colorScheme: "light",
});
await openSpecimen(mobile, "mobile");

const mobileChecks = await mobile.evaluate(() => ({
  width: {
    scroll: document.documentElement.scrollWidth,
    viewport: window.innerWidth,
  },
  controlFontSizes: [
    ...document.querySelectorAll(
      'input[type="number"], input[type="search"], select',
    ),
  ].map((element) => Number.parseFloat(getComputedStyle(element).fontSize)),
  headerHeight: document.querySelector(".site-header").getBoundingClientRect().height,
  downloadRight: document
    .querySelector(".download-button")
    .getBoundingClientRect().right,
}));
assert.ok(mobileChecks.width.scroll <= mobileChecks.width.viewport + 1);
assert.equal(
  mobileChecks.controlFontSizes.every((size) => size >= 16),
  true,
);
assert.ok(mobileChecks.headerHeight >= 44);
assert.ok(mobileChecks.downloadRight <= 391);

await mobile.screenshot({
  path: `${output}/FractalMono-factsheet-mobile.png`,
  animations: "disabled",
});

const printable = await browser.newPage({
  viewport: { width: 1440, height: 1000 },
  colorScheme: "light",
});
await openSpecimen(printable, "print");
await printable.emulateMedia({ media: "print", colorScheme: "light" });
await printable.pdf({
  path: `${output}/FractalMono-factsheet.pdf`,
  format: "A4",
  printBackground: true,
  margin: {
    top: "10mm",
    right: "10mm",
    bottom: "12mm",
    left: "10mm",
  },
  displayHeaderFooter: true,
  headerTemplate: "<span></span>",
  footerTemplate:
    '<div style="width:100%;padding:0 10mm;color:#777;font:8px monospace;display:flex;justify-content:space-between"><span>Fractal Mono ${VERSION}</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>',
});

await Promise.all([desktop.close(), mobile.close(), printable.close()]);
await browser.close();
await new Promise((resolveClose) => {
  server.close(resolveClose);
});

assert.deepEqual(browserErrors, []);
assert.deepEqual([...externalRequests], []);

console.log(
  JSON.stringify(
    {
      inventory,
      mobile: mobileChecks,
      accessibility,
      reducedMotion,
      browserErrors,
      externalRequests: [...externalRequests],
      outputs: [
        "specimens/FractalMono-factsheet.png",
        "specimens/FractalMono-factsheet-dark.png",
        "specimens/FractalMono-factsheet-features.png",
        "specimens/FractalMono-case-feature.png",
        "specimens/FractalMono-factsheet-mobile.png",
        "specimens/FractalMono-factsheet.pdf",
      ],
    },
    null,
    2,
  ),
);
