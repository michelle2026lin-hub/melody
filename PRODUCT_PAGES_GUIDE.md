# 型号追踪页 —— 使用说明

这套系统让你不用给每个型号单独建网页。加一个新型号，只改 `assets/data/products.json` 这一个文件 + 传对应的图片文件夹。

## 一、图片：直接传进仓库，不用走 Drive 共享

1. 在仓库的 `assets/images/` 文件夹下，为每个型号新建一个子文件夹，名字用型号编号，比如 `assets/images/H001/`
2. 把这个型号的 5-10 张实拍图，原封不动拖进这个文件夹（跟你手机相册的分类习惯完全对应，一个相册=一个文件夹）
3. 文件名随便取，但要记住，等下要填进数据表里，建议用简单的 `01.jpg` `02.jpg` 这种顺序命名，方便管理

**GitHub 网页拖拽上传子文件夹经常不稳定**，如果拖整个文件夹失败，两个办法：
- 用 GitHub Desktop 客户端（图形界面，支持整个文件夹拖拽，比网页版稳）
- 或者一张张上传（进 `assets/images/` → Add file → 手动建 `H001/01.jpg` 这样的路径文件名）

## 二、视频：用 YouTube 或 Bilibili，不要传进仓库

视频文件太大，传进 GitHub 仓库会拖垮整个网站加载速度，改用视频平台：

1. 把型号视频上传到 YouTube（设为**不公开/Unlisted**）或 Bilibili（设为**仅自己可见**里的"不公开"选项）
2. YouTube 视频ID：网址 `youtube.com/watch?v=` 后面那串
   Bilibili 视频ID：BV号，网址里 `bilibili.com/video/BV.../` 中间那段
3. 填进 `products.json` 的 `video` 字段：
   ```json
   "video": { "platform": "youtube", "id": "dQw4w9WgXcQ" }
   ```

## 三、怎么加一个新型号

1. 把这个型号的图片文件夹传进 `assets/images/型号编号/`
2. 打开 `assets/data/products.json`，照着已有的 `H001` 那段格式复制一份，改成新的型号编号（比如 `H003`）：

```json
"H003": {
  "name": "型号中文名/卖点名",
  "tagline": "一句话卖点",
  "category": "hinge",
  "categoryLabel": "Hinges",
  "images": ["01.jpg", "02.jpg", "03.jpg"],
  "video": { "platform": "youtube", "id": "视频ID" },
  "specs": { "杯径": "35mm", "开合角度": "165°" }
}
```

**注意**：`images` 数组里的文件名，必须跟 `assets/images/H003/` 文件夹里的实际文件名完全一致（大小写、后缀名都要对上），对不上图片就显示不出来。

`category` 目前支持：`hinge`（铰链）/ `slide`（滑轨）/ `stopper`（门吸），以后加新分类自己定新值，同时在 `category.html` 顶部导航栏加一行链接即可。

`specs` 字段名和内容随便定，会自动显示成规格表。

改完保存，Commit 到 GitHub 就生效，**不用建新的 HTML 文件**。

## 四、发给客户的链接长这样

```
https://michelle2026lin-hub.github.io/melody/product.html?model=H003&cid=RX001
```

- `model=H003` 决定显示哪个型号
- `cid=RX001` 是客户身份标识，用来做浏览追踪

**cid 用什么值**：可以直接用客户的 WhatsApp 手机号（去掉符号，只留数字），机器人跟客户对话时本来就知道这个号码，不需要额外查表就能自动拼出链接。如果不想让手机号明文出现在链接里，可以在生成链接前加一层哈希处理（需要时告诉我，我给你补这段代码），效果一样，只是链接里看不出是电话号码。

## 五、分类浏览页（category.html）

客户看完一款，想看同类的其它款，用这个链接：

```
https://michelle2026lin-hub.github.io/melody/category.html?type=hinge&cid=RX001
```

会自动列出 `products.json` 里所有 `category` 是 `hinge` 的型号，点进去是各自的 product.html，cid 会自动带过去，同一个客户在你网站里逛几款都算同一次追踪。

## 六、⚠️ 关于 WhatsApp/微信链接预览图的重要限制

因为 `product.html` 是打开后靠 JavaScript 读数据表才把型号名称/图片显示出来的，**WhatsApp、微信这些平台抓取链接预览图的程序不会执行网页里的JS**，只会读 HTML 里写死的预览标签。这意味着：不管你发哪个型号的链接，客户在聊天里看到的预览图/标题目前都是同一张默认图，**做不到"每个型号各自的预览图"**。

如果你在意这个体验（客户没点开链接之前，就能在聊天列表里看到型号图片），需要额外加一个"预览生成"小工具——你改完数据表后跑一下，会自动帮每个型号生成一份小文件专门给平台抓取用，真人点击会自动跳到正式页面，你完全不用改变现在"只改数据表"的习惯。需要的话说一声，我加上。

## 七、关于工厂素材（配件/冲压/组装/包装/装柜/客户参观）

这些不是"型号"，适合做一个独立的"工厂实力页"，按类目切换而不是按型号切换。做法跟这套完全一样（模板页+配置表+YouTube/Bilibili视频），说一声我就开始搭。

## 八、关于接入客服机器人（wa_reply_bot）

等 wa_reply_bot 真正能识别客户问的型号时，它要做的事：
1. 拿到客户 WhatsApp 手机号 → 清洗成纯数字当 cid
2. 查 `products.json` 里有没有对应型号
3. 拼出 `product.html?model=XXX&cid=手机号` 这样的链接
4. 发给客户

不需要机器人直接碰 Google Drive 或视频平台，这部分全部由模板页处理好了。
