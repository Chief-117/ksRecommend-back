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

    # ➤ 解析前端傳來的價格範圍
    min_price = None
    max_price = None
    if price_range:
        if price_range == "2000+":
            min_price = 2000
            max_price = float("inf")
        elif "-" in price_range:
            try:
                parts = price_range.split("-")
                min_price = int(parts[0])
                max_price = int(parts[1]) if parts[1].strip() else float("inf")
            except:
                pass  # 無效格式就略過價格篩選

    # ➤ 將價格字串轉為最小與最大值
    def parse_price_string(price_str):
        try:
            # 清理價格字串
            s = price_str.replace("元", "").replace("約", "").replace("以上", "").replace("~", "-").replace("－", "-").strip()
            if not s or s.startswith("$") and len(s) <= 1:  # 處理空字串或僅有"$"的情況
                return None, None
            if s.startswith("$"):  # 移除開頭的"$"符號
                s = s[1:]
            if "-" in s:
                nums = [int(x) for x in s.split("-") if x.strip().isdigit()]
                if len(nums) >= 2:
                    return nums[0], nums[1]  # 返回最小與最大值
                elif len(nums) == 1:
                    return nums[0], nums[0]  # 單一價格視為最小與最大值相同
            elif s.isdigit():
                num = int(s)
                return num, num  # 單一價格視為最小與最大值相同
            elif s == "$$":  # 假設 "$$" 對應 400-800
                return 400, 800
            elif s == "$$$":  # 假設 "$$$" 對應 800-1200
                return 800, 1200
        except:
            return None, None
        return None, None

    # ➤ 檢查價格範圍是否重疊
    def is_price_in_range(restaurant_min, restaurant_max, min_price, max_price):
        if restaurant_min is None or restaurant_max is None:
            return False  # 無有效價格資料，排除
        # 檢查價格範圍是否完全在指定範圍內或有交集
        if min_price == 2000 and max_price == float("inf"):  # 處理 "2000+" 情況
            return restaurant_min >= 2000
        return restaurant_min <= max_price and restaurant_max >= min_price

    # ➤ 篩選資料
    results = []
    for r in data:
        if r.get("district", "").strip() != district:
            continue
        if food_type != "all" and food_type not in r.get("type", "").strip():
            continue

        if min_price is not None and max_price is not None:
            price_str = r.get("price_range", "").strip()
            restaurant_min, restaurant_max = parse_price_string(price_str)
            if not is_price_in_range(restaurant_min, restaurant_max, min_price, max_price):
                continue

        results.append(r)

    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True)