/**
 * 生成"链接预览专用"小页面
 * ---------------------------------------------
 * 为什么需要这个：product.html 是打开后靠 JS 读 products.json 才渲染内容的，
 * WhatsApp/微信抓取链接预览图的程序不会执行 JS，只认写死在 HTML <head> 里的标签。
 * 所以每次改完 products.json，跑一下这个脚本，会在 /p/ 文件夹下给每个型号
 * 生成一个几行的静态小文件，专门给平台爬虫看 OG 标签；真人点击会立刻跳转到真正的
 * product.html，感觉不到中间多了一步。
 *
 * 用法：在仓库根目录下运行
 *   node scripts/generate-previews.js
 *
 * 以后客户链接改发这个格式（不再直接发 product.html）：
 *   https://michelle2026lin-hub.github.io/melody/p/H001.html?cid=RX001
 */
const fs = require('fs');
const path = require('path');

const SITE_ROOT = 'https://michelle2026lin-hub.github.io/melody'; // 你的实际网址，改这里
const DATA_PATH = path.join(__dirname, 'assets', 'data', 'products.json');
const OUT_DIR = path.join(__dirname, 'p');

const data = JSON.parse(fs.readFileSync(DATA_PATH, 'utf8'));

if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });

function escapeHtml(str = '') {
  return String(str).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

let count = 0;
for (const [key, model] of Object.entries(data)) {
  if (key.startsWith('_')) continue; // skip the "_说明" instructions entry

  const title = escapeHtml(model.name || key);
  const desc = escapeHtml(model.tagline || 'Hongtai Precision Hardware');
  const firstImage = (model.images || [])[0];
  const ogImageTag = firstImage
    ? `<meta property="og:image" content="${SITE_ROOT}/assets/${model.category || 'hinge'}/${key}/${firstImage}">`
    : '';

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>${title} — Hongtai Precision Hardware</title>
<meta property="og:title" content="${title}">
<meta property="og:description" content="${desc}">
${ogImageTag}
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
<meta http-equiv="refresh" content="0; url=../product.html?model=${key}${'${QS_PLACEHOLDER}'}">
<script>
  // preserve ?cid=... (and any other query params) when forwarding to the real page
  var qs = window.location.search; // e.g. "?cid=RX001"
  window.location.replace('../product.html?model=${key}' + (qs ? '&' + qs.slice(1) : ''));
</script>
</head>
<body>
  <p>Redirecting to <a href="../product.html?model=${key}">${title}</a>…</p>
</body>
</html>
`.replace('${QS_PLACEHOLDER}', ''); // meta-refresh fallback has no query (JS handles the real redirect)

  fs.writeFileSync(path.join(OUT_DIR, `${key}.html`), html, 'utf8');
  count++;
}

console.log(`✅ 生成了 ${count} 个预览页，在 /p/ 文件夹下`);
