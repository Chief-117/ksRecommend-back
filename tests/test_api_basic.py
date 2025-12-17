import os
import requests

def test_restaurants_api():
    base_url = os.getenv(
        "API_BASE_URL",
        "http://127.0.0.1:5000"
    )

    url = f"{base_url}/api/restaurants"
    params = {"district": "鼓山區"}

    response = requests.get(url, params=params, timeout=5)

    assert response.status_code == 200
    assert isinstance(response.json(), list)
