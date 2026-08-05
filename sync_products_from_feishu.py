#!/usr/bin/env python3
"""
sync_products_from_feishu.py — 从飞书"产品主表"同步生成 products.json

✅ 这一版只读一张表："产品主表"（tblcCrvPm4yjHcc3）。
   一个型号一条记录，字段包括：产品、货描、克重、网站代码、克重单位、
   单价单位、订单数量单位。不再需要"产品&装箱库"参与。

✅ 图片/视频只跟"型号"绑定：assets/{网站代码}/ 这个文件夹下。

用法：把这个脚本放进本地网站项目文件夹（能看到assets/product.html的
那一层），运行：
    python3 sync_products_from_feishu.py

⚠️ 首次使用需要在同一文件夹下新建一个 feishu_secret.txt 文件，
   里面只写一行飞书应用密钥，不要写进这个脚本本体（避免密钥被提交到
   公开仓库被拦截）。
"""

import os
import re
import json
import requests

# ══════════════════════════════════════════
# 配置区
# ══════════════════════════════════════════
APP_ID     = "cli_a93642b6fbb99bc3"
BASE_ID    = "BrWfbe480a83Z2scZJJcgSLqnLc"
MASTER_TABLE_ID = "tblcCrvPm4yjHcc3"  # 产品主表：唯一数据来源

DEFAULT_CATEGORY = ("hinge", "Hinges")
# 网站代码第一个字母 -> 分类。新加了合页(Y)和小五金(M)两个分类；
# 如果你的飞书表里"隐藏轨/滑轨"用的不是下面这套首字母，去飞书表里把
# 网站代码前缀改成对应字母就行，不用改这个脚本。
CATEGORY_BY_PREFIX = {
    "H": ("hinge", "Hinges"),
    "S": ("slide", "Drawer Slides"),
    "U": ("undermount", "Undermount Slides"),
    "T": ("tandembox", "Tandem Box / Slim Box"),
    "G": ("gasspring", "Gas Spring / Lift"),
    "D": ("stopper", "Door Stopper"),
    "Y": ("doorhinge", "Door Hinge"),
    "P": ("pushcatcher", "Push Catcher"),
    "M": ("misc", "Misc Hardware"),
}

JSON_PATH = "assets/data/products.json"
ASSETS_ROOT = "assets"


def _load_app_secret():
    secret_file = "feishu_secret.txt"
    if not os.path.exists(secret_file):
        print(f"❌ 找不到 {secret_file} 这个文件")
        print(f"   请在这个脚本同一个文件夹下，新建一个叫 {secret_file} 的文本文件，")
        print(f"   里面只写一行飞书应用密钥")
        exit(1)
    with open(secret_file, encoding="utf-8") as f:
        return f.read().strip()

APP_SECRET = _load_app_secret()


def get_token():
    res = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=10,
    )
    return res.json()["tenant_access_token"]


def fv(fields, key, default=""):
    """兼容字段名带空格/括号后缀的情况"""
    v = fields.get(key, None)
    if v is None:
        def _normalize(s):
            s = re.sub(r"[\(（][^\)）]*[\)）]", "", s)
            s = re.sub(r"\s+", "", s)
            return s
        target = _normalize(key)
        for real_key, real_val in fields.items():
            if _normalize(real_key) == target:
                v = real_val
                break
    if v is None:
        v = default
    if v is None:
        return default
    if isinstance(v, list):
        if not v:
            return default
        item = v[0]
        return item.get("text", item.get("value", str(item))) if isinstance(item, dict) else str(item)
    if isinstance(v, dict):
        return v.get("value", v.get("text", str(v)))
    return v


def s(v) -> str:
    return str(v).strip() if v is not None else ""


def fetch_all_records(token, table_id):
    headers = {"Authorization": f"Bearer {token}"}
    all_items, page_token = [], None
    while True:
        params = {"page_size": 100}
        if page_token:
            params["page_token"] = page_token
        res = requests.get(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_ID}/tables/{table_id}/records",
            headers=headers, params=params, timeout=15,
        )
        data = res.json().get("data", {})
        all_items.extend(data.get("items", []))
        page_token = data.get("page_token")
        if not page_token:
            break
    return [it["fields"] for it in all_items]


def scan_local_images(model_code: str) -> list:
    folder = os.path.join(ASSETS_ROOT, model_code)
    if not os.path.isdir(folder):
        return []
    valid_ext = (".jpg", ".jpeg", ".png", ".webp")
    return [f for f in sorted(os.listdir(folder)) if f.lower().endswith(valid_ext)]


def main():
    print("正在获取飞书Token...")
    token = get_token()

    print("正在拉取「产品主表」...")
    rows = fetch_all_records(token, MASTER_TABLE_ID)
    print(f"共 {len(rows)} 个型号")

    existing_data = {}
    if os.path.exists(JSON_PATH):
        try:
            with open(JSON_PATH, encoding="utf-8") as f:
                existing_data = json.load(f)
        except Exception as e:
            print(f"⚠️ 读取现有products.json失败，将视为空文件重新生成: {e}")

    # 每次都是干净重建（只保留视频字段这种"手工加过、飞书里没有"的信息），
    # 这样测试用的示例数据（比如"示例模型二"）、以前手滑生成的脏数据，
    # 不会一直赖在products.json里不走。
    new_data = {
        "_说明": "由sync_products_from_feishu.py自动同步生成，唯一数据来源是飞书「产品主表」。图片放在 assets/{网站代码}/ 下"
    }

    updated_count = 0
    no_code_count = 0
    not_ready_count = 0
    for row in rows:
        code = s(fv(row, "网站代码", ""))
        if not code:
            no_code_count += 1
            continue

        # 网站代码里必须带序号（比如H001），只写了字母（比如单独一个"H"）
        # 说明这个型号还没准备好上线，跳过，不生成页面
        if not any(ch.isdigit() for ch in code):
            not_ready_count += 1
            continue

        category, category_label = CATEGORY_BY_PREFIX.get(code[:1].upper(), DEFAULT_CATEGORY)
        name = s(fv(row, "产品", code))
        huomiao = s(fv(row, "货描", ""))
        tagline = huomiao[:80] + ("..." if len(huomiao) > 80 else "")

        existing_entry = existing_data.get(code, {})
        video = existing_entry.get("video", {"platform": "", "id": ""})

        specs = {
            "克重": f"{s(fv(row, '克重', ''))}{s(fv(row, '克重单位', ''))}".strip(),
            "单价单位": s(fv(row, "单价单位", "")),
            "订单数量单位": s(fv(row, "订单数量单位", "")),
        }
        specs = {k: v for k, v in specs.items() if v}

        new_data[code] = {
            "name": name,
            "tagline": tagline,
            "category": category,
            "categoryLabel": category_label,
            "images": scan_local_images(code),
            "video": video,
            "specs": specs,
        }
        updated_count += 1

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 已更新/新增 {updated_count} 个型号")
    if no_code_count:
        print(f"⚠️ 有 {no_code_count} 个型号还没填「网站代码」，已跳过")
    if not_ready_count:
        print(f"⚠️ 有 {not_ready_count} 个型号「网站代码」只写了字母没写序号（还没准备好上线），已跳过")
    print(f"✅ products.json 已保存到: {os.path.abspath(JSON_PATH)}")
    print("接下来用git提交、推送上线即可")


if __name__ == "__main__":
    main()
