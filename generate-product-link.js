/**
 * 把这个函数加进 wa_reply_bot.js（复用同一个 CONFIG 对象即可）
 * 用途：客户问某个型号时，自动生成带追踪 cid 的产品页链接
 */

const crypto = require('crypto');

const SITE_BASE_URL = 'https://michelle2026lin-hub.github.io/melody';

/**
 * @param {string} customerPhone - 客户 WhatsApp 号码，形如 "918320561551@c.us" 或纯数字
 * @param {string} modelKey - 型号编号，比如 "H001"，需对应 products.json 里的 key
 * @returns {string} 带 cid 的产品页链接（走 /p/ 静态预览页，同时解决预览图问题）
 */
function generateProductLink(customerPhone, modelKey) {
  const cleanPhone = String(customerPhone).replace(/[^0-9]/g, '');
  const cid = crypto
    .createHash('md5')
    .update(cleanPhone)
    .digest('hex')
    .slice(0, 8); // 取前8位，够用且链接不会太长

  return `${SITE_BASE_URL}/p/${modelKey}.html?cid=${cid}`;
}

// ---- 示例用法（可以直接在 wa_reply_bot.js 里这样调用）----
// const link = generateProductLink(msg.from, 'H001');
// await chat.sendMessage(`这是我们这款铰链的详细资料，你可以看下：${link}`);

module.exports = { generateProductLink };
