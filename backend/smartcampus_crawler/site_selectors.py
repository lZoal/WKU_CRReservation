# smartcampus_crawler/site_selectors.py
from dataclasses import dataclass

@dataclass(frozen=True)
class LoginSelectors:
    id_input: str = 'input#userid'
    pw_input: str = 'input#passwd'
    submit_btn: str = 'form#f_login button[type="submit"]'

@dataclass(frozen=True)
class NavSelectors:
    # 상단 탭 "정보서비스"
    top_info_tab_xpath: str = '//ul[contains(@class,"gnb") or contains(@id,"gnb")]//a[normalize-space()="정보서비스"]'
    # 좌측 트리 "시간표관리"
    left_timetable_group_xpath: str = '//div[contains(@class,"left") or contains(@id,"left")]//a[normalize-space()="시간표관리"]'
    # 좌측 하위 메뉴 "강의실별 시간표조회" (공백/변형 대비 contains)
    left_room_tt_xpath: str = '//div[contains(@class,"left") or contains(@id,"left")]//a[contains(normalize-space(),"강의실별 시간표")]'

@dataclass(frozen=True)
class RoomSearchSelectors:
    # 입력칸은 유연하게 (id/name/placeholder/title 어떤 경우든)
    room_keyword_input_xpath: str = (
        '//*[@id="lectureRoomNm" or @name="lectureRoomNm" or '
        '@id="lectureRoomName" or @name="lectureRoomName" or '
        '(@type="text" and (contains(@placeholder,"강의실") or contains(@title,"강의실")))]'
    )
    room_find_btn_xpath: str = '//input[@id="lectureRoomSearch"]'
    room_select_xpath: str = (
        '//select[.//option and (contains(@id,"room") or contains(@name,"room") or contains(@title,"강의실"))]'
    )
    search_btn_xpath: str = (
        '(//button[normalize-space()="조회" or normalize-space()="검색"]'
        ' | //input[@type="button" and (@value="조회" or @value="검색")]'
        ' | //a[normalize-space()="조회" or normalize-space()="검색"])[1]'
    )
@dataclass(frozen=True)
class TableSelectors:
    # '주간 시간표' 섹션 아래 첫 번째 테이블
    weekly_table_xpath: str = '(//h3|//h4)[contains(normalize-space(),"주간") and contains(.,"시간표")]/following::table[1] | //table[contains(@summary,"시간표") or contains(@id,"timetable")]'
    row_xpath: str = './/tbody/tr'
    cell_xpath: str = './/td'
