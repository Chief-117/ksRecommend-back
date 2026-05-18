import os
import json
import re
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ======================
# 載入資料
# ======================
json_path = os.path.join(
    os.path.dirname(__file__),
    "crawler",
    "kaohsiung_restaurants_detailed.json"
)
json_path = os.path.abspath(json_path)

if not os.path.exists(json_path):
    raise FileNotFoundError(f"找不到 JSON 檔案：{json_path}")

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)
    print("JSON 筆數 =", len(data))


# ======================
# 價格解析
# ======================
def extract_price_bounds(price_str):
    if not price_str or "未提供" in price_str or "暫無" in price_str:
        return None, None

    if "超過" in price_str or "以上" in price_str or "起" in price_str:
        nums = re.findall(r"\d+", price_str.replace(",", ""))
        if nums:
            return int(nums[0]), None
        return None, None

    s = price_str.replace("~", "-").replace("－", "-").replace(",", "")
    s = re.sub(r"[^\d\-]", "", s)

    if "-" in s:
        nums = [int(x) for x in s.split("-") if x.isdigit()]
        if len(nums) == 2:
            return nums[0], nums[1]
    elif s.isdigit():
        v = int(s)
        return v, v

    return None, None


# ======================
# API
# ======================
@app.route("/api/restaurants", methods=["GET"])
def get_restaurants():
    district = request.args.get("district", "").strip()
    food_type = request.args.get("type", "").strip()
    price_range = request.args.get("price", "").strip()

    # 🔴 1. 模擬錯誤：如果前端「完全沒傳」或是傳空字串的 district
    if not district:
        # 回傳 400 Bad Request，讓 pytest 紀錄，同時讓 JMeter 報告抓到這個錯誤類型
        return jsonify({
            "status": "error",
            "message": "缺少必要的 district 參數"
        }), 400

    results = []

    for r in data:
        # ✅ 回到最單純、你已確認 JSON 一定有的 ==
        if r.get("district", "").strip() != district:
            continue

        # 類型篩選
        if food_type and food_type != "all":
            r_types = (
                r.get("type", "")
                .replace("、", ",")
                .replace(" ", "")
                .split(",")
            )
            if food_type not in r_types:
                continue

        # 價格篩選
        if price_range:
            price_str = r.get("price_range", "").strip()
            price_min, price_max = extract_price_bounds(price_str)

            if price_range == "0-500":
                if price_min is None or price_max is None:
                    continue
                if not (0 <= price_min and price_max <= 500):
                    continue

            elif price_range == "500-1000":
                if price_min is None or price_max is None:
                    continue
                if not (500 <= price_min and price_max <= 1000):
                    continue

            elif price_range == "1000-2000":
                if price_min is None or price_max is None:
                    continue
                if not (1000 <= price_min and price_max <= 2000):
                    continue

            elif price_range == "2000up":
                if price_min is None:
                    continue
                if not (
                    price_min >= 2000 or
                    (price_max is not None and price_min <= 2000 < price_max)
                ):
                    continue

        results.append(r)

    # 🔴 2. 模擬錯誤：如果過濾完發現一筆餐廳都沒有，代表輸入了不存在的行政區
    if len(results) == 0:
        # 回傳 404 Not Found
        return jsonify({
            "status": "error",
            "message": f"找不到行政區 '{district}' 的任何餐廳資料"
        }), 404

    # 🟢 3. 正常找到資料，回傳 200 成功
    response = make_response(jsonify(results))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ======================
# 啟動
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)