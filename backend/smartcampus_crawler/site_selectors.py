# smartcampus_crawler/site_selectors.py
from dataclasses import dataclass

@dataclass(frozen=True)
class LoginSelectors:
    # 로그인 폼
    id_input: str = 'input#userid'
    pw_input: str = 'input#passwd'
    submit_btn: str = 'form#f_login button[type="submit"]'

@dataclass(frozen=True)
class RoomSearchSelectors:
    """
    강의실 검색 UI 셀렉터 (유연 매칭)
    """
    # '강의실명' 입력창(여러 케이스 대응)
    room_keyword_input_xpath: str = (
        '//*[@id="lectureRoomNm" or @name="lectureRoomNm" or '
        '@id="lectureRoomName" or @name="lectureRoomName" or '
        '(@type="text" and (contains(@placeholder,"강의실") or contains(@title,"강의실")))]'
    )
    # '강의실찾기' 버튼 후보
    room_find_btn_xpath: str = '//input[@id="lectureRoomSearch"]'
    # 검색 결과 select
    room_select_xpath: str = (
        '//select[.//option and (contains(@id,"room") or contains(@name,"room") or contains(@title,"강의실"))]'
    )
    # 조회/검색 버튼(있을 때만 사용)
    search_btn_xpath: str = (
        '(//button[normalize-space()="조회" or normalize-space()="검색"]'
        ' | //input[@type="button" and (@value="조회" or @value="검색")]'
        ' | //a[normalize-space()="조회" or normalize-space()="검색"])[1]'
    )

@dataclass(frozen=True)
class TableSelectors:
    # '주간 시간표' 테이블(여러 케이스 대응)
    weekly_table_xpath: str = (
        '(//h3|//h4)[contains(normalize-space(),"주간") and contains(.,"시간표")]/following::table[1]'
        ' | //table[contains(@summary,"시간표") or contains(@id,"timetable")]'
    )
    row_xpath: str = './/tbody/tr'
    cell_xpath: str = './/td'
