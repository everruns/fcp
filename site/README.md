# FCP Site

Static Astro site for the repository `SPEC.md`, deployed through
Cloudflare Workers Static Assets.

## Development

```sh
npm install
npm run dev
```

Astro renders `../SPEC.md` into HTML at build time. The deployed page does
not fetch or render Markdown in the browser.

## Deploy

```sh
npm run deploy
```

`npm run deploy` builds static assets into `dist/` and publishes them with
Wrangler.
