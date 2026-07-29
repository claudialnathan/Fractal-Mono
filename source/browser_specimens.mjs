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
  const loaded = await page.evaluate(() => document.fonts.check('400 16px "CLN Mono"'));
  if (!loaded) errors.push(`${name}: CLN Mono did not load`);
  return page;
}

const code = await openPage("code-example.html", { width: 1440, height: 1138 });
results.codeLigatures = await code.locator(".code").evaluate(
  (element) => getComputedStyle(element).fontVariantLigatures
);
results.codeVersion = (await code.locator(".version").textContent())?.trim();
await code.screenshot({ path: `${specimens}/CLNMono-code-example.png`, fullPage: true });

const ligatures = await openPage("ligature-specimen.html", { width: 1440, height: 1000 });
const ligatureToggle = ligatures.getByRole("checkbox", { name: /Optional programming ligatures/i });
results.ligatureToggleDefault = await ligatureToggle.isChecked();
results.ligatureDefault = await ligatures.locator(".hero-proof").evaluate(
  (element) => getComputedStyle(element).fontVariantLigatures
);
await ligatures.screenshot({ path: `${specimens}/CLNMono-ligature-specimen.png`, fullPage: true });
await ligatures
  .locator(".group")
  .filter({ hasText: "Markup" })
  .screenshot({ path: `${specimens}/CLNMono-markup-proof.png` });
await ligatureToggle.check();
results.ligatureEnabled = await ligatures.locator(".hero-proof").evaluate(
  (element) => getComputedStyle(element).fontVariantLigatures
);

const audit = await openPage("ligature-audit.html", { width: 1440, height: 1000 });
results.auditRows = await audit.locator(".row").count();
results.auditToggleDefault = await audit.getByRole("checkbox", { name: /Preview optional programming ligatures/i }).isChecked();
await audit.screenshot({ path: `${specimens}/CLNMono-ligature-audit.png`, fullPage: true });

const main = await openPage("specimen.html", { width: 1440, height: 1000 });
results.mainError = await main.locator("body").getAttribute("data-specimen-error");
results.mainOverflow = await main.evaluate(
  () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
);
results.mainVersion = (await main.locator("[data-footer-version]").textContent())?.trim();
const opticalSlider = main.locator("#tester-optical");
results.opticalDefault = await opticalSlider.inputValue();
await opticalSlider.fill("72");
results.opticalDisplay = await main.locator("#tester-text").evaluate(
  (element) => getComputedStyle(element).fontVariationSettings,
);
await main.screenshot({ path: `${specimens}/CLNMono-factsheet.png`, fullPage: true });

const outline = await browser.newPage({ viewport: { width: 1600, height: 760 } });
outline.on("pageerror", (error) => errors.push(`outline proof: ${error.message}`));
await outline.goto(pathToFileURL(`${specimens}/CLNMono-outline-proof.svg`).href, {
  waitUntil: "load",
});
await outline.screenshot({ path: `${specimens}/CLNMono-outline-proof.png` });

const failures = [
  results.codeLigatures !== "none" &&
    `code page does not disable ligatures: ${results.codeLigatures}`,
  results.codeVersion !== "CLN Mono 1.300 · ligatures off" &&
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
  results.mainVersion !== "Version 1.300" &&
    `unexpected main specimen version: ${results.mainVersion}`,
  results.opticalDefault !== "14" &&
    `unexpected optical-size default: ${results.opticalDefault}`,
  !results.opticalDisplay.includes('"opsz" 72') &&
    `optical-size control did not reach Display: ${results.opticalDisplay}`,
  ...errors,
].filter(Boolean);

await Promise.all([
  code.close(),
  ligatures.close(),
  audit.close(),
  main.close(),
  outline.close(),
]);
await browser.close();
console.log(JSON.stringify({ ...results, errors }, null, 2));

if (failures.length) {
  throw new Error(failures.join("\n"));
}
