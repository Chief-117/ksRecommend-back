import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 允許跨域存取

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
    if price_range == "2000+":
        min_price = 2000
        max_price = float("inf")
    elif "-" in price_range:
        try:
            parts = price_range.split("-")
            min_price = int(parts[0])
            max_price = int(parts[1]) if parts[1].strip() else float("inf")
        except:
            pass

    # ➤ 將 price_range 字串轉成最小與最大價格
    def parse_price_string(price_str):
        try:
            s = price_str.strip().replace("元", "").replace("約", "").replace("以上", "").replace("~", "-").replace("－", "-").replace(",", "")
            if not s:
                return None, None
            if s in ["$", "＄"]:
                return 0, 200
            elif s == "$$":
                return 200, 600
            elif s == "$$$":
                return 600, 1200
            if s.startswith("$"):
                s = s[1:]
            nums = [int(x) for x in s.split("-") if x.strip().isdigit()]
            if len(nums) == 1:
                return nums[0], nums[0]
            elif len(nums) >= 2:
                return nums[0], nums[1]
        except:
            return None, None
        return None, None

    # ➤ 價格區間比對邏輯（交集 or 下限比對）
    def is_price_in_range(restaurant_min, restaurant_max, filter_min, filter_max):
        if restaurant_min is None or restaurant_max is None:
            return False
        if filter_max == float("inf"):
            # 2000+：最低價格必須 ≥ 2000
            return restaurant_min >= filter_min
        else:
            # 一般區間：只要有交集即可
            return restaurant_max >= filter_min and restaurant_min <= filter_max

    # ➤ 篩選資料
    results = []
    for r in data:
        if r.get("district", "").strip() != district:
            continue

        # ➤ 多分類菜系支援（"中式,熱炒" 類型）
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
            if not is_price_in_range(r_min, r_max, min_price, max_price):
                continue

        results.append(r)

    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True)
