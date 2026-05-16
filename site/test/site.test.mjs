import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const html = await readFile(new URL("../dist/index.html", import.meta.url), "utf8");

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
  assert.match(html, /<script type="application\/ld\+json">/);
  assert.match(html, /https:\/\/github\.com\/everruns\/fcp/);
  assert.match(html, /aria-label="GitHub repository"/);
});
