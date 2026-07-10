import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import test from "node:test";

const html = await readFile(new URL("../dist/index.html", import.meta.url), "utf8");
const distFiles = await readdir(new URL("../dist/", import.meta.url));
const robots = await readFile(new URL("../dist/robots.txt", import.meta.url), "utf8");
const sitemap = await readFile(new URL("../dist/sitemap.xml", import.meta.url), "utf8");

test("renders the spec as static HTML", () => {
  assert.match(html, /<h1[^>]*>FCP .* Free Communication Protocol<\/h1>/);
  assert.match(html, /<h2[^>]*>Abstract<\/h2>/);
  assert.match(html, /Capability handshake,\s+parameter\s+collection,\s+and error handling/);
  assert.doesNotMatch(html, /axios/i);
  assert.doesNotMatch(html, /marked/i);
});

test("includes SEO metadata and repository link", () => {
  assert.match(html, /<title>FCP - Free Communication Protocol Specification<\/title>/);
  assert.match(html, /<meta name="description" content="The Free Communication Protocol \(FCP\) specification/);
  assert.match(html, /<meta property="og:type" content="article">/);
  assert.match(html, /<link rel="canonical" href="https:\/\/fcp\.md\/">/);
  assert.match(html, /<meta property="og:url" content="https:\/\/fcp\.md\/">/);
  assert.match(html, /<script type="application\/ld\+json">/);
  assert.match(html, /"url":"https:\/\/fcp\.md\/"/);
  assert.match(html, /https:\/\/github\.com\/everruns\/fcp/);
  assert.match(html, /aria-label="GitHub repository"/);
});

test("loads the Google tag (gtag.js)", () => {
  assert.match(html, /https:\/\/www\.googletagmanager\.com\/gtag\/js\?id=G-XYFQSGRXXV/);
  assert.match(html, /gtag\('config', 'G-XYFQSGRXXV'\)|gtag\("config", "G-XYFQSGRXXV"\)/);
});

test("publishes crawl metadata for the canonical URL", () => {
  assert.match(robots, /User-agent: \*/);
  assert.match(robots, /Allow: \//);
  assert.match(robots, /Content-Signal: ai-train=yes, search=yes, ai-input=yes/);
  assert.match(robots, /Sitemap: https:\/\/fcp\.md\/sitemap\.xml/);
  assert.match(sitemap, /<urlset[^>]+xmlns="http:\/\/www\.sitemaps\.org\/schemas\/sitemap\/0\.9"/);
  assert.match(sitemap, /<loc>https:\/\/fcp\.md\/<\/loc>/);
  assert.match(sitemap, /<lastmod>\d{4}-\d{2}-\d{2}<\/lastmod>/);
  assert.ok(!distFiles.includes("sitemap-index.xml"));
  assert.ok(!distFiles.includes("sitemap-0.xml"));
});
