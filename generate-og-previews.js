#!/usr/bin/env node
/**
 * generate-og-previews.js
 * ---------------------------------------------------------
 * 为每个型号生成一份静态预览页，放在 /p/{modelKey}.html
 * 用途：WhatsApp / 微信 / Facebook 等平台的链接预览抓取程序不会执行 JS，
 *       抓不到 product.html 里靠 JS 渲染出来的型号名/图片。
 *       这份静态文件把标题和图片写死在 HTML 里，平台抓得到；
 *       真人打开会被 0 秒 meta-refresh 自动跳转到正式的 product.html。
 *
 * 用法：改完 assets/data/products.json 后，在仓库根目录跑一次：
 *   node generate-og-previews.js
 * 会自动在 p/ 文件夹下生成/更新所有型号的预览文件。
 *
 * 发给客户的链接从原来的：
 *   product.html?model=H001&cid=xxx
 * 改成：
 *   p/H001.html?cid=xxx
 * （cid 会被脚本自动透传到跳转后的正式链接）
 * ---------------------------------------------------------
 */

const fs = require('fs');
const path = require('path');

const SITE_ROOT = process.cwd();
const PRODUCTS_JSON = path.join(SITE_ROOT, 'assets/data/products.json');
const OUTPUT_DIR = path.join(SITE_ROOT, 'p');

// 改成你实际部署的域名
const BASE_URL = 'https://michelle2026lin-hub.github.io/melody';

function loadProducts() {
  const raw = fs.readFileSync(PRODUCTS_JSON, 'utf8');
  const data = JSON.parse(raw);
  const entries = {};
  for (const [key, val] of Object.entries(data)) {
    if (key.startsWith('_')) continue; // skip "_说明" 字段
    entries[key] = val;
  }
  return entries;
}

function escapeHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function buildPreviewHtml(modelKey, model) {
  const title = `${model.name || modelKey} — Hongtai Precision Hardware`;
  const description = model.tagline || 'Precision cabinet hardware, manufactured in Jieyang, Guangdong.';
  const firstImage = (model.images && model.images[0]) || null;
  const imageUrl = firstImage
    ? `${BASE_URL}/assets/images/${modelKey}/${firstImage}`
    : `${BASE_URL}/assets/images/og-default.jpg`; // 建议放一张默认厂标图作兜底

  const escTitle = escapeHtml(title);
  const escDesc = escapeHtml(description);

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${escTitle}</title>

<!-- Open Graph tags: 平台抓取程序只读这些静态标签，不执行下面的跳转脚本 -->
<meta property="og:type" content="product">
<meta property="og:title" content="${escTitle}">
<meta property="og:description" content="${escDesc}">
<meta property="og:image" content="${imageUrl}">
<meta property="og:url" content="${BASE_URL}/p/${modelKey}.html">

<!-- Twitter Card 兜底（部分场景会用到） -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="${escTitle}">
<meta name="twitter:description" content="${escDesc}">
<meta name="twitter:image" content="${imageUrl}">

<!-- 真人访客：0 秒跳转到正式产品页，cid 参数自动透传 -->
<script>
  (function () {
    var params = new URLSearchParams(window.location.search);
    var cid = params.get('cid');
    var target = 'product.html?model=${modelKey}' + (cid ? '&cid=' + encodeURIComponent(cid) : '');
    window.location.replace('../' + target);
  })();
</script>
<meta http-equiv="refresh" content="0; url=../product.html?model=${modelKey}">
</head>
<body>
  <p>Redirecting to <a href="../product.html?model=${modelKey}">${escTitle}</a>…</p>
</body>
</html>
`;
}

function main() {
  if (!fs.existsSync(PRODUCTS_JSON)) {
    console.error('❌ 找不到 assets/data/products.json，请在仓库根目录运行本脚本');
    process.exit(1);
  }

  fs.mkdirSync(OUTPUT_DIR, { recursive: true });

  const products = loadProducts();
  const keys = Object.keys(products);

  if (keys.length === 0) {
    console.log('⚠️ products.json 里没有型号，未生成任何文件');
    return;
  }

  for (const key of keys) {
    const html = buildPreviewHtml(key, products[key]);
    const outPath = path.join(OUTPUT_DIR, `${key}.html`);
    fs.writeFileSync(outPath, html, 'utf8');
    console.log(`✅ p/${key}.html`);
  }

  console.log(`\n完成，共生成 ${keys.length} 个预览页。`);
  console.log('发给客户的链接格式改为：');
  console.log(`  ${BASE_URL}/p/H001.html?cid=你的cid`);
}

main();
