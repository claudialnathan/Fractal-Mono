import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { chromium } from "playwright";

const project = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const output = `${project}/specimens`;
const artifact = `${output}/CLN-Mono-Type-Specimen.html`;
const preview = `${output}/CLN-Mono-Type-Specimen-Preview.png`;
const mobilePreview = `${output}/CLN-Mono-Type-Specimen-Mobile.png`;
const codePreview = `${output}/CLN-Mono-Type-Specimen-Code.png`;
const repertoirePreview = `${output}/CLN-Mono-Type-Specimen-Repertoire.png`;
const rPreview = `${output}/CLN-Mono-Type-Specimen-Lowercase-R.png`;
const rasterPreview = `${output}/CLN-Mono-Rasterisation-1x.png`;
const rasterRetinaPreview = `${output}/CLN-Mono-Rasterisation-2x.png`;

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });
const consoleMessages = [];
const pageErrors = [];
const requests = [];

page.on("console", (message) => {
  if (["error", "warning"].includes(message.type())) {
    consoleMessages.push(`${message.type()}: ${message.text()}`);
  }
});
page.on("pageerror", (error) => pageErrors.push(error.message));
page.on("request", (request) => requests.push(request.url()));

await page.goto(pathToFileURL(artifact).href, { waitUntil: "load" });
await page.evaluate(() => document.fonts.ready);

const fontLoaded = await page.evaluate(() =>
  document.fonts.check('400 16px "CLN Mono Specimen"')
);
const fontFamily = await page.locator("#plain-tester").evaluate(
  (element) => getComputedStyle(element).fontFamily
);
const displayedVersion = await page.locator(".meta-value").first().textContent();
const glyphCards = await page.locator(".glyph-card").count();
const initialVisibleCount = await page.locator("#character-count").textContent();
const accessibleStructure = {
  h1: await page.getByRole("heading", { level: 1, name: "CLN MONO" }).count(),
  h2: await page.getByRole("heading", { level: 2 }).count(),
  slider: await page.getByRole("slider", { name: /Weight axis/i }).count(),
  programmingLigatures: await page.getByRole("checkbox", { name: /Optional programming ligatures/i }).count(),
  plainTester: await page.getByRole("textbox", { name: "Plain text" }).count(),
  codeTester: await page.getByRole("textbox", { name: "Code / JavaScript" }).count(),
  characterSearch: await page.getByRole("searchbox", { name: "Filter characters" }).count(),
};

await page.locator("#weight").fill("800");
const maxWeight = await page.locator("#plain-tester").evaluate(
  (element) => getComputedStyle(element).fontWeight
);
await page.locator("#weight").fill("137");
const intermediateWeight = await page.locator("#code-tester").evaluate(
  (element) => getComputedStyle(element).fontWeight
);
await page.locator("#weight").fill("400");

const plainText = "A live plain-text tester — editable at every weight.";
const codeText = 'const exact = value === 3 && state !== "idle";';
await page.getByLabel("Plain text").fill(plainText);
await page.getByLabel("Code / JavaScript").fill(codeText);
const testerValues = await Promise.all([
  page.getByLabel("Plain text").inputValue(),
  page.getByLabel("Code / JavaScript").inputValue(),
]);
const ligatureDefault = await page.locator("#code-tester").evaluate(
  (element) => getComputedStyle(element).fontVariantLigatures
);
await page.getByRole("checkbox", { name: /Optional programming ligatures/i }).check();
const ligatureEnabled = await page.locator("#code-tester").evaluate(
  (element) => getComputedStyle(element).fontVariantLigatures
);

await page.locator("#character-search").fill("U+0410");
const filteredCount = await page.locator("#character-count").textContent();
const visibleFilteredCards = await page.locator(".glyph-card:not([hidden])").count();
await page.locator("#character-search").fill("");

const desktopOverflow = await page.evaluate(
  () => document.documentElement.scrollWidth > document.documentElement.clientWidth
);

await page.reload({ waitUntil: "load" });
await page.evaluate(() => document.fonts.ready);
await page.evaluate(() => window.scrollTo(0, 0));
await page.screenshot({ path: preview, fullPage: false });

await page.locator('section[aria-labelledby="code-heading"]').scrollIntoViewIfNeeded();
await page.screenshot({ path: codePreview, fullPage: false });
await page.locator(".core-line").first().scrollIntoViewIfNeeded();
await page.screenshot({ path: rPreview, fullPage: false });
await page.locator(".weight-control").evaluate((element) => {
  element.style.display = "none";
});
await page.locator('section[aria-labelledby="raster-heading"]').screenshot({ path: rasterPreview });
await page.locator("#glyph-grid").scrollIntoViewIfNeeded();
await page.screenshot({ path: repertoirePreview, fullPage: false });

const retinaPage = await browser.newPage({
  viewport: { width: 800, height: 1100 },
  deviceScaleFactor: 2,
});
await retinaPage.goto(pathToFileURL(artifact).href, { waitUntil: "load" });
await retinaPage.evaluate(() => document.fonts.ready);
await retinaPage.locator(".weight-control").evaluate((element) => {
  element.style.display = "none";
});
await retinaPage.locator('section[aria-labelledby="raster-heading"]').screenshot({
  path: rasterRetinaPreview,
});
await retinaPage.close();

await page.setViewportSize({ width: 390, height: 844 });
await page.reload({ waitUntil: "load" });
await page.evaluate(() => document.fonts.ready);
await page.evaluate(() => window.scrollTo(0, 0));
const mobileOverflow = await page.evaluate(
  () => document.documentElement.scrollWidth > document.documentElement.clientWidth
);
await page.screenshot({ path: mobilePreview, fullPage: false });

const externalRequests = requests.filter(
  (url) => !url.startsWith("file:") && !url.startsWith("data:")
);

const result = {
  fontLoaded,
  fontFamily,
  displayedVersion,
  glyphCards,
  initialVisibleCount,
  accessibleStructure,
  maxWeight,
  intermediateWeight,
  testerValues,
  ligatureDefault,
  ligatureEnabled,
  filteredCount,
  visibleFilteredCards,
  desktopOverflow,
  mobileOverflow,
  consoleMessages,
  pageErrors,
  externalRequests,
  preview,
  mobilePreview,
  codePreview,
  repertoirePreview,
  rPreview,
  rasterPreview,
  rasterRetinaPreview,
};

console.log(JSON.stringify(result, null, 2));

const failures = [
  !fontLoaded && "embedded variable font did not load",
  displayedVersion?.trim() !== "Version 1.300" && `unexpected specimen version: ${displayedVersion}`,
  glyphCards !== 1363 && `expected 1363 glyph cards, received ${glyphCards}`,
  initialVisibleCount?.trim() !== "1,363 / 1,363" && "initial character count is wrong",
  Object.entries(accessibleStructure).some(([, count]) => count !== 1 && count !== 7) &&
    `unexpected accessible structure: ${JSON.stringify(accessibleStructure)}`,
  accessibleStructure.h2 !== 7 && `expected seven level-two headings, received ${accessibleStructure.h2}`,
  maxWeight !== "800" && `weight 800 resolved to ${maxWeight}`,
  intermediateWeight !== "137" && `weight 137 resolved to ${intermediateWeight}`,
  testerValues[0] !== plainText && "plain tester is not editable",
  testerValues[1] !== codeText && "code tester is not editable",
  ligatureDefault !== "none" && `ligatures are not disabled by default: ${ligatureDefault}`,
  !ligatureEnabled.includes("discretionary-ligatures") &&
    `dlig opt-in did not enable: ${ligatureEnabled}`,
  filteredCount?.trim() !== "1 / 1,363" && "character filter count is wrong",
  visibleFilteredCards !== 1 && "character filter did not isolate one card",
  desktopOverflow && "desktop layout has horizontal overflow",
  mobileOverflow && "mobile layout has horizontal overflow",
  consoleMessages.length > 0 && "console contains errors or warnings",
  pageErrors.length > 0 && "page emitted an uncaught error",
  externalRequests.length > 0 && "page made an external request",
].filter(Boolean);

await browser.close();

if (failures.length > 0) {
  throw new Error(failures.join("\n"));
}
