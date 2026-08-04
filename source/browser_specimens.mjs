import { readFileSync } from "node:fs";
// Read from source/version.py so a release cannot leave this behind.
const VERSION = readFileSync(new URL("version.py", import.meta.url), "utf8")
  .match(/^VERSION = "([^"]+)"/m)[1];
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { chromium } from "playwright";

const project = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const specimens = `${project}/specimens`;
const browser = await chromium.launch({ headless: true });
const errors = [];
const results = {};

async function openPage(name, viewport) {
  const page = await browser.newPage({ viewport });
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      errors.push(`${name} ${message.type()}: ${message.text()}`);
    }
  });
  page.on("pageerror", (error) => errors.push(`${name}: ${error.message}`));
  await page.goto(pathToFileURL(`${project}/${name}`).href, { waitUntil: "load" });
  await page.evaluate(() => document.fonts.ready);
  const loaded = await page.evaluate(() => document.fonts.check('400 16px "Fractal Mono"'));
  if (!loaded) errors.push(`${name}: Fractal Mono did not load`);
  return page;
}

const code = await openPage("code-example.html", { width: 1440, height: 1138 });
results.codeLigatures = await code.locator(".code").evaluate(
  (element) => getComputedStyle(element).fontVariantLigatures
);
results.codeVersion = (await code.locator(".version").textContent())?.trim();
await code.screenshot({ path: `${specimens}/FractalMono-code-example.png`, fullPage: true });

const ligatures = await openPage("ligature-specimen.html", { width: 1440, height: 1000 });
const ligatureToggle = ligatures.getByRole("checkbox", { name: /Optional programming ligatures/i });
results.ligatureToggleDefault = await ligatureToggle.isChecked();
results.ligatureDefault = await ligatures.locator(".hero-proof").evaluate(
  (element) => getComputedStyle(element).fontVariantLigatures
);
await ligatures.screenshot({ path: `${specimens}/FractalMono-ligature-specimen.png`, fullPage: true });
await ligatures
  .locator(".group")
  .filter({ hasText: "Markup" })
  .screenshot({ path: `${specimens}/FractalMono-markup-proof.png` });
await ligatureToggle.check();
results.ligatureEnabled = await ligatures.locator(".hero-proof").evaluate(
  (element) => getComputedStyle(element).fontVariantLigatures
);

const audit = await openPage("ligature-audit.html", { width: 1440, height: 1000 });
results.auditRows = await audit.locator(".row").count();
results.auditToggleDefault = await audit.getByRole("checkbox", { name: /Preview optional programming ligatures/i }).isChecked();
await audit.screenshot({ path: `${specimens}/FractalMono-ligature-audit.png`, fullPage: true });

const main = await openPage("specimen.html", { width: 1440, height: 1000 });
results.mainError = await main.locator("body").getAttribute("data-specimen-error");
results.mainOverflow = await main.evaluate(
  () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
);
results.mainVersion = (await main.locator("[data-footer-version]").textContent())?.trim();
const opticalSlider = main.locator("#tester-optical");
const widthSlider = main.locator("#tester-width");
results.opticalDefault = await opticalSlider.inputValue();
results.widthDefault = await widthSlider.inputValue();
await widthSlider.fill("115");
await opticalSlider.fill("72");
results.opticalDisplay = await main.locator("#tester-text").evaluate(
  (element) => getComputedStyle(element).fontVariationSettings,
);
results.widthAnimation = await main.evaluate(async () => {
  const probe = document.createElement("span");
  probe.textContent = "MMMMMMMMMM";
  Object.assign(probe.style, {
    position: "fixed",
    inset: "0 auto auto 0",
    visibility: "hidden",
    whiteSpace: "pre",
    fontFamily: '"Fractal Mono", monospace',
    fontSize: "96px",
    fontWeight: "400",
    fontVariationSettings: '"wdth" 85, "opsz" 14',
  });
  document.body.append(probe);
  const condensed = probe.getBoundingClientRect().width;
  probe.style.fontVariationSettings = '"wdth" 115, "opsz" 14';
  const expanded = probe.getBoundingClientRect().width;
  const animation = probe.animate(
    [
      { fontVariationSettings: '"wdth" 85, "opsz" 14' },
      { fontVariationSettings: '"wdth" 115, "opsz" 14' },
    ],
    { duration: 1000, fill: "both" },
  );
  animation.pause();
  animation.currentTime = 500;
  await new Promise((resolveFrame) => requestAnimationFrame(resolveFrame));
  const midpoint = probe.getBoundingClientRect().width;
  const settings = getComputedStyle(probe).fontVariationSettings;
  animation.cancel();
  probe.remove();
  return { condensed, midpoint, expanded, settings };
});
await main.screenshot({ path: `${specimens}/FractalMono-factsheet.png`, fullPage: true });

const outline = await browser.newPage({ viewport: { width: 1600, height: 760 } });
outline.on("pageerror", (error) => errors.push(`outline proof: ${error.message}`));
await outline.goto(pathToFileURL(`${specimens}/FractalMono-outline-proof.svg`).href, {
  waitUntil: "load",
});
await outline.screenshot({ path: `${specimens}/FractalMono-outline-proof.png` });

const signature = await browser.newPage({ viewport: { width: 1800, height: 1800 } });
signature.on("pageerror", (error) => errors.push(`RrK proof: ${error.message}`));
await signature.goto(pathToFileURL(`${specimens}/FractalMono-RrK-proof.svg`).href, {
  waitUntil: "load",
});
await signature.screenshot({ path: `${specimens}/FractalMono-RrK-proof.png` });

const failures = [
  results.codeLigatures !== "none" &&
    `code page does not disable ligatures: ${results.codeLigatures}`,
  results.codeVersion !== `Fractal Mono ${VERSION} · ligatures off` &&
    `unexpected code-page version: ${results.codeVersion}`,
  results.ligatureToggleDefault && "ligature feature is enabled by default in the specimen",
  results.ligatureDefault !== "none" &&
    `specimen does not default ligatures off: ${results.ligatureDefault}`,
  !results.ligatureEnabled.includes("discretionary-ligatures") &&
    `specimen dlig control did not enable the feature: ${results.ligatureEnabled}`,
  results.auditRows !== 153 && `expected 153 audit rows, received ${results.auditRows}`,
  results.auditToggleDefault && "audit dlig preview is enabled by default",
  results.mainError && `main specimen error: ${results.mainError}`,
  results.mainOverflow > 1 && `main specimen overflows by ${results.mainOverflow}px`,
  results.mainVersion !== `Version ${VERSION}` &&
    `unexpected main specimen version: ${results.mainVersion}`,
  results.opticalDefault !== "14" &&
    `unexpected optical-size default: ${results.opticalDefault}`,
  results.widthDefault !== "100" &&
    `unexpected width default: ${results.widthDefault}`,
  !results.opticalDisplay.includes('"opsz" 72') &&
    `optical-size control did not reach Display: ${results.opticalDisplay}`,
  !results.opticalDisplay.includes('"wdth" 115') &&
    `width control did not reach Expanded: ${results.opticalDisplay}`,
  !(
    results.widthAnimation.condensed <
      results.widthAnimation.midpoint &&
    results.widthAnimation.midpoint <
      results.widthAnimation.expanded
  ) &&
    `wdth animation did not progress monotonically: ${JSON.stringify(results.widthAnimation)}`,
  !results.widthAnimation.settings.includes('"wdth" 100') &&
    `wdth animation midpoint is not Normal: ${results.widthAnimation.settings}`,
  ...errors,
].filter(Boolean);

await Promise.all([
  code.close(),
  ligatures.close(),
  audit.close(),
  main.close(),
  outline.close(),
  signature.close(),
]);
await browser.close();
console.log(JSON.stringify({ ...results, errors }, null, 2));

if (failures.length) {
  throw new Error(failures.join("\n"));
}
