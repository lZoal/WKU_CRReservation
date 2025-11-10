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
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# 표준모듈 selectors 와 충돌하지 않도록 파일명은 site_selectors.py 여야 합니다.
from .site_selectors import (
    LoginSelectors,
    NavSelectors,
    RoomSearchSelectors,
    TableSelectors,
)

# =========================
# 공용 유틸
# =========================
def wait_css(driver, css, timeout=10):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, css))
    )

def click_xpath(driver, xpath, timeout=10):
    el = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.XPATH, xpath))
    )
    try:
        el.click()
    except Exception:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        driver.execute_script("arguments[0].click();", el)
    return el

def click_first_that_exists(driver, xpaths, timeout_each=2):
    last_exc = None
    for xp in xpaths:
        try:
            el = WebDriverWait(driver, timeout_each).until(
                EC.element_to_be_clickable((By.XPATH, xp))
            )
            try:
                el.click()
            except Exception:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                driver.execute_script("arguments[0].click();", el)
            return True
        except Exception as e:
            last_exc = e
            continue
    if last_exc:
        raise last_exc
    return False

# =========================
# 프레임 탐색 유틸
# =========================
from collections import deque

def switch_to_default(driver):
    """최상위 문서로 포커스 복귀"""
    try:
        driver.switch_to.default_content()
    except Exception:
        pass

def list_and_switch_into_frame_containing(
    driver,
    by,
    value,
    max_depth: int = 6,
    per_level_limit: int = 20,
    timeout: float = 0.5,
) -> bool:
    """
    모든 iframe/frame을 BFS로 순회하면서 (by, value)에 해당하는 요소가
    '현재 문서'에 존재하는 프레임을 찾으면 그 프레임으로 전환하고 True 반환.
    찾지 못하면 False 반환.
    """
    switch_to_default(driver)

    # 루트에서 먼저 시도
    try:
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
        return True
    except Exception:
        pass

    visited = set()
    queue = deque([[]])  # [] = 루트

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

        # 현재 문서에서 대상 요소 존재 확인
        try:
            WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
            return True
        except Exception:
            pass

        # 하위 프레임 확장
        if len(path) < max_depth:
            frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
            for i in range(min(len(frames), per_level_limit)):
                queue.append(path + [i])

    switch_to_default(driver)
    return False

def switch_into_room_form_frame(driver, max_depth=8):
    """
    '강의실명' 입력칸을 찾을 때까지 모든 프레임을 순회하며 진입한다.
    여러 후보 XPath를 순서대로 시험한다.
    """
    candidates = [
        '//*[@id="lectureRoomNm"]',
        '//*[@name="lectureRoomNm"]',
        '//*[@id="lectureRoomName"]',
        '//*[@name="lectureRoomName"]',
        '//input[@type="text" and (contains(@placeholder,"강의실") or contains(@title,"강의실"))]',
        '//form//input[@type="text"]',
    ]

    # 루트에서 먼저 시도
    for xp in candidates:
        try:
            WebDriverWait(driver, 1.0).until(EC.presence_of_element_located((By.XPATH, xp)))
            return True
        except Exception:
            pass

    # 프레임 BFS 순회
    for xp in candidates:
        ok = list_and_switch_into_frame_containing(driver, By.XPATH, xp, max_depth=max_depth, timeout=0.3)
        if ok:
            return True
    return False

def get_select_options_texts(select_el):
    sel = Select(select_el)
    return [ (o.text or "").strip() for o in sel.options ]

def find_select_in_any_frame(driver, select_xpath, max_depth=6):
    # 현재 프레임에서 먼저
    try:
        return WebDriverWait(driver, 1).until(EC.presence_of_element_located((By.XPATH, select_xpath)))
    except Exception:
        pass
    # 프레임 순회
    found = list_and_switch_into_frame_containing(driver, By.XPATH, select_xpath, max_depth=max_depth)
    if found:
        return WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, select_xpath)))
    return None

# =========================
# 로그인
# =========================
def login(driver, base_url: str, user_id: str, user_pw: str, sel: LoginSelectors):
    driver.get(base_url)

    # 로그인 폼 대기
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "form#f_login"))
    )
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, sel.id_input))
    ).send_keys(user_id)

    driver.find_element(By.CSS_SELECTOR, sel.pw_input).send_keys(user_pw)
    driver.find_element(By.CSS_SELECTOR, sel.submit_btn).click()

    # 리다이렉트 대기
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
        raise SystemExit("로그인 리다이렉트 확인 실패(캡차/네트워크/셀렉터 확인).")

# =========================
# 네비게이션 → 강의실별 시간표
# =========================
def go_to_room_timetable(driver, nav: NavSelectors):
    """
    1) 세션/창/프레임 상태를 정리한 뒤
    2) TIMETABLE_URL로 여러 방식으로 진입 시도
    3) 안 되면 메뉴 클릭으로 폴백
    """
    tt_url = os.getenv("TIMETABLE_URL")
    from .site_selectors import RoomSearchSelectors
    rs = RoomSearchSelectors()

    def switch_to_last_window():
        try:
            handles = driver.window_handles
            driver.switch_to.window(handles[-1])
        except Exception:
            pass

    def ensure_top_context():
        try:
            driver.switch_to.default_content()
        except Exception:
            pass

    def wait_session_ready():
        # 로그인 직후 세션 쿠키와 도메인 정착 대기
        for _ in range(20):  # ~5초
            try:
                # 쿠키 체크 (포털이 JSESSIONID/WMONID 등 사용할 수 있음)
                ck = driver.get_cookies()
                if ck and "intra.wku.ac.kr" in driver.current_url:
                    return
            except Exception:
                pass
            time.sleep(0.25)

    def landed_on_room_page():
        # 입력칸이 보이면 성공
        try:
            WebDriverWait(driver, 1.5).until(
                EC.presence_of_element_located((By.XPATH, rs.room_keyword_input_xpath))
            )
            return True
        except Exception:
            # 프레임 탐색
            try:
                ok = list_and_switch_into_frame_containing(
                    driver, By.XPATH, rs.room_keyword_input_xpath, max_depth=8
                )
                return bool(ok)
            except Exception:
                return False

    # ----------------------
    # 1) 세션/창/프레임 정리
    # ----------------------
    wait_session_ready()
    switch_to_last_window()
    ensure_top_context()

    # ----------------------
    # 2) TIMETABLE_URL 직행 시도
    # ----------------------
    if tt_url:
        attempts = []

        # A) 표준 driver.get
        attempts.append(("driver.get", lambda: driver.get(tt_url)))

        # B) JS assign (동일 탭 강제 네비게이션)
        attempts.append(("js-assign", lambda: driver.execute_script(
            "window.top.location.assign(arguments[0]);", tt_url)))

        # C) JS open 새탭 → 그 탭으로 스위치
        def open_blank_then_switch():
            driver.execute_script("window.open(arguments[0], '_blank');", tt_url)
            time.sleep(0.5)
            switch_to_last_window()
        attempts.append(("js-open-blank", open_blank_then_switch))

        for tag, fn in attempts:
            try:
                ensure_top_context()
                fn()
                # URL 형태가 변할 수 있으니 가벼운 대기
                time.sleep(0.5)
                switch_to_last_window()
                ensure_top_context()

                # 도착 확인: 입력칸 탐지
                if landed_on_room_page():
                    # 최종 확인용 대기(안정화)
                    WebDriverWait(driver, 6).until(
                        EC.presence_of_element_located((By.XPATH, rs.room_keyword_input_xpath))
                    )
                    return
            except Exception:
                continue
        # 여기까지 안되면 메뉴 클릭으로 폴백

    # ----------------------
    # 3) 폴백: 메뉴 클릭 네비게이션
    # ----------------------
    try:
        # 상단 탭 "정보서비스"
        try:
            click_xpath(driver, nav.top_info_tab_xpath, 10)
        except Exception:
            pass

        # 좌측 "시간표관리" 그룹
        try:
            click_xpath(driver, nav.left_timetable_group_xpath, 10)
        except Exception:
            pass

        # "강의실별 시간표"
        click_xpath(driver, nav.left_room_tt_xpath, 12)

        # 프레임 안 입력칸 대기
        if not landed_on_room_page():
            raise TimeoutException("강의실 입력칸 감지 실패(프레임/셀렉터 확인)")

        WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.XPATH, rs.room_keyword_input_xpath))
        )
        return
    except Exception as e:
        ts = int(time.time())
        try:
            driver.save_screenshot(f"goto_room_error_{ts}.png")
        except Exception:
            pass
        raise SystemExit(f"강의실별 시간표 진입 실패: {e}")
# =========================
# 강의실 검색/선택
# =========================
def run_room_query(driver, rs: RoomSearchSelectors, room_keyword: str, room_option_text: str):
    from selenium.common.exceptions import StaleElementReferenceException

    def get_kw(timeout=10):
        # 매번 새로 찾아서 stale 회피
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, rs.room_keyword_input_xpath))
        )

    # 1) 입력칸 채우기 (+ 이벤트 보강)
    kw = get_kw()
    kw.clear()
    kw.send_keys(room_keyword)
    try:
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('change',{bubbles:true}));"
            "arguments[0].dispatchEvent(new Event('input',{bubbles:true}));",
            kw
        )
    except Exception:
        pass

    # 2) '강의실찾기' 버튼 클릭 (id로 직접 + staleness 대기)
    def click_search_btn_and_wait():
        btn = WebDriverWait(driver, 6).until(
            EC.element_to_be_clickable((By.XPATH, rs.room_find_btn_xpath))  # //input[@id="lectureRoomSearch"]
        )
        try:
            btn.click()
        except Exception:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            try:
                btn.click()
            except Exception:
                driver.execute_script("arguments[0].click();", btn)

        # 버튼/입력칸 중 하나가 사라지거나 re-render 되도록 잠깐 대기 (staleness)
        try:
            WebDriverWait(driver, 3).until(EC.staleness_of(btn))
        except Exception:
            pass
        try:
            WebDriverWait(driver, 3).until(EC.staleness_of(kw))
        except Exception:
            pass

    # 클릭 2회 시도 → 실패 시 ENTER 대체 (ENTER도 stale 대비하여 매번 재조회)
    clicked = False
    for _ in range(2):
        try:
            click_search_btn_and_wait()
            clicked = True
            break
        except Exception:
            pass
    if not clicked:
        try:
            get_kw().send_keys(Keys.ENTER)
        except StaleElementReferenceException:
            get_kw().send_keys(Keys.ENTER)

    # 3) 콤보박스가 실제로 채워질 때까지 대기 (프레임 이동 포함, stale 대비)
    wanted = room_option_text.strip()

    def safe_get_options(select_el):
        from selenium.webdriver.support.ui import Select
        try:
            sel = Select(select_el)
            return [ (o.text or "").strip() for o in sel.options ]
        except StaleElementReferenceException:
            # select가 갈아끼워진 경우 재탐색
            new_sel = find_select_in_any_frame(driver, rs.room_select_xpath, max_depth=6)
            if not new_sel:
                return []
            sel = Select(new_sel)
            return [ (o.text or "").strip() for o in sel.options ]

    sel_el = None
    options = []
    for _ in range(28):  # 최대 ~7초 (0.25*28)
        # 프레임을 돌며 최신 select를 다시 찾는다
        sel_el = find_select_in_any_frame(driver, rs.room_select_xpath, max_depth=6)
        if sel_el is not None:
            options = safe_get_options(sel_el)
            if len(options) > 1 or any(wanted == t for t in options):
                break
        time.sleep(0.25)
    else:
        raise SystemExit(
            f"콤보박스가 아직 채워지지 않았습니다. 현재 옵션: {options or ['(없음)']}\n"
            f"→ 검색 버튼 이벤트/프레임 전환 타이밍 때문에 select가 늦게 생성됩니다."
        )

    # 4) 원하는 옵션 존재 확인 후 선택 (여기도 stale 대비를 위해 재조회 허용)
    if not any(wanted == t for t in options):
        # 한 번 더 최신 select를 재조회 후 최종 확인
        sel_el = find_select_in_any_frame(driver, rs.room_select_xpath, max_depth=6) or sel_el
        options = safe_get_options(sel_el)
        if not any(wanted == t for t in options):
            raise SystemExit(f"콤보박스에 '{wanted}' 옵션이 없습니다.\n현재 옵션: {options}")

    Select(sel_el).select_by_visible_text(wanted)

    # 5) (있으면) 조회/검색 버튼 클릭 (stale-safe)
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
                try:
                    els[0].click()
                except StaleElementReferenceException:
                    # 버튼이 갈아끼워졌다면 다시 찾아 클릭
                    els = driver.find_elements(By.XPATH, xp)
                    if els:
                        try:
                            els[0].click()
                        except Exception:
                            driver.execute_script("arguments[0].click();", els[0])
                except Exception:
                    driver.execute_script("arguments[0].click();", els[0])
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
    # 내용 로딩 대기
    for _ in range(20):
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
        cells = [ (cell.text or "").strip() for cell in r.find_elements(By.XPATH, ts.cell_xpath) ]
        if cells:
            data.append(cells)
    maxw = max((len(x) for x in data), default=0)
    data = [row + [""]*(maxw - len(row)) for row in data]
    df = pd.DataFrame(data, columns=[f"col_{i+1}" for i in range(maxw)])
    return df

# =========================
# CLI
# =========================
def cli():
    load_dotenv()

    parser = argparse.ArgumentParser(description="WKU 강의실별 시간표 크롤러")
    parser.add_argument("--room_kw", required=True, help="강의실명 키워드 (예: 302)")
    parser.add_argument("--room_select", required=True, help="콤보박스 표시명 (예: 공학관 - 302강의실)")
    parser.add_argument("--out_csv", default="room_timetable.csv", help="출력 CSV 파일명")
    parser.add_argument("--base_url", default=os.getenv("BASE_URL"), help="로그인 페이지 URL")
    parser.add_argument("--timetable_url", default=os.getenv("TIMETABLE_URL"),
                        help="강의실별 시간표 페이지 직접 URL (프레임/JS 라우팅 우회)")
    parser.add_argument("--headless", dest="headless", action="store_true", help="브라우저 창 숨김")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="브라우저 창 표시")
    parser.set_defaults(headless=(os.getenv("HEADLESS","true").lower() in ("1","true","y","on")))
    args = parser.parse_args()

    # CLI 인자로 주어진 timetable_url을 환경변수에 주입(우선순위)
    if args.timetable_url:
        os.environ["TIMETABLE_URL"] = args.timetable_url

    user_id = os.getenv("PORTAL_ID")
    user_pw = os.getenv("PORTAL_PW")
    if not (args.base_url and isinstance(args.base_url, str)):
        raise SystemExit("BASE_URL이 비었습니다. .env를 확인하세요.")
    if not user_id or not user_pw:
        raise SystemExit("PORTAL_ID/PORTAL_PW가 비었습니다. .env를 확인하세요.")

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
        login(driver, args.base_url, user_id, user_pw, LoginSelectors())

        print("[*] 강의실별 시간표 페이지 이동...")
        go_to_room_timetable(driver, NavSelectors())

        print(f"[*] 강의실 검색: kw='{args.room_kw}', select='{args.room_select}'")
        run_room_query(driver, RoomSearchSelectors(), args.room_kw, args.room_select)

        print("[*] 테이블 로딩 대기...")
        table = wait_timetable(driver, TableSelectors())

        df = parse_weekly_table_to_df(table, TableSelectors())
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
