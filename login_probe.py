import os, time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

load_dotenv()

BASE_URL = os.getenv("BASE_URL")
UID = os.getenv("PORTAL_ID")
PW  = os.getenv("PORTAL_PW")

ID  = "input#userid"
PWI = "input#passwd"
BTN = "form#f_login button[type='submit']"

opts = webdriver.ChromeOptions()
if os.getenv("HEADLESS", "true").lower() in ("1","true","y","on"):
    opts.add_argument("--headless=new")
opts.add_argument("--window-size=1280,2000")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)

try:
    driver.get(BASE_URL)
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "form#f_login")))
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ID))).send_keys(UID)
    driver.find_element(By.CSS_SELECTOR, PWI).send_keys(PW)
    driver.find_element(By.CSS_SELECTOR, BTN).click()

    WebDriverWait(driver, 15).until(
        EC.any_of(
            EC.url_contains("loginReturn.jsp"),
            EC.url_contains("SWupis"),
            EC.url_contains("intra.wku.ac.kr")
        )
    )
    print("[✅] 로그인 성공 (리다이렉트 감지 완료)")
    print("현재 URL:", driver.current_url)
except Exception as e:
    print("[❌] 로그인 실패:", e)
finally:
    driver.quit()
