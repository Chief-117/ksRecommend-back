import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 啟用 CORS 讓前端可存取

# ✅ 指向 JSON 資料位置
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
    price_range = request.args.get("price", "").strip()  # ⬅️ 接收價格參數（如 0-500）

    if not district:
        return jsonify([])

    # 👉 解析價格區間
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
                max_price = int(parts[1])
            except:
                pass  # 解析失敗就略過價格比對

    # 👉 將 price_range 字串轉成可比對的平均價格
    def parse_price_string(price_str):
        try:
            s = price_str.replace("元", "").replace("約", "").replace("以上", "").replace("~", "-").replace("－", "-")
            nums = [int(x) for x in s.split("-") if x.strip().isdigit()]
            if len(nums) == 1:
                return nums[0]
            elif len(nums) >= 2:
                return sum(nums) // len(nums)  # 取平均值
        except:
            return None
        return None

    results = []
    for r in data:
        if r.get("district", "").strip() != district:
            continue
        if food_type != "all" and food_type not in r.get("type", "").strip():
            continue

        # 價格篩選邏輯
        if min_price is not None and max_price is not None:
            price_str = r.get("price_range", "")
            avg_price = parse_price_string(price_str)
            if avg_price is None or not (min_price <= avg_price <= max_price):
                continue

        results.append(r)

    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True)
