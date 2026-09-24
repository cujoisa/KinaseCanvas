// Captures the KinaseCanvas Explorer (docs/index.html) for manuscript Figure 4: one full-page
// screenshot plus the bounding box of each panel, which make_fig4.R crops and composites.
// Usage (from the repository root):  node scripts/figure4/capture_fig4.js
// Uses the locally installed Google Chrome; set CHROME_PATH to point at a different Chromium binary.
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const REPO = path.resolve(__dirname, '..', '..');
const url = pathToFileURL(path.join(REPO, 'docs', 'index.html')).href;
const OUT = path.join(__dirname, 'capture');
fs.mkdirSync(OUT, { recursive: true });
(async () => {
  const launch = process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : { channel: 'chrome' };
  const browser = await chromium.launch({ ...launch, headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 2 });
  const errs = []; page.on('pageerror', e => errs.push(e.message));
  await page.goto(url); await page.waitForTimeout(2500);
  // the live page scrolls the sidebar internally when it is taller than the window; for the figure show it whole
  await page.addStyleTag({ content:
    '#sidebar{max-height:none !important;overflow:visible !important} '
    // let panel E run under panel D (gap 16 + detail 370)
    + '#table{width:calc(100% + 386px)}' });
  await page.check('#pairModeChk');
  await page.fill('#kinSel', 'TNIK'); await page.fill('#subSel', 'ORC2');
  await page.press('#subSel', 'Enter'); await page.waitForTimeout(2500);
  const box = await page.locator('#cy').boundingBox();
  let ok = false;
  for (const dy of [0, -4, 4, -8, 8, -12, 12]) {
    await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2 + dy); await page.waitForTimeout(400);
    if (/Sites/.test(await page.locator('#detailBody').innerText())) { ok = true; break; }
  }
  await page.uncheck('#pairModeChk');
  await page.fill('#subSel', ''); await page.fill('#kinSel', 'TNIK');
  await page.press('#kinSel', 'Enter'); await page.waitForTimeout(6000);
  const TABLE_ROWS = 14;
  await page.evaluate(n => {
    const box = document.querySelector('.tablebox'); const th = box.querySelector('thead').getBoundingClientRect().height;
    const rows = box.querySelectorAll('tbody tr'); const rh = rows[1].getBoundingClientRect().top - rows[0].getBoundingClientRect().top;
    box.style.maxHeight = (th + n * rh + 2) + 'px';
  }, TABLE_ROWS);
  await page.mouse.move(5, 5); await page.evaluate(() => window.scrollTo(0, 0)); await page.waitForTimeout(600);
  await page.screenshot({ path: OUT + '/page.png', fullPage: true });
  const boxes = {};
  for (const [k, sel] of [['topbar', '#topbar'], ['sidebar', '#sidebar'], ['cy', '#cy'], ['detail', '#detailPanel'],
                          ['table', '#table'], ['row6', '#edgesTable tbody tr:nth-child(6)'], ['row14', '#edgesTable tbody tr:nth-child(14)'],
                          ['thead', '#edgesTable thead']]) {
    const b = await page.locator(sel).first().boundingBox().catch(() => null);
    if (b) boxes[k] = { x: b.x, y: b.y, w: b.width, h: b.height };
  }
  fs.writeFileSync(OUT + '/boxes.json', JSON.stringify(boxes, null, 1));
  console.log('edge selected:', ok, '| errors:', errs.length ? errs : 'none');
  console.log(JSON.stringify(boxes));
  await browser.close();
})();
