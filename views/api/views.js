import template from "../template.js";

// komarev only counts requests from GitHub's image proxy, so pass its user agent through.
const BADGE = "https://komarev.com/ghpvc/?username=Dhirenderchoudhary";

export default async function handler(req, res) {
  let views = "—";
  try {
    const headers = { "User-Agent": req.headers["user-agent"] ?? "" };
    const badge = await (await fetch(BADGE, { headers, signal: AbortSignal.timeout(3000) })).text();
    views = [...badge.matchAll(/>([\d,]+)<\/text>/g)].at(-1)?.[1] ?? views;
  } catch {}
  res.setHeader("Content-Type", "image/svg+xml; charset=utf-8");
  res.setHeader("Cache-Control", "max-age=0, no-cache, no-store, must-revalidate");
  res.send(template.replace("__VIEWS__", views));
}
