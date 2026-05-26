import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";
import sitemapEnhance from "./integrations/sitemap-enhance.mjs";
import { siteUrl } from "./src/site-url.js";

export default defineConfig({
  output: "static",
  site: siteUrl,
  integrations: [sitemap(), sitemapEnhance()],
});
