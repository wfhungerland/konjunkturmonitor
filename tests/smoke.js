// Seitentest: lädt die gebaute Seite im Browser, klappt alles aus, scrollt durch und bricht ab bei
// JavaScript-Fehlern oder Abbildungen, die leer bleiben (Modus „Alles“, ?alles=1). Aufruf: node tests/smoke.js site/index.html
const { chromium } = require("playwright");
const path = require("path");
(async () => {
  const file = path.resolve(process.argv[2] || "site/index.html");
  const browser = await chromium.launch();
  const errors = [];
  for (const [name, width] of [["breit", 1440], ["Handy", 390]]) {
    const page = await browser.newPage({ viewport: { width, height: 900 } });
    page.on("pageerror", e => errors.push(`${name}: ${e.message}`));
    page.on("console", m => { if (m.type() === "error" && !/favicon|net::ERR/.test(m.text())) errors.push(`${name}: ${m.text()}`); });
    await page.goto("file://" + file + "?alles=1", { waitUntil: "load" });  // alle Kapitel, nicht nur die Kurzfassung
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
  await browser.close();
  if (errors.length) { console.error(errors.join("\n")); process.exit(1); }
  console.log("Seitentest bestanden.");
})();
