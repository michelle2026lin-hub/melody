# Hongtai Precision Hardware — site skeleton

Static site, ready for GitHub Pages. No build step, no dependencies beyond Google Fonts (CDN).

## Files

```
index.html          ← catalog homepage
hinge-product.html   ← sample product detail page (tracker.js wired in)
tracker.js            ← client-open / dwell-time / scroll tracker
assets/css/style.css  ← shared design system
```

## 1. Deploy to GitHub Pages

1. Create a new GitHub repo (public is fine for a product catalog — nothing here is sensitive).
2. Push these files to the repo root (`main` branch).
3. Repo → **Settings → Pages → Source** → select `main` branch, `/ (root)` folder → **Save**.
4. Wait 1–2 minutes. Your site is live at `https://your-username.github.io/your-repo-name/`.
5. Later, once you buy your brand `.com`: **Settings → Pages → Custom domain** → enter it. GitHub issues a free HTTPS certificate automatically.

## 2. Wire up the tracker (optional but recommended)

`tracker.js` posts events to a Google Apps Script Web App. To activate it:

1. Reuse (or redeploy) your existing Apps Script `doGet` handler — it should accept `cid`, `page`, `action`, `progress`, `duration` as query params and append a row to a Sheet, plus notify Feishu on `action=open`.
2. Deploy the script as a **Web App** (Execute as: Me: Anyone with the link can access) and copy the `/exec` URL.
3. Open `tracker.js` and replace:
   ```js
   const WEB_APP_URL = "https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec";
   ```
   with your real deployment URL.
4. Commit and push — GitHub Pages updates automatically within a minute.

## 3. Send a tracked link to a client

Add a `?cid=` parameter unique to that client/order:

```
https://your-username.github.io/your-repo-name/hinge-product.html?cid=RX001
```

Every open, 30-second heartbeat, scroll-depth milestone, and close event fires to your sheet, tagged with `RX001`.

**Known limit:** forwarding is not directly trackable — there is no way to tell whether a second open came from the same person reopening the link or from someone they forwarded it to. Assigning one `cid` per contact is the closest practical workaround (multiple opens from different devices/IPs under the same `cid` is a signal, not proof).

## 4. Add more products

Duplicate `hinge-product.html`, rename it (e.g. `slide-product.html`), update the spec table and copy, then add a card for it in `index.html`'s catalog grid (`<a class="cat-card" href="slide-product.html">`).

## 5. Before going live

- Replace the `PRODUCT PHOTO` / thumbnail placeholders in `hinge-product.html` with real images in `assets/images/`.
- Fill in the real Apps Script URL in `tracker.js` (step 2).
- If you don't want the tracker firing on the homepage too, only `<script src="tracker.js"></script>` is included on `hinge-product.html` — add it to other product pages the same way once you duplicate them.
