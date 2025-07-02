import os
import json
import re
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 載入資料
json_path = os.path.join(os.path.dirname(__file__), "crawler", "kaohsiung_restaurants_detailed.json")
json_path = os.path.abspath(json_path)

if not os.path.exists(json_path):
    raise FileNotFoundError(f"找不到 JSON 檔案：{json_path}")

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

@app.route("/api/restaurants")
def get_restaurants():
    district = request.args.get("district", "").strip()
    food_type = request.args.get("type", "").strip()
    price_range = request.args.get("price", "").strip()

    if not district:
        return jsonify([])

    # ➤ 解析價格範圍參數
    min_price, max_price = None, None
    if price_range == "2000up":
        min_price = 2000
        max_price = float("inf")
    elif "-" in price_range:
        try:
            parts = price_range.split("-")
            min_price = int(parts[0])
            max_price = int(parts[1]) if parts[1].strip() and parts[1] != "inf" else float("inf")
        except (ValueError, IndexError):
            min_price, max_price = None, None

    # ➤ 將價格字串轉成 min / max
    def parse_price_string(price_str):
        try:
            s = price_str.lower().strip()
            is_over = "超過" in s or "以上" in s
            s = s.replace("元", "").replace("約", "").replace("以上", "").replace("超過", "")
            s = s.replace("~", "-").replace("－", "-").replace(",", "")
            s = re.sub(r"[^0-9\-]", "", s)

            if not s or s in ["$", "$$", "$$$"]:  # 處理無效價格格式
                return None, None

            if "-" in s:
                nums = [int(x) for x in s.split("-") if x.isdigit()]
                if len(nums) == 2:
                    return (nums[0], float("inf")) if is_over else (nums[0], nums[1])
            elif s.isdigit():
                val = int(s)
                return (val, float("inf")) if is_over else (val, val)
        except (ValueError, IndexError):
            return None, None
        return None, None

    # ➤ 比對是否符合篩選條件
    def is_price_in_range(restaurant_min, restaurant_max, filter_min, filter_max):
        if restaurant_min is None or restaurant_max is None:
            return False
        if filter_max == float("inf"):
            return restaurant_max >= filter_min  # 檢查餐廳價格範圍的上限是否 >= 2000
        return restaurant_max >= filter_min and restaurant_min <= filter_max

    # ➤ 開始篩選資料
    results = []
    for r in data:
        if r.get("district", "").strip() != district:
            continue

        if food_type != "all":
            r_types = r.get("type", "").replace("、", ",").replace(" ", "").split(",")
            if food_type not in r_types:
                continue

        # ➤ 價格篩選
        if min_price is not None and max_price is not None:
            price_str = r.get("price_range", "").strip()
            if not price_str or "未提供" in price_str or "暫無" in price_str:
                continue
            r_min, r_max = parse_price_string(price_str)

            if r_min is None or r_max is None:
                print(f"[DEBUG] ❌ {r.get('name')} ➜ 無法解析價格: {price_str}")
                continue

            print(f"[DEBUG] {r.get('name')} | 原始: {price_str} ➜ min={r_min}, max={r_max} | 篩選: min={min_price}~max={max_price}")

            if not is_price_in_range(r_min, r_max, min_price, max_price):
                print("      ⛔ 被排除")
                continue
            else:
                print("      ✅ 通過")

        results.append(r)

    response = make_response(jsonify(results))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

if __name__ == "__main__":
    app.run(debug=True)