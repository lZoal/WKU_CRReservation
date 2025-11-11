# smartcampus_crawler/crawler.py
import os
import re
import time
import argparse
from typing import List, Tuple, Optional

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
from selenium.common.exceptions import (
    TimeoutException, StaleElementReferenceException, NoSuchElementException
)

from .site_selectors import LoginSelectors, RoomSearchSelectors, TableSelectors

WAIT = 10  # 기본 대기(초)

# ───────────────────────── 공용 유틸 ─────────────────────────
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

from collections import deque
def list_and_switch_into_frame_containing(driver, by, value, max_depth=6, per_level_limit=20, timeout=0.5) -> bool:
    """
    모든 iframe/frame을 BFS로 순회하여 (by,value) 요소가 존재하는 프레임으로 전환.
    찾으면 True, 아니면 False.
    """
    switch_to_default(driver)
    try:
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
        return True
    except Exception:
        pass

    visited = set()
    queue = deque([[]])
    while queue:
        path = queue.popleft()
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
    try:
        return WebDriverWait(driver, 1).until(EC.presence_of_element_located((By.XPATH, select_xpath)))
    except Exception:
        pass
    if list_and_switch_into_frame_containing(driver, By.XPATH, select_xpath, max_depth=max_depth):
        return WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, select_xpath)))
    return None

def ensure_still_logged_in(driver):
    # 로그인 폼이 다시 보이면 세션 아웃
    try:
        driver.find_element(By.CSS_SELECTOR, "form#f_login")
        raise SystemExit("세션 만료: 로그인 페이지로 복귀함(SSO/쿠키 확인).")
    except NoSuchElementException:
        return

def sanitize_filename(text: str) -> str:
    text = re.sub(r"[\\/:*?\"<>|\r\n]+", "_", (text or "").strip())
    return re.sub(r"\s+", " ", text)

# 플레이스홀더/안내문구 필터 (select/목록에 가짜 항목이 섞일 때 제거)
PLACEHOLDER_PAT = re.compile(
    r"("
    r"선택|전체|검색|조회|클릭|없음|미선택|"
    r"please|select|choose|"
    r"입력.*후|강의실명.*클릭|강의실찾기|"
    r"^-$|^--|^—$"
    r")",
    re.I,
)
def is_placeholder(text: str) -> bool:
    t = (text or "").strip()
    return (not t) or PLACEHOLDER_PAT.search(t) is not None

def set_input_value(driver, el, text: str):
    """input.value를 JS로 정확히 세팅하고 input/change 이벤트까지 발생."""
    driver.execute_script(
        "arguments[0].value = arguments[1];"
        "arguments[0].dispatchEvent(new Event('input', {bubbles:true}));"
        "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));",
        el, text
    )

def ensure_room_list_ready(driver, rs: RoomSearchSelectors, room_keyword: str, retries: int = 2):
    """
    강의실 목록(select/커스텀)이 현재 문서/프레임에 없으면
    '강의실찾기'를 다시 눌러 목록을 복구한다. (최대 retries+1회 시도)
    """
    for _ in range(retries + 1):
        try:
            opts, sel, listbox = collect_room_options(driver, rs)
            if opts:
                return opts, sel, listbox
        except SystemExit:
            pass  # 목록이 아직 비었거나 플레이스홀더뿐
        # 목록이 없으면 재트리거
        trigger_room_search(driver, rs, room_keyword)
    raise SystemExit("강의실 목록 UI 준비 실패(재트리거 후에도 목록 미탐지).")

# ───────────────────────── 로그인/이동 ─────────────────────────
def login(driver, base_url: str, user_id: str, user_pw: str, sel: LoginSelectors):
    driver.get(base_url)
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "form#f_login")))
    WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.CSS_SELECTOR, sel.id_input))).send_keys(user_id)
    driver.find_element(By.CSS_SELECTOR, sel.pw_input).send_keys(user_pw)
    driver.find_element(By.CSS_SELECTOR, sel.submit_btn).click()

    try:
        WebDriverWait(driver, 15).until(
            EC.any_of(
                EC.url_contains("loginReturn"),
                EC.url_contains("SWupis"),
                EC.url_contains("intra.wku.ac.kr"),
            )
        )
    except TimeoutException:
        ts = int(time.time())
        driver.save_screenshot(f"login_timeout_{ts}.png")
        raise SystemExit("로그인 리다이렉트 실패.")

def open_room_timetable_direct(driver, timetable_url: str, rs: RoomSearchSelectors):
    """
    로그인 세션 유지 상태에서 시간표 페이지로 직접 진입.
    입력칸 탐지되면 성공.
    """
    def landed():
        try:
            WebDriverWait(driver, 1.5).until(EC.presence_of_element_located((By.XPATH, rs.room_keyword_input_xpath)))
            return True
        except Exception:
            return list_and_switch_into_frame_containing(driver, By.XPATH, rs.room_keyword_input_xpath, max_depth=8)

    if not timetable_url:
        raise SystemExit("TIMETABLE_URL이 비었습니다.")

    switch_to_default(driver)
    try:
        driver.get(timetable_url); time.sleep(0.5)
        if landed(): ensure_still_logged_in(driver); return
    except Exception:
        pass

    try:
        switch_to_default(driver)
        driver.execute_script("window.top.location.assign(arguments[0]);", timetable_url)
        time.sleep(0.7)
        if landed(): ensure_still_logged_in(driver); return
    except Exception:
        pass

    try:
        switch_to_default(driver)
        driver.execute_script("window.open(arguments[0], '_blank');", timetable_url)
        time.sleep(0.7)
        driver.switch_to.window(driver.window_handles[-1])
        switch_to_default(driver)
        if landed(): ensure_still_logged_in(driver); return
    except Exception:
        pass

    ts = int(time.time())
    try: driver.save_screenshot(f"goto_direct_fail_{ts}.png")
    except Exception: pass
    raise SystemExit("강의실 시간표 페이지 직접 진입 실패.")

# ───────────────────────── 검색/옵션 수집/선택 ─────────────────────────
def trigger_room_search(driver, rs: RoomSearchSelectors, room_keyword: str):
    """
    키워드 입력 → '강의실찾기' 클릭.
    일부 사이트에서 첫 클릭 후 입력칸이 초기화되므로,
    유효 옵션이 뜰 때까지 입력 재설정 + 재클릭을 최대 3회까지 자동 재시도.
    """
    ensure_still_logged_in(driver)
    switch_to_default(driver)

    # 입력칸 진입
    if not list_and_switch_into_frame_containing(driver, By.XPATH, rs.room_keyword_input_xpath, max_depth=8):
        raise SystemExit("강의실명 입력칸을 찾지 못했습니다.")
    kw = WebDriverWait(driver, WAIT).until(
        EC.presence_of_element_located((By.XPATH, rs.room_keyword_input_xpath))
    )

    def type_keyword():
        try:
            kw.clear()
        except Exception:
            pass
        js_focus_scroll_click(driver, kw)
        set_input_value(driver, kw, room_keyword)
        kw.send_keys(Keys.END)  # 일부 onchange 트리거 유도

    def click_find():
        btn_candidates = [
            '//input[@id="lectureRoomSearch"]',
            '//button[@id="lectureRoomSearch"]',
            '//button[contains(normalize-space(),"강의실찾기")]',
            '//input[@type="button" and contains(@value,"강의실찾기")]',
            '//a[contains(normalize-space(),"강의실찾기")]',
        ]
        btn = None
        for xp in btn_candidates:
            try:
                btn = WebDriverWait(driver, 1.5).until(
                    EC.presence_of_element_located((By.XPATH, xp))
                )
                break
            except Exception:
                continue
        if btn is None:
            kw.send_keys(Keys.ENTER)
            return
        WebDriverWait(driver, WAIT).until(lambda d: btn.get_attribute("disabled") in (None, "", "false"))
        js_focus_scroll_click(driver, btn)

    # 재시도 루프: 입력→클릭→결과확인 (최대 3회)
    for attempt in range(1, 4):
        ensure_still_logged_in(driver)

        # 입력 요소 재획득(프레임/갱신 대응)
        try:
            kw = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, rs.room_keyword_input_xpath))
            )
        except Exception:
            if not list_and_switch_into_frame_containing(driver, By.XPATH, rs.room_keyword_input_xpath, max_depth=8):
                raise SystemExit("입력칸 재탐색 실패")
            kw = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, rs.room_keyword_input_xpath))
            )

        type_keyword()
        click_find()

        # 유효 옵션 로드 대기 (플레이스홀더 제외)
        loaded = False
        start = time.time()
        while time.time() - start < 3.0:  # 시도당 최대 3초
            try:
                opts, _, _ = collect_room_options(driver, rs)
                if opts:
                    loaded = True
                    break
            except SystemExit:
                pass
            time.sleep(0.25)

        if loaded:
            # 콤보박스가 접혀 있으면 살짝 포커싱
            try:
                sel_el = find_select_in_any_frame(driver, rs.room_select_xpath, max_depth=8)
                if sel_el:
                    js_focus_scroll_click(driver, sel_el)
            except Exception:
                pass
            return  # 완료

        # 실패 → 입력칸 값 확인 후 재시도
        try:
            current_val = kw.get_attribute("value") or ""
        except Exception:
            current_val = ""
        print(f"[retry] attempt={attempt} value_after_click='{current_val}'")

    ts = int(time.time())
    try:
        driver.save_screenshot(f"no_valid_options_after_retries_{ts}.png")
    except Exception:
        pass
    raise SystemExit("강의실찾기 후 유효 옵션이 3회 재시도에도 로드되지 않았습니다.")

def collect_room_options(driver, rs: RoomSearchSelectors) -> Tuple[List[str], Optional[Select], Optional[object]]:
    """
    결과 목록 수집.
    - <select>인 경우: (텍스트리스트, Select, None)
    - 커스텀 드롭다운인 경우: (텍스트리스트, None, listbox_el)
    """
    # 1) select
    sel_el = None; options_text = []
    for _ in range(32):
        sel_el = find_select_in_any_frame(driver, rs.room_select_xpath, max_depth=8)
        if sel_el is not None:
            try:
                sel = Select(sel_el)
                options_text = [(o.text or "").strip() for o in sel.options]
                options_text = [t for t in options_text if t and not is_placeholder(t)]
                if options_text:
                    return options_text, sel, None
            except StaleElementReferenceException:
                pass
        time.sleep(0.25)

    # 2) custom dropdown
    listbox = None
    for _ in range(32):
        for xp in [
            '//*[@role="listbox"]',
            '//ul[contains(@class,"select") or contains(@class,"listbox") or contains(@class,"dropdown")]',
            '//div[contains(@class,"select") and .//li]',
        ]:
            try:
                listbox = WebDriverWait(driver, 0.5).until(EC.presence_of_element_located((By.XPATH, xp)))
                break
            except Exception:
                continue
        if listbox is not None:
            break
        time.sleep(0.25)
    if listbox is None:
        raise SystemExit("강의실 목록 UI를 찾지 못했습니다.")

    candidates = listbox.find_elements(By.XPATH, ".//li|.//*[@role='option']|.//option|.//a")
    options_text = [ (e.text or "").strip() for e in candidates ]
    options_text = [t for t in options_text if t and not is_placeholder(t)]
    if not options_text:
        raise SystemExit("검색 결과가 없습니다(플레이스홀더만 있음). 키워드/버튼 동작 확인.")
    return options_text, None, listbox

def select_room_option(driver, wanted_text: str, sel: Optional[Select], listbox) -> None:
    """표시 텍스트로 옵션 선택(정확→부분 일치)."""
    if sel is not None:
        for opt in sel.options:
            txt = (opt.text or "").strip()
            if txt == wanted_text:
                sel.select_by_visible_text(wanted_text); return
        for opt in sel.options:
            txt = (opt.text or "").strip()
            if wanted_text in txt:
                sel.select_by_visible_text(txt); return
        raise SystemExit(f"옵션 '{wanted_text}' 찾지 못함. 현재: {[o.text for o in sel.options]}")
    else:
        try: js_focus_scroll_click(driver, listbox)
        except Exception: pass

        items = listbox.find_elements(By.XPATH, ".//li|.//*[@role='option']|.//option|.//a")
        target = None
        for el in items:
            if (el.text or "").strip() == wanted_text: target = el; break
        if target is None:
            for el in items:
                if wanted_text in (el.text or ""): target = el; break
        if target is None:
            raise SystemExit(f"옵션 '{wanted_text}' 찾지 못함(커스텀 목록).")
        js_focus_scroll_click(driver, target)

# ───────────────────────── 테이블 대기/파싱 ─────────────────────────
def wait_timetable(driver, ts: TableSelectors):
    table = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, ts.weekly_table_xpath))
    )
    for _ in range(20):
        rows = table.find_elements(By.XPATH, ts.row_xpath)
        if len(rows) >= 1:
            non_empty = any((cell.text or "").strip()
                            for r in rows for cell in r.find_elements(By.XPATH, ts.cell_xpath))
            if non_empty: return table
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

# ───────────────────────── 전체/단일 스크랩 ─────────────────────────
def scrape_all_rooms(driver,
                     rs: RoomSearchSelectors,
                     options_text: List[str],
                     sel: Optional[Select],
                     listbox,
                     out_dir: str,
                     combined_path: Optional[str],
                     include_regex: Optional[str] = None,
                     room_keyword: Optional[str] = None) -> Tuple[List[str], pd.DataFrame]:

    os.makedirs(out_dir or ".", exist_ok=True)
    combined_rows: List[pd.DataFrame] = []
    saved_files: List[str] = []
    pattern = re.compile(include_regex) if include_regex else None

    # 초기 필터링
    options_text = [t for t in options_text if t and not is_placeholder(t)]
    seen = set()

    for idx, display in enumerate(options_text, 1):
        txt = display.strip()
        if not txt or txt in seen:
            continue
        if pattern and not pattern.search(txt):
            continue

        # 매 회차: 목록 확보(없거나 사라지면 강의실찾기 재트리거)
        try:
            cur_options, cur_sel, cur_listbox = ensure_room_list_ready(
                driver, rs, room_keyword or "", retries=1
            )
            cur_options = [t for t in cur_options if t and not is_placeholder(t)]
            if not cur_options:
                print(f"[skip] '{txt}': 유효 옵션이 없습니다(플레이스홀더만)."); continue
        except Exception as e:
            print(f"[skip] 목록 확보 실패: {e}"); continue

        # 정확→부분 일치로 보정
        target = txt if txt in cur_options else next((o for o in cur_options if txt in o), None)
        if not target:
            print(f"[skip] '{txt}' 현재 목록에 없음. 현재={cur_options[:6]}..."); continue

        # 선택
        try:
            select_room_option(driver, target, cur_sel, cur_listbox)
        except SystemExit as e:
            print(f"[skip] 선택 실패: {target} ({e})"); continue

        # (선택) 조회/검색 버튼 - 있으면 누르고, 없으면 바로 진행
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

        # 표 로딩/파싱
        try:
            table = wait_timetable(driver, TableSelectors())
            df = parse_weekly_table_to_df(table, TableSelectors())
            df.insert(0, "room", target)
            fname = sanitize_filename(target) + ".csv"
            path = os.path.join(out_dir, fname)
            df.to_csv(path, index=False, encoding="utf-8-sig")
            saved_files.append(path)
            combined_rows.append(df)
            seen.add(txt)
            print(f"[{idx:02d}/{len(options_text)}] saved: {path} (rows={len(df)})")
        except Exception as e:
            print(f"[warn] 파싱 실패: {target} ({e})")
            continue

    combined_df = pd.concat(combined_rows, ignore_index=True) if combined_rows else pd.DataFrame()
    if combined_path:
        os.makedirs(os.path.dirname(combined_path) or ".", exist_ok=True)
        combined_df.to_csv(combined_path, index=False, encoding="utf-8-sig")
    return saved_files, combined_df

# ───────────────────────── CLI ─────────────────────────
def cli():
    load_dotenv()

    parser = argparse.ArgumentParser(description="WKU 강의실 시간표 크롤러 (직접 링크/건물 전체 지원)")
    parser.add_argument("--room_kw", required=True, help="강의실 키워드(예: '공학관' 또는 '302')")
    parser.add_argument("--room_select", help="(single) 선택할 표시명(예: '공학관 - 302강의실')")
    parser.add_argument("--mode", choices=["single", "all"], default="single", help="single=단일, all=옵션 전체")
    parser.add_argument("--out_csv", default="./output/room_timetable.csv", help="(single) 출력 CSV 경로")
    parser.add_argument("--out_dir", default="./output/rooms", help="(all) 개별 CSV 폴더")
    parser.add_argument("--combined_csv", default="./output/rooms_combined.csv", help="(all) 통합 CSV 경로")
    parser.add_argument("--include_regex", default=None, help="(all) 옵션 텍스트 필터 정규식")

    parser.add_argument("--base_url", default=os.getenv("BASE_URL"), help="로그인 페이지 URL")
    parser.add_argument("--timetable_url", default=os.getenv("TIMETABLE_URL"), help="강의실 시간표 URL")
    parser.add_argument("--headless", dest="headless", action="store_true", help="브라우저 숨김")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="브라우저 표시")
    parser.set_defaults(headless=(os.getenv("HEADLESS", "true").lower() in ("1", "true", "y", "on")))
    args = parser.parse_args()

    if not args.base_url:
        raise SystemExit("BASE_URL이 비었습니다(.env 확인).")
    if not os.getenv("PORTAL_ID") or not os.getenv("PORTAL_PW"):
        raise SystemExit("PORTAL_ID/PORTAL_PW가 비었습니다(.env 확인).")
    if not args.timetable_url:
        raise SystemExit("TIMETABLE_URL이 비었습니다(.env 확인).")
    if args.mode == "single" and not args.room_select:
        raise SystemExit("--mode single에서는 --room_select 필요.")

    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1400,1000")
    if args.headless: options.add_argument("--headless=new")
    options.add_argument("--disable-gpu"); options.add_argument("--no-sandbox"); options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        print("[*] 로그인...")
        login(driver, args.base_url, os.getenv("PORTAL_ID"), os.getenv("PORTAL_PW"), LoginSelectors())

        print("[*] 시간표 페이지로 직접 진입...")
        open_room_timetable_direct(driver, args.timetable_url, RoomSearchSelectors())

        print(f"[*] 강의실 검색 트리거: kw='{args.room_kw}'")
        trigger_room_search(driver, RoomSearchSelectors(), args.room_kw)

        print("[*] 옵션 목록 수집...")
        options_text, sel, listbox = collect_room_options(driver, RoomSearchSelectors())
        options_text = [t.strip() for t in options_text if t and t.strip()]

        if args.mode == "single":
            print(f"[*] 단일 스크랩: '{args.room_select}'")
            # 선택 + 조회(있을 때만)
            select_room_option(driver, args.room_select.strip(), sel, listbox)
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
                        js_focus_scroll_click(driver, els[0]); break
                except Exception:
                    continue
            table = wait_timetable(driver, TableSelectors())
            df = parse_weekly_table_to_df(table, TableSelectors())
            os.makedirs(os.path.dirname(args.out_csv) or ".", exist_ok=True)
            df.to_csv(args.out_csv, index=False, encoding="utf-8-sig")
            print(f"[✅] 완료: {args.out_csv}")

        else:
            print(f"[*] 전체 스크랩 시작 (옵션 {len(options_text)}개). include_regex={args.include_regex or '(없음)'}")
            saved_files, combined_df = scrape_all_rooms(
                driver, RoomSearchSelectors(), options_text, sel, listbox,
                out_dir=args.out_dir, combined_path=args.combined_csv,
                include_regex=args.include_regex, room_keyword=args.room_kw
            )
            print(f"[✅] 개별 {len(saved_files)}건 저장 → {args.out_dir}")
            print(f"[✅] 통합 CSV 저장 → {args.combined_csv} (행 {len(combined_df)}개)")

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
