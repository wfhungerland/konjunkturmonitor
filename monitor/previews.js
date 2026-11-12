// Vorschaubilder für die Seite: fotografiert jede einfache Zeitreihen-Grafik einmal im Browser und legt sie als
// prev/<anker>-d.webp (breit) und prev/<anker>-m.webp (Handy) neben die Seite. Die Seite zeigt zuerst das Bild
// und lädt die lebendige Grafik erst beim Überfahren oder Antippen. Welche Bilder es gibt, trägt der Lauf in die
// Seite ein (Platzhalter PREV); ohne diesen Lauf zeichnet die Seite wie bisher sofort.
// Aufruf nach dem Bau: node monitor/previews.js site
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
(async () => {
  const root = path.resolve(process.argv[2] || "site");
  const pages = ["index.html", "en/index.html"].map(p => path.join(root, p)).filter(p => fs.existsSync(p));
  const browser = await chromium.launch();
  let n = 0, bytes = 0;
  for (const file of pages) {
    const out = path.join(path.dirname(file), "prev"), man = {};
    fs.rmSync(out, { recursive: true, force: true }); fs.mkdirSync(out, { recursive: true });
    for (const [suf, width] of [["d", 1440], ["m", 390]]) {
      const page = await browser.newPage({ viewport: { width, height: 900 }, deviceScaleFactor: 2 });
      await page.goto("file://" + file + "?alles=1&noprev=1", { waitUntil: "load" });
      await page.waitForTimeout(800);
      await page.evaluate(() => document.querySelectorAll("details").forEach(d => d.open = true));
      for (let y = 0; y < await page.evaluate(() => document.body.scrollHeight); y += 700) {
        await page.evaluate(y => scrollTo(0, y), y); await page.waitForTimeout(60); }
      await page.waitForTimeout(1500);
      await page.mouse.move(0, 0);
      const list = await page.evaluate(() => [...document.querySelectorAll(".card .chart")]
        .filter(ch => ch._fullLayout && ch._c && prevKind(ch._c) && ch.offsetWidth > 0)
        .map(ch => { const ue = ch.closest(".card").querySelector(".unit"); return { a: ch._c.anchor, u: !!ue && getComputedStyle(ue).display === "none" }; }));
      for (const { a, u } of list) {
        const el = page.locator(`#${a} .chart`).first();
        await el.scrollIntoViewIfNeeded();
        const png = await el.screenshot({ type: "png", animations: "disabled" });
        const url = await page.evaluate(async b64 => {  // PNG im Browser zu WebP umrechnen
          const bm = await createImageBitmap(await (await fetch("data:image/png;base64," + b64)).blob());
          const cv = document.createElement("canvas"); cv.width = bm.width; cv.height = bm.height; cv.getContext("2d").drawImage(bm, 0, 0);
          return cv.toDataURL("image/webp", 0.85); }, png.toString("base64"));
        const buf = Buffer.from(url.split(",")[1], "base64");
        fs.writeFileSync(path.join(out, `${a}-${suf}.webp`), buf); n++; bytes += buf.length;
        (man[a] ??= {})[suf] = u ? { u: 1 } : {};
      }
      await page.close();
    }
    const html = fs.readFileSync(file, "utf8");
    if (!html.includes("/*__PREV__*/null")) throw new Error("Platzhalter PREV fehlt in " + file);
    fs.writeFileSync(file, html.replace("/*__PREV__*/null", JSON.stringify(man)));
  }
  await browser.close();
  console.log(`Vorschaubilder: ${n} Dateien, ${(bytes / 1e6).toFixed(1)} MB`);
})();
