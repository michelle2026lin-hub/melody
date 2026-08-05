#!/usr/bin/env python3
"""
sync_products_from_feishu.py — 从飞书"产品&装箱库"同步生成 products.json

✅ 按型号分组的逻辑（重要，跟第一版完全不同）：
   "产品&装箱库"里，同一个型号会有好几行（不同SIZE/包装方式/液压管的
   组合），这些行不是各自独立的产品，而是同一个型号页面下的"参数表"。
   分组依据是"网站代码"这个字段——同一个型号的所有变体行，
   "网站代码"必须填成完全一样的值（比如都填"H1"），脚本才能正确
   把它们归到同一个型号页面里。

✅ 图片/视频只跟"型号"绑定，不跟"包装方式"绑定：
   型号主图/视频放在 assets/{网站代码}/ 这个文件夹下，是型号本身的
   通用素材（不涉及任何客户定制Logo）。包装方式这一项，网站上只显示
   文字描述，不关联任何实拍图片/视频——因为包装实拍素材很可能是
   其他客户订单里带着那个客户品牌Logo拍的，不适合公开展示，
   这是跟Order+Video模块"客户Logo不得流向公开社媒"同一条红线。

用法：把这个脚本放进本地网站项目文件夹（能看到assets/product.html的
那一层），运行：
    python3 sync_products_from_feishu.py
"""

import os
import re
import json
import requests

# ══════════════════════════════════════════
# 配置区
# ══════════════════════════════════════════
APP_ID     = "cli_a93642b6fbb99bc3"
# ✅ 修复真实安全问题：之前APP_SECRET直接写死在这个脚本里，你的仓库是
# 公开仓库，一旦推送成功，任何人都能看到这个密钥。现在改成从一个单独的
# 本地文件 feishu_secret.txt 读取，这个文件需要加进 .gitignore，
# 永远不会被提交到GitHub上
def _load_app_secret():
    secret_file = "feishu_secret.txt"
    if not os.path.exists(secret_file):
        print(f"❌ 找不到 {secret_file} 这个文件")
        print(f"   请在这个脚本同一个文件夹下，新建一个叫 {secret_file} 的文本文件，")
        print(f"   里面只写一行：Y0zdHVkdanDgshztW5nsCd4xndA3yKci")
        print(f"   （这一步只需要做一次）")
        exit(1)
    with open(secret_file, encoding="utf-8") as f:
        return f.read().strip()

APP_SECRET = _load_app_secret()
BASE_ID    = "BrWfbe480a83Z2scZJJcgSLqnLc"
PRODUCT_TABLE_ID = "tblW0mqEonhNoWY0"  # 产品&装箱库

DEFAULT_CATEGORY = ("hinge", "Hinges")  # 兜底默认值，网站代码首字母不在下面
                                          # 这张映射表里时使用
# ✅ 新增：按"网站代码"首字母自动判断分类，不需要在飞书里额外加"分类"字段。
# 以后加滑轨/门吸产品时，只要网站代码按这个约定命名（比如滑轨用S1/S2...），
# 就能自动分类到正确的产品目录页
CATEGORY_BY_PREFIX = {
    "H": ("hinge", "Hinges"),
    "S": ("slide", "Slides"),
    "D": ("stopper", "Door Stopper"),
}

JSON_PATH = "assets/data/products.json"
ASSETS_ROOT = "assets"  # ✅ 图片文件夹直接是 assets/{网站代码}/，不再按分类分层


def get_token():
    res = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=10,
    )
    return res.json()["tenant_access_token"]


def fv(fields, key, default=""):
    """兼容字段名带空格/括号后缀的情况，同generate_pi_pl.py"""
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
        result = item.get("text", item.get("value", str(item))) if isinstance(item, dict) else str(item)
    elif isinstance(v, dict):
        result = v.get("value", v.get("text", str(v)))
    else:
        result = v
    return result


def s(v) -> str:
    """✅ 修复上一版的真实bug：飞书返回的数字字段有时是float/int类型，
    不是文字，之前直接对它调用.strip()会崩溃。统一先转字符串再处理。"""
    return str(v).strip() if v is not None else ""


def fetch_all_products(token):
    headers = {"Authorization": f"Bearer {token}"}
    all_items, page_token = [], None
    while True:
        params = {"page_size": 100}
        if page_token:
            params["page_token"] = page_token
        res = requests.get(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_ID}/tables/{PRODUCT_TABLE_ID}/records",
            headers=headers, params=params, timeout=15,
        )
        data = res.json().get("data", {})
        all_items.extend(data.get("items", []))
        page_token = data.get("page_token")
        if not page_token:
            break
    return [it["fields"] for it in all_items]


def scan_local_images(model_code: str) -> list:
    """扫描本地 assets/{网站代码}/ 这个文件夹（不再分category子层），
    看有哪些图片文件，自动填进images数组"""
    folder = os.path.join(ASSETS_ROOT, model_code)
    if not os.path.isdir(folder):
        return []
    valid_ext = (".jpg", ".jpeg", ".png", ".webp")
    return [f for f in sorted(os.listdir(folder)) if f.lower().endswith(valid_ext)]


def build_product_entry(model_code: str, rows: list, existing_entry: dict = None) -> dict:
    """
    ✅ 核心改动：接收"同一个网站代码下的所有变体行"(rows)，而不是单独一行。
    型号名/图片/视频只取第一行的信息（因为同一组理应是同一个型号）；
    参数表(variants)是一个数组，每个变体行各自一条，只保留产品/SIZE/包装方式
    这三项（按你确认的范围，不包含液压管/单价这些，且包装方式只是文字，
    不关联任何图片视频）。
    """
    first = rows[0]
    category, category_label = CATEGORY_BY_PREFIX.get(model_code[:1].upper(), DEFAULT_CATEGORY)

    name = fv(first, "产品", model_code)
    huomiao = s(fv(first, "货描", ""))
    tagline = huomiao[:80] + ("..." if len(huomiao) > 80 else "")

    images = scan_local_images(model_code)
    video = (existing_entry or {}).get("video", {"platform": "", "id": ""})

    # ✅ 参数表：每个变体行一条，只保留产品/SIZE/包装方式这三项文字信息
    variants = []
    for row in rows:
        variants.append({
            "产品": s(fv(row, "产品", name)),
            "SIZE": s(fv(row, "SIZE", "")),
            "包装方式": s(fv(row, "包装方式", "")),  # 纯文字，不关联图片/视频
        })

    return {
        "name": name,
        "tagline": tagline,
        "category": category,
        "categoryLabel": category_label,
        "images": images,
        "video": video,
        "variants": variants,  # ✅ 新字段：这个型号下所有SIZE/包装方式的组合列表
    }


def main():
    print("正在获取飞书Token...")
    token = get_token()

    print("正在拉取「产品&装箱库」全部记录...")
    all_fields = fetch_all_products(token)
    print(f"共拉取到 {len(all_fields)} 条记录")

    # ✅ 按"网站代码"分组：同一个网站代码下的多行，归成一组
    groups = {}
    no_code_count = 0
    for fields in all_fields:
        code = s(fv(fields, "网站代码", ""))
        if not code:
            no_code_count += 1
            continue
        groups.setdefault(code, []).append(fields)

    print(f"按网站代码分组后，共 {len(groups)} 个型号")
    if no_code_count:
        print(f"⚠️ 有 {no_code_count} 条记录没有填「网站代码」，已跳过")

    existing_data = {}
    if os.path.exists(JSON_PATH):
        try:
            with open(JSON_PATH, encoding="utf-8") as f:
                existing_data = json.load(f)
        except Exception as e:
            print(f"⚠️ 读取现有products.json失败，将视为空文件重新生成: {e}")

    new_data = dict(existing_data)
    if "_说明" not in new_data:
        new_data["_说明"] = "由sync_products_from_feishu.py自动同步生成，按「网站代码」把产品&装箱库里的多行变体汇总成一个型号页面，图片放在 assets/{网站代码}/ 下"

    updated_count = 0
    for model_code, rows in groups.items():
        entry = build_product_entry(model_code, rows, existing_data.get(model_code))
        new_data[model_code] = entry
        updated_count += 1

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 已更新/新增 {updated_count} 个型号")
    print(f"✅ products.json 已保存到: {os.path.abspath(JSON_PATH)}")
    print("接下来用GitHub Desktop（或git命令行）提交、推送上线即可")


if __name__ == "__main__":
    main()
