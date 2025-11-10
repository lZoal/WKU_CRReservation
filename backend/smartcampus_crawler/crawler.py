# smartcampus_crawler/crawler.py
import os
import time
import argparse
from typing import List

from dotenv import load_dotenv
import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

from .site_selectors import (
    LoginSelectors,
    RoomSearchSelectors,
    TableSelectors,
)

WAIT = 10  # 기본 대기(초)

# =========================
# 공용 유틸
# =========================
def js_focus_scroll_click(driver, el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    driver.execute_script("arguments[0].focus();", el)
    try:
        el.click()
    except Exception:
        driver.execute_script("arguments[0].click();", el)

def switch_to_default(driver):
    try:
        driver.switch_to.default_content()
    except Exception:
        pass

# ----- 프레임 탐색(BFS) -----
from collections import deque
def list_and_switch_into_frame_containing(driver, by, value, max_depth=6, per_level_limit=20, timeout=0.5) -> bool:
    """
    모든 iframe/frame을 BFS로 순회하여 (by,value) 요소가 '현재 문서'에 존재하는 프레임을 찾으면
    그 프레임으로 전환하고 True 반환, 없으면 False.
    """
    switch_to_default(driver)

    # 루트에서 바로 존재하면 OK
    try:
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
        return True
    except Exception:
        pass

    visited = set()
    queue = deque([[]])  # []=루트

    while queue:
        path = queue.popleft()

        # 경로 따라 프레임 진입
        switch_to_default(driver)
        ok = True
        for idx in path:
            frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
            if idx >= len(frames):
                ok = False
                break
            driver.switch_to.frame(frames[idx])
        if not ok:
            continue

        key = tuple(path)
        if key in visited:
            continue
        visited.add(key)

        try:
            WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
            return True
        except Exception:
            pass

        if len(path) < max_depth:
            frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
            for i in range(min(len(frames), per_level_limit)):
                queue.append(path + [i])

    switch_to_default(driver)
    return False

def find_select_in_any_frame(driver, select_xpath, max_depth=6):
    # 현재 프레임 검색 → 없으면 프레임 BFS
    try:
        return WebDriverWait(driver, 1).until(EC.presence_of_element_located((By.XPATH, select_xpath)))
    except Exception:
        pass
    if list_and_switch_into_frame_containing(driver, By.XPATH, select_xpath, max_depth=max_depth):
        return WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, select_xpath)))
    return None

# =========================
# 로그인
# =========================
def login(driver, base_url: str, user_id: str, user_pw: str, sel: LoginSelectors):
    driver.get(base_url)

    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "form#f_login")))
    WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.CSS_SELECTOR, sel.id_input))).send_keys(user_id)
    driver.find_element(By.CSS_SELECTOR, sel.pw_input).send_keys(user_pw)
    driver.find_element(By.CSS_SELECTOR, sel.submit_btn).click()

    # 로그인 후 리다이렉트 대기
    try:
        WebDriverWait(driver, 15).until(
            EC.any_of(
                EC.url_contains("loginReturn.jsp"),
                EC.url_contains("SWupis"),
                EC.url_contains("intra.wku.ac.kr"),
            )
        )
    except TimeoutException:
        ts = int(time.time())
        driver.save_screenshot(f"login_timeout_{ts}.png")
        raise SystemExit("로그인 리다이렉트 실패(캡차/네트워크/셀렉터 확인).")

# =========================
# 강의실별 시간표 페이지로 "직접" 진입
# =========================
def open_room_timetable_direct(driver, timetable_url: str, rs: RoomSearchSelectors):
    """
    메뉴 클릭 없이, 로그인 세션 유지 상태에서 timetable_url로 직접 이동.
    - window.top.location.assign / window.open 등 다양한 경로로 시도
    - 도착 판정: '강의실명' 입력칸이 현재 문서(또는 프레임)에서 탐지되면 성공
    """
    def landed():
        # 입력칸이 현재 문서에 있거나, 프레임을 순회해 발견되면 True
        try:
            WebDriverWait(driver, 1.5).until(EC.presence_of_element_located((By.XPATH, rs.room_keyword_input_xpath)))
            return True
        except Exception:
            return list_and_switch_into_frame_containing(driver, By.XPATH, rs.room_keyword_input_xpath, max_depth=8)

    if not timetable_url:
        raise SystemExit("TIMETABLE_URL이 비었습니다(.env 확인).")

    switch_to_default(driver)

    # 시도 1: driver.get
    try:
        driver.get(timetable_url)
        time.sleep(0.5)
        if landed():
            return
    except Exception:
        pass

    # 시도 2: js-assign
    try:
        switch_to_default(driver)
        driver.execute_script("window.top.location.assign(arguments[0]);", timetable_url)
        time.sleep(0.7)
        if landed():
            return
    except Exception:
        pass

    # 시도 3: 새탭 open 후 그 탭으로 전환
    try:
        switch_to_default(driver)
        driver.execute_script("window.open(arguments[0], '_blank');", timetable_url)
        time.sleep(0.7)
        driver.switch_to.window(driver.window_handles[-1])
        switch_to_default(driver)
        if landed():
            return
    except Exception:
        pass

    ts = int(time.time())
    try:
        driver.save_screenshot(f"goto_direct_fail_{ts}.png")
    except Exception:
        pass
    raise SystemExit("강의실별 시간표 페이지 직접 진입 실패.")

# =========================
# 강의실 검색/선택 (버튼 안정화)
# =========================
def run_room_query(driver, rs: RoomSearchSelectors, room_keyword: str, room_option_text: str):
    """
    - '강의실명' 입력 → change/input 이벤트 강제
    - '강의실찾기' 버튼 클릭 (활성 대기 + 안전 클릭)
    - 콤보박스 옵션 로딩 대기 → 원하는 옵션 선택
    - (있으면) '조회/검색' 버튼 클릭
    """
    # 1) 입력칸
    switch_to_default(driver)
    if not list_and_switch_into_frame_containing(driver, By.XPATH, rs.room_keyword_input_xpath, max_depth=8):
        raise SystemExit("강의실명 입력칸을 찾지 못했습니다(프레임/셀렉터 확인).")

    kw = WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, rs.room_keyword_input_xpath)))
    kw.clear()
    kw.send_keys(room_keyword)
    # 이벤트 강제
    try:
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('input',{bubbles:true}));"
            "arguments[0].dispatchEvent(new Event('change',{bubbles:true}));",
            kw
        )
    except Exception:
        pass

    # 2) '강의실찾기' 버튼
    try:
        btn = WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, rs.room_find_btn_xpath)))
        # disabled 해제 대기
        WebDriverWait(driver, WAIT).until(lambda d: btn.get_attribute("disabled") in (None, "", "false"))
        js_focus_scroll_click(driver, btn)  # 안정 클릭
    except Exception:
        # 버튼 실패 시 Enter로 트리거
        try:
            kw = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, rs.room_keyword_input_xpath)))
            kw.send_keys(Keys.ENTER)
        except Exception as e:
            raise SystemExit(f"'강의실찾기' 버튼 클릭 및 Enter 트리거 실패: {e}")

    # 3) 콤보박스 옵션 로딩 대기
    wanted = (room_option_text or "").strip()
    sel_el = None
    options = []

    for _ in range(32):  # ~8초
        sel_el = find_select_in_any_frame(driver, rs.room_select_xpath, max_depth=8)
        if sel_el is not None:
            try:
                sel = Select(sel_el)
                options = [(o.text or "").strip() for o in sel.options]
            except StaleElementReferenceException:
                continue

            # 옵션이 1개 이상 늘어나거나, 원하는 문구가 등장하면 OK
            if len(options) > 1 or any(wanted == t for t in options):
                break
        time.sleep(0.25)
    else:
        raise SystemExit(f"콤보박스 로딩 지연. 현재 옵션: {options or ['(없음)']}")

    if not any(wanted == t for t in options):
        # 부분 일치라도 선택하고 싶다면 여기서 contains로 고치면 됨
        raise SystemExit(f"'{wanted}' 옵션을 찾을 수 없습니다. 현재 옵션: {options}")

    Select(sel_el).select_by_visible_text(wanted)

    # 4) (있으면) 조회/검색
    for xp in [
        '//button[normalize-space()="조회"]',
        '//button[normalize-space()="검색"]',
        '//input[@type="button" and (@value="조회" or @value="검색")]',
        '//a[normalize-space()="조회"]',
        '//a[normalize-space()="검색"]',
    ]:
        try:
            els = driver.find_elements(By.XPATH, xp)
            if els:
                js_focus_scroll_click(driver, els[0])
                break
        except Exception:
            continue

# =========================
# 시간표 테이블 대기/파싱
# =========================
def wait_timetable(driver, ts: TableSelectors):
    table = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, ts.weekly_table_xpath))
    )
    for _ in range(20):  # 내용 로딩 대기
        rows = table.find_elements(By.XPATH, ts.row_xpath)
        if len(rows) >= 1:
            non_empty = any(
                (cell.text or "").strip()
                for r in rows
                for cell in r.find_elements(By.XPATH, ts.cell_xpath)
            )
            if non_empty:
                return table
        time.sleep(0.25)
    return table

def parse_weekly_table_to_df(table, ts: TableSelectors) -> pd.DataFrame:
    rows = table.find_elements(By.XPATH, ts.row_xpath)
    data: List[List[str]] = []
    for r in rows:
        cells = [(cell.text or "").strip() for cell in r.find_elements(By.XPATH, ts.cell_xpath)]
        if cells:
            data.append(cells)
    maxw = max((len(x) for x in data), default=0)
    data = [row + [""] * (maxw - len(row)) for row in data]
    return pd.DataFrame(data, columns=[f"col_{i+1}" for i in range(maxw)])

# =========================
# CLI
# =========================
def cli():
    load_dotenv()

    parser = argparse.ArgumentParser(description="WKU 강의실별 시간표 크롤러 (직접 링크 진입 버전)")
    parser.add_argument("--room_kw", required=True, help="강의실명 키워드 (예: 302)")
    parser.add_argument("--room_select", required=True, help="콤보박스 표시명 (예: 공학관 - 302강의실)")
    parser.add_argument("--out_csv", default="./output/room_timetable.csv", help="출력 CSV 경로")
    parser.add_argument("--base_url", default=os.getenv("BASE_URL"), help="로그인 페이지 URL")
    parser.add_argument("--timetable_url", default=os.getenv("TIMETABLE_URL"), help="강의실별 시간표 페이지 URL")
    parser.add_argument("--headless", dest="headless", action="store_true", help="브라우저 창 숨김")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="브라우저 창 표시")
    parser.set_defaults(headless=(os.getenv("HEADLESS", "true").lower() in ("1", "true", "y", "on")))
    args = parser.parse_args()

    if not args.base_url:
        raise SystemExit("BASE_URL이 비었습니다(.env 확인).")
    if not os.getenv("PORTAL_ID") or not os.getenv("PORTAL_PW"):
        raise SystemExit("PORTAL_ID/PORTAL_PW가 비었습니다(.env 확인).")
    if not args.timetable_url:
        raise SystemExit("TIMETABLE_URL이 비었습니다(.env 확인).")

    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1400,1000")
    if args.headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        print("[*] 로그인...")
        login(driver, args.base_url, os.getenv("PORTAL_ID"), os.getenv("PORTAL_PW"), LoginSelectors())

        print("[*] 시간표 페이지로 직접 진입...")
        open_room_timetable_direct(driver, args.timetable_url, RoomSearchSelectors())

        print(f"[*] 강의실 검색: kw='{args.room_kw}', select='{args.room_select}'")
        run_room_query(driver, RoomSearchSelectors(), args.room_kw, args.room_select)

        print("[*] 테이블 로딩 대기...")
        table = wait_timetable(driver, TableSelectors())

        df = parse_weekly_table_to_df(table, TableSelectors())
        os.makedirs(os.path.dirname(args.out_csv) or ".", exist_ok=True)
        df.to_csv(args.out_csv, index=False, encoding="utf-8-sig")
        print(f"[✅] 완료! → {args.out_csv}")

    except Exception as e:
        print("[❌] 에러:", e)
        ts = int(time.time())
        try:
            driver.save_screenshot(f"error_{ts}.png")
            print(f"스크린샷 저장: error_{ts}.png")
        except Exception:
            pass
        raise
    finally:
        driver.quit()

if __name__ == "__main__":
    cli()
