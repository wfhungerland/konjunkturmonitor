// Seitentest: lädt die gebaute Seite im Browser, klappt alles aus, scrollt durch und bricht ab bei
// JavaScript-Fehlern oder Abbildungen, die leer bleiben (Modus „Alles“, ?alles=1). Aufruf: node tests/smoke.js site/index.html
// Die Seite kommt über einen kleinen lokalen Webserver, wie im Netz; so greift auch die Content-Security-Policy (monitor/csp.py),
// und ein Verstoß dagegen bricht den Test ab.
const { chromium } = require("playwright");
const path = require("path");
const http = require("http");
const fs = require("fs");
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".json": "application/json", ".webp": "image/webp", ".png": "image/png", ".woff2": "font/woff2", ".xml": "application/xml", ".csv": "text/csv" };
(async () => {
  const file = path.resolve(process.argv[2] || "site/index.html");
  const root = fs.existsSync(path.join(path.dirname(file), "plotly.min.js")) ? path.dirname(file) : path.dirname(path.dirname(file));  // site/ auch für site/en/index.html
  const server = http.createServer((req, res) => {
    const p = path.join(root, decodeURIComponent(new URL(req.url, "http://x").pathname));
    if (!p.startsWith(root) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { "Content-Type": TYPES[path.extname(p)] || "application/octet-stream" }); fs.createReadStream(p).pipe(res); });
  await new Promise(ok => server.listen(0, "127.0.0.1", ok));
  const url = `http://127.0.0.1:${server.address().port}/${path.relative(root, file).split(path.sep).join("/")}`;
  const browser = await chromium.launch();
  const errors = [];
  for (const [name, width] of [["breit", 1440], ["Handy", 390]]) {
    const page = await browser.newPage({ viewport: { width, height: 900 } });
    page.on("pageerror", e => errors.push(`${name}: ${e.message}`));
    page.on("console", m => { if (m.type() === "error" && (!/favicon|net::ERR|Failed to load resource/.test(m.text()) || /Content Security Policy/.test(m.text()))) errors.push(`${name}: ${m.text()}`); });
    await page.goto(url + "?alles=1", { waitUntil: "load" });  // alle Kapitel, nicht nur die Kurzfassung
    await page.waitForTimeout(1000);
    await page.evaluate(() => document.querySelectorAll("details").forEach(d => d.open = true));
    for (let y = 0; y < await page.evaluate(() => document.body.scrollHeight); y += 600) {
      await page.evaluate(y => scrollTo(0, y), y); await page.waitForTimeout(80); }
    await page.waitForTimeout(2000);
    const res = await page.evaluate(() => {
      const cards = [...document.querySelectorAll(".card")];
      const empty = cards.filter(c => { const ch = c.querySelector(".chart, .tilewrap"); return ch && !ch.children.length; })
        .map(c => (c.querySelector("h3") || c).textContent.trim().slice(0, 60));
      return { n: cards.length, empty };
    });
    console.log(`${name}: ${res.n} Abbildungen, leer: ${res.empty.length}`);
    if (res.n < 10) errors.push(`${name}: nur ${res.n} Abbildungen gefunden`);
    res.empty.forEach(t => errors.push(`${name}: leere Abbildung „${t}“`));
    await page.close();
  }
  await browser.close(); server.close();
  if (errors.length) { console.error(errors.join("\n")); process.exit(1); }
  console.log("Seitentest bestanden.");
})();
