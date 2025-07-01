import os
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

# ✅ 使用「上一層」的 crawler 資料夾
json_path = os.path.join(os.path.dirname(__file__),  "crawler", "kaohsiung_restaurants_detailed.json")
json_path = os.path.abspath(json_path)

if not os.path.exists(json_path):
    raise FileNotFoundError(f"找不到 JSON 檔案：{json_path}")

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

@app.route("/api/restaurants")
def get_restaurants():
    district = request.args.get("district", "").strip()
    food_type = request.args.get("type", "").strip()

    if not district:
        return jsonify([])

    results = [
        r for r in data
        if r.get("district", "").strip() == district and 
           (food_type == "all" or food_type in r.get("type", "").strip())
    ]
    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True)
