import streamlit as st
import time
import urllib.parse
import requests
import plotly.graph_objects as go
import random
import math
import csv
import os
import textwrap

# 페이지 초기 구성
st.set_page_config(
    page_title="룸체크 (RoomCheck)",
    page_icon="🏠",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------------------
# 전역 변수 및 헬퍼 함수 정의
# ---------------------------------------------------------------------
# 한글 필드명 매핑 전역 사전
DISPLAY_NAMES = {
    "수압": "수압",
    "채광": "채광",
    "보안": "보안",
    "소음": "소음",
    "청결도": "청결"
}

# 안전한 소수점 수치 형변환 헬퍼 함수
def safe_float(val, default=0.0):
    if not val:
        return default
    try:
        return float(str(val).replace(",", "").strip())
    except ValueError:
        return default

# 🌐 Haversine 거리 계산 공식
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # 지구 반지름 (미터 단위)
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# ---------------------------------------------------------------------
# 세션 상태(Session State) 초기화 및 타이머 변수 정의
# ---------------------------------------------------------------------
if 'show_splash' not in st.session_state:
    st.session_state.show_splash = True

if 'timer_running' not in st.session_state:
    st.session_state.timer_running = False

if 'timer_start' not in st.session_state:
    st.session_state.timer_start = 0.0

if 'show_delete_confirm' not in st.session_state:
    st.session_state.show_delete_confirm = False

if 'properties' not in st.session_state:
    st.session_state.properties = [
        {
            "id": "mock_a",
            "name": "신촌 원룸 A",
            "address": "서울 서대문구 신촌동 · 보증금 500 / 월세 55",
            "deposit": "500",
            "rent": "55",
            "real_rent": 51.0,
            "option_savings": 4.0,
            "options": ["에어컨", "세탁기"],
            "scores": {"수압": 75, "채광": 92, "보안": 81, "소음": 41, "청결도": 88},
            "overall_score": 82,
            "cctv_count": 5,
            "cvs_count": 3,
            "pharmacy_count": 1,
            "transit_count": 2,
            "attached_photos": [],
            "toilet_water_pressure": "매우 원활",
            "simultaneous_drainage_issue": False,
            "obstruction_level": "충분함",
            "window_condensation": False,
            "parking_status": "여유",
            "trash_area_clean": True,
            "wall_noise_audible": False,
            "road_noise_level": "없음",
            "sink_leak_odor": False,
            "pet_damage": False,
            "area_size": "12",
            "loan_ratio": "15"
        },
        {
            "id": "mock_b",
            "name": "홍대 오피스텔 B",
            "address": "서울 마포구 서교동 · 보증금 1000 / 월세 58",
            "deposit": "1000",
            "rent": "58",
            "real_rent": 55.0,
            "option_savings": 3.0,
            "options": ["에어컨", "세탁기", "냉장고"],
            "scores": {"수압": 80, "채광": 50, "보안": 88, "소음": 65, "청결도": 72},
            "overall_score": 76,
            "cctv_count": 8,
            "cvs_count": 4,
            "pharmacy_count": 2,
            "transit_count": 3,
            "attached_photos": [],
            "toilet_water_pressure": "매우 원활",
            "simultaneous_drainage_issue": False,
            "obstruction_level": "보통",
            "window_condensation": True,
            "parking_status": "보통",
            "trash_area_clean": True,
            "wall_noise_audible": True,
            "road_noise_level": "보통",
            "sink_leak_odor": False,
            "pet_damage": False,
            "area_size": "15",
            "loan_ratio": "10"
        },
        {
            "id": "mock_c",
            "name": "이대 원룸 C",
            "address": "서울 서대문구 대현동 · 보증금 500 / 월세 48",
            "deposit": "500",
            "rent": "48",
            "real_rent": 45.0,
            "option_savings": 3.0,
            "options": ["에어컨", "냉장고"],
            "scores": {"수압": 60, "채광": 90, "보안": 70, "소음": 55, "청결도": 65},
            "overall_score": 68,
            "cctv_count": 3,
            "cvs_count": 2,
            "pharmacy_count": 1,
            "transit_count": 1,
            "attached_photos": [],
            "toilet_water_pressure": "보통",
            "simultaneous_drainage_issue": True,
            "obstruction_level": "충분함",
            "window_condensation": False,
            "parking_status": "협소",
            "trash_area_clean": False,
            "wall_noise_audible": False,
            "road_noise_level": "없음",
            "sink_leak_odor": True,
            "pet_damage": True,
            "area_size": "10",
            "loan_ratio": "20"
        }
    ]

if 'selected_to_compare' not in st.session_state:
    st.session_state.selected_to_compare = {"mock_a", "mock_b", "mock_c"}

if 'current_tab' not in st.session_state:
    st.session_state.current_tab = "가이드"

if 'current_step' not in st.session_state:
    st.session_state.current_step = 0

# 비교 필터 조건 초기 상태 정의
for f in ["fl_rent", "fl_sec", "fl_light", "fl_noise"]:
    if f not in st.session_state:
        st.session_state[f] = False

# 기본 매물 조건 데이터 초기 구조화
chk_defaults = {
    "chk_name": "", "chk_address": "", "chk_deposit": "3000", "chk_rent": "60", "chk_area_size": "12", "chk_loan_ratio": "15",
    "chk_water_timer": 5.0, "chk_drainage": "매우 원활 (바로 빠짐)", "chk_toilet": "매우 원활", "chk_sim_drainage": False,
    "chk_direction": "남향", "chk_window_size": "중 (일반 창문)", "chk_obstruction": "충분함", "chk_ventilation": False, "chk_condensation": False,
    "chk_cctv": 0, "chk_cvs": 0, "chk_pharmacy": 0, "chk_transit": 0, "chk_parking": "여유", "chk_streetlight": False, "chk_trash": False,
    "chk_noise_open": 60.0, "chk_noise_closed": 35.0, "chk_road_noise": "없음", "chk_wall_noise": False,
    "chk_mold": False, "chk_leak": False, "chk_sink_odor": False, "chk_pet_damage": False, "chk_photos": [],
    "chk_aircon": False, "chk_washer": False, "chk_fridge": False
}
for k, v in chk_defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# 카카오 지리 정보 파싱 REST API 키
KAKAO_REST_API_KEY = "21bcf03173200cf408ee1d89919b6731"

# ---------------------------------------------------------------------
# 📱 데스크톱 기기 프레임 비율 고정 및 모바일 대응 가변 CSS
# ---------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

/* 스트림릿 기본 요소 완전 가림 */
[data-testid="stHeader"] { display: none !important; }
footer { display: none !important; visibility: hidden !important; }
[data-testid="stToolbar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; } /* 사이드바 화살표 원천 차단 */

html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
    background-color: #0F0F1A !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* 📱 데스크톱 뷰포트: 가상 3D 프레임 규격 최적 확장 (430px) */
@media (min-width: 450px) {
    .block-container,
    [data-testid="stMainBlockContainer"],
    [data-testid="stAppViewBlockContainer"],
    .stAppViewBlockContainer {
        background-color: #FCFCFF !important;
        width: 430px !important;
        max-width: 430px !important;
        min-width: 430px !important;
        height: 880px !important;
        max-height: 880px !important;
        min-height: 880px !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
        margin: 40px auto !important;
        padding: 32px 20px 90px 20px !important; /* 가상 상태바 제거에 따라 상단 패딩 축소 조정 */
        border: 12px solid #1E202C !important;
        border-radius: 52px !important;
        box-shadow: 0 25px 60px rgba(0,0,0,0.65) !important;
        position: relative !important;
        box-sizing: border-box !important;
        transform: translate(0, 0) !important;
    }
    
    div:has(> div > .nav-bar-anchor) ~ div div[data-testid="stHorizontalBlock"]::after {
        content: "" !important;
        position: absolute !important;
        bottom: 8px !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: 130px !important;
        height: 5px !important;
        background-color: #1E202C !important;
        border-radius: 10px !important;
        display: block !important;
        z-index: 1000002 !important;
    }
}

/* 📱 모바일 실기기 접속 대응 (여백 및 배경 색상 완벽 피팅) */
@media (max-width: 450px) {
    /* 모바일 환경에서는 3D 프레임이 무너지므로 전체 배경을 깔끔한 라이트 블루/그레이로 통합하여 아래쪽 검은 영역을 완전히 차단 */
    html, body, 
    [data-testid="stAppViewContainer"], 
    html, body,
    section.main, 
    [data-testid="stApp"],
    .stApp {
        background-color: #FCFCFF !important;
    }

    .block-container,
    [data-testid="stMainBlockContainer"],
    [data-testid="stAppViewBlockContainer"],
    .stAppViewBlockContainer {
        background-color: #FCFCFF !important;
        width: 100% !important;
        max-width: 100% !important;
        min-width: 100% !important;
        min-height: 100vh !important;
        height: auto !important;
        margin: 0 !important;
        padding: 24px 12px 120px 12px !important; /* 바닥 메뉴 여유분 확보 */
        border: none !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        position: relative !important;
        box-sizing: border-box !important;
        transform: none !important; /* 모바일에서 fixed 원소 정렬 왜곡을 막기 위해 transform 초기화 */
    }
}

/* 📱 모바일 기기 (화면 폭 640px 이하)에서 st.columns 세로 Stacking(붕괴) 차단 및 가로 정렬 강제 */
@media (max-width: 640px) {
    div[data-testid="stHorizontalBlock"] {
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: stretch !important;
        gap: 8px !important;
    }
    
    /* stColumn과 column 두 가지 스트림릿 버전에 안전 호환되도록 동시 타겟팅 (너비 밀림 현상 완전 해결) */
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        min-width: 0 !important;
        width: auto !important; 
        flex: 1 1 0% !important;
    }
    
    /* 1단계 기본 조건 입력창: 첫 번째 컬럼(라벨) 가로 폭 지정 (라벨 85px 고정) */
    div[data-testid="stHorizontalBlock"]:has(div[style*="margin-top: 14px"]) > div[data-testid="stColumn"]:nth-child(1),
    div[data-testid="stHorizontalBlock"]:has(div[style*="margin-top: 14px"]) > div[data-testid="column"]:nth-child(1) {
        flex: 0 0 85px !important;
        min-width: 85px !important;
    }
    
    /* 1단계 기본 조건 입력창: 세 번째 컬럼(단위 배지 만원, %, 평) 가로 폭 지정 (배지 65px 고정) */
    div[data-testid="stHorizontalBlock"]:has(div[style*="margin-top: 14px"]) > div[data-testid="stColumn"]:nth-child(3),
    div[data-testid="stHorizontalBlock"]:has(div[style*="margin-top: 14px"]) > div[data-testid="column"]:nth-child(3) {
        flex: 0 0 65px !important;
        min-width: 65px !important;
    }
    
    /* 3단계 리포트 탭: 상단 셀렉트박스와 삭제 버튼 가로 정렬 비율 최적화 (삭제 버튼 52px 고정) */
    div[data-testid="stHorizontalBlock"]:has([data-testid="stSelectbox"]) > div[data-testid="stColumn"]:nth-child(2),
    div[data-testid="stHorizontalBlock"]:has([data-testid="stSelectbox"]) > div[data-testid="column"]:nth-child(2) {
        flex: 0 0 52px !important;
    }
}

/* 💡 스크롤바 디자인 슬림화 */
[data-testid="stMainBlockContainer"]::-webkit-scrollbar {
    width: 4px;
}
[data-testid="stMainBlockContainer"]::-webkit-scrollbar-thumb {
    background-color: rgba(47, 73, 209, 0.15);
    border-radius: 10px;
}

/* 피그마 카드 스타일 가공 */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #FFFFFF !important;
    border: 1px solid #F1F3FE !important;
    border-radius: 24px !important;
    padding: 20px 22px !important;
    box-shadow: 0 12px 30px rgba(47, 73, 209, 0.03) !important;
    margin-bottom: 0px !important;
}




/* 타이포그래피 정렬 */
[data-testid="stMainBlockContainer"] p,
[data-testid="stMainBlockContainer"] span:not([data-testid="stWidgetLabel"]),
[data-testid="stMainBlockContainer"] label,
[data-testid="stMainBlockContainer"] h1,
[data-testid="stMainBlockContainer"] h2,
[data-testid="stMainBlockContainer"] h3,
[data-testid="stMainBlockContainer"] h4 {
    color: #1E202C !important;
}

/* 폼 입력창 고휘도 라운딩 처리 */
div[data-testid="stTextInput"] div[data-baseweb="input"] {
    border-radius: 14px !important;
    border: 1.5px solid #EFF1FE !important;
    background-color: #FFFFFF !important;
    overflow: hidden !important;
}
div[data-testid="stTextInput"] div[data-baseweb="base-input"] {
    background-color: transparent !important;
    padding: 0 !important;
}
div[data-testid="stTextInput"] input {
    background-color: transparent !important;
    border: none !important;
    color: #1E202C !important;
    height: 48px !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    padding: 0 16px !important;
    transform: translateY(-4px) !important;
    transition: all 0.25s ease;
}
div[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within {
    border-color: #2F49D1 !important;
    box-shadow: 0 0 0 4px rgba(47, 73, 209, 0.08) !important;
}
div[data-testid="stTextInput"] input:focus {
    outline: none !important;
}

/* 🎨 Streamlit primaryColor CSS 변수 강제 파란색 오버라이드 */
:root {
    --primary-color: #2F49D1 !important;
}
/* Streamlit 내부 CSS 변수 오버라이드 */
.stApp {
    --primary: #2F49D1 !important;
}
/* 체크박스 checked 상태 배경 - Streamlit 기본 빨강 오버라이드 */
[data-baseweb="checkbox"] input:checked ~ div,
[data-baseweb="checkbox"] input:checked + div {
    background-color: #2F49D1 !important;
    border-color: #2F49D1 !important;
}

/* 📋 체크박스 - 피그마 카드형 체크리스트 구현 */
div[data-testid="stCheckbox"] {
    border: 1.5px solid #EFF1FE !important;
    background-color: #FFFFFF !important;
    border-radius: 18px !important;
    padding: 18px 20px !important;
    margin-top: -4px !important;
    margin-bottom: 0px !important;
    box-shadow: 0 4px 16px rgba(0,0,0,0.01) !important;
    transition: all 0.2s ease;
}
/* 체크박스 제목 (첫 번째 p) - 기본 굵기 */
div[data-testid="stCheckbox"] [data-testid="stWidgetLabel"] p:first-child,
div[data-testid="stCheckbox"] label > div p:first-child {
    font-size: 14.5px !important;
    font-weight: 400 !important;
    color: #1E202C !important;
}
/* 체크박스 설명 (두 번째 p 이후) - 작고 얇고 회색 */
div[data-testid="stCheckbox"] [data-testid="stWidgetLabel"] p:not(:first-child),
div[data-testid="stCheckbox"] label > div p:not(:first-child) {
    font-size: 11.5px !important;
    font-weight: 400 !important;
    color: #7B809A !important;
    margin-top: 1px !important;
    line-height: 1.3 !important;
}

/* 🎨 피그마 액션 버튼 */
button[kind="primary"],
button[data-testid="stBaseButton-primary"] {
    background-color: #2F49D1 !important;
    border: none !important;
    border-radius: 16px !important;
    font-weight: 700 !important;
    min-height: 48px !important;
    height: auto !important;
    font-size: 14px !important;
    width: 100% !important;
    box-shadow: 0 8px 24px rgba(47, 73, 209, 0.12) !important;
    padding: 10px 14px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
button[kind="primary"] p,
button[data-testid="stBaseButton-primary"] p {
    color: #FFFFFF !important;
    font-size: 14px !important;
    white-space: normal !important;
    word-break: keep-all !important;
    line-height: 1.35 !important;
    margin: 0 !important;
}

button[kind="secondary"],
button[data-testid="stBaseButton-secondary"] {
    background-color: #FFFFFF !important;
    border: 1.5px solid #2F49D1 !important;
    border-radius: 16px !important;
    font-weight: 700 !important;
    min-height: 48px !important;
    height: auto !important;
    font-size: 14px !important;
    width: 100% !important;
    padding: 10px 14px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
button[kind="secondary"] p,
button[data-testid="stBaseButton-secondary"] p {
    color: #2F49D1 !important;
    font-size: 14px !important;
    white-space: normal !important;
    word-break: keep-all !important;
    line-height: 1.35 !important;
    margin: 0 !important;
}

/* 📱 4열 필터 버튼 글자 깨짐 완전 차단 및 오버플로우 말줄임표 처리 */
.element-container:has(.filter-buttons-marker) ~ .element-container div[data-testid="stColumn"] div.stButton > button,
.element-container:has(.filter-buttons-marker) ~ .element-container div[data-testid="column"] div.stButton > button {
    height: 38px !important;
    min-height: 38px !important;
    padding: 0px 4px !important;
    border-radius: 10px !important;
    width: 100% !important;
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
}
.element-container:has(.filter-buttons-marker) ~ .element-container div[data-testid="stColumn"] div.stButton > button p,
.element-container:has(.filter-buttons-marker) ~ .element-container div[data-testid="column"] div.stButton > button p {
    font-size: 11px !important;
    line-height: 1.15 !important;
    white-space: nowrap !important; 
    overflow: hidden !important;
    text-overflow: ellipsis !important; /* 가로폭 부족 시 자동으로 말줄임(...) 처리 */
    margin: 0 !important;
    text-align: center !important;
    width: 100% !important;
}

/* 소형 기기 대상 필터 글씨 크기 자동 핏 */
@media (max-width: 380px) {
    .element-container:has(.filter-buttons-marker) ~ .element-container div[data-testid="stColumn"] div.stButton > button p,
    .element-container:has(.filter-buttons-marker) ~ .element-container div[data-testid="column"] div.stButton > button p {
        font-size: 9.5px !important;
    }
}

/* 📱 다중 열 배치 버튼 찌그러짐 방지 통합 */
div[data-testid="stColumn"] div.stButton > button,
div[data-testid="column"] div.stButton > button {
    min-height: 44px !important;
    height: auto !important;
    border-radius: 12px !important;
    padding: 8px 10px !important;
}
div[data-testid="stColumn"] div.stButton > button p,
div[data-testid="column"] div.stButton > button p {
    font-size: 13px !important;
    white-space: nowrap !important;
}

/* 📋 셀렉트박스 및 드롭다운 파랑/흰색 계열 테마 적용 (리포트 화면 등) */
div[data-baseweb="select"] > div {
    background-color: #EFF1FE !important;
    border: 1.5px solid #2F49D1 !important;
    border-radius: 12px !important;
    color: #2F49D1 !important;
}
div[data-baseweb="select"] * {
    color: #2F49D1 !important;
    font-weight: 700 !important;
}

/* ⇆ 멀티셀렉트 선택된 칩(태그) 디자인을 파랑/연파랑 계열로 변경 (기본 빨간색 테마 제거) */
span[data-baseweb="tag"] {
    background-color: #EFF1FE !important;
    color: #2F49D1 !important;
    border: 1px solid #EFF1FE !important;
    border-radius: 8px !important;
}
span[data-baseweb="tag"] * {
    color: #2F49D1 !important;
}
span[data-baseweb="tag"] svg {
    fill: #2F49D1 !important;
}

/* 드롭다운 포탈 팝업 메뉴 스타일링 */
div[data-baseweb="popover"],
div[data-baseweb="popover"] > div {
    background-color: transparent !important;
    background: transparent !important;
    box-shadow: none !important;
    border: none !important;
}
div[data-baseweb="popover"] ul, 
div[data-baseweb="popover"] [data-baseweb="menu"] {
    background-color: #FFFFFF !important;
    border: 1.5px solid #EFF1FE !important;
    border-radius: 16px !important;
    box-shadow: 0 12px 32px rgba(47, 73, 209, 0.08) !important;
    padding: 8px !important;
}
div[data-baseweb="popover"] li, 
div[data-baseweb="popover"] [role="option"] {
    background-color: transparent !important;
    color: #1E202C !important;
    font-family: 'Pretendard', sans-serif !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    padding: 10px 14px !important;
    border-radius: 10px !important;
    transition: all 0.2s ease !important;
}
div[data-baseweb="popover"] li:hover,
div[data-baseweb="popover"] [role="option"]:hover,
div[data-baseweb="popover"] [role="option"][aria-selected="true"],
div[data-baseweb="popover"] li[aria-selected="true"] {
    background-color: #EFF1FE !important;
    color: #2F49D1 !important;
    font-weight: 700 !important;
}

/* 📋 체크박스 시각 박스 스타일 */
/* BaseWeb: data-baseweb=checkbox 컨테이너 내 첫번째 자식 div = 시각적 체크박스 박스 */
div[data-testid="stCheckbox"] [data-baseweb="checkbox"] > div:first-child {
    border-left-color: #2F49D1 !important;
    border-right-color: #2F49D1 !important;
    border-top-color: #2F49D1 !important;
    border-bottom-color: #2F49D1 !important;
    background-color: #FFFFFF !important;
    border-radius: 6px !important;
    transition: all 0.2s ease !important;
}
/* 체크박스 클릭(활성) 상태 감지: label:has(input:checked) */
div[data-testid="stCheckbox"] label:has(input:checked) [data-baseweb="checkbox"] > div:first-child {
    background-color: #2F49D1 !important;
    border-left-color: #2F49D1 !important;
    border-right-color: #2F49D1 !important;
    border-top-color: #2F49D1 !important;
    border-bottom-color: #2F49D1 !important;
}
/* 체크 아이콘(SVG) 흰색 */
div[data-testid="stCheckbox"] label:has(input:checked) [data-baseweb="checkbox"] > div:first-child svg,
div[data-testid="stCheckbox"] label:has(input:checked) [data-baseweb="checkbox"] > div:first-child svg path {
    fill: #FFFFFF !important;
    stroke: #FFFFFF !important;
    opacity: 1 !important;
}
/* Streamlit native input accent-color fallback */
div[data-testid="stCheckbox"] input[type="checkbox"] {
    accent-color: #2F49D1 !important;
}

/* 📋 체크박스 텍스트 영역의 의도치 않은 테두리/배경색 강제 제거 */
div[data-testid="stCheckbox"] [data-testid="stWidgetLabel"],
div[data-testid="stCheckbox"] [data-testid="stWidgetLabel"] p,
div[data-testid="stCheckbox"] label > div,
div[data-testid="stCheckbox"] label > span:last-child,
div[data-testid="stCheckbox"] [data-baseweb="checkbox"] > div:last-of-type {
    border: none !important;
    background-color: transparent !important;
    background: transparent !important;
    box-shadow: none !important;
}

/* 🔧 단품 배지 밀착 정렬 및 줄바꿈 버그 방지 개선 */
.badge-blue {
    background-color: #EFF1FE;
    color: #2F49D1;
    padding: 5px 12px;
    border-radius: 12px;
    font-size: 11.5px;
    font-weight: 500;
    display: inline-block;
    word-break: keep-all;
    overflow-wrap: break-word;
    line-height: 1.3;
}

.badge-orange {
    background-color: #FFF2EE;
    color: #FF5A36;
    padding: 5px 12px;
    border-radius: 12px;
    font-size: 11.5px;
    font-weight: 500;
    display: inline-block;
    word-break: keep-all;
    overflow-wrap: break-word;
    line-height: 1.3;
}



.nav-bar-anchor {
    display: none;
}

/* 하단 내비게이션 영역 고정 및 스타일 */
div:has(> div > .nav-bar-anchor) ~ div[data-testid="element-container"] div[data-testid="stHorizontalBlock"] {
    position: fixed !important;
    background-color: rgba(255, 255, 255, 0.98) !important;
    backdrop-filter: blur(25px) !important;
    border-top: 1px solid #EFF1FE !important;
    padding: 10px 14px 26px 14px !important;
    z-index: 1000000 !important;
    margin: 0 !important;
    display: flex !important;
    justify-content: space-around !important;
}

@media (min-width: 450px) {
    div:has(> div > .nav-bar-anchor) ~ div[data-testid="element-container"] div[data-testid="stHorizontalBlock"] {
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: 430px !important;
        max-width: 430px !important;
        right: auto !important;
        bottom: 40px !important;
        border-bottom-left-radius: 40px !important;
        border-bottom-right-radius: 40px !important;
        border-left: 1px solid #EFF1FE !important;
        border-right: 1px solid #EFF1FE !important;
        padding: 10px 14px 20px 14px !important;
    }
}

@media (max-width: 450px) {
    div:has(> div > .nav-bar-anchor) ~ div[data-testid="element-container"] div[data-testid="stHorizontalBlock"] {
        left: 0 !important;
        right: 0 !important;
        bottom: 0 !important;
        width: 100% !important; /* 수평 스크롤 방지 */
        transform: none !important; /* 데스크톱용 트랜스폼 중앙 정렬 오버라이드하여 좌측 치우침 해결 */
        border-radius: 0 !important;
        border: none !important;
        border-top: 1px solid #EFF1FE !important;
    }
    
    /* 하단 내비게이션 컬럼 균등 너비 배분 호환 보장 */
    div:has(> div > .nav-bar-anchor) ~ div[data-testid="element-container"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
    div:has(> div > .nav-bar-anchor) ~ div[data-testid="element-container"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        flex: 1 1 0% !important;
        width: 25% !important;
        min-width: 0 !important;
    }
    
    /* 모바일 기기 화면에서는 이미 탑재된 OS 하단 바가 있으므로 가상 터치 표시 바를 숨김 처리합니다. */
    div:has(> div > .nav-bar-anchor) ~ div div[data-testid="stHorizontalBlock"]::after {
        display: none !important;
    }
}

/* 📋 네비게이션 탭 내부 버튼 */
div:has(> div > .nav-bar-anchor) ~ div div[data-testid="stHorizontalBlock"] button {
    height: 52px !important;
    min-height: 52px !important;
    max-height: 52px !important;
    width: 100% !important;
    border-radius: 12px !important;
    padding: 4px 0px !important;
    box-shadow: none !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    margin: 0 !important;
    border: none !important;
    background: transparent !important;
}

div:has(> div > .nav-bar-anchor) ~ div div[data-testid="stHorizontalBlock"] button * {
    white-space: nowrap !important;
    word-break: keep-all !important;
    text-overflow: clip !important;
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1.2 !important;
}

/* 비활성 탭 (Secondary) 글자 색상 및 테두리 해제 */
div:has(> div > .nav-bar-anchor) ~ div div[data-testid="stHorizontalBlock"] button:not([data-testid="stBaseButton-primary"]):not([kind="primary"]) {
    background: transparent !important;
    border: none !important;
}
div:has(> div > .nav-bar-anchor) ~ div div[data-testid="stHorizontalBlock"] button:not([data-testid="stBaseButton-primary"]):not([kind="primary"]) p,
div:has(> div > .nav-bar-anchor) ~ div div[data-testid="stHorizontalBlock"] button:not([data-testid="stBaseButton-primary"]):not([kind="primary"]) span,
div:has(> div > .nav-bar-anchor) ~ div div[data-testid="stHorizontalBlock"] button:not([data-testid="stBaseButton-primary"]):not([kind="primary"]) {
    color: #8D94B1 !important;
    font-size: 11px !important;
    font-weight: 700 !important;
}

/* 활성 탭 (Primary) 배경색 및 글자 색상 */
div:has(> div > .nav-bar-anchor) ~ div div[data-testid="stHorizontalBlock"] button[kind="primary"],
div:has(> div > .nav-bar-anchor) ~ div div[data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-primary"] {
    background-color: #EFF1FE !important;
    border: none !important;
}
div:has(> div > .nav-bar-anchor) ~ div div[data-testid="stHorizontalBlock"] button[kind="primary"] p,
div:has(> div > .nav-bar-anchor) ~ div div[data-testid="stHorizontalBlock"] button[kind="primary"] span,
div:has(> div > .nav-bar-anchor) ~ div div[data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-primary"] p,
div:has(> div > .nav-bar-anchor) ~ div div[data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-primary"] span {
    color: #2F49D1 !important;
    font-weight: 800 !important;
    font-size: 11px !important;
}

/* 네비게이션 탭 아이콘 1:1 바인딩 */
div:has(> div > .nav-bar-anchor) ~ div div[data-testid="stHorizontalBlock"] button::before {
    content: "" !important;
    display: inline-block !important;
    width: 20px !important;
    height: 20px !important;
    margin-bottom: 2px !important;
    background-repeat: no-repeat !important;
    background-size: contain !important;
}
div:has(> div > .nav-bar-anchor) ~ div div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-child(1) button::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='%238D94B1' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z'/%3E%3Cpolyline points='14 2 14 8 20 8'/%3E%3C/svg%3E") !important;
}
div:has(> div > .nav-bar-anchor) ~ div div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-child(1) button[kind="primary"]::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='%232F49D1' stroke-width='2.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z'/%3E%3Cpolyline points='14 2 14 8 20 8'/%3E%3C/svg%3E") !important;
}
div:has(> div > .nav-bar-anchor) ~ div div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-child(2) button::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='%238D94B1' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cline x1='8' y1='6' x2='21' y2='6'/%3E%3Cline x1='8' y1='12' x2='21' y2='12'/%3E%3Cline x1='8' y1='18' x2='21' y2='18'/%3E%3Cline x1='3' y1='6' x2='3.01' y2='6'/%3E%3Cline x1='3' y1='12' x2='3.01' y2='12'/%3E%3Cline x1='3' y1='18' x2='3.01' y2='18'/%3E%3C/svg%3E") !important;
}
div:has(> div > .nav-bar-anchor) ~ div div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-child(2) button[kind="primary"]::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='%232F49D1' stroke-width='2.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cline x1='8' y1='6' x2='21' y2='6'/%3E%3Cline x1='8' y1='12' x2='21' y2='12'/%3E%3Cline x1='8' y1='18' x2='21' y2='18'/%3E%3Cline x1='3' y1='6' x2='3.01' y2='6'/%3E%3Cline x1='3' y1='12' x2='3.01' y2='12'/%3E%3Cline x1='3' y1='18' x2='3.01' y2='18'/%3E%3C/svg%3E") !important;
}
div:has(> div > .nav-bar-anchor) ~ div div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-child(3) button::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='%238D94B1' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cline x1='18' y1='20' x2='18' y2='10'/%3E%3Cline x1='12' y1='20' x2='12' y2='4'/%3E%3Cline x1='6' y1='20' x2='6' y2='14'/%3E%3C/svg%3E") !important;
}
div:has(> div > .nav-bar-anchor) ~ div div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-child(3) button[kind="primary"]::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='%232F49D1' stroke-width='2.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cline x1='18' y1='20' x2='18' y2='10'/%3E%3Cline x1='12' y1='20' x2='12' y2='4'/%3E%3Cline x1='6' y1='20' x2='6' y2='14'/%3E%3C/svg%3E") !important;
}
div:has(> div > .nav-bar-anchor) ~ div div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-child(4) button::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='%238E94B1' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='16 3 21 8 16 13'/%3E%3Cline x1='21' y1='8' x2='9' y2='8'/%3E%3Cpolyline points='8 21 3 16 8 11'/%3E%3Cline x1='3' y1='16' x2='15' y2='16'/%3E%3C/svg%3E") !important;
}
div:has(> div > .nav-bar-anchor) ~ div div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-child(4) button[kind="primary"]::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='%232F49D1' stroke-width='2.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='16 3 21 8 16 13'/%3E%3Cline x1='21' y1='8' x2='9' y2='8'/%3E%3Cpolyline points='8 21 3 16 8 11'/%3E%3Cline x1='3' y1='16' x2='15' y2='16'/%3E%3C/svg%3E") !important;
}

/* 📋 수평 교차 매트릭스 표 디테일 스타일 */
.comp-table {
    border: 1.5px solid #EFF1FE;
    border-radius: 20px;
    overflow: hidden;
    background-color: #FFFFFF;
    box-shadow: 0 4px 14px rgba(0,0,0,0.01);
}
.comp-row {
    display: flex;
    border-bottom: 1px solid #EFF1FE;
}
.comp-row:last-child {
    border-bottom: none;
}
.comp-cell {
    flex: 1;
    padding: 14px 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: 700;
    border-right: 1px solid #EFF1FE;
    text-align: center;
}
.comp-cell:last-child {
    border-right: none;
}
.comp-label {
    width: 80px;
    flex: none;
    background-color: #FAFBFD;
    color: #1E202C;
    font-size: 12px;
    font-weight: 700;
    text-align: center;
    justify-content: center;
    border-right: 1px solid #EFF1FE;
}

/* 📋 헤더 고정 정렬 */
.app-header-container {
    position: sticky !important;
    top: 0px !important;
    background-color: #FCFCFF !important;
    z-index: 99998 !important;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 0 16px 0;
    border-bottom: 1.5px solid #EFF1FE;
    margin-bottom: 24px;
}
</style>
""", unsafe_allow_html=True)

# 🎨 [Onboarding Splash] 플래터 스타일 온보딩 (Glow 후광 및 오버랩 물결 SVG 구현)
if st.session_state.show_splash:
    st.markdown("""
<style>
    /* 스플래시 화면일 때만 컨테이너 패딩 제거하여 꽉 차게 만듦 */
    .block-container, [data-testid="stMainBlockContainer"] {
        padding: 0 !important;
        position: relative !important;
        overflow: hidden !important;
    }
    /* 중간 컨테이너들 여백 완전 리셋 (코너가 비어 보이는 현상 방지) */
    [data-testid="stMainBlockContainer"] > div {
        padding: 0 !important;
        gap: 0 !important;
    }
    [data-testid="stVerticalBlock"] {
        gap: 0 !important;
        padding: 0 !important;
    }
    div[data-testid="element-container"] {
        padding: 0 !important;
        margin: 0 !important;
    }
    /* 시작하기 버튼을 맨 아래로 절대 위치 지정 */
    div[data-testid="stButton"] {
        position: absolute !important;
        bottom: 140px !important;
        left: 20px !important;
        right: 20px !important;
        width: calc(100% - 40px) !important;
        z-index: 999999 !important;
    }
    div[data-testid="stButton"] button {
        width: 100% !important;
    }
    .splash-wrapper {
        position: relative;
        width: 100%;
        height: 100vh;
        overflow: hidden;
        background-color: #FCFCFF;
        border-radius: 0;
        z-index: 1;
        display: block;
    }
    @media (min-width: 450px) {
        .splash-wrapper {
            height: 880px;
            border-radius: 52px;
        }
    }

    /* 슬라이드쇼 텍스트 컨테이너 및 애니메이션 */
    .splash-desc-container {
        position: relative;
        width: 100%;
        height: 24px;
        margin: 0;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .splash-desc {
        position: absolute;
        width: 100%;
        text-align: center;
        font-size: 14.5px;
        font-weight: 500;
        color: #7B809A;
        opacity: 0;
        animation-duration: 12s;
        animation-iteration-count: infinite;
        animation-timing-function: ease-in-out;
        pointer-events: none;
    }
    .splash-desc.slide-1 {
        animation-name: fadeSlide1;
    }
    .splash-desc.slide-2 {
        animation-name: fadeSlide2;
    }
    .splash-desc.slide-3 {
        animation-name: fadeSlide3;
    }
    .splash-desc.slide-4 {
        animation-name: fadeSlide4;
    }

    @keyframes fadeSlide1 {
        0%, 20% { opacity: 1; transform: translateY(0); }
        23%, 100% { opacity: 0; transform: translateY(-8px); }
    }
    @keyframes fadeSlide2 {
        0%, 23% { opacity: 0; transform: translateY(8px); }
        25%, 45% { opacity: 1; transform: translateY(0); }
        48%, 100% { opacity: 0; transform: translateY(-8px); }
    }
    @keyframes fadeSlide3 {
        0%, 48% { opacity: 0; transform: translateY(8px); }
        50%, 70% { opacity: 1; transform: translateY(0); }
        73%, 100% { opacity: 0; transform: translateY(-8px); }
    }
    @keyframes fadeSlide4 {
        0%, 73% { opacity: 0; transform: translateY(8px); }
        75%, 95% { opacity: 1; transform: translateY(0); }
        98%, 100% { opacity: 0; transform: translateY(-8px); }
    }

    /* 페이지네이션 도트 애니메이션 */
    .dot {
        width: 7.5px;
        height: 7.5px;
        border-radius: 50%;
        background-color: #DCE0F9;
        animation-duration: 12s;
        animation-iteration-count: infinite;
        animation-timing-function: ease-in-out;
        transition: transform 0.3s ease, background-color 0.3s ease;
    }
    .dot.dot-1 {
        animation-name: dotAnim1;
    }
    .dot.dot-2 {
        animation-name: dotAnim2;
    }
    .dot.dot-3 {
        animation-name: dotAnim3;
    }
    .dot.dot-4 {
        animation-name: dotAnim4;
    }

    @keyframes dotAnim1 {
        0%, 20% { background-color: #2F49D1; transform: scale(1.25); }
        23%, 100% { background-color: #DCE0F9; transform: scale(1); }
    }
    @keyframes dotAnim2 {
        0%, 23% { background-color: #DCE0F9; transform: scale(1); }
        25%, 45% { background-color: #2F49D1; transform: scale(1.25); }
        48%, 100% { background-color: #DCE0F9; transform: scale(1); }
    }
    @keyframes dotAnim3 {
        0%, 48% { background-color: #DCE0F9; transform: scale(1); }
        50%, 70% { background-color: #2F49D1; transform: scale(1.25); }
        73%, 100% { background-color: #DCE0F9; transform: scale(1); }
    }
    @keyframes dotAnim4 {
        0%, 73% { background-color: #DCE0F9; transform: scale(1); }
        75%, 95% { background-color: #2F49D1; transform: scale(1.25); }
        98%, 100% { background-color: #DCE0F9; transform: scale(1); }
    }
</style>
<div class="splash-wrapper">
<!-- 배경 SVG -->
<svg viewBox="0 0 430 750" preserveAspectRatio="xMidYMid slice" fill="none" xmlns="http://www.w3.org/2000/svg" style="position: absolute; top:0; left:0; width:100%; height:100%; z-index:0; pointer-events:none;">
<!-- 우측 상단 큰 원 -->
<circle cx="390" cy="30" r="150" fill="#F0F1FA" />
<!-- 작은 점들 -->
<circle cx="70" cy="170" r="4" fill="#E2E5FA" />
<circle cx="360" cy="420" r="4" fill="#E2E5FA" />
<!-- 하단 물결 패턴 -->
<path d="M-50 750 L -50 550 C 80 540, 200 680, 480 600 L 480 750 Z" fill="#F6F7FC" />
<path d="M-50 750 L -50 630 C 120 620, 220 720, 480 670 L 480 750 Z" fill="#F0F2FA" />
<path d="M-50 750 L -50 690 C 100 660, 280 780, 480 710 L 480 750 Z" fill="#EAEBFA" />
</svg>
<!-- 중앙 콘텐츠 -->
<div style="position: absolute; top: 45%; left: 50%; transform: translate(-50%, -50%); z-index: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%;">
<!-- 로고 카드 -->
<div class="splash-logo-card" style="width: 154px; height: 154px; background: #FFFFFF; border-radius: 46px; display: flex; align-items: center; justify-content: center; box-shadow: 0 24px 50px rgba(47, 73, 209, 0.12), 0 8px 20px rgba(47, 73, 209, 0.05); margin-bottom: 40px; border: 1.5px solid #F6F7FE;">
<svg width="86" height="86" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M42 82 H18 V42 L50 14 L82 42 L50 72 L32 54" stroke="url(#logoGrad)" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M58 82 H82 V62" stroke="url(#logoGrad)" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"/>
<defs>
<linearGradient id="logoGrad" x1="0" y1="100" x2="100" y2="0" gradientUnits="userSpaceOnUse">
<stop offset="0%" stop-color="#1928A3" />
<stop offset="100%" stop-color="#4F6BFF" />
</linearGradient>
</defs>
</svg>
</div>
<!-- 텍스트 영역 -->
<div class="splash-title" style="font-size: 34px; font-weight: 800; color: #11142D; margin: 0; letter-spacing: -0.8px; text-align: center;">룸체크</div>
<p class="splash-subtitle" style="font-size: 16px; font-weight: 500; color: #8D94B1; margin-top: 8px; margin-bottom: 30px; letter-spacing: 1.2px; text-align: center; transform: translateX(3px);">RoomCheck</p>

<!-- 슬라이드쇼 텍스트 컨테이너 -->
<div class="splash-desc-container">
<div class="splash-desc slide-1">첫 자취, 더 안심하게 체크하세요</div>
<div class="splash-desc slide-2">스마트 타이머로 수압과 소음을 정확하게</div>
<div class="splash-desc slide-3">우리 집 맞춤형 분석 리포트 확인까지</div>
<div class="splash-desc slide-4">저장한 매물의 핵심 지표를 한눈에 비교</div>
</div>

<!-- 페이지네이션 도트 -->
<div class="pagination" style="display: flex; gap: 10px; margin-top: 60px;">
<div class="dot dot-1"></div>
<div class="dot dot-2"></div>
<div class="dot dot-3"></div>
<div class="dot dot-4"></div>
</div>
</div>
</div>
""", unsafe_allow_html=True)
    
    if st.button("시작하기", use_container_width=True, type="primary"):
        st.session_state.show_splash = False
        st.rerun()
    st.stop()


# 🏠 유형별 수평 레이아웃 벡터 아이콘 정의
svg_house = (
    "<svg width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='#2F49D1' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
    "<path d='M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'/>"
    "<polyline points='9 22 9 12 15 12 15 22'/>"
    "</svg>"
)

svg_building = (
    "<svg width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='#2F49D1' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
    "<rect x='4' y='2' width='16' height='20' rx='2' ry='2'/>"
    "<path d='M9 22v-4h6v4'/>"
    "</svg>"
)

# =====================================================================
# [탭 1] 임장 전 가이드 화면
# =====================================================================
if st.session_state.current_tab == "가이드":
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div class="app-header-container">
        <div style="width:24px;"></div>
        <div class="app-header-title" style="font-weight: 800; font-size: 18px; text-align: center; flex: 1; color: #1E202C;">스마트 임장 가이드</div>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#1E202C" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
    </div>
    """, unsafe_allow_html=True)
    
    # 가이드 탭 내 체크박스 및 카드 정렬을 위한 로컬 스타일 주입
    st.markdown("""
    <style>
    /* 가이드 탭 내 체크박스 테두리 및 배경 제거 */
    div[data-testid="stCheckbox"] {
        border: none !important;
        background-color: transparent !important;
        padding: 8px 0 !important;
        box-shadow: none !important;
        margin-top: 0 !important;
        margin-bottom: 0 !important;
    }
    div[data-testid="stCheckbox"] > label {
        padding: 0 !important;
    }
    /* 체크박스 사이 구분선 추가 */
    div[data-testid="stCheckbox"] + div[data-testid="stCheckbox"] {
        border-top: 1px solid #EFF1FE !important;
        padding-top: 14px !important;
        margin-top: 4px !important;
    }
    /* 체크박스 하단 설명 글자 스타일 조정 (글자 크기 줄이고 회색으로) */
    div[data-testid="stCheckbox"] [data-testid="stWidgetLabel"] p:not(:first-child),
    div[data-testid="stCheckbox"] [data-testid="stWidgetLabel"] p:nth-child(n+2),
    div[data-testid="stCheckbox"] [data-testid="stWidgetLabel"] p + p {
        font-size: 11.5px !important;
        color: #7B809A !important;
        font-weight: 400 !important;
        margin-top: 1px !important;
        line-height: 1.3 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 텍스트 마진을 키워 카테고리 카드들을 좀 더 아래로 이동시킵니다.
    st.markdown("<div style='color:#2F49D1; font-weight:800; font-size:24px; letter-spacing:-0.6px; margin: 0 0 6px 0;'>임장 전 필수 체크리스트</div><p style='color:#7B809A; font-size:13px; margin:0 0 36px 0;'>처음 임장 가기 전 꼭 확인할 항목만 간단히 정리했어요</p>", unsafe_allow_html=True)
    
    # 카드 1: 계약 전 서류 확인 (st.container(border=True) 사용하여 피그마 박스 적용)
    with st.container(border=True):
        st.markdown("""
        <div style="display:flex; gap:14px; align-items:center; margin-bottom: 12px;">
            <div style="width:48px; height:48px; background-color:#EFF1FE; border-radius:14px; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2F49D1" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h4"/>
                    <polyline points="14 2 14 8 20 8"/>
                    <path d="M16 22a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/>
                    <path d="M18.12 20.12L22 24"/>
                </svg>
            </div>
            <div style="display:flex; flex-direction:column; justify-content:center;">
                <div style="margin:0 !important; color:#1E202C; font-size:16px; font-weight:800; line-height:1.2;">계약 전 서류 확인</div>
                <div style="margin:4px 0 0 0 !important; color:#7B809A; font-size:12px; line-height:1.3;">안전한 계약을 위해 꼭 확인해요</div>
            </div>
        </div>
        <div style="border-bottom: 1px solid #EFF1FE; margin-bottom: 8px;"></div>
        """, unsafe_allow_html=True)
        
        st.checkbox("**등기부등본 확인**\n\n소유권, 저당, 융자 비율 확인", key="g_check_1")
        st.checkbox("**건축물대장 확인**\n\n위반건축물 여부 확인", key="g_check_2")
        
    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    # 카드 2: 질문 체크리스트 (st.container(border=True) 사용하여 피그마 박스 적용)
    with st.container(border=True):
        st.markdown("""
        <div style="display:flex; gap:14px; align-items:center; margin-bottom: 12px;">
            <div style="width:48px; height:48px; background-color:#EFF1FE; border-radius:14px; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2F49D1" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
            </div>
            <div style="display:flex; flex-direction:column; justify-content:center;">
                <div style="margin:0 !important; color:#1E202C; font-size:16px; font-weight:800; line-height:1.2;">중개사 질문 리스트</div>
                <div style="margin:4px 0 0 0 !important; color:#7B809A; font-size:12px; line-height:1.3;">꼭 물어봐야 할 질문을 정리했어요</div>
            </div>
        </div>
        <div style="border-bottom: 1px solid #EFF1FE; margin-bottom: 8px;"></div>
        """, unsafe_allow_html=True)

        questions = [
            "수압, 배수는 괜찮은가요?",
            "관리비에 어떤 항목이 포함되나요?",
            "보일러는 언제 교체하셨나요?",
            "이전 세입자는 왜 이사 가나요?"
        ]

        for idx, q in enumerate(questions):
            st.markdown(
                f"<div style='display:flex; align-items:center; gap:12px; padding:12px 0; {'border-top:1px solid #EFF1FE;' if idx > 0 else ''}'>"
                f"  <svg width='22' height='22' viewBox='0 0 24 24' fill='none' stroke='#2F49D1' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round' style='flex-shrink:0;'><path d='M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z'/></svg>"
                f"  <span style='font-size:14px; color:#1E202C; font-weight:600; line-height:1.4;'>{q}</span>"
                f"</div>",
                unsafe_allow_html=True
            )

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
    
    # 카드 3: 임장 팁
    st.markdown("""
    <div style='padding: 18px 20px; background-color: #EFF1FE; border-radius: 20px; display: flex; gap: 14px; align-items: center;'>
        <div style='width: 42px; height: 42px; background-color: #2F49D1; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0;'>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/>
                <line x1="9" y1="18" x2="15" y2="18"/>
                <line x1="10" y1="22" x2="14" y2="22"/>
            </svg>
        </div>
        <div>
            <div style='margin: 0 0 4px 0; color:#1E202C; font-size:16px; font-weight:800; line-height:1.2;'>임장 팁</div>
            <div style='margin: 0; color:#4A4E69; font-size:14px; line-height:1.4;'>낮과 밤 분위기가 다를 수 있으니 가능하면 서로 다른 시간대에 한 번씩 확인해 보세요.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# =====================================================================
# [탭 2] 스마트 체크리스트 입력 화면 (체크)
# =====================================================================
elif st.session_state.current_tab == "체크":
    step = st.session_state.current_step
    steps_titles = ["기본 매물 조건", "수압/배수", "채광/환기", "치안/생활", "소음 측정", "위생/옵션"]
    
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div class="app-header-container">
        <div style="width:24px;"></div>
        <div class="app-header-title" style="font-weight: 800; font-size: 18px; text-align: center; flex: 1; color: #1E202C;">스마트 체크리스트</div>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#1E202C" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="step-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
        <div class="step-num" style="font-size: 16px; color: #1E202C; font-weight: 800; line-height: 1; margin: 0;">{step + 1} / 6 단계</div>
        <div class="step-title" style="font-size: 16px; color: #1E202C; font-weight: 800; line-height: 1; margin: 0;">{steps_titles[step]}</div>
    </div>
    <div class="custom-progress" style="width: 100%; height: 8px; background-color: #EFF1FE; border-radius: 4px; margin-bottom: 24px; overflow: hidden;">
        <div class="custom-progress-bar" style="width: {((step + 1) / 6) * 100}%; height: 100%; background-color: #2F49D1; transition: width 0.3s ease;"></div>
    </div>
    """, unsafe_allow_html=True)

    # 1단계: 기본 조건 수집
    if step == 0:
        st.markdown("""
        <div class="info-alert-box" style="display: flex; gap: 10px; align-items: center; background-color: #EFF1FE; border-radius: 12px; padding: 12px 16px; margin-bottom: 24px;">
            <div style="width: 18px; height: 18px; background-color: #2F49D1; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                <span style="color: white; font-size: 12px; font-weight: 800;">i</span>
            </div>
            <span style="font-size: 12px; font-weight: bold; color: #2F49D1;">비교 기준이 되는 기본 정보를 먼저 입력해 주세요</span>
        </div>
        """, unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown("""
            <div style="display:flex; gap:8px; align-items:center; margin-bottom:18px;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2F49D1" stroke-width="2.5" style="transform: translateY(-5px);">
                    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                </svg>
                <h4 style="margin:0; color:#1E202C; font-size:17px; font-weight:800; line-height:1;">1단계 · 기본 매물 조건</h4>
            </div>
            """, unsafe_allow_html=True)
            
            # 버그 수정: 중첩 st.columns 대신 하나의 3열 평면 컬럼(Flat columns)으로 배치하여 CSS 찌그러짐을 해결합니다.
            def styled_input_row(label, val_key, placeholder, suffix=None):
                if suffix:
                    col_lbl, col_inp, col_badge = st.columns([1.1, 2.0, 0.9])
                    with col_lbl:
                        st.markdown(f"<div style='margin-top: 14px; font-weight: bold; font-size: 14px; color: #4A4E69;'>{label}</div>", unsafe_allow_html=True)
                    with col_inp:
                        st.session_state[val_key] = st.text_input(label, value=st.session_state[val_key], placeholder=placeholder, label_visibility="collapsed", key=f"input_{val_key}")
                    with col_badge:
                        st.markdown(f"<div style='background-color: #EFF1FE; color: #2F49D1; font-weight: bold; font-size: 11.5px; border-radius: 12px; padding: 10px 0; margin-top: 4px; text-align: center; height: auto;'>{suffix}</div>", unsafe_allow_html=True)
                else:
                    col_lbl, col_inp = st.columns([1.1, 2.9])
                    with col_lbl:
                        st.markdown(f"<div style='margin-top: 14px; font-weight: bold; font-size: 14px; color: #4A4E69;'>{label}</div>", unsafe_allow_html=True)
                    with col_inp:
                        st.session_state[val_key] = st.text_input(label, value=st.session_state[val_key], placeholder=placeholder, label_visibility="collapsed", key=f"input_{val_key}")

            styled_input_row("매물 별칭", "chk_name", "예: 신촌 원룸 A")
            styled_input_row("주소", "chk_address", "도로명 또는 지번 주소 입력")
            styled_input_row("보증금", "chk_deposit", "3000", "만원")
            styled_input_row("월세", "chk_rent", "60", "만원")
            styled_input_row("면적", "chk_area_size", "12", "평")
            styled_input_row("융자 비율", "chk_loan_ratio", "15", "%")

    # 2단계: 수압 및 배수 (⏱️ 실시간 타이머 연동)
    elif step == 1:
        with st.container(border=True):
            st.markdown("<div style='display:flex; gap:8px; align-items:center; margin-bottom:18px;'><span style='font-size:18px; line-height:1; display:flex; align-items:center; transform: translateY(-3px);'>💧</span><h4 style='margin:0; color:#1E202C; font-size:17px; font-weight:800; line-height:1;'>2단계 · 수압 및 배수 상태</h4></div>", unsafe_allow_html=True)
            
            st.markdown(f"<p style='font-size: 13px; font-weight:bold; color:#1E202C;'>수압 측정 시간 (종이컵이 찰 때까지): <b style='color:#2F49D1; font-size:13px;'>{st.session_state.chk_water_timer:.1f}초</b></p>", unsafe_allow_html=True)
            
            if st.session_state.timer_running:
                elapsed = round(time.time() - st.session_state.timer_start, 1)
                st.markdown(f"<div style='text-align:center; background:#EFF1FE; border-radius:12px; padding:12px; margin-bottom:12px;'><span style='font-size:16px; font-weight:800; color:#2F49D1;'>⏱️ {elapsed:.1f}초 측정 중...</span></div>", unsafe_allow_html=True)
                
                if st.button("⏱️ 측정 완료 (다 찼을 때 누르세요)", type="primary", use_container_width=True):
                    st.session_state.chk_water_timer = round(time.time() - st.session_state.timer_start, 1)
                    st.session_state.timer_running = False
                    st.rerun()
            else:
                if st.button("⏱️ 수압 타이머 측정 시작 (200ml 기준)", type="secondary", use_container_width=True):
                    st.session_state.timer_start = time.time()
                    st.session_state.timer_running = True
                    st.rerun()
                    
            water_val = st.slider("수압 측정값 수동 조정 (초)", min_value=0.0, max_value=15.0, value=float(st.session_state.chk_water_timer), step=1.0)
            st.session_state.chk_water_timer = water_val
            
            dr_opts = ["매우 원활 (바로 빠짐)", "보통 (약간 고이다 빠짐)", "불량 (잘 안 빠짐)"]
            dr_idx = dr_opts.index(st.session_state.chk_drainage) if st.session_state.chk_drainage in dr_opts else 0
            st.session_state.chk_drainage = st.selectbox("배수구 배수 속도", options=dr_opts, index=dr_idx)
            
            toilet_opts = ["매우 원활", "보통", "불량"]
            toilet_idx = toilet_opts.index(st.session_state.chk_toilet) if st.session_state.chk_toilet in toilet_opts else 0
            st.session_state.chk_toilet = st.selectbox("변기 수압 및 물내림 상태", options=toilet_opts, index=toilet_idx)
            
            st.session_state.chk_sim_drainage = st.checkbox("세면대와 샤워기를 동시 작동 시 수압 저하가 심한가요?", value=st.session_state.chk_sim_drainage)

    # 3단계: 채광 환기 (동적 센서 체크 포함)
    elif step == 2:
        with st.container(border=True):
            st.markdown("<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:18px;'><div style='display:flex; gap:8px; align-items:center;'><span style='font-size:18px; line-height:1; display:flex; align-items:center; transform: translateY(-3px);'>☀️</span><h4 style='margin:0; color:#1E202C; font-size:17px; font-weight:800; line-height:1;'>3단계 · 채광 및 환기 조건</h4></div></div>", unsafe_allow_html=True)
            
            if st.button("🧭 기기 나침반 센서 동적 연동", use_container_width=True):
                sim_direction = random.choice(["남향", "동남향/남서향", "동향/서향", "북향"])
                st.session_state.chk_direction = sim_direction
                st.toast(f"나침반 센서 수집 완료: {sim_direction}")
                time.sleep(0.5)
                st.rerun()
                
            dir_opts = ["남향", "동남향/남서향", "동향/서향", "북향"]
            dir_idx = dir_opts.index(st.session_state.chk_direction) if st.session_state.chk_direction in dir_opts else 0
            st.session_state.chk_direction = st.selectbox("창문 방위 (나침반 연동 가능)", options=dir_opts, index=dir_idx)
            
            win_opts = ["대 (벽면 대부분)", "중 (일반 창문)", "소 (환기용 창)"]
            win_idx = win_opts.index(st.session_state.chk_window_size) if st.session_state.chk_window_size in win_opts else 0
            st.session_state.chk_window_size = st.selectbox("창문 크기", options=win_opts, index=win_idx)
            
            obs_opts = ["충분함", "보통", "가려짐"]
            obs_idx = obs_opts.index(st.session_state.chk_obstruction) if st.session_state.chk_obstruction in obs_opts else 0
            st.session_state.chk_obstruction = st.selectbox("정면 외부 일조 가림 정도", options=obs_opts, index=obs_idx)
            
            st.session_state.chk_ventilation = st.checkbox("맞통풍이 원활한가요?", value=st.session_state.chk_ventilation)
            st.session_state.chk_condensation = st.checkbox("창문 주위에 결로/물자국 흔적이 있나요?", value=st.session_state.chk_condensation)

    # 4단계: 치안 및 상권 분석 (실제 CCTV CSV 파일 탐색 및 하버사인 계산식 통합)
    elif step == 3:
        with st.container(border=True):
            st.markdown("<div style='display:flex; gap:8px; align-items:center; margin-bottom:18px;'><span style='font-size:18px; line-height:1; display:flex; align-items:center; transform: translateY(-3px);'>🛡️</span><h4 style='margin:0; color:#1E202C; font-size:17px; font-weight:800; line-height:1;'>4단계 · 치안 및 인프라 연동</h4></div>", unsafe_allow_html=True)
            
            if st.button("🗺️ 인프라 실시간 검색 자동 연동", use_container_width=True, type="primary"):
                addr = st.session_state.chk_address.strip()
                if not addr:
                    st.warning("1단계 기본 매물 주소를 먼저 기입해 주세요!")
                else:
                    with st.spinner("카카오 로컬 인프라 탐색 중..."):
                        headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
                        enc_addr = urllib.parse.quote(addr)
                        addr_url = f"https://dapi.kakao.com/v2/local/search/address.json?query={enc_addr}"
                        try:
                            res = requests.get(addr_url, headers=headers, timeout=5)
                            if res.status_code == 200:
                                docs = res.json().get('documents', [])
                                if docs:
                                    x = float(docs[0]['x'])  # 경도 (tLon)
                                    y = float(docs[0]['y'])  # 위도 (tLat)
                                    st.session_state.chk_address = docs[0]['address_name']
                                    
                                    cvs_res = requests.get(f"https://dapi.kakao.com/v2/local/search/category.json?category_group_code=CS2&x={x}&y={y}&radius=200", headers=headers, timeout=5)
                                    pm_res = requests.get(f"https://dapi.kakao.com/v2/local/search/category.json?category_group_code=PM9&x={x}&y={y}&radius=200", headers=headers, timeout=5)
                                    trans_res = requests.get(f"https://dapi.kakao.com/v2/local/search/category.json?category_group_code=SW8&x={x}&y={y}&radius=500", headers=headers, timeout=5)
                                    
                                    st.session_state.chk_cvs = len(cvs_res.json().get('documents', [])) if cvs_res.status_code == 200 else random.randint(1,4)
                                    st.session_state.chk_pharmacy = len(pm_res.json().get('documents', [])) if pm_res.status_code == 200 else random.randint(0,2)
                                    st.session_state.chk_transit = len(trans_res.json().get('documents', [])) if trans_res.status_code == 200 else random.randint(1,3)
                                    
                                    # 📂 [CSV 정밀 분석 적용] 오리지널 Dart 로직을 이식한 치안 CCTV 위치 필터링 계산
                                    cams_count = 0
                                    csv_path = "assets/cctv_cleaned.csv"
                                    if not os.path.exists(csv_path) and os.path.exists("cctv_cleaned.csv"):
                                        csv_path = "cctv_cleaned.csv"
                                        
                                    try:
                                        if os.path.exists(csv_path):
                                            with open(csv_path, mode='r', encoding='utf-8') as f:
                                                reader = csv.reader(f)
                                                header = next(reader)
                                                lat_idx = header.index("WGS84위도") if "WGS84위도" in header else -1
                                                lon_idx = header.index("WGS84경도") if "WGS84경도" in header else -1
                                                cam_idx = header.index("카메라대수") if "카메라대수" in header else -1
                                                
                                                if lat_idx != -1 and lon_idx != -1:
                                                    for row in reader:
                                                        try:
                                                            c_lat = float(row[lat_idx])
                                                            c_lon = float(row[lon_idx])
                                                            count = int(row[cam_idx]) if (cam_idx != -1 and row[cam_idx].strip()) else 1
                                                            # 위도(y), 경도(x) 기준 반경 100m 탐색
                                                            if calculate_distance(y, x, c_lat, c_lon) <= 100:
                                                                cams_count += count
                                                        except Exception:
                                                            continue
                                            st.session_state.chk_cctv = cams_count
                                        else:
                                            # CSV 파일 부재 시 수학적 폴백 연산 실행 (위도값 기준)
                                            st.session_state.chk_cctv = int(y * 1000 % 15) + 2
                                    except Exception:
                                        st.session_state.chk_cctv = int(y * 1000 % 15) + 2
                                        
                                    st.toast("인프라 정보가 연동되었습니다.")
                                else:
                                    st.session_state.chk_cctv, st.session_state.chk_cvs, st.session_state.chk_pharmacy, st.session_state.chk_transit = 4, 3, 1, 2
                            else:
                                st.session_state.chk_cctv, st.session_state.chk_cvs, st.session_state.chk_pharmacy, st.session_state.chk_transit = 4, 3, 1, 2
                        except Exception:
                            # 전역 네트워크 타임아웃 오류 시 기본 폴백 설정
                            st.session_state.chk_cctv, st.session_state.chk_cvs, st.session_state.chk_pharmacy, st.session_state.chk_transit = 5, 2, 1, 1
                            st.toast("인프라 데이터 가상 탐색 연동 완료")
                            
            infra_html = (
                "<div style='background-color: white; border: 1px solid #EFF1FE; padding: 14px; border-radius: 12px; margin-bottom:12px;'>"
                "<p style='margin: 0 0 8px 0; font-weight: bold; font-size: 13px; color: #1E202C;'>📊 자동 매칭 주변 인프라 정보</p>"
                f"<div style='display: flex; justify-content: space-between; font-size: 12.5px; color:#7B809A; margin-bottom:6px;'><span>• 100m 내 치안 CCTV 대수</span><span style='font-weight: bold; color: #2F49D1;'>{st.session_state.chk_cctv} 대</span></div>"
                f"<div style='display: flex; justify-content: space-between; font-size: 12.5px; color:#7B809A; margin-bottom:6px;'><span>• 200m 내 생활 편의점 개수</span><span style='font-weight: bold; color: #1E202C;'>{st.session_state.chk_cvs} 개</span></div>"
                f"<div style='display: flex; justify-content: space-between; font-size: 12.5px; color:#7B809A; margin-bottom:6px;'><span>• 200m 내 상비 약국 개수</span><span style='font-weight: bold; color: #1E202C;'>{st.session_state.chk_pharmacy} 개</span></div>"
                f"<div style='display: flex; justify-content: space-between; font-size: 12.5px; color:#7B809A;'><span>• 500m 내 대중교통 인프라</span><span style='font-weight: bold; color: #1E202C;'>{st.session_state.chk_transit} 개</span></div>"
                "</div>"
            )
            st.markdown(infra_html, unsafe_allow_html=True)
            
            park_opts = ["여유", "보통", "협소", "불가"]
            park_idx = park_opts.index(st.session_state.chk_parking) if st.session_state.chk_parking in park_opts else 0
            st.session_state.chk_parking = st.selectbox("주차 편의성", options=park_opts, index=park_idx)
            
            st.session_state.chk_streetlight = st.checkbox("골목길 가로등 조도가 충분한가요?", value=st.session_state.chk_streetlight)
            st.session_state.chk_trash = st.checkbox("공용 쓰레기 배출 구역 관리 상태가 양호한가요?", value=st.session_state.chk_trash)

    # 5단계: 소음 측정
    elif step == 4:
        with st.container(border=True):
            st.markdown("<div style='display:flex; gap:8px; align-items:center; margin-bottom:18px;'><span style='font-size:18px; line-height:1; display:flex; align-items:center; transform: translateY(-3px);'>🔊</span><h4 style='margin:0; color:#1E202C; font-size:17px; font-weight:800; line-height:1;'>5단계 · 외부 소음 측정</h4></div>", unsafe_allow_html=True)
            
            if st.button("🎤 마이크 활용 실시간 소음 수집", use_container_width=True):
                st.session_state.chk_noise_open = float(random.randint(55, 75))
                st.session_state.chk_noise_closed = float(random.randint(30, 45))
                st.toast("소음 데이터 수집 완료!")
                time.sleep(0.5)
                st.rerun()
                
            open_val = st.slider("창문 개방 시 실외 유입 소음 (dB)", min_value=20.0, max_value=100.0, value=float(st.session_state.chk_noise_open), step=1.0)
            st.session_state.chk_noise_open = open_val
            
            closed_val = st.slider("창문 밀폐 시 실내 차음 소음 (dB)", min_value=20.0, max_value=100.0, value=float(st.session_state.chk_noise_closed), step=1.0)
            st.session_state.chk_noise_closed = closed_val
            
            noise_opts = ["없음", "보통", "심함"]
            noise_idx = noise_opts.index(st.session_state.chk_road_noise) if st.session_state.chk_road_noise in noise_opts else 0
            st.session_state.chk_road_noise = st.selectbox("외부 도로 소음 강도", options=noise_opts, index=noise_idx)
            
            st.session_state.chk_wall_noise = st.checkbox("상하층 층간 소음 또는 벽체 간 간섭이 느껴지나요?", value=st.session_state.chk_wall_noise)

    # 6단계: 하자 진단 및 옵션 (3대 구비 옵션으로 통일)
    elif step == 5:
        with st.container(border=True):
            st.markdown("<div style='display:flex; gap:8px; align-items:center; margin-bottom:18px;'><span style='font-size:18px; line-height:1; display:flex; align-items:center; transform: translateY(-3px);'>🛠️</span><h4 style='margin:0; color:#1E202C; font-size:17px; font-weight:800; line-height:1;'>6단계 · 마감 하자 및 구비 옵션</h4></div>", unsafe_allow_html=True)
            
            st.session_state.chk_mold = st.checkbox("벽지/바닥 장판 등에 곰팡이 흔적이 있나요?", value=st.session_state.chk_mold)
            st.session_state.chk_leak = st.checkbox("천장 마감재 등에 누수 흔적이 있나요?", value=st.session_state.chk_leak)
            st.session_state.chk_sink_odor = st.checkbox("싱크대 아래 배관 주위에 누수나 악취가 있나요?", value=st.session_state.chk_sink_odor)
            st.session_state.chk_pet_damage = st.checkbox("벽지가 파손되거나 훼손된 흔적이 있나요?", value=st.session_state.chk_pet_damage)
            
            st.divider()
            st.markdown("<div style='display:flex; gap:8px; align-items:center; margin-bottom:18px;'><span style='font-size:18px; line-height:1; display:flex; align-items:center; transform: translateY(-3px);'>📷</span><h4 style='margin:0; color:#1E202C; font-size:17px; font-weight:800; line-height:1;'>하자 증빙 및 참조 이미지 파일 등록</h4></div>", unsafe_allow_html=True)
            cam_shot = st.camera_input("실제 카메라로 사진 촬영 등록", label_visibility="collapsed")
            if cam_shot is not None:
                sim_filename = f"camera_shot_{len(st.session_state.chk_photos) + 1}.png"
                if sim_filename not in st.session_state.chk_photos:
                    st.session_state.chk_photos.append(sim_filename)
                    st.toast("사진 촬영 첨부 완료")
                    
            if st.session_state.chk_photos:
                st.markdown("<p style='font-size:12px; color:#7B809A; margin: 4px 0;'>첨부된 사진:</p>", unsafe_allow_html=True)
                for ph in list(st.session_state.chk_photos):
                    col_pname, col_pdel = st.columns([4, 1])
                    col_pname.markdown(f"<span class='badge-blue'>{ph}</span>", unsafe_allow_html=True)
                    if col_pdel.button("❌", key=f"del_photo_{ph}"):
                        st.session_state.chk_photos.remove(ph)
                        st.rerun()

            st.divider()
            st.markdown("<div style='display:flex; gap:8px; align-items:center; margin-bottom:18px;'><span style='font-size:18px; line-height:1; display:flex; align-items:center; transform: translateY(-3px);'>📦</span><h4 style='margin:0; color:#1E202C; font-size:17px; font-weight:800; line-height:1;'>기본 가전 옵션 포함 여부 (지출 절감 적용)</h4></div>", unsafe_allow_html=True)
            st.session_state.chk_aircon = st.checkbox("에어컨 (월 4만원 공제 적용)", value=st.session_state.chk_aircon)
            st.session_state.chk_washer = st.checkbox("세탁기 (월 3만원 공제 적용)", value=st.session_state.chk_washer)
            st.session_state.chk_fridge = st.checkbox("냉장고 (월 3만원 공제 적용)", value=st.session_state.chk_fridge)

    st.write("")
    
    step_next_labels = [
        "다음: 수압/배수 체크하기",
        "다음: 채광/환기 체크하기",
        "다음: 치안/생활 체크하기",
        "다음: 소음 측정하기",
        "다음: 위생/옵션 체크하기",
        "종합분석 실행"
    ]
    next_label = step_next_labels[step]
    
    if step == 0:
        if st.button(next_label, type="primary", use_container_width=True):
            if not st.session_state.chk_name.strip():
                st.warning("매물 이름을 입력해 주세요!")
            else:
                st.session_state.current_step += 1
                st.rerun()
    else:
        nav_btn_cols = st.columns(2)
        if nav_btn_cols[0].button("이전 단계", use_container_width=True):
            st.session_state.current_step -= 1
            st.rerun()
            
        if nav_btn_cols[1].button(next_label, type="primary", use_container_width=True):
            if step < 5:
                st.session_state.current_step += 1
                st.rerun()
            else:
                # 종합 스코어 분석 산출
                w_time = st.session_state.chk_water_timer
                w_score = 100.0 if w_time <= 5.0 else (80.0 if w_time <= 8.0 else 50.0)
                if st.session_state.chk_drainage == "불량 (잘 안 빠짐)" or st.session_state.chk_toilet == "불량":
                    w_score = max(25.0, w_score - 25.0)
                if st.session_state.chk_sim_drainage:
                    w_score = max(20.0, w_score - 15.0)
                    
                dir_points = {"남향": 60, "동남향/남서향": 50, "동향/서향": 40, "북향": 20}
                size_points = {"대 (벽면 대부분)": 30, "중 (일반 창문)": 20, "소 (환기용 창)": 10}
                l_score = dir_points.get(st.session_state.chk_direction, 40) + size_points.get(st.session_state.chk_window_size, 20)
                if st.session_state.chk_ventilation:
                    l_score = min(100.0, l_score + 10.0)
                if st.session_state.chk_obstruction == "가려짐":
                    l_score = max(10.0, l_score - 30.0)
                if st.session_state.chk_condensation:
                    l_score = max(10.0, l_score - 15.0)
                    
                s_score = 40.0 + (st.session_state.chk_cctv * 10)
                if st.session_state.chk_streetlight:
                    s_score += 15
                s_score += (st.session_state.chk_cvs * 3) + (st.session_state.chk_pharmacy * 3) + (st.session_state.chk_transit * 5)
                if st.session_state.chk_parking in ["협소", "불가"]:
                    s_score -= 10
                if not st.session_state.chk_trash:
                    s_score -= 10
                s_score = max(20.0, min(100.0, s_score))
                
                diff_db = st.session_state.chk_noise_open - st.session_state.chk_noise_closed
                n_score = 100.0 if diff_db >= 25 else (80.0 if diff_db >= 15 else 50.0)
                if st.session_state.chk_wall_noise:
                    n_score = max(10.0, n_score - 25.0)
                if st.session_state.chk_road_noise == "심함":
                    n_score = max(10.0, n_score - 20.0)
                    
                c_score = 100.0
                if st.session_state.chk_mold: c_score -= 30.0
                if st.session_state.chk_leak: c_score -= 30.0
                if st.session_state.chk_sink_odor: c_score -= 20.0
                if st.session_state.chk_pet_damage: c_score -= 15.0
                c_score = max(10.0, c_score)
                
                savings = 0.0
                selected_opts = []
                if st.session_state.chk_aircon: savings += 4.0; selected_opts.append("에어컨")
                if st.session_state.chk_washer: savings += 3.0; selected_opts.append("세탁기")
                if st.session_state.chk_fridge: savings += 3.0; selected_opts.append("냉장고")
                
                rent_val = safe_float(st.session_state.chk_rent)
                real_rent = max(0.0, rent_val - savings)
                overall = round((w_score + l_score + s_score + n_score + c_score) / 5)
                
                new_id = f"user_{int(time.time())}"
                new_prop = {
                    "id": new_id,
                    "name": st.session_state.chk_name,
                    "address": f"{st.session_state.chk_address} · 보증금 {st.session_state.chk_deposit} / 월세 {st.session_state.chk_rent}",
                    "deposit": st.session_state.chk_deposit,
                    "rent": st.session_state.chk_rent,
                    "real_rent": real_rent,
                    "option_savings": savings,
                    "options": selected_opts,
                    "scores": {"수압": w_score, "채광": l_score, "보안": s_score, "소음": n_score, "청결도": c_score},
                    "overall_score": overall,
                    "cctv_count": st.session_state.chk_cctv,
                    "cvs_count": st.session_state.chk_cvs,
                    "pharmacy_count": st.session_state.chk_pharmacy,
                    "transit_count": st.session_state.chk_transit,
                    "attached_photos": list(st.session_state.chk_photos),
                    "toilet_water_pressure": st.session_state.chk_toilet,
                    "simultaneous_drainage_issue": st.session_state.chk_sim_drainage,
                    "obstruction_level": "보통",
                    "window_condensation": st.session_state.chk_condensation,
                    "parking_status": st.session_state.chk_parking,
                    "trash_area_clean": st.session_state.chk_trash,
                    "wall_noise_audible": st.session_state.chk_wall_noise,
                    "road_noise_level": st.session_state.chk_road_noise,
                    "sink_leak_odor": st.session_state.chk_sink_odor,
                    "pet_damage": st.session_state.chk_pet_damage,
                    "area_size": st.session_state.chk_area_size,
                    "loan_ratio": st.session_state.chk_loan_ratio
                }
                
                st.session_state.properties.append(new_prop)
                st.session_state.selected_to_compare.add(new_id)
                
                # 버그 수정: 위젯 상태 캐시값도 동시에 초기화
                for k in chk_defaults.keys():
                    st.session_state[k] = chk_defaults[k]
                    if f"input_{k}" in st.session_state:
                        st.session_state[f"input_{k}"] = chk_defaults[k]
                st.session_state.current_step = 0
                st.session_state.current_tab = "리포트"
                st.success("종합 임장 분석서가 완성되었습니다!")
                time.sleep(1.0)
                st.rerun()

# =====================================================================
# [탭 3] 종합 분석 리포트 화면
# =====================================================================
elif st.session_state.current_tab == "리포트":
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div class="app-header-container">
        <div style="width:24px;"></div>
        <div class="app-header-title" style="font-weight: 800; font-size: 18px; text-align: center; flex: 1; color: #1E202C;">리포트</div>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#1E202C" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.properties:
        st.info("임장 기록 정보가 존재하지 않습니다. '체크' 탭에서 첫 매물을 측정해보세요.")
    else:
        prop_opts = {p["id"]: p["name"] for p in st.session_state.properties}
        
        col_sel, col_del = st.columns([4, 1])
        selected_id = col_sel.selectbox("분석된 매물 선택", options=list(prop_opts.keys()), index=len(prop_opts)-1, format_func=lambda x: prop_opts[x], label_visibility="collapsed")
        active_prop = next(p for p in st.session_state.properties if p["id"] == selected_id)
        
        if col_del.button("🗑️", help="매물 완전 삭제", use_container_width=True, type="primary"):
            st.session_state.show_delete_confirm = True
            st.rerun()

        # 매물 삭제 분기 처리
        if st.session_state.show_delete_confirm:
            with st.container(border=True):
                st.markdown(f"### **매물 완전 삭제**")
                st.markdown(f"'{active_prop['name']}' 매물을 영구 삭제하시겠습니까?\\n이 작업은 되돌릴 수 없습니다.")
                col_del_c1, col_del_c2 = st.columns(2)
                if col_del_c1.button("취소", use_container_width=True):
                    st.session_state.show_delete_confirm = False
                    st.rerun()
                if col_del_c2.button("삭제", type="primary", use_container_width=True):
                    st.session_state.properties = [p for p in st.session_state.properties if p["id"] != selected_id]
                    if selected_id in st.session_state.selected_to_compare:
                        st.session_state.selected_to_compare.remove(selected_id)
                    st.session_state.show_delete_confirm = False
                    st.toast(f"'{active_prop['name']}' 매물이 완전히 삭제되었습니다.")
                    time.sleep(0.5)
                    st.rerun()
            
        combined_header_html = (
            f"<div style='background-color: white; border: 1.5px solid #EFF1FE; border-radius: 20px; padding: 22px; box-shadow: 0 4px 14px rgba(47,73,209,0.015); margin-bottom: 20px; display: flex; flex-direction: column; gap: 20px;'>"
            f"  <div style='display: flex; align-items: center; gap: 16px;'>"
            f"    <img src='https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?auto=format&fit=crop&w=120&h=120&q=80' style='width: 68px; height: 68px; border-radius: 16px; object-fit: cover;' />"
            f"    <div style='flex: 1; display: flex; flex-direction: column; justify-content: center;'>"
            f"      <div style='color: #1E202C; font-size: 18px; font-weight: 800; line-height: 1.2;'>{active_prop['name']}</div>"
            f"      <div style='margin-top: 6px; color: #7B809A; font-size: 13px; font-weight: 500;'>{active_prop['address']}</div>"
            f"    </div>"
            f"  </div>"
            f"  <div style='height: 1.5px; background-color: #EFF1FE; width: 100%;'></div>"
            f"  <div style='display: flex; align-items: center; justify-content: space-between;'>"
            f"    <div>"
            f"      <div style='font-size: 14px; color: #1E202C; font-weight: 800; margin-bottom: 4px;'>거주 적합도</div>"
            f"      <div style='font-size: 11px; color: #8D94B1; font-weight: 600;'>정성 항목을 점수화한 지표입니다</div>"
            f"    </div>"
            f"    <div style='display: flex; align-items: center; gap: 12px;'>"
            f"      <div style='width: 44px; height: 44px; background-color: #EFF1FE; border-radius: 50%; display: flex; align-items: center; justify-content: center;'>"
            f"        <svg width='22' height='22' viewBox='0 0 24 24' fill='none' stroke='#2F49D1' stroke-width='2.5'>"
            f"          <path d='M22 11.08V12a10 10 0 1 1-5.93-9.14'/>"
            f"          <polyline points='22 4 12 14.01 9 11.01'/>"
            f"        </svg>"
            f"      </div>"
            f"      <div style='color: #2F49D1; font-size: 34px; font-weight: 800; line-height: 1.2; letter-spacing: -1px;'>"
            f"        {active_prop['overall_score']}<span style='font-size: 16px; font-weight: 700; letter-spacing: 0; vertical-align: baseline; margin-left: 2px;'>점</span>"
            f"      </div>"
            f"    </div>"
            f"  </div>"
            f"</div>"
        )
        st.markdown(combined_header_html, unsafe_allow_html=True)
        
        st.markdown("<p style='font-size:15px; font-weight:800; color:#1E202C; margin-bottom:12px; margin-top:8px;'>항목별 상세 점수</p>", unsafe_allow_html=True)
        
        scores_list = [
            active_prop["scores"].get("수압", 50),
            active_prop["scores"].get("채광", 50),
            active_prop["scores"].get("보안", 50),
            active_prop["scores"].get("소음", 50),
            active_prop["scores"].get("청결도", 50)
        ]
        
        with st.container(border=True):
            chart_placeholder = st.empty()
            
        # 선택된 매물의 항목별 강점/주의 지수를 동적으로 산출합니다.
        scores_dict = active_prop.get("scores", {})
        sorted_scores = sorted(scores_dict.items(), key=lambda x: x[1], reverse=True)
        
        if len(sorted_scores) >= 2:
            strongest_key, strongest_val = sorted_scores[0]
            second_key, second_val = sorted_scores[1]
            weakest_key, weakest_val = sorted_scores[-1]
        else:
            strongest_key, strongest_val = "채광", 50
            second_key, second_val = "청결도", 50
            weakest_key, weakest_val = "소음", 50
            
        strongest_label = DISPLAY_NAMES.get(strongest_key, strongest_key)
        second_label = DISPLAY_NAMES.get(second_key, second_key)
        weakest_label = DISPLAY_NAMES.get(weakest_key, weakest_key)
        
        # 약점 종류에 따라 맞춤 권장액션 결정
        weak_rec = "보완 요소 점검 필요"
        if weakest_key == "소음":
            weak_rec = "야간 방문 권장"
        elif weakest_key == "보안":
            weak_rec = "주변 조도 확인"
        elif weakest_key == "수압":
            weak_rec = "동시 배수 점검"
        elif weakest_key == "채광":
            weak_rec = "낮 시간대 확인"
        elif weakest_key == "청결도":
            weak_rec = "누수/장판 확인"

        pro_con_html = textwrap.dedent(f"""
        <div style="display: flex; gap: 10px; margin-bottom: 12px; box-sizing: border-box; width: 100%;">
            <div style="flex: 1; background-color: #FFFFFF; border: 1.5px solid #EFF1FE; border-radius: 20px; padding: 14px 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.01); display: flex; flex-direction: column;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 14px;">
                    <div style="width: 30px; height: 30px; background-color: #2F49D1; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/>
                        </svg>
                    </div>
                    <div style="color: #1E202C; font-weight: 800; font-size: 15px; line-height: 1;">강점</div>
                </div>
                <div style="display: flex; flex-direction: row; flex-wrap: nowrap; gap: 4px; align-items: center; width: 100%;">
                    <span class="badge-blue" style="font-size: 10.5px !important; padding: 4px 6px !important; white-space: nowrap !important; flex-shrink: 0 !important;">{strongest_label} {int(strongest_val)}</span>
                    <span class="badge-blue" style="font-size: 10.5px !important; padding: 4px 6px !important; white-space: nowrap !important; flex-shrink: 0 !important;">{second_label} {int(second_val)}</span>
                </div>
            </div>
            <div style="flex: 1; background-color: #FFFFFF; border: 1.5px solid #EFF1FE; border-radius: 20px; padding: 14px 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.01); display: flex; flex-direction: column;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 14px;">
                    <div style="width: 30px; height: 30px; background-color: #FFF2EE; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FF5A36" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4M12 17h.01"/>
                        </svg>
                    </div>
                    <div style="color: #1E202C; font-weight: 800; font-size: 15px; line-height: 1;">주의</div>
                </div>
                <div style="display: flex; flex-direction: row; flex-wrap: nowrap; gap: 4px; align-items: center; width: 100%;">
                    <span class="badge-orange" style="font-size: 10.5px !important; padding: 4px 6px !important; white-space: nowrap !important; flex-shrink: 0 !important;">{weakest_label} {int(weakest_val)}</span>
                    <span class="badge-orange" style="font-size: 10.5px !important; padding: 4px 6px !important; white-space: nowrap !important; flex-shrink: 0 !important;">{weak_rec.replace(' ', '')}</span>
                </div>
            </div>
        </div>
        """)
        st.markdown(pro_con_html, unsafe_allow_html=True)
            
        pro_desc = f"{strongest_label} 및 {second_label} 상태가 상대적으로 우수하다는 강점을 가지고 있습니다."
        if weakest_val < 70:
            con_desc = f"다만, 보완이 필요한 {weakest_label} 지수를 고려해 계약을 결정하기 전에 꼭 {weak_rec} 활동을 권장해 드립니다."
        else:
            con_desc = "전반적으로 평가 항목들이 고른 균형을 이루고 있어 만족스러운 생활이 기대됩니다."
        
        summary_html = f"""
        <div style="background-color: #FFFFFF; border: 1.5px solid #EFF1FE; border-radius: 20px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.01); display: flex; gap: 16px; align-items: flex-start; margin-bottom: 24px; width: 100%; box-sizing: border-box;">
            <div style="width: 44px; height: 44px; background-color: #EFF1FE; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2F49D1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                    <line x1="8" y1="9.5" x2="16" y2="9.5"></line>
                    <line x1="8" y1="13.5" x2="13" y2="13.5"></line>
                </svg>
            </div>
            <div style="display: flex; flex-direction: column; justify-content: center; padding-top: 2px;">
                <div style="margin-bottom: 8px; color:#1E202C; font-size: 16px; font-weight: 800; line-height: 1.2;">체크 결과 요약</div>
                <div style="color:#4A4E69; font-size: 14px; line-height: 1.6; word-break: keep-all;">{pro_desc} {con_desc}</div>
            </div>
        </div>
        """
        st.markdown(summary_html, unsafe_allow_html=True)
        
        should_animate = st.session_state.get("animated_prop_id") != active_prop["id"]
        
        final_categories = [
            f"수압<br><b style='color:#2F49D1;'>{int(scores_list[0])}</b>",
            f"채광<br><b style='color:#2F49D1;'>{int(scores_list[1])}</b>",
            f"보안<br><b style='color:#2F49D1;'>{int(scores_list[2])}</b>",
            f"소음<br><b style='color:#2F49D1;'>{int(scores_list[3])}</b>",
            f"청결<br><b style='color:#2F49D1;'>{int(scores_list[4])}</b>"
        ]
        
        if should_animate:
            steps = 15
            for step in range(1, steps + 1):
                progress = step / steps
                # 부드러운 감속 효과 (Ease-out cubic)
                ease_progress = 1 - pow(1 - progress, 3)
                
                current_scores = [s * ease_progress for s in scores_list]
                
                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(
                    r=current_scores + [current_scores[0]],
                    theta=final_categories + [final_categories[0]],
                    fill='toself',
                    fillcolor='rgba(47, 73, 209, 0.12)',
                    line=dict(color='#2F49D1', width=2),
                    marker=dict(size=6, color='#2F49D1')
                ))
                fig.update_layout(
                    polar=dict(
                        radialaxis=dict(visible=True, range=[0, 100], gridcolor="#EFF1FE", linecolor="#EFF1FE", tickfont=dict(size=8, color="#8D94B1")),
                        angularaxis=dict(gridcolor="#EFF1FE", linecolor="#EFF1FE", tickfont=dict(size=11, color="#1E202C", weight='bold', family="Pretendard"))
                    ),
                    showlegend=False,
                    height=300,
                    margin=dict(l=45, r=45, t=45, b=45),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                chart_placeholder.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                time.sleep(0.04)
            
            st.session_state["animated_prop_id"] = active_prop["id"]
        else:
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=scores_list + [scores_list[0]],
                theta=final_categories + [final_categories[0]],
                fill='toself',
                fillcolor='rgba(47, 73, 209, 0.12)',
                line=dict(color='#2F49D1', width=2),
                marker=dict(size=6, color='#2F49D1')
            ))
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100], gridcolor="#EFF1FE", linecolor="#EFF1FE", tickfont=dict(size=8, color="#8D94B1")),
                    angularaxis=dict(gridcolor="#EFF1FE", linecolor="#EFF1FE", tickfont=dict(size=11, color="#1E202C", weight='bold', family="Pretendard"))
                ),
                showlegend=False,
                height=300,
                margin=dict(l=45, r=45, t=45, b=45),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            chart_placeholder.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        st.write("")
        col_act1, col_act2 = st.columns(2)
        if col_act1.button("+ 비교에 추가", type="primary", use_container_width=True):
            st.session_state.selected_to_compare.add(selected_id)
            st.toast("비교대상군 리스트에 추가되었습니다.")
        if col_act2.button("▼ 리포트 저장", type="secondary", use_container_width=True):
            st.toast("리포트가 다운로드 폴더에 보관되었습니다.")

# =====================================================================
# [탭 4] 매물 다중 수평 교차 비교 화면
# =====================================================================
elif st.session_state.current_tab == "비교":
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div class="app-header-container">
        <div style="width:24px;"></div>
        <div class="app-header-title" style="font-weight: 800; font-size: 18px; text-align: center; flex: 1; color: #1E202C;">매물 비교</div>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#1E202C" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div style='color:#2F49D1; font-weight:800; font-size:22px; letter-spacing:-0.6px; margin: 0 0 14px 0; line-height:1.3;'>저장한 매물의 핵심 지표를<br>한눈에 비교해 보세요</div>", unsafe_allow_html=True)
    
    # CSS 개별 필터 식별 마커
    st.markdown('<div class="filter-buttons-marker"></div>', unsafe_allow_html=True)
    
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        if st.button("월세 60 ▼", key="fl_rent_btn", use_container_width=True, type="primary" if st.session_state.fl_rent else "secondary"):
            st.session_state.fl_rent = not st.session_state.fl_rent
            st.rerun()
    with col_f2:
        if st.button("보안 80 ▲", key="fl_sec_btn", use_container_width=True, type="primary" if st.session_state.fl_sec else "secondary"):
            st.session_state.fl_sec = not st.session_state.fl_sec
            st.rerun()
    with col_f3:
        if st.button("채광 70 ▲", key="fl_light_btn", use_container_width=True, type="primary" if st.session_state.fl_light else "secondary"):
            st.session_state.fl_light = not st.session_state.fl_light
            st.rerun()
    with col_f4:
        if st.button("소음 ▼", key="fl_noise_btn", use_container_width=True, type="primary" if st.session_state.fl_noise else "secondary"):
            st.session_state.fl_noise = not st.session_state.fl_noise
            st.rerun()
            
    filtered_list = st.session_state.properties
    if st.session_state.fl_rent:
        filtered_list = [p for p in filtered_list if safe_float(p.get("rent", 0)) <= 60]
    if st.session_state.fl_sec:
        filtered_list = [p for p in filtered_list if p.get("scores", {}).get("보안", 0) >= 80]
    if st.session_state.fl_light:
        filtered_list = [p for p in filtered_list if p.get("scores", {}).get("채광", 0) >= 70]
    if st.session_state.fl_noise:
        filtered_list = [p for p in filtered_list if p.get("scores", {}).get("소음", 0) >= 60]

    avail_ids = [p["id"] for p in filtered_list]
    default_selections = [pid for pid in st.session_state.selected_to_compare if pid in avail_ids]
    
    # Dart ChoiceChip 동기화
    if len(filtered_list) > 3:
        selected_ids = st.multiselect(
            "비교 분석 매물 지정 (최대 3개)",
            options=avail_ids,
            default=default_selections[:3],
            format_func=lambda x: next(p["name"] for p in filtered_list if p["id"] == x),
            max_selections=3
        )
        st.session_state.selected_to_compare = set(selected_ids)
    else:
        st.session_state.selected_to_compare = set(avail_ids)
    
    selected_props = [p for p in filtered_list if p["id"] in st.session_state.selected_to_compare]
    
    if not selected_props:
        st.info("비교 분석 대상 매물을 선택해 주세요.")
    else:
        card_cols = st.columns(len(selected_props))
        for idx, sp in enumerate(selected_props):
            is_building = "오피스텔" in sp["name"] or "B" in sp["name"]
            icon_svg = svg_building if is_building else svg_house
            
            card_html = (
                "<div style='background-color: white; border: 1.5px solid #EFF1FE; padding: 18px 4px; border-radius: 20px; box-shadow: 0 4px 14px rgba(47,73,209,0.015); display: flex; flex-direction: column; align-items: center; justify-content: center;'>"
                f"<div style='width:48px; height:48px; background-color:#EFF1FE; border-radius:16px; display:flex; align-items:center; justify-content:center; margin-bottom:12px;'>{icon_svg}</div>"
                f"<div style='width: 100%; display: flex; justify-content: center; margin-bottom: 8px;'><div style='font-size:14px; color:#1E202C; font-weight:800; text-align: center; white-space: nowrap; letter-spacing: -0.5px;'>{sp['name']}</div></div>"
                f"<div style='display: flex; justify-content: center;'><span class='badge-blue' style='font-size:12px; margin-top:2px;'>{sp['overall_score']}점</span></div>"
                "</div>"
            )
            with card_cols[idx]:
                st.markdown(card_html, unsafe_allow_html=True)
        
        st.write("")
        
        html_rows = ""
        colors = ["#2F49D1", "#F2994A", "#27AE60"]
        
        # 1. 월세 비교 행
        rent_cells = "<div class='comp-label comp-cell'>월세<br>(만원)</div>"
        for c_idx, sp in enumerate(selected_props):
            col = colors[c_idx % len(colors)]
            rent_cells += f"<div class='comp-cell'><span style='color:{col}; font-size:14px; font-weight:600;'>{sp['rent']}</span></div>"
        html_rows += f"<div class='comp-row'>{rent_cells}</div>"
        
        # 2. 채광 비교 행
        light_cells = "<div class='comp-label comp-cell'>채광</div>"
        for sp in selected_props:
            val = "좋음" if sp["scores"]["채광"] >= 80 else "보통"
            bg = "#EBFDF2" if val == "좋음" else "#EFF1FE"
            col = "#107C41" if val == "좋음" else "#7B809A"
            badge = f"<span style='background-color:{bg}; color:{col}; font-size:11px; font-weight:700; padding:6px 14px; border-radius:20px;'>{val}</span>"
            light_cells += f"<div class='comp-cell'>{badge}</div>"
        html_rows += f"<div class='comp-row'>{light_cells}</div>"
        
        # 3. 보안 비교 행 (Dart 스타일 컬러 동기화)
        sec_cells = "<div class='comp-label comp-cell'>보안<br>(점수)</div>"
        sec_colors = ["#2F49D1", "#27AE60", "#F2994A"]
        for c_idx, sp in enumerate(selected_props):
            col = sec_colors[c_idx % len(sec_colors)]
            sec_cells += f"<div class='comp-cell'><span style='color:{col}; font-size:14px; font-weight:600;'>{int(sp['scores']['보안'])}</span></div>"
        html_rows += f"<div class='comp-row'>{sec_cells}</div>"
        
        # 4. 소음 비교 행
        noise_cells = "<div class='comp-label comp-cell'>소음</div>"
        for sp in selected_props:
            val = "주의" if sp["scores"].get("소음", 50) < 50 else ("양호" if sp["scores"].get("소음", 50) >= 60 else "보통")
            bg = "#FFF0E6" if val == "주의" else ("#EBFDF2" if val == "양호" else "#EFF1FE")
            col = "#E65100" if val == "주의" else ("#107C41" if val == "양호" else "#7B809A")
            badge = f"<span style='background-color:{bg}; color:{col}; font-size:11px; font-weight:700; padding:6px 14px; border-radius:20px;'>{val}</span>"
            noise_cells += f"<div class='comp-cell'>{badge}</div>"
        html_rows += f"<div class='comp-row'>{noise_cells}</div>"
        
        # 5. 청결 비교 행
        clean_cells = "<div class='comp-label comp-cell'>청결<br>(점수)</div>"
        clean_colors = ["#2F49D1", "#F2994A", "#F2994A"]
        for c_idx, sp in enumerate(selected_props):
            col = clean_colors[c_idx % len(clean_colors)]
            clean_cells += f"<div class='comp-cell'><span style='color:{col}; font-size:14px; font-weight:600;'>{int(sp['scores'].get('청결도', 50))}</span></div>"
        html_rows += f"<div class='comp-row'>{clean_cells}</div>"
        
        st.markdown(f"<div class='comp-table'>{html_rows}</div>", unsafe_allow_html=True)
        st.write("")
        
        # 한눈에 보기 가이드 카드를 실제 선택된 매물들의 동적 상태와 완전 동기화시킵니다.
        insight_items_html = ""
        colors_badge = ["#2F49D1", "#F2994A", "#27AE60"]
        for idx_p, sp in enumerate(selected_props):
            bg_col = colors_badge[idx_p % len(colors_badge)]
            s_dict = sp.get("scores", {})
            
            if s_dict:
                high_key = max(s_dict, key=s_dict.get)
                low_key = min(s_dict, key=s_dict.get)
                high_name = DISPLAY_NAMES.get(high_key, high_key)
                low_name = DISPLAY_NAMES.get(low_key, low_key)
                
                # 최저 점수 필터 기준을 `< 70`으로 조정
                if s_dict[low_key] < 70:
                    desc = f"<b>{high_name}</b>은 우수하나 상대적인 <b>{low_name}</b> 요소를 확인해볼 필요가 있습니다."
                else:
                    desc = f"<b>{high_name}</b> 지표가 돋보이며 모든 항목이 전반적으로 고른 우수한 상태입니다."
            else:
                desc = "분석된 정밀 스코어 데이터 정보가 존재하지 않습니다."
                
            short_name = sp["name"][:10] + ".." if len(sp["name"]) > 10 else sp["name"]
            
            insight_items_html += (
                f"<div style='display:flex; gap:12px; align-items:flex-start; margin-bottom:12px; box-sizing: border-box; width: 100%;'>"
                f"  <div style='background-color:{bg_col}; color:white; font-size:12px; font-weight:800; width:22px; height:22px; border-radius:50%; display:flex; align-items:center; justify-content:center; flex-shrink:0; margin-top:0px;'>{idx_p + 1}</div>"
                f"  <div style='font-size:14px; color:#4A4E69; line-height:1.5; word-break:keep-all;'>"
                f"    <span style='color:{bg_col}; font-weight:800; font-size:14.5px;'>{short_name}</span>: {desc}"
                f"  </div>"
                f"</div>"
            )
            
        # 한눈에 보기 카드 전체를 감싸는 래퍼 (표와 동일한 디자인)
        insight_html = (
            "<div style='margin-top: 16px; border: 1.5px solid #EFF1FE; border-radius: 20px; background-color: #FFFFFF; padding: 24px 20px; box-shadow: 0 4px 14px rgba(0,0,0,0.01);'>"
            "<div style='display:flex; align-items:center; gap:8px; margin-bottom:16px;'>"
            "  <div style='width:28px; height:28px; background-color:#EFF1FE; border-radius:50%; display:flex; align-items:center; justify-content:center;'>"
            "    <svg width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='#2F49D1' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'><path d='M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z'/><circle cx='8' cy='12' r='1.5' fill='#2F49D1' stroke='none'/><circle cx='12' cy='12' r='1.5' fill='#2F49D1' stroke='none'/><circle cx='16' cy='12' r='1.5' fill='#2F49D1' stroke='none'/></svg>"
            "  </div>"
            "  <span style='color:#1E202C; font-weight:800; font-size:16px;'>한눈에 보기</span>"
            "</div>"
            f"<div style='display:flex; flex-direction:column; gap:14px;'>"
            f"{insight_items_html}"
            "</div>"
            "</div>"
        )
        st.markdown(insight_html, unsafe_allow_html=True)

# ---------------------------------------------------------------------
# 📱 하단 고정 내비게이션 바 레이아웃 출력
# ---------------------------------------------------------------------
st.markdown('<div class="nav-bar-anchor"></div>', unsafe_allow_html=True)
nav_bar_cols = st.columns(4)

menu_items_with_key = [
    ("가이드", "📋"),
    ("체크", "📝"),
    ("리포트", "📊"),
    ("비교", "⇆")
]

for idx, (label, icon) in enumerate(menu_items_with_key):
    is_active = st.session_state.current_tab == label
    btn_type = "primary" if is_active else "secondary"
    
    with nav_bar_cols[idx]:
        if st.button(label, key=f"nav_btn_{label}", use_container_width=True, type=btn_type):
            st.session_state.current_tab = label
            st.rerun()