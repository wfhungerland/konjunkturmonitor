// Onepager-Test: merkt Abbildungen als Lesezeichen, löst „Als Onepager (Word)“ aus und speichert die Datei.
// Die Seite läuft dafür über einen kleinen lokalen Webserver, weil der Browser Vorschaubilder von file:// nicht umrechnen darf.
// Aufruf: node tests/onepager.js site/index.html ziel.docx [kennung,kennung,…]
const { chromium } = require("playwright");
const http = require("http"), fs = require("fs"), path = require("path");
(async () => {
  const file = path.resolve(process.argv[2] || "site/index.html"), out = path.resolve(process.argv[3] || "onepager.docx");
  const root = fs.existsSync(path.join(path.dirname(file), "..", "plotly.min.js")) ? path.resolve(path.dirname(file), "..") : path.dirname(file);
  const types = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".webp": "image/webp", ".json": "application/json", ".woff2": "font/woff2", ".png": "image/png" };
  const srv = http.createServer((q, s) => { const f = path.join(root, decodeURIComponent(q.url.split("?")[0]));
    if (!f.startsWith(root) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { s.writeHead(404); return s.end(); }
    s.writeHead(200, { "Content-Type": types[path.extname(f)] || "application/octet-stream" }); fs.createReadStream(f).pipe(s); });
  await new Promise(r => srv.listen(0, "127.0.0.1", r));
  const url = `http://127.0.0.1:${srv.address().port}/${path.relative(root, file).split(path.sep).join("/")}`;
  const browser = await chromium.launch(), page = await browser.newPage({ viewport: { width: 1440, height: 900 }, acceptDownloads: true }), errors = [];
  page.on("pageerror", e => errors.push(e.message));
  await page.goto(url + "?alles=1", { waitUntil: "load" }); await page.waitForTimeout(800);
  // ohne Vorgabe: zwei Liniengrafiken, gestapelte Balken, eine Länderkarte, eine Abbildung mit Vorschaubild und eine ohne
  const ids = process.argv[4] ? process.argv[4].split(",") : await page.evaluate(() => { const all = DATA.topics.flatMap(t => t.charts).filter(c => c.chart);
    const kind = k => all.filter(c => kmKind(c) === k), rest = all.filter(c => !kmKind(c));
    const b = rest.filter(c => PREVS && PREVS[c.anchor]), d = rest.filter(c => !(PREVS && PREVS[c.anchor]));
    return [...kind("line").slice(0, 2), ...kind("stacked").slice(0, 1), ...kind("map").slice(0, 1), ...b.slice(0, 1), ...d.slice(0, 1)].map(c => c.chart); });
  await page.evaluate(ids => localStorage.setItem("km.sammlung", JSON.stringify(ids)), ids);
  await page.goto(url + "?alles=1#sammlung"); await page.reload({ waitUntil: "load" }); await page.waitForTimeout(1500);  // neu laden: die Seite liest die Lesezeichen beim Start
  const btn = page.locator("#sammlung .colbar button", { hasText: /Onepager|one-pager/ });
  if (!(await btn.count())) errors.push("Knopf für den Onepager fehlt in der Lesezeichen-Ansicht");
  else { const [dl] = await Promise.all([page.waitForEvent("download", { timeout: 30000 }), btn.click()]); await dl.saveAs(out);
    console.log(`Onepager: ${ids.length} Abbildungen, ${fs.statSync(out).size} Bytes, Name „${dl.suggestedFilename()}“`);
    if (!/^Konjunkturmonitor \(\d{4}-\d{2}-\d{2}\) \w+\.docx$/.test(dl.suggestedFilename())) errors.push("Dateiname folgt nicht dem Regelwerk: " + dl.suggestedFilename()); }
  await browser.close(); srv.close();
  if (errors.length) { console.error(errors.join("\n")); process.exit(1); }
  console.log("Onepager-Test bestanden.");
})();
