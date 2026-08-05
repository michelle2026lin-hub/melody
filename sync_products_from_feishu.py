#!/usr/bin/env python3
"""
sync_products_from_feishu.py — 从飞书同步生成 products.json

✅ 这一版的数据来源改成两张表配合：
   "产品主表"（tblcCrvPm4yjHcc3）：一个型号一条记录，提供"网站代码"、
      型号名称、货描、克重这些"型号级别"的信息。"网站代码"只需要在
      这张表里，每个型号填一次，不需要在"产品&装箱库"的每一行变体
      记录上重复填。
   "产品&装箱库"（tblW0mqEonhNoWY0）：一个型号有多行（不同SIZE/包装
      方式的组合），提供参数表数据。通过"产品"这个字段的名字文字，
      去匹配"产品主表"里对应的型号，从而找到这一行该归到哪个网站代码。

✅ 图片/视频只跟"型号"绑定：assets/{网站代码}/ 这个文件夹下。
✅ 包装方式只显示文字，不关联任何图片/视频（避免客户品牌信息外泄）。

用法：把这个脚本放进本地网站项目文件夹（能看到assets/product.html的
那一层），运行：
    python3 sync_products_from_feishu.py

⚠️ 首次使用需要在同一文件夹下新建一个 feishu_secret.txt 文件，
   里面只写一行飞书应用密钥（问Melody要，不要写进这个脚本本体里，
   避免密钥被提交到公开仓库）。
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
MASTER_TABLE_ID  = "tblcCrvPm4yjHcc3"  # 产品主表：一型号一条，提供网站代码
PRODUCT_TABLE_ID = "tblW0mqEonhNoWY0"  # 产品&装箱库：一型号多行，提供SIZE/包装方式

DEFAULT_CATEGORY = ("hinge", "Hinges")
CATEGORY_BY_PREFIX = {
    "H": ("hinge", "Hinges"),
    "S": ("slide", "Slides"),
    "D": ("stopper", "Door Stopper"),
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
    master_rows = fetch_all_records(token, MASTER_TABLE_ID)
    print(f"共 {len(master_rows)} 个型号")

    # ✅ 建立 "产品名文字" → 网站代码/型号信息 的对照表
    master_by_name = {}
    no_code_in_master = 0
    for row in master_rows:
        pname = s(fv(row, "产品", ""))
        code = s(fv(row, "网站代码", ""))
        if not pname:
            continue
        if not code:
            no_code_in_master += 1
            continue
        master_by_name[pname] = {
            "code": code,
            "name": s(fv(row, "产品", code)),
            "huomiao": s(fv(row, "货描", "")),
        }
    print(f"「产品主表」里已填「网站代码」的型号：{len(master_by_name)} 个")
    if no_code_in_master:
        print(f"⚠️ 有 {no_code_in_master} 个型号还没填「网站代码」，暂时不会出现在网站上")

    print("正在拉取「产品&装箱库」全部变体记录...")
    variant_rows = fetch_all_records(token, PRODUCT_TABLE_ID)
    print(f"共 {len(variant_rows)} 条变体记录")

    # ✅ 按"产品"名字匹配到产品主表，归到对应网站代码
    groups = {}  # code -> {"master": {...}, "variants": [...]}
    unmatched = 0
    for row in variant_rows:
        pname = s(fv(row, "产品", ""))
        master = master_by_name.get(pname)
        if not master:
            unmatched += 1
            continue
        code = master["code"]
        if code not in groups:
            groups[code] = {"master": master, "variants": []}
        groups[code]["variants"].append({
            "产品": pname,
            "SIZE": s(fv(row, "SIZE", "")),
            "包装方式": s(fv(row, "包装方式", "")),
        })
    print(f"成功匹配、归组的变体记录：{len(variant_rows) - unmatched} 条")
    if unmatched:
        print(f"⚠️ 有 {unmatched} 条变体记录，「产品」名字在产品主表里没找到匹配（或者产品主表那边还没填网站代码），已跳过")

    existing_data = {}
    if os.path.exists(JSON_PATH):
        try:
            with open(JSON_PATH, encoding="utf-8") as f:
                existing_data = json.load(f)
        except Exception as e:
            print(f"⚠️ 读取现有products.json失败，将视为空文件重新生成: {e}")

    new_data = dict(existing_data)
    if "_说明" not in new_data:
        new_data["_说明"] = "由sync_products_from_feishu.py自动同步生成：网站代码来自「产品主表」，SIZE/包装方式来自「产品&装箱库」按产品名匹配归组。图片放在 assets/{网站代码}/ 下"

    updated_count = 0
    for code, g in groups.items():
        master = g["master"]
        category, category_label = CATEGORY_BY_PREFIX.get(code[:1].upper(), DEFAULT_CATEGORY)
        huomiao = master["huomiao"]
        tagline = huomiao[:80] + ("..." if len(huomiao) > 80 else "")
        existing_entry = existing_data.get(code, {})
        video = existing_entry.get("video", {"platform": "", "id": ""})

        new_data[code] = {
            "name": master["name"],
            "tagline": tagline,
            "category": category,
            "categoryLabel": category_label,
            "images": scan_local_images(code),
            "video": video,
            "variants": g["variants"],
        }
        updated_count += 1

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 已更新/新增 {updated_count} 个型号")
    print(f"✅ products.json 已保存到: {os.path.abspath(JSON_PATH)}")
    print("接下来用git提交、推送上线即可")


if __name__ == "__main__":
    main()
