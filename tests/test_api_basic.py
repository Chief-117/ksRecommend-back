import os
import requests

# 🟢 1. 你原本的成功測試：測試正確帶入「鼓山區」參數
def test_restaurants_api_success():
    base_url = os.getenv(
        "API_BASE_URL",
        "http://127.0.0.1:5000"
    )

    url = f"{base_url}/api/restaurants"
    params = {"district": "鼓山區"}

    response = requests.get(url, params=params, timeout=5)

    assert response.status_code == 200
    assert isinstance(response.json(), list)


# 🔴 2. 模擬錯誤測試 A：故意「不帶 district 參數」，看 Flask 會不會防呆
def test_restaurants_api_missing_param():
    base_url = os.getenv(
        "API_BASE_URL",
        "http://127.0.0.1:5000"
    )

    url = f"{base_url}/api/restaurants"
    # 💡 關鍵：params 留空，完全不傳 district 參數
    params = {} 

    response = requests.get(url, params=params, timeout=5)

    # 💡 預期結果：後端應該要防呆並回傳 400 (Bad Request)，代表拒絕這次請求
    assert response.status_code == 400
    
    # 你甚至可以加這一行，檢查後端吐回來的錯誤訊息對不對
    # assert "缺少 district 參數" in response.json().get("error", "")


# 🔴 3. 模擬錯誤測試 B：故意輸入「不存在的行政區」
def test_restaurants_api_invalid_district():
    base_url = os.getenv(
        "API_BASE_URL",
        "http://127.0.0.1:5000"
    )

    url = f"{base_url}/api/restaurants"
    # 💡 關鍵：故意亂填一個不存在的區域
    params = {"district": "沒有這個區啦"} 

    response = requests.get(url, params=params, timeout=5)

    # 💡 預期結果：後端查不到資料，應該回傳 404 (Not Found)
    assert response.status_code == 404