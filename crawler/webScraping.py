import os
import json
import time
import re
from urllib.parse import quote
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options

# ====== 設定 Selenium WebDriver ======
options = Options()
options.add_argument("start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")

service = Service(executable_path=r'C:\Users\S117\Desktop\ksRecommendation\crawler\msedgedriver.exe')
driver = webdriver.Edge(service=service, options=options)

# ====== 載入搜尋任務 JSON ======
tasks_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kaohsiung_tasks.json")
with open(tasks_path, "r", encoding="utf-8") as f:
    tasks = json.load(f)

results = []

for task in tasks:
    district = task["district"]
    cuisine_type = task["type"]
    query = f"{district} {cuisine_type} 餐廳"
    url = f"https://www.google.com/maps/search/{quote(query)}"

    print(f"搜尋：{query}")
    driver.get(url)
    time.sleep(3)

    try:
        scrollable_div = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@aria-label, '結果')]"))
        )
    except:
        print(f"⚠️ {query} 搜尋結果無可滾動區塊，跳過")
        continue

    for _ in range(8):
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
        time.sleep(1)

    cards = driver.find_elements(By.CSS_SELECTOR, 'div.Nv2PK.THOPZb.CpccDe')
    print(f"{district} {cuisine_type} - 找到 {len(cards)} 筆結果")

    for idx, card in enumerate(cards[:20]):
        try:
            a_tag = card.find_element(By.CSS_SELECTOR, 'a.hfpxzc')
            maps_url = a_tag.get_attribute('href')

            driver.execute_script("window.open(arguments[0]);", maps_url)
            driver.switch_to.window(driver.window_handles[-1])

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.DUwDvf'))
            )
            time.sleep(1.5)

            name = driver.find_element(By.CSS_SELECTOR, 'h1.DUwDvf').text.strip() if driver.find_elements(By.CSS_SELECTOR, 'h1.DUwDvf') else ""
            rating = driver.find_element(By.CSS_SELECTOR, '.F7nice span').text.strip() if driver.find_elements(By.CSS_SELECTOR, '.F7nice span') else "無"
            raw_address = driver.find_element(By.CSS_SELECTOR, '[data-item-id="address"]').text.strip() if driver.find_elements(By.CSS_SELECTOR, '[data-item-id="address"]') else ""
            address = re.sub(r'[^\u4e00-\u9fa5\d\sA-Za-z號巷弄路街區\-]', '', raw_address)
            status = driver.find_element(By.CSS_SELECTOR, '.ZDu9vd').text.strip() if driver.find_elements(By.CSS_SELECTOR, '.ZDu9vd') else ""

            # 抓圖片
            image_url = ""
            try:
                image_tag = driver.find_element(By.CSS_SELECTOR, '.aoRNLd img')
                image_url = image_tag.get_attribute('src') if image_tag else ""
            except:
                try:
                    fallback_img = driver.find_element(By.CSS_SELECTOR, 'img[data-atf]')
                    image_url = fallback_img.get_attribute('src') if fallback_img else ""
                except:
                    image_url = ""

            price_range = ""
            spans = driver.find_elements(By.CSS_SELECTOR, '.mgr77e span')
            for span in spans:
                text = span.text.strip().replace("·", "")
                if "$" in text or "元" in text:
                    price_range = text
                    break

            print(f"#{idx+1}")
            print("name:", name)
            print("rating:", rating)
            print("price_range:", price_range)
            print("address:", address)
            print("status:", status)
            print("image:", image_url)
            print("url:", maps_url)
            print("----------")

            results.append({
                "name": name,
                "image": image_url,
                "rating": rating,
                "price_range": price_range,
                "address": address,
                "status": status,
                "maps_url": maps_url,
                "district": district,
                "type": cuisine_type
            })

            driver.close()
            driver.switch_to.window(driver.window_handles[0])

        except Exception as e:
            print(f"擷取詳細頁面資料時出錯：{e}")
            try:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
            except:
                pass
            continue

# ====== 儲存結果到 JSON ======
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kaohsiung_restaurants_detailed.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("✅ 所有資料已完成爬取並儲存為 kaohsiung_restaurants_detailed.json")
driver.quit()
