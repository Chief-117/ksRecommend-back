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

    def extract_price_bounds(price_str):
        if not price_str or "未提供" in price_str or "暫無" in price_str:
            return None, None
        if "超過" in price_str or "以上" in price_str or "起" in price_str:
            return 2000, None  # 無上限視為 None
        s = price_str.lower().strip()
        s = s.replace("~", "-").replace("－", "-").replace(",", "")
        s = re.sub(r"[^\d\-]", "", s)
        if "-" in s:
            nums = [int(x) for x in s.split("-") if x.isdigit()]
            if len(nums) == 2:
                return nums[0], nums[1]
        elif s.isdigit():
            val = int(s)
            return val, val
        return None, None

    results = []
    for r in data:
        if r.get("district", "").strip() != district:
            continue

        if food_type != "all":
            r_types = r.get("type", "").replace("、", ",").replace(" ", "").split(",")
            if food_type not in r_types:
                continue

        price_str = r.get("price_range", "").strip()
        price_min, price_max = extract_price_bounds(price_str)

        if price_range:
            if price_range == "0-500":
                if price_min is None or price_max is None:
                    continue
                if not (price_min >= 0 and price_max <= 500):
                    continue

            elif price_range == "500-1000":
                if price_min is None or price_max is None:
                    continue
                if not (price_min >= 500 and price_max <= 1000):
                    continue

            elif price_range == "1000-2000":
                if price_min is None or price_max is None:
                    continue
                if not (price_min >= 1000 and price_max <= 2000):
                    continue

            elif price_range == "2000up":
                # 三種情況符合 2000up：
                # 1. min >= 2000
                # 2. min <= 2000 且 max > 2000（跨過門檻）
                # 3. 無上限（max 是 None）
                if price_min is None:
                    continue
                if not (
                    (price_min >= 2000) or
                    (price_max is not None and price_min <= 2000 and price_max > 2000) or
                    (price_max is None)
                ):
                    continue

        results.append(r)

    response = make_response(jsonify(results))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

if __name__ == "__main__":
    app.run(debug=True)
