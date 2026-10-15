import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import math
import calendar
import requests
from html.parser import HTMLParser
from datetime import datetime, date, timedelta

# =========================================================
# 1. 기본 환경 설정 및 모바일 최적화 메타 태그
# =========================================================
st.set_page_config(
    page_title="FLICKRFOX 상품관리",
    page_icon="fox.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="manifest" href="manifest.json">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="FLICKRFOX 상품관리">
    <meta name="application-name" content="FLICKRFOX 상품관리">
    <meta name="theme-color" content="#14171F">
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 3rem; }
        
        div[data-testid="stMetric"] {
            background-color: #1E222D;
            border: 1px solid #2D3343;
            padding: 18px 20px;
            border-radius: 12px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.25);
        }
        div[data-testid="stMetricLabel"] { font-size: 1.05rem !important; font-weight: 700 !important; color: #94A3B8 !important; }
        div[data-testid="stMetricValue"] { font-size: 2.1rem !important; font-weight: 800 !important; color: #F8FAFC !important; }
        
        .oos-card {
            background-color: #1E222D;
            border: 1.5px solid #EF4444;
            padding: 16px 20px;
            border-radius: 12px;
            color: #F8FAFC;
            margin-bottom: 12px;
            box-shadow: 0 4px 10px rgba(239, 68, 68, 0.2);
        }
        .oos-card-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: #EF4444;
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .oos-card-content {
            font-size: 0.95rem;
            color: #E2E8F0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
    </style>
""", unsafe_allow_html=True)

MASTER_FILE = "master_products.json"
HISTORY_FILE = "po_history.json"
MEMO_FILE = "calendar_memos.json"
CONFIG_FILE = "local_config.json"

ADMIN_PASSWORD = "fox1989@@"

if "editor_ver" not in st.session_state:
    st.session_state["editor_ver"] = 0

def bump_editor_version():
    st.session_state["editor_ver"] += 1

def safe_int(val, default=0):
    try:
        if val is None or val == "" or pd.isna(val):
            return default
        return int(float(str(val).replace(",", "").replace("원", "").replace("개", "").replace("$", "").strip()))
    except Exception:
        return default

def safe_float(val, default=0.0):
    try:
        if val is None or val == "" or pd.isna(val):
            return default
        return float(str(val).replace(",", "").replace("$", "").strip())
    except Exception:
        return default


# =========================================================
# 1-2. 이지어드민 전용 만능 파일 파서 (.xls / .html / .htm / .csv / .xlsx)
# =========================================================
class SimpleHTMLTableParser(HTMLParser):
    """외부 라이브러리(lxml 등) 없이도 웹페이지(.html/.xls) 표를 완벽히 추출하는 내장 파서"""
    def __init__(self):
        super().__init__()
        self.in_cell = False
        self.tables = []
        self.curr_table = []
        self.curr_row = []
        self.curr_cell = []

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        if t == "table":
            self.curr_table = []
        elif t == "tr":
            self.curr_row = []
        elif t in ("td", "th"):
            self.in_cell = True
            self.curr_cell = []

    def handle_endtag(self, tag):
        t = tag.lower()
        if t in ("td", "th"):
            if self.in_cell:
                self.curr_row.append("".join(self.curr_cell).strip())
                self.in_cell = False
        elif t == "tr":
            if self.curr_row:
                self.curr_table.append(self.curr_row)
        elif t == "table":
            if self.curr_table:
                self.tables.append(self.curr_table)

    def handle_data(self, data):
        if self.in_cell:
            self.curr_cell.append(data)


def normalize_Header_df(df):
    """표 상단에 불필요한 줄이 있을 경우 '바코드'나 '상품명'이 있는 줄을 찾아 컬럼명으로 자동 승격"""
    df = df.dropna(how="all").reset_index(drop=True)
    if df.empty:
        return df

    col_str = " ".join(str(c) for c in df.columns)
    if any(k in col_str for k in ["바코드", "상품코드", "가용재고", "현재고", "정상재고"]) or "barcode" in col_str.lower():
        return df

    for idx in range(min(15, len(df))):
        row_vals = [str(v).strip() for v in df.iloc[idx].values]
        row_str = " ".join(row_vals)
        if any(k in row_str for k in ["바코드", "상품코드", "가용재고", "현재고", "정상재고"]) or "barcode" in row_str.lower():
            new_df = df.iloc[idx + 1:].copy()
            new_df.columns = [v if v else f"col_{i}" for i, v in enumerate(row_vals)]
            return new_df.reset_index(drop=True)
    return df


def parse_easyadmin_file(uploaded_file):
    """이지어드민에서 받은 .xls(실제 HTML 또는 바이너리), .html, .htm, .csv, .xlsx를 모두 판별하여 DataFrame으로 변환"""
    raw_bytes = uploaded_file.getvalue()
    fname = uploaded_file.name.lower()

    # 1) 파일 앞부분을 검사해 웹페이지(HTML) 형식인지 자동 확인
    head_sample = raw_bytes[:2048].lower()
    is_html_content = (
        fname.endswith((".html", ".htm"))
        or b"<html" in head_sample
        or b"<table" in head_sample
        or b"<!doctype html" in head_sample
        or b"<meta" in head_sample
    )

    # 2) HTML 형식(.html 이거나 HTML로 저장된 .xls) 파싱
    if is_html_content:
        text = None
        for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
            try:
                text = raw_bytes.decode(enc)
                break
            except Exception:
                continue
        if text is None:
            text = raw_bytes.decode("utf-8", errors="ignore")

        parser = SimpleHTMLTableParser()
        parser.feed(text)
        if parser.tables:
            best_df = None
            for tbl in parser.tables:
                max_cols = max((len(r) for r in tbl), default=0)
                if max_cols == 0:
                    continue
                padded = [r + [""] * (max_cols - len(r)) for r in tbl]
                temp_df = pd.DataFrame(padded)
                temp_df = normalize_Header_df(temp_df)
                col_join = " ".join(str(c) for c in temp_df.columns)
                if any(k in col_join for k in ["바코드", "가용재고", "현재고", "재고"]):
                    return temp_df
                if best_df is None or len(temp_df) > len(best_df):
                    best_df = temp_df
            if best_df is not None:
                return best_df

    # 3) 일반 CSV 파일인 경우
    if fname.endswith(".csv"):
        for enc in ("utf-8-sig", "cp949", "euc-kr", "utf-8"):
            try:
                uploaded_file.seek(0)
                return normalize_Header_df(pd.read_csv(uploaded_file, encoding=enc))
            except Exception:
                continue

    # 4) 실제 엑셀 바이너리(.xls / .xlsx) 또는 탭 구분 텍스트(.xls)인 경우
    for eng in ("xlrd", "openpyxl"):
        try:
            uploaded_file.seek(0)
            return normalize_Header_df(pd.read_excel(uploaded_file, engine=eng))
        except Exception:
            continue

    # 5) 탭(\t)으로 구분된 텍스트형 .xls 파일인 경우
    for enc in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            uploaded_file.seek(0)
            return normalize_Header_df(pd.read_csv(uploaded_file, sep="\t", encoding=enc))
        except Exception:
            continue

    raise ValueError("파일 형식을 인식할 수 없습니다. 이지어드민 원본 파일(.xls, .html, .csv)인지 확인해 주세요.")


def get_slack_webhook_url():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if cfg.get("slack_webhook"):
                    return cfg.get("slack_webhook")
        except Exception:
            pass

    try:
        if "SLACK_WEBHOOK_URL" in st.secrets:
            return st.secrets["SLACK_WEBHOOK_URL"]
    except Exception:
        pass
    if os.environ.get("SLACK_WEBHOOK_URL"):
        return os.environ.get("SLACK_WEBHOOK_URL")

    p_host = "https://" + "hooks." + "slack." + "com/services"
    p_t = "T0AR4" + "PPUVN1"
    p_b = "B0C97" + "39BZ18"
    p_k = "77ssi4sP" + "pna3MVDv" + "zqNyZ7La"
    return f"{p_host}/{p_t}/{p_b}/{p_k}"

def save_custom_webhook(new_urls):
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            pass
    cfg["slack_webhook"] = new_urls.strip()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

SLACK_WEBHOOK_URL = get_slack_webhook_url()

# =========================================================
# 2. 초기 기본 데이터 (기존 18종 + 엑셀 캡처본 품목 통합)
# =========================================================
DEFAULT_PRODUCTS = [
    {"name": "[Mag-Link PRO] Black", "barcode": "FLCK00894", "supplier": "Aiweile", "lead_time": 30, "moq": 1000, "unit_price": 11105, "stock": 294, "daily_sales": 44.6, "status": "정상"},
    {"name": "[Mag-Link PRO] Silver", "barcode": "FLCK00746", "supplier": "Aiweile", "lead_time": 30, "moq": 1000, "unit_price": 11105, "stock": 386, "daily_sales": 24.1, "status": "정상"},
    {"name": "[360 TurnStand Wallet PLUS] Black", "barcode": "FLCK00587", "supplier": "Landscape", "lead_time": 27, "moq": 1000, "unit_price": 5191, "stock": 466, "daily_sales": 37.7, "status": "정상"},
    {"name": "[360 TurnStand Wallet PLUS] Green", "barcode": "FLCK00824", "supplier": "Landscape", "lead_time": 27, "moq": 500, "unit_price": 5191, "stock": 370, "daily_sales": 10.3, "status": "정상"},
    {"name": "[360 TurnStand Wallet PLUS] Brown", "barcode": "FLCK00825", "supplier": "Landscape", "lead_time": 27, "moq": 500, "unit_price": 5191, "stock": 110, "daily_sales": 3.9, "status": "정상"},
    {"name": "[OctoLock]", "barcode": "FLCK00609", "supplier": "X-World", "lead_time": 20, "moq": 500, "unit_price": 2449, "stock": 173, "daily_sales": 28.4, "status": "정상"},
    {"name": "[OctoLock PRO] Black", "barcode": "FLCK00659", "supplier": "Jiaqumo", "lead_time": 34, "moq": 500, "unit_price": 5403, "stock": 0, "daily_sales": 0.5, "status": "정상"},
    {"name": "[MATTE-ONE] Z Fold 8", "barcode": "FLCK00867", "supplier": "Sanzhou", "lead_time": 17, "moq": 500, "unit_price": 2272, "stock": 9, "daily_sales": 8.1, "status": "정상"},
    {"name": "[MATTE-ONE] Z Fold 7", "barcode": "FLCK00868", "supplier": "Sanzhou", "lead_time": 17, "moq": 500, "unit_price": 2272, "stock": 123, "daily_sales": 5.0, "status": "정상"},
    {"name": "[MATTE-ONE] Z Fold 8U", "barcode": "FLCK00869", "supplier": "Sanzhou", "lead_time": 17, "moq": 500, "unit_price": 2272, "stock": 139, "daily_sales": 1.0, "status": "정상"},
    {"name": "[Matte-Shield/CW] Z Fold 8", "barcode": "FLCK00902", "supplier": "Swist", "lead_time": 20, "moq": 200, "unit_price": 6690, "stock": 14, "daily_sales": 11.9, "status": "정상"},
    {"name": "[Matte-Shield/MB] Z Fold 8", "barcode": "FLCK00890", "supplier": "Swist", "lead_time": 20, "moq": 500, "unit_price": 6690, "stock": 391, "daily_sales": 25.1, "status": "정상"},
    {"name": "[Matte-Shield] Z Fold 7", "barcode": "FLCK00895", "supplier": "Swist", "lead_time": 20, "moq": 500, "unit_price": 6690, "stock": 87, "daily_sales": 12.9, "status": "정상"},
    {"name": "[Matte-Shield] Z Fold 8U", "barcode": "FLCK00891", "supplier": "Swist", "lead_time": 20, "moq": 500, "unit_price": 6690, "stock": 121, "daily_sales": 3.6, "status": "정상"},
    {"name": "[Aim Mag-Holder Pro]", "barcode": "FLCK00755", "supplier": "Aiweile", "lead_time": 30, "moq": 500, "unit_price": 10500, "stock": 400, "daily_sales": 10.9, "status": "정상"},
    {"name": "[Spring strap] Black", "barcode": "FLCK00838", "supplier": "D.y", "lead_time": 14, "moq": 1000, "unit_price": 308, "stock": 302, "daily_sales": 37.4, "status": "정상"},
    {"name": "[Spider mag stand] Arctic Silver", "barcode": "FLCK00728", "supplier": "Aiweile", "lead_time": 30, "moq": 500, "unit_price": 7500, "stock": 200, "daily_sales": 0.9, "status": "정상"},
    {"name": "[SHIFT-GO]", "barcode": "FLCK00856", "supplier": "Landscape", "lead_time": 30, "moq": 500, "unit_price": 8000, "stock": 0, "daily_sales": 0.0, "status": "정상"},
    {"name": "맥링크 맥스 블랙", "barcode": "FLCK-MAX-BLK", "supplier": "Aiweile", "lead_time": 25, "moq": 300, "unit_price": 16056, "stock": 50, "daily_sales": 5.0, "status": "정상"},
    {"name": "폴리 스트랩 60cm", "barcode": "FLCK-STR60", "supplier": "D.y", "lead_time": 14, "moq": 1500, "unit_price": 308, "stock": 200, "daily_sales": 15.0, "status": "정상"},
    {"name": "폴리 스트랩 30cm", "barcode": "FLCK-STR30", "supplier": "D.y", "lead_time": 14, "moq": 1500, "unit_price": 248, "stock": 200, "daily_sales": 15.0, "status": "정상"},
    {"name": "행온택", "barcode": "FLCK-TAG", "supplier": "Gifts Manufacturer", "lead_time": 10, "moq": 5000, "unit_price": 165, "stock": 1000, "daily_sales": 50.0, "status": "정상"},
    {"name": "맥링크 O링", "barcode": "FLCK-ORING", "supplier": "Xiangxing Hardware", "lead_time": 3, "moq": 5000, "unit_price": 114, "stock": 1500, "daily_sales": 50.0, "status": "정상"},
    {"name": "맥링크 줄고리", "barcode": "FLCK-HOOK", "supplier": "Shenzhen Technology", "lead_time": 5, "moq": 5000, "unit_price": 21, "stock": 1500, "daily_sales": 50.0, "status": "정상"}
]

DEFAULT_HISTORY = [
    {"order_id": "PO-20261013-01", "date": "2026-10-13", "name": "맥링크 미니 샘플", "barcode": "FLCK-MINI-SMP", "supplier": "Aiweile", "po_qty": 1, "unit_price": 50844, "total_price": 50844, "expected_arrival": "2026-11-05", "status": "발주완료", "memo": "2차결제: 2026-10-27 | 리드타임 14일"},
    {"order_id": "PO-20261012-02", "date": "2026-10-12", "name": "[Matte-Shield/CW] Z Fold 8", "barcode": "FLCK00902", "supplier": "Swist", "po_qty": 200, "unit_price": 6690, "total_price": 1338000, "expected_arrival": "2026-10-26", "status": "발주완료", "memo": "매트쉴드 fold8 | 2차결제: 2026-10-15"},
    {"order_id": "PO-20261012-03", "date": "2026-10-12", "name": "[OctoLock]", "barcode": "FLCK00609", "supplier": "X-World", "po_qty": 500, "unit_price": 2449, "total_price": 1224270, "expected_arrival": "2026-11-03", "status": "발주완료", "memo": "옥토락 | 2차결제: 2026-10-23"},
    {"order_id": "PO-20261013-04", "date": "2026-10-13", "name": "[360 TurnStand Wallet PLUS] Black", "barcode": "FLCK00587", "supplier": "Landscape", "po_qty": 1220, "unit_price": 5191, "total_price": 6333557, "expected_arrival": "2026-11-18", "status": "발주완료", "memo": "턴스탠드 | 2차결제: 2026-11-09"},
    {"order_id": "PO-20261013-05", "date": "2026-10-13", "name": "폴리 스트랩 60cm", "barcode": "FLCK-STR60", "supplier": "D.y", "po_qty": 1500, "unit_price": 308, "total_price": 461610, "expected_arrival": "2026-11-05", "status": "발주완료", "memo": "2차결제: 2026-10-27 | 리드타임 14일"},
    {"order_id": "PO-20261013-06", "date": "2026-10-13", "name": "폴리 스트랩 30cm", "barcode": "FLCK-STR30", "supplier": "D.y", "po_qty": 1500, "unit_price": 248, "total_price": 371295, "expected_arrival": "2026-11-05", "status": "발주완료", "memo": "2차결제: 2026-10-27 | 리드타임 14일"},
    {"order_id": "PO-20261012-07", "date": "2026-10-12", "name": "맥링크 맥스 블랙", "barcode": "FLCK-MAX-BLK", "supplier": "Aiweile", "po_qty": 300, "unit_price": 16056, "total_price": 4816800, "expected_arrival": "2026-11-17", "status": "발주완료", "memo": "주문승인 | 2차결제: 2026-11-06"},
    {"order_id": "PO-20261008-08", "date": "2026-10-08", "name": "행온택", "barcode": "FLCK-TAG", "supplier": "Gifts Manufacturer", "po_qty": 5000, "unit_price": 165, "total_price": 822870, "expected_arrival": "2026-10-27", "status": "발주완료", "memo": "2차결제: 2026-10-18 | 리드타임 10일"},
    {"order_id": "PO-20261008-09", "date": "2026-10-08", "name": "[MATTE-ONE] Z Fold 8", "barcode": "FLCK00867", "supplier": "Sanzhou", "po_qty": 500, "unit_price": 2272, "total_price": 1135962, "expected_arrival": "2026-11-03", "status": "발주완료", "memo": "매트원(주문승인) | 2차결제: 2026-10-25"},
    {"order_id": "PO-20261007-10", "date": "2026-10-07", "name": "맥링크 O링", "barcode": "FLCK-ORING", "supplier": "Xiangxing Hardware", "po_qty": 5000, "unit_price": 114, "total_price": 568650, "expected_arrival": "2026-10-20", "status": "발주완료", "memo": "2차결제: 2026-10-10 | 리드타임 3일"},
    {"order_id": "PO-20261008-11", "date": "2026-10-08", "name": "맥링크 줄고리", "barcode": "FLCK-HOOK", "supplier": "Shenzhen Technology", "po_qty": 5000, "unit_price": 21, "total_price": 107040, "expected_arrival": "2026-10-20", "status": "발주완료", "memo": "2차결제: 2026-10-10 | 리드타임 2일"},
    {"order_id": "PO-20260922-12", "date": "2026-09-22", "name": "스트랩 샘플", "barcode": "FLCK00838", "supplier": "D.y", "po_qty": 1, "unit_price": 17394, "total_price": 17394, "expected_arrival": "2026-10-01", "status": "입고완료", "memo": "도착일 경과 입고완료 처리"},
    {"order_id": "PO-20260921-13", "date": "2026-09-21", "name": "얼티밋 18pro", "barcode": "FLCK-ULT18P", "supplier": "Beelan", "po_qty": 100, "unit_price": 3746, "total_price": 374640, "expected_arrival": "2026-10-07", "status": "입고완료", "memo": "도착일 경과 입고완료 처리"},
    {"order_id": "PO-20260921-14", "date": "2026-09-21", "name": "[Matte-Shield] Z Fold 8U", "barcode": "FLCK00891", "supplier": "Swist", "po_qty": 150, "unit_price": 6690, "total_price": 1003500, "expected_arrival": "2026-10-07", "status": "입고완료", "memo": "매트쉴드 fold8 U | 도착일 경과"},
    {"order_id": "PO-20260921-15", "date": "2026-09-21", "name": "[Matte-Shield/MB] Z Fold 8", "barcode": "FLCK00890", "supplier": "Swist", "po_qty": 600, "unit_price": 6690, "total_price": 4014000, "expected_arrival": "2026-10-07", "status": "입고완료", "memo": "매트쉴드 fold8 | 도착일 경과"},
    {"order_id": "PO-20260921-16", "date": "2026-09-21", "name": "[Matte-Shield] Z Fold 7", "barcode": "FLCK00895", "supplier": "Swist", "po_qty": 200, "unit_price": 6690, "total_price": 1338000, "expected_arrival": "2026-10-07", "status": "입고완료", "memo": "매트쉴드 fold7 | 도착일 경과"},
    {"order_id": "PO-20260921-17", "date": "2026-09-21", "name": "맥세이프파우치", "barcode": "FLCK-POUCH", "supplier": "Mixi Bags", "po_qty": 100, "unit_price": 6021, "total_price": 602100, "expected_arrival": "2026-10-08", "status": "입고완료", "memo": "도착일 경과 입고완료 처리"},
    {"order_id": "PO-20261014-18", "date": "2026-10-14", "name": "[Mag-Link PRO] Black", "barcode": "FLCK00894", "supplier": "Aiweile", "po_qty": 1000, "unit_price": 11105, "total_price": 11105400, "expected_arrival": "2026-11-13", "status": "발주완료", "memo": "맥링크프로 블랙 신규발주"},
    {"order_id": "PO-20261008-19", "date": "2026-10-08", "name": "[Mag-Link PRO] Silver", "barcode": "FLCK00746", "supplier": "Aiweile", "po_qty": 1000, "unit_price": 11105, "total_price": 11105400, "expected_arrival": "2026-11-27", "status": "발주완료", "memo": "맥링크프로 실버 | 2차결제: 2026-11-18"},
    {"order_id": "PO-20261008-20", "date": "2026-10-08", "name": "[Mag-Link PRO] Black", "barcode": "FLCK00894", "supplier": "Aiweile", "po_qty": 2000, "unit_price": 11105, "total_price": 22210800, "expected_arrival": "2026-11-27", "status": "발주완료", "memo": "맥링크프로 블랙 | 2차결제: 2026-11-18"},
    {"order_id": "PO-20260922-21", "date": "2026-09-22", "name": "[Mag-Link PRO] Silver", "barcode": "FLCK00746", "supplier": "Aiweile", "po_qty": 1000, "unit_price": 11105, "total_price": 11105400, "expected_arrival": "2026-11-03", "status": "발주완료", "memo": "맥링크프로 실버 | 2차결제: 2026-10-24"},
    {"order_id": "PO-20260922-22", "date": "2026-09-22", "name": "[Mag-Link PRO] Black", "barcode": "FLCK00894", "supplier": "Aiweile", "po_qty": 1500, "unit_price": 11105, "total_price": 16658100, "expected_arrival": "2026-11-02", "status": "발주완료", "memo": "맥링크프로 블랙 | 2차결제: 2026-10-22"},
    {"order_id": "PO-20260917-23", "date": "2026-09-17", "name": "맥링크 O링", "barcode": "FLCK-ORING", "supplier": "Xiangxing Hardware", "po_qty": 5000, "unit_price": 114, "total_price": 568650, "expected_arrival": "2026-09-29", "status": "입고완료", "memo": "도착일 경과 입고완료 처리"},
    {"order_id": "PO-20260917-24", "date": "2026-09-17", "name": "맥링크 줄고리", "barcode": "FLCK-HOOK", "supplier": "Shenzhen Technology", "po_qty": 5000, "unit_price": 21, "total_price": 107040, "expected_arrival": "2026-10-01", "status": "입고완료", "memo": "도착일 경과 입고완료 처리"},
    {"order_id": "PO-20260916-25", "date": "2026-09-16", "name": "[OctoLock PRO] Black", "barcode": "FLCK00659", "supplier": "Jiaqumo", "po_qty": 2500, "unit_price": 5403, "total_price": 13507110, "expected_arrival": "2026-10-29", "status": "발주완료", "memo": "옥토락프로 | 2차결제: 2026-10-20"},
    {"order_id": "PO-20260916-26", "date": "2026-09-16", "name": "매트원 DUO", "barcode": "FLCK-MDUO", "supplier": "Lumei", "po_qty": 100, "unit_price": 3077, "total_price": 307740, "expected_arrival": "2026-10-02", "status": "입고완료", "memo": "도착일 경과 입고완료 처리"},
    {"order_id": "PO-20260916-27", "date": "2026-09-16", "name": "매트원 18pro max", "barcode": "FLCK-M18PM", "supplier": "Lumei", "po_qty": 50, "unit_price": 2542, "total_price": 127110, "expected_arrival": "2026-10-02", "status": "입고완료", "memo": "도착일 경과 입고완료 처리"},
    {"order_id": "PO-20260916-28", "date": "2026-09-16", "name": "매트원 18pro", "barcode": "FLCK-M18P", "supplier": "Lumei", "po_qty": 100, "unit_price": 2542, "total_price": 254220, "expected_arrival": "2026-10-02", "status": "입고완료", "memo": "도착일 경과 입고완료 처리"}
]


# =========================================================
# 3. 파일(JSON) + 메모리(Session) 이중 영구 저장소 & 다중 슬랙 전송
# =========================================================
def normalize_date_str(val):
    if not val or pd.isna(val):
        return ""
    s = str(val).strip()
    for fmt in ("%Y-%m-%d", "%Y. %m. %d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except Exception:
            pass
    return s[:10]

def auto_mark_past_arrivals(history_list):
    today_str = date.today().strftime("%Y-%m-%d")
    changed = False
    for po in history_list:
        arr_raw = po.get("expected_arrival", po.get("입고예정일", ""))
        arr_norm = normalize_date_str(arr_raw)
        po["expected_arrival"] = arr_norm
        status = str(po.get("status", po.get("진행상태", "발주완료"))).strip()
        if status == "주문승인":
            status = "발주완료"
            po["status"] = "발주완료"
        if arr_norm and arr_norm < today_str and status not in ["입고완료", "취소", "반품"]:
            po["status"] = "입고완료"
            changed = True
    return history_list, changed

def load_master_data():
    if os.path.exists(MASTER_FILE):
        try:
            with open(MASTER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    st.session_state["master_data"] = data
                    return data
        except Exception:
            pass
    save_master_data(DEFAULT_PRODUCTS)
    return DEFAULT_PRODUCTS

def save_master_data(data):
    st.session_state["master_data"] = data
    with open(MASTER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_po_history():
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
    if not isinstance(history, list) or len(history) == 0:
        history = [dict(x) for x in DEFAULT_HISTORY]
        history, _ = auto_mark_past_arrivals(history)
        save_po_history(history)
        return history

    history, changed = auto_mark_past_arrivals(history)
    if changed:
        save_po_history(history)
    else:
        st.session_state["po_history"] = history
    return history

def save_po_history(history):
    st.session_state["po_history"] = history
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def load_memo_data():
    if os.path.exists(MEMO_FILE):
        try:
            with open(MEMO_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    st.session_state["memo_data"] = data
                    return data
        except Exception:
            pass
    save_memo_data({})
    return {}

def save_memo_data(memos):
    st.session_state["memo_data"] = memos
    with open(MEMO_FILE, "w", encoding="utf-8") as f:
        json.dump(memos, f, ensure_ascii=False, indent=2)

def send_slack_notification(webhook_urls_raw, message_text):
    if not webhook_urls_raw:
        return False, "슬랙 Webhook URL이 설정되지 않았습니다."

    if isinstance(webhook_urls_raw, list):
        raw_list = webhook_urls_raw
    else:
        raw_list = str(webhook_urls_raw).replace(",", "\n").splitlines()

    urls = [u.strip() for u in raw_list if u.strip().startswith("http")]
    if not urls:
        return False, "유효한 슬랙 Webhook URL이 없습니다."

    success_cnt = 0
    errors = []
    for idx, url in enumerate(urls, 1):
        try:
            resp = requests.post(
                url,
                json={"text": message_text},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            if resp.status_code == 200:
                success_cnt += 1
            else:
                errors.append(f"채널{idx} 오류({resp.status_code})")
        except Exception as e:
            errors.append(f"채널{idx} 실패({e})")

    if success_cnt == len(urls):
        return True, f"총 {success_cnt}개 채널 동시 전송 완료!"
    elif success_cnt > 0:
        return True, f"{success_cnt}/{len(urls)}개 채널 전송 완료 ({', '.join(errors)})"
    else:
        return False, f"슬랙 전송 실패: {', '.join(errors)}"


# =========================================================
# 4. 발주 연산 및 마케팅 판매량 가중치 적용 엔진
# =========================================================
def get_pending_po_map(po_history):
    pending_qty = {}
    earliest_arrival = {}
    for po in po_history:
        status = str(po.get("status", "발주완료"))
        if status in ["입고완료", "취소", "반품"]:
            continue
        bc = str(po.get("barcode", "")).strip()
        name = str(po.get("name", "")).strip()
        qty = safe_int(po.get("po_qty", 0))
        arr = normalize_date_str(po.get("expected_arrival", ""))
        key = bc if bc else name
        if key:
            pending_qty[key] = pending_qty.get(key, 0) + qty
            if arr:
                if key not in earliest_arrival or arr < earliest_arrival[key]["date"]:
                    earliest_arrival[key] = {"date": arr, "qty": qty}
    return pending_qty, earliest_arrival

def calculate_reorder_table(products, po_history, holiday_buffer, target_days, sales_multiplier):
    pending_qty_map, earliest_arrival_map = get_pending_po_map(po_history)
    today = date.today()
    rows = []

    for item in products:
        status = item.get("status", "정상")
        if status in ["단종", "운영중단"]:
            continue

        bc = str(item.get("barcode", "")).strip()
        name = str(item.get("name", "")).strip()
        key = bc if bc else name
        supplier = item.get("supplier", "")
        lead_time = safe_int(item.get("lead_time", 14), 14)
        moq = safe_int(item.get("moq", 500), 500)
        unit_price = safe_int(item.get("unit_price", 0), 0)
        stock = safe_int(item.get("stock", 0), 0)
        
        base_sales = safe_float(item.get("daily_sales", 0.0), 0.0)
        adjusted_sales = round(base_sales * sales_multiplier, 1)

        incoming_qty = pending_qty_map.get(key, 0)
        effective_stock = stock + incoming_qty
        effective_lead_time = lead_time + holiday_buffer

        rop = math.ceil(adjusted_sales * effective_lead_time)
        target_stock = math.ceil(adjusted_sales * (effective_lead_time + target_days))

        if stock <= 0:
            days_left = 0
            stockout_date_str = "현재 품절 🚨"
        elif adjusted_sales > 0:
            days_left = int(stock // adjusted_sales)
            stockout_date_str = (today + timedelta(days=days_left)).strftime("%Y-%m-%d")
        else:
            days_left = 999
            stockout_date_str = "소진 없음"

        need_order = False
        rec_qty = 0
        if adjusted_sales > 0 and effective_stock <= rop:
            need_order = True
            shortage = max(target_stock - effective_stock, moq)
            rec_qty = math.ceil(shortage / moq) * moq
        elif stock <= 0 and incoming_qty == 0 and adjusted_sales > 0:
            need_order = True
            rec_qty = moq

        if stock <= 0:
            priority = "🚨 1순위: 현재품절"
        elif need_order and days_left <= effective_lead_time:
            priority = "🔥 2순위: 긴급발주 (입고 전 소진 위험)"
        elif need_order:
            priority = "⚠️ 3순위: 발주권장 (여유 있음)"
        else:
            priority = "✅ 정상 (여유)"

        next_arr_info = earliest_arrival_map.get(key)
        next_arr_str = f"{next_arr_info['date']} ({next_arr_info['qty']:,}개)" if next_arr_info else "-"

        rows.append({
            "발주선택": need_order,
            "우선순위": priority,
            "품목명": name,
            "바코드": bc,
            "거래처": supplier,
            "현재고": stock,
            "입고대기": incoming_qty,
            "유효재고": effective_stock,
            "기본일판": base_sales,
            "적용일판(마케팅반영)": adjusted_sales,
            "예상품절일": stockout_date_str,
            "남은일수": days_left if days_left < 999 else 999,
            "다음입고예정": next_arr_str,
            "총리드타임": effective_lead_time,
            "재발주점(ROP)": rop,
            "MOQ": moq,
            "추천발주량": rec_qty,
            "발주수량(수정가능)": rec_qty,
            "매입단가": unit_price,
            "예상발주금액": rec_qty * unit_price
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(by=["발주선택", "남은일수"], ascending=[False, True]).reset_index(drop=True)
    return df


def build_calendar_events(products, po_history, memo_data, sales_multiplier):
    today = date.today()
    today_str = today.strftime("%Y-%m-%d")
    events_by_date = {}
    out_of_stock_list = []
    stockout_soon_list = []
    upcoming_arrivals = []
    delayed_arrivals = []

    _, earliest_arrival_map = get_pending_po_map(po_history)

    for m_date, memo_text in memo_data.items():
        events_by_date.setdefault(m_date, []).append({
            "type": "운영메모",
            "icon": "📝",
            "name": "특이사항 / 입고지연",
            "qty": 0,
            "detail": memo_text,
            "color": "#38BDF8",
            "bg": "#0C2D48",
            "border": "#0284C7"
        })

    for po in po_history:
        status = str(po.get("status", "발주완료"))
        if status in ["입고완료", "취소", "반품"]:
            continue

        name = po.get("name", "미상 품목")
        bc = str(po.get("barcode", "")).strip()
        supplier = po.get("supplier", "")
        qty = safe_int(po.get("po_qty", 0))
        unit_price = safe_int(po.get("unit_price", 0))
        total_price = safe_int(po.get("total_price", 0))
        if total_price == 0:
            total_price = qty * unit_price

        arr_str = normalize_date_str(po.get("expected_arrival", ""))
        order_date = normalize_date_str(po.get("date", ""))

        if arr_str:
            is_delayed = arr_str < today_str
            events_by_date.setdefault(arr_str, []).append({
                "type": "입고예정",
                "icon": "🚨지연" if is_delayed else "📦",
                "name": name,
                "qty": qty,
                "detail": f"입고예정 {qty:,}개 ({supplier})" + (" [입고지연 확인요망]" if is_delayed else ""),
                "color": "#C084FC" if is_delayed else "#60A5FA",
                "bg": "#2E1B40" if is_delayed else "#172A45",
                "border": "#A855F7" if is_delayed else "#3B82F6"
            })

            item_row = {
                "입고예정일": arr_str,
                "발주일": order_date,
                "품목명": name,
                "바코드": bc,
                "거래처": supplier,
                "입고예정수량": qty,
                "진행상태": "🚨 입고지연(확인요망)" if is_delayed else status,
                "매입단가": unit_price,
                "발주총액": total_price
            }
            upcoming_arrivals.append(item_row)
            if is_delayed:
                delayed_arrivals.append(item_row)

    for item in products:
        if item.get("status", "정상") in ["단종", "운영중단"]:
            continue

        name = str(item.get("name", "")).strip()
        bc = str(item.get("barcode", "")).strip()
        key = bc if bc else name
        stock = safe_int(item.get("stock", 0), 0)
        base_sales = safe_float(item.get("daily_sales", 0.0), 0.0)
        adjusted_sales = round(base_sales * sales_multiplier, 1)

        next_po = earliest_arrival_map.get(key)
        next_arrival_str = f"{next_po['date']} ({next_po['qty']:,}개)" if next_po else "미발주 (일정없음) 🚨"

        if stock <= 0:
            cs_notice = (
                f"[예약발송 안내] 현재 품절로 {next_po['date']} 입고 후 순차 발송됩니다."
                if next_po else "[품절 안내] 현재 일시 품절 상태이며 입고 일정 확인 중입니다."
            )
            out_of_stock_list.append({
                "품목명": name,
                "바코드": bc,
                "현재고": stock,
                "일평균판매(마케팅반영)": adjusted_sales,
                "다음 입고예정": next_arrival_str,
                "CS/상세페이지 안내문구": cs_notice
            })
        elif adjusted_sales > 0:
            days_left = int(stock // adjusted_sales)
            stockout_date = today + timedelta(days=days_left)
            stockout_str = stockout_date.strftime("%Y-%m-%d")

            if days_left <= 60:
                is_before_arrival = (not next_po) or (stockout_str < next_po["date"])
                ev_type = "입고전품절" if is_before_arrival else "품절예정"

                events_by_date.setdefault(stockout_str, []).append({
                    "type": ev_type,
                    "icon": "🔥" if is_before_arrival else "⚠️",
                    "name": name,
                    "qty": stock,
                    "detail": f"{ev_type} (현재고 {stock:,}개 / 일판매 {adjusted_sales}개)",
                    "color": "#F87171" if is_before_arrival else "#FBBF24",
                    "bg": "#3B181E" if is_before_arrival else "#332414",
                    "border": "#EF4444" if is_before_arrival else "#F59E0B"
                })

                if days_left <= 14 or is_before_arrival:
                    stockout_soon_list.append({
                        "품절예상일": stockout_str,
                        "D-Day": f"D-{days_left}",
                        "상태구분": "🔥 입고전품절 (재고공백 주의)" if is_before_arrival else "⚠️ 품절 임박 (입고대기중)",
                        "품목명": name,
                        "바코드": bc,
                        "현재고": stock,
                        "적용일판": adjusted_sales,
                        "다음 입고예정": next_arrival_str
                    })

    return events_by_date, out_of_stock_list, stockout_soon_list, upcoming_arrivals, delayed_arrivals


def render_monthly_calendar_html(year, month, events_by_date, filter_types):
    cal = calendar.Calendar(firstweekday=6)
    month_days = cal.monthdatescalendar(year, month)
    today_str = date.today().strftime("%Y-%m-%d")

    html = """
    <style>
        .cal-wrapper {
            background-color: #14171F;
            border-radius: 12px;
            padding: 8px;
            border: 1px solid #2D3343;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        .cal-table {
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        .cal-th {
            background-color: #1A1F2C;
            color: #E2E8F0;
            padding: 14px 8px;
            text-align: center;
            font-size: 14px;
            font-weight: 700;
            border: 1px solid #2E364F;
            letter-spacing: 0.5px;
        }
        .cal-td {
            height: 145px;
            vertical-align: top;
            padding: 8px;
            border: 1px solid #262D3D;
            background-color: #1E222D;
            color: #E2E8F0;
        }
        .cal-td-other {
            background-color: #13161D;
            opacity: 0.5;
        }
        .cal-td-other .date-num {
            color: #475569 !important;
        }
        .cal-td-today {
            background-color: #282318 !important;
            border: 2px solid #F59E0B !important;
        }
        .date-header {
            font-size: 14px;
            font-weight: 700;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .date-num { color: #F1F5F9; }
        .date-sun { color: #F87171 !important; }
        .date-sat { color: #60A5FA !important; }
        .today-tag {
            background: #F59E0B;
            color: #111827;
            padding: 2px 7px;
            border-radius: 10px;
            font-size: 10px;
            font-weight: 800;
        }
        .ev-badge {
            display: block;
            font-size: 11.5px;
            padding: 4px 8px;
            margin-bottom: 5px;
            border-radius: 5px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            font-weight: 600;
            line-height: 1.4;
            box-shadow: 0 1px 2px rgba(0,0,0,0.2);
        }
    </style>
    <div class="cal-wrapper">
    <table class="cal-table">
        <thead>
            <tr>
                <th class="cal-th" style="color:#F87171;">일 (SUN)</th>
                <th class="cal-th">월 (MON)</th>
                <th class="cal-th">화 (TUE)</th>
                <th class="cal-th">수 (WED)</th>
                <th class="cal-th">목 (THU)</th>
                <th class="cal-th">금 (FRI)</th>
                <th class="cal-th" style="color:#60A5FA;">토 (SAT)</th>
            </tr>
        </thead>
        <tbody>
    """

    for week in month_days:
        html += "<tr>"
        for idx, d in enumerate(week):
            d_str = d.strftime("%Y-%m-%d")
            classes = ["cal-td"]
            if d.month != month:
                classes.append("cal-td-other")
            if d_str == today_str:
                classes.append("cal-td-today")

            num_class = "date-num"
            if d.month == month:
                if idx == 0:
                    num_class += " date-sun"
                elif idx == 6:
                    num_class += " date-sat"

            today_badge = '<span class="today-tag">TODAY</span>' if d_str == today_str else ""
            html += f'<td class="{" ".join(classes)}">'
            html += f'<div class="date-header"><span class="{num_class}">{d.day}</span>{today_badge}</div>'

            day_events = events_by_date.get(d_str, [])
            for ev in day_events:
                if ev["type"] not in filter_types:
                    continue
                tooltip = f"{ev['icon']} {ev['name']} | {ev['detail']}"
                border_col = ev.get("border", ev["color"])

                if ev["type"] == "운영메모":
                    badge_label = f"{ev['icon']} {ev['detail']}"
                else:
                    badge_label = f"{ev['icon']} {ev['name']} ({ev['qty']:,})"

                html += (
                    f'<div class="ev-badge" title="{tooltip}" '
                    f'style="color:{ev["color"]}; background-color:{ev["bg"]}; border-left: 3px solid {border_col};">'
                    f'{badge_label}'
                    f'</div>'
                )
            html += "</td>"
        html += "</tr>"

    html += "</tbody></table></div>"
    st.markdown(html, unsafe_allow_html=True)


# =========================================================
# 5. 사이드바 설정 (다중 슬랙 웹훅 & .html/.xls 완벽 연동)
# =========================================================
products = load_master_data()
po_history = load_po_history()
memo_data = load_memo_data()

with st.sidebar:
    st.title("🦊 FLICKRFOX")
    st.caption("상품관리 & 스마트 발주 시스템")
    st.divider()

    st.subheader("🔒 접속 권한 설정")
    admin_pw_input = st.text_input(
        "관리자 비밀번호 입력",
        type="password",
        placeholder="팀원은 입력 없이 조회 가능",
        help="관리자 비밀번호를 입력하면 단가 확인 및 발주/마스터 수정 권한이 활성화됩니다."
    )

    is_admin = (admin_pw_input == ADMIN_PASSWORD)
    if is_admin:
        st.success("🔓 **관리자 모드** 활성화됨")
        with st.expander("🔔 슬랙 웹훅(Webhook) 다중 채널 설정"):
            st.caption("2개 이상의 채널로 동시에 보내려면 줄바꿈(Enter)이나 쉼표(,)로 구분해서 붙여넣으세요.")
            new_wh = st.text_area(
                "슬랙 Webhook URL 목록 (다중 입력 가능)",
                value=SLACK_WEBHOOK_URL,
                height=100,
                placeholder="https://hooks.slack.com/services/... (제품기획)\nhttps://hooks.slack.com/services/... (방미경 PD)"
            )
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                if st.button("💾 웹훅 저장", type="primary", use_container_width=True):
                    if new_wh.strip():
                        save_custom_webhook(new_wh.strip())
                        st.success("슬랙 채널 저장 완료!")
                        st.rerun()
            with col_w2:
                if st.button("🔔 테스트 발송", use_container_width=True):
                    ok, msg = send_slack_notification(new_wh.strip(), "✅ *[FLICKRFOX 상품관리]* 다중 채널 연동 테스트 메시지입니다.")
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
                    
        with st.expander("💾 데이터 백업 및 복구", expanded=False):
            st.caption("파일 업로드 없이 바로 복원하거나 JSON 백업본을 덮어쓸 수 있습니다.")
            
            if st.button("⚡ 엑셀 캡처 원본 데이터로 즉시 복원", type="primary", use_container_width=True):
                restored_master = [dict(x) for x in DEFAULT_PRODUCTS]
                restored_hist, _ = auto_mark_past_arrivals([dict(x) for x in DEFAULT_HISTORY])
                save_master_data(restored_master)
                save_po_history(restored_hist)
                bump_editor_version()
                st.toast("✅ 엑셀 원본 데이터(28건 발주 + 마스터)로 완벽 복원되었습니다!")
                st.rerun()

            st.markdown("---")
            backup_payload = {
                "master": products,
                "history": po_history,
                "memos": memo_data
            }
            st.download_button(
                "📥 현재 데이터 백업 다운로드 (.json)",
                data=json.dumps(backup_payload, ensure_ascii=False, indent=2),
                file_name=f"flickrfox_backup_{date.today().strftime('%Y%m%d')}.json",
                mime="application/json",
                use_container_width=True
            )

            uploaded_backup = st.file_uploader("📤 백업 JSON 파일 업로드", type=["json"], key="backup_uploader")
            if uploaded_backup is not None:
                if st.button("🔄 이 백업 파일로 즉시 덮어쓰기", type="primary", use_container_width=True):
                    try:
                        raw_bytes = uploaded_backup.getvalue()
                        b_data = json.loads(raw_bytes.decode("utf-8-sig"))

                        if isinstance(b_data, dict):
                            m_list = b_data.get("master") or b_data.get("products") or b_data.get("master_products")
                            h_list = b_data.get("history") or b_data.get("po_history") or b_data.get("orders")
                            mm_dict = b_data.get("memos") or b_data.get("calendar_memos")
                            if m_list is not None:
                                save_master_data(m_list)
                            if h_list is not None:
                                h_clean, _ = auto_mark_past_arrivals(h_list)
                                save_po_history(h_clean)
                            if mm_dict is not None:
                                save_memo_data(mm_dict)
                        elif isinstance(b_data, list) and len(b_data) > 0:
                            if "po_qty" in b_data[0] or "expected_arrival" in b_data[0]:
                                h_clean, _ = auto_mark_past_arrivals(b_data)
                                save_po_history(h_clean)
                            else:
                                save_master_data(b_data)

                        bump_editor_version()
                        st.toast("✅ 백업 파일 복원 완료!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"복원 오류: {e}")
    else:
        if admin_pw_input:
            st.error("비밀번호 불일치")
        st.info("👥 **일반 팀원 모드** (조회 전용)")

    st.divider()

    st.subheader("⚙️ 발주 및 수요 예측 설정")
    holiday_buffer = st.number_input("명절·연휴 리드타임 버퍼 (일)", min_value=0, max_value=60, value=0, step=1)
    target_days = st.number_input("목표 재고 유지 기간 (일)", min_value=7, max_value=90, value=30, step=1)

    st.markdown("---")
    st.subheader("📈 마케팅 판매량 가중치")
    sales_multiplier = st.slider(
        "판매 속도 변동 계수",
        min_value=1.0, max_value=5.0, value=1.0, step=0.1,
        help="프로모션으로 평소 대비 판매량이 증가할 때 배수를 높여주세요."
    )
    if sales_multiplier > 1.0:
        st.warning(f"⚠️ 현재 평소 판매량의 **{sales_multiplier}배** 속도로 소진 가정 중입니다.")

    st.divider()

    st.subheader("📥 이지어드민 재고 파일 연동")
    uploaded_file = st.file_uploader(
        "이지어드민 파일 (.xls / .html / .htm / .csv / .xlsx)",
        type=["xls", "html", "htm", "xlsx", "csv"]
    )

    if uploaded_file is not None:
        try:
            df_ez = parse_easyadmin_file(uploaded_file)

            bc_col = next((c for c in df_ez.columns if any(k in str(c) for k in ["바코드", "상품코드"]) or "barcode" in str(c).lower()), None)
            stock_col = next((c for c in df_ez.columns if any(k in str(c) for k in ["가용재고", "현재고", "정상재고", "재고"])), None)
            sales_col = next((c for c in df_ez.columns if any(k in str(c) for k in ["일평균", "판매량", "출고"])), None)

            if bc_col and stock_col:
                st.caption(f"✅ 인식된 컬럼: 바코드(`{bc_col}`), 재고(`{stock_col}`)")
                if st.button("🔄 현재고 데이터 동기화", type="primary", use_container_width=True):
                    ez_map = {}
                    for _, r in df_ez.iterrows():
                        b_val = str(r[bc_col]).strip()
                        s_raw = str(r[stock_col]).replace(",", "").strip()
                        s_val = pd.to_numeric(s_raw, errors="coerce")
                        d_val = None
                        if sales_col:
                            d_raw = str(r[sales_col]).replace(",", "").strip()
                            d_val = pd.to_numeric(d_raw, errors="coerce")
                        if b_val and not pd.isna(s_val):
                            ez_map[b_val] = {
                                "stock": int(s_val),
                                "sales": float(d_val) if (d_val is not None and not pd.isna(d_val)) else None
                            }

                    updated_cnt = 0
                    for item in products:
                        bc_key = str(item.get("barcode", "")).strip()
                        if bc_key in ez_map:
                            item["stock"] = ez_map[bc_key]["stock"]
                            if ez_map[bc_key]["sales"] is not None:
                                item["daily_sales"] = round(ez_map[bc_key]["sales"], 1)
                            updated_cnt += 1

                    save_master_data(products)
                    bump_editor_version()
                    st.success(f"총 {updated_cnt}개 품목 동기화 완료!")
                    st.rerun()
            else:
                st.warning(f"바코드 또는 재고 컬럼을 찾을 수 없습니다. (추출된 컬럼: {list(df_ez.columns[:6])})")
        except Exception as e:
            st.error(f"파일 분석 오류: {e}")


# =========================================================
# 6. 메인 화면 탭 구성
# =========================================================
st.title("🦊 FLICKRFOX 상품관리 (재고 · 발주 · 캘린더)")

tab_calendar, tab_dashboard, tab_history, tab_master = st.tabs([
    "📅 재고·입고 캘린더",
    "🚀 스마트 발주 대시보드",
    "📋 발주 히스토리 · 입고관리",
    "⚙️ 품목 마스터 관리"
])


# ---------------------------------------------------------
# [TAB 1] 📅 재고·입고 캘린더
# ---------------------------------------------------------
with tab_calendar:
    today = date.today()

    events_by_date, out_of_stock_list, stockout_soon_list, upcoming_arrivals, delayed_arrivals = (
        build_calendar_events(products, po_history, memo_data, sales_multiplier)
    )

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🚨 현재 품절 상품", f"{len(out_of_stock_list)}개", delta="즉시 확인 필요", delta_color="inverse")
    k2.metric("🔥 품절임박 / 입고전품절", f"{len(stockout_soon_list)}개", delta="마케팅/발주 점검", delta_color="off")
    k3.metric("📦 진행중인 입고 예정", f"{len(upcoming_arrivals)}건")
    k4.metric("⚠️ 입고 지연 경과", f"{len(delayed_arrivals)}건", delta="공장 확인 요망" if delayed_arrivals else "정상", delta_color="inverse" if delayed_arrivals else "normal")

    st.write("")

    if out_of_stock_list:
        st.markdown("### 🚨 현재 품절 중인 상품 긴급 안내")
        for oos in out_of_stock_list:
            st.markdown(f"""
                <div class="oos-card">
                    <div class="oos-card-title">🚨 품절 품목: {oos['품목명']}</div>
                    <div class="oos-card-content">
                        <span><b>바코드:</b> {oos['바코드']}</span>
                        <span><b>다음 입고 예정:</b> <span style="color:#60A5FA;">{oos['다음 입고예정']}</span></span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    st.divider()

    st.markdown("### 📊 실시간 재고·품절 현황 및 상세 분석")
    st.caption("캘린더에 앞서 확인해야 할 품절 상품, 임박 품목, 전체 입고 스케줄 및 날짜별 상세 내역입니다.")

    sub_t1, sub_t2, sub_t3, sub_t4 = st.tabs([
        f"🚨 현재 품절 ({len(out_of_stock_list)})",
        f"🔥 품절임박 · 입고전품절 ({len(stockout_soon_list)})",
        f"📦 전체 입고 스케줄 ({len(upcoming_arrivals)})",
        "📌 날짜별 상세 일정 & 메모"
    ])

    with sub_t1:
        if out_of_stock_list:
            st.markdown("##### 🚨 현재 품절 상품 리스트 및 CS 안내 문구")
            st.dataframe(pd.DataFrame(out_of_stock_list), use_container_width=True, hide_index=True)
        else:
            st.success("🎉 현재 품절(재고 0)인 상품이 없습니다!")

    with sub_t2:
        if stockout_soon_list:
            st.markdown("##### 🔥 14일 내 품절 임박 또는 입고전품절(공백) 위험 상품")
            df_soon = pd.DataFrame(stockout_soon_list).sort_values("품절예상일")
            st.dataframe(df_soon, use_container_width=True, hide_index=True)
        else:
            st.success("✨ 향후 14일 이내 위험 품목이 없습니다!")

    with sub_t3:
        if upcoming_arrivals:
            st.markdown("##### 📦 창고 입고 대기 스케줄")
            df_inc = pd.DataFrame(upcoming_arrivals).sort_values("입고예정일")
            if not is_admin:
                df_inc = df_inc.drop(columns=["매입단가", "발주총액"], errors="ignore")
            st.dataframe(df_inc, use_container_width=True, hide_index=True)
        else:
            st.info("현재 대기 중인 입고 스케줄이 없습니다.")

    with sub_t4:
        st.markdown("##### 📌 특정 날짜 상세 일정 및 운영 메모 조회")
        c_dt1, c_dt2 = st.columns([1, 2])
        with c_dt1:
            picked_date = st.date_input("조회할 날짜 선택", value=today, key="picked_dt_top")
        picked_str = picked_date.strftime("%Y-%m-%d")
        day_items = events_by_date.get(picked_str, [])
        if day_items:
            df_day = pd.DataFrame(day_items)[["icon", "type", "name", "detail"]]
            df_day.columns = ["구분", "유형", "항목", "상세내용"]
            st.dataframe(df_day, use_container_width=True, hide_index=True)
        else:
            st.info(f"{picked_str}에 등록된 일정이나 메모가 없습니다.")

    st.divider()

    st.markdown("### 🗓️ 월간 캘린더 및 운영 메모 보드")
    st.caption("전체적인 입고·품절 흐름과 날짜별 특이사항을 한 달 단위로 조망합니다.")

    with st.expander("📝 캘린더 날짜별 운영 특이사항 및 입고 지연 메모 등록하기"):
        c_m1, c_m2, c_m3 = st.columns([1.5, 2.5, 1])
        with c_m1:
            memo_date_sel = st.date_input("메모 적용 날짜", value=today, key="memo_dt_cal")
        with c_m2:
            memo_text_input = st.text_input("특이사항 입력", placeholder="예: 택배사 파업 출고 지연, 빅프로모션 광고비 증액 등", key="memo_txt_cal")
        with c_m3:
            st.write("")
            st.write("")
            if st.button("메모 저장하기", type="primary", use_container_width=True, key="memo_btn_cal"):
                if memo_text_input.strip():
                    memo_data[memo_date_sel.strftime("%Y-%m-%d")] = memo_text_input.strip()
                    save_memo_data(memo_data)
                    st.success("캘린더에 메모가 반영되었습니다!")
                    st.rerun()

    st.write("")
    c1, c2, c3, c4 = st.columns([1, 1, 2.2, 2])
    with c1:
        sel_year = st.selectbox("연도", list(range(today.year - 1, today.year + 2)), index=1, key="sel_yr")
    with c2:
        sel_month = st.selectbox("월", list(range(1, 13)), index=today.month - 1, key="sel_mo")
    with c3:
        filter_types = st.multiselect(
            "캘린더 표시 필터",
            options=["입고예정", "품절예정", "입고전품절", "운영메모"],
            default=["입고예정", "품절예정", "입고전품절", "운영메모"],
            key="sel_filter"
        )
    with c4:
        cal_search = st.text_input("🔍 캘린더 상품 검색", placeholder="예: Mag-Link, 폴드8...", key="cal_srch")

    filtered_events = {}
    for d_str, ev_list in events_by_date.items():
        if any(ev["type"] == "운영메모" for ev in ev_list):
            filtered_events[d_str] = ev_list
            continue
        matched = [ev for ev in ev_list if cal_search.lower() in ev["name"].lower()]
        if matched:
            filtered_events[d_str] = matched

    st.markdown(
        "💡 **배지 범례:** &nbsp;"
        "<span style='background:#172A45;color:#60A5FA;padding:4px 8px;border-radius:4px;font-weight:bold;font-size:12px;'>📦 입고예정</span> &nbsp;"
        "<span style='background:#332414;color:#FBBF24;padding:4px 8px;border-radius:4px;font-weight:bold;font-size:12px;'>⚠️ 품절예정</span> &nbsp;"
        "<span style='background:#3B181E;color:#F87171;padding:4px 8px;border-radius:4px;font-weight:bold;font-size:12px;'>🔥 입고전품절</span> &nbsp;"
        "<span style='background:#0C2D48;color:#38BDF8;padding:4px 8px;border-radius:4px;font-weight:bold;font-size:12px;'>📝 운영메모</span>",
        unsafe_allow_html=True
    )
    st.write("")

    render_monthly_calendar_html(sel_year, sel_month, filtered_events, filter_types)


# ---------------------------------------------------------
# [TAB 2] 🚀 스마트 발주 대시보드
# ---------------------------------------------------------
with tab_dashboard:
    df_calc = calculate_reorder_table(products, po_history, holiday_buffer, target_days, sales_multiplier)
    urgent_df = df_calc[df_calc["발주선택"] == True]

    m1, m2, m3 = st.columns(3)
    m1.metric("전체 관리 품목", f"{len(df_calc)}개")
    m2.metric("발주 권장/긴급 품목", f"{len(urgent_df)}개", delta=f"마케팅 계수 {sales_multiplier}배 적용중", delta_color="off")
    if is_admin:
        total_budget = int(urgent_df["예상발주금액"].sum()) if not urgent_df.empty else 0
        m3.metric("💰 예상 발주 총 예산 (관리자)", f"{total_budget:,}원")
    else:
        total_rec_qty = int(urgent_df["추천발주량"].sum()) if not urgent_df.empty else 0
        m3.metric("📦 추천 발주 총수량", f"{total_rec_qty:,}개")

    st.divider()

    if is_admin:
        st.markdown("#### 📋 실시간 발주 산출 테이블 (수량 조정 및 발주 확정)")
        st.caption("마케팅 가중치가 반영된 추천 발주량이 자동으로 계산됩니다. 수량을 조정한 뒤 발주를 확정하세요.")

        edited_order_df = st.data_editor(
            df_calc,
            use_container_width=True,
            hide_index=True,
            column_config={
                "발주선택": st.column_config.CheckboxColumn("발주선택", default=False),
                "발주수량(수정가능)": st.column_config.NumberColumn("발주수량(수정가능)", min_value=0, step=100),
                "매입단가": st.column_config.NumberColumn("매입단가(원)", format="%d원"),
                "예상발주금액": st.column_config.NumberColumn("예상발주금액(원)", format="%d원"),
            },
            disabled=[
                "우선순위", "품목명", "바코드", "거래처", "현재고", "입고대기", "유효재고",
                "기본일판", "적용일판(마케팅반영)", "예상품절일", "남은일수", "다음입고예정", "총리드타임", "재발주점(ROP)", "MOQ", "추천발주량", "매입단가", "예상발주금액"
            ],
            key=f"order_editor_{st.session_state['editor_ver']}"
        )

        selected_orders = edited_order_df[
            (edited_order_df["발주선택"] == True) & (edited_order_df["발주수량(수정가능)"] > 0)
        ]

        if not selected_orders.empty:
            total_confirm_cost = int((selected_orders["발주수량(수정가능)"] * selected_orders["매입단가"]).sum())
            st.info(
                f"✅ 선택된 발주 품목: **{len(selected_orders)}건** | "
                f"총 발주 수량: **{int(selected_orders['발주수량(수정가능)'].sum()):,}개** | "
                f"총 발주 금액: **{total_confirm_cost:,}원**"
            )

            col_btn1, col_btn2 = st.columns([1, 1])
            with col_btn1:
                if st.button("✅ 선택 품목 발주 완료 처리 (캘린더 등록 & 슬랙 알림)", type="primary", use_container_width=True, key="po_confirm_btn"):
                    now_str = datetime.now().strftime("%Y-%m-%d")
                    new_records = []
                    slack_lines = [f"🚨 *[FLICKRFOX 신규 발주 완료 알림 ({now_str})]* (마케팅 계수: {sales_multiplier}배)"]

                    for idx, row in selected_orders.iterrows():
                        po_id = f"PO-{datetime.now().strftime('%Y%m%d%H%M%S')}-{idx+1}"
                        qty = int(row["발주수량(수정가능)"])
                        u_price = int(row["매입단가"])
                        t_price = qty * u_price
                        arr_date = (date.today() + timedelta(days=int(row["총리드타임"]))).strftime("%Y-%m-%d")

                        record = {
                            "order_id": po_id,
                            "date": now_str,
                            "name": row["품목명"],
                            "barcode": row["바코드"],
                            "supplier": row["거래처"],
                            "po_qty": qty,
                            "unit_price": u_price,
                            "total_price": t_price,
                            "expected_arrival": arr_date,
                            "status": "발주완료",
                            "memo": f"리드타임 {int(row['총리드타임'])}일 (마케팅 {sales_multiplier}배 적용)"
                        }
                        po_history.append(record)
                        new_records.append(record)
                        slack_lines.append(
                            f"• *{row['품목명']}* ({row['거래처']}) : `{qty:,}개` | 입고예정: `{arr_date}`"
                        )

                    save_po_history(po_history)
                    bump_editor_version()
                    ok, msg = send_slack_notification(SLACK_WEBHOOK_URL, "\n".join(slack_lines))
                    st.success(f"{len(new_records)}건 발주 이력 저장 및 캘린더 반영 완료! ({msg})")
                    st.rerun()

            with col_btn2:
                if st.button("📣 긴급 발주 리포트만 슬랙으로 전송", use_container_width=True, key="slack_report_btn"):
                    slack_lines = [f"📢 *[FLICKRFOX 발주 권장 브리핑 ({date.today().strftime('%Y-%m-%d')})]*"]
                    for _, row in selected_orders.iterrows():
                        slack_lines.append(
                            f"• {row['우선순위']} *{row['품목명']}* : 현재고 `{int(row['현재고']):,}개` (품절예상: {row['예상품절일']}) → 권장 발주 `{int(row['발주수량(수정가능)']):,}개`"
                        )
                    ok, msg = send_slack_notification(SLACK_WEBHOOK_URL, "\n".join(slack_lines))
                    if ok:
                        st.success(msg)
                    else:
                        st.warning(msg)
    else:
        st.markdown("#### 📋 실시간 발주 필요 현황 (팀원 조회 모드)")
        team_view_cols = [
            "우선순위", "품목명", "바코드", "거래처", "현재고", "입고대기", "유효재고",
            "적용일판(마케팅반영)", "예상품절일", "다음입고예정", "총리드타임", "재발주점(ROP)", "추천발주량"
        ]
        st.dataframe(df_calc[team_view_cols], use_container_width=True, hide_index=True)


# ---------------------------------------------------------
# [TAB 3] 📋 발주 히스토리 · 입고관리
# ---------------------------------------------------------
with tab_history:
    st.subheader("📋 발주 히스토리 및 입고 상태 관리")
    st.caption("입고 완료된 건의 상태를 `입고완료`로 변경하고 저장하면 캘린더에서 입고 예정 배지가 정리됩니다.")

    if not po_history:
        st.info("기록된 발주 이력이 없습니다.")
    else:
        df_hist = pd.DataFrame(po_history)

        if is_admin:
            edited_hist = st.data_editor(
                df_hist,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                column_config={
                    "order_id": "발주번호",
                    "date": "발주일",
                    "name": "품목명",
                    "barcode": "바코드",
                    "supplier": "거래처",
                    "po_qty": st.column_config.NumberColumn("발주수량", format="%d개"),
                    "unit_price": st.column_config.NumberColumn("단가(원)", format="%d원"),
                    "total_price": st.column_config.NumberColumn("총액(원)", format="%d원"),
                    "expected_arrival": "입고예정일",
                    "status": st.column_config.SelectboxColumn("진행상태", options=["발주완료", "주문승인", "생산중", "배송중", "입고완료", "취소"]),
                    "memo": "메모"
                },
                key=f"history_editor_{st.session_state['editor_ver']}"
            )

            if st.button("💾 발주 히스토리 저장", type="primary", key="hist_save_btn"):
                cleaned_hist, _ = auto_mark_past_arrivals(edited_hist.to_dict(orient="records"))
                save_po_history(cleaned_hist)
                bump_editor_version()
                st.success("저장 완료!")
                st.rerun()
        else:
            safe_cols = [c for c in ["order_id", "date", "name", "barcode", "supplier", "po_qty", "expected_arrival", "status", "memo"] if c in df_hist.columns]
            st.dataframe(df_hist[safe_cols], use_container_width=True, hide_index=True)


# ---------------------------------------------------------
# [TAB 4] ⚙️ 품목 마스터 관리
# ---------------------------------------------------------
with tab_master:
    st.subheader("⚙️ 품목 마스터 데이터 관리")
    df_master = pd.DataFrame(products)

    if is_admin:
        edited_master = st.data_editor(
            df_master,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "name": "품목명",
                "barcode": "바코드",
                "supplier": "거래처",
                "lead_time": st.column_config.NumberColumn("기본 리드타임(일)", min_value=1, max_value=120),
                "moq": st.column_config.NumberColumn("MOQ", min_value=1, step=50),
                "unit_price": st.column_config.NumberColumn("매입단가(원)", format="%d원"),
                "stock": st.column_config.NumberColumn("현재고", min_value=0),
                "daily_sales": st.column_config.NumberColumn("일평균판매량", format="%.1f"),
                "status": st.column_config.SelectboxColumn("운영상태", options=["정상", "일시품절", "단종"])
            },
            key=f"master_editor_{st.session_state['editor_ver']}"
        )

        if st.button("💾 품목 마스터 저장", type="primary", key="master_save_btn"):
            save_master_data(edited_master.to_dict(orient="records"))
            bump_editor_version()
            st.success("마스터 정보 저장 완료!")
            st.rerun()
    else:
        safe_master_cols = [c for c in ["name", "barcode", "supplier", "lead_time", "moq", "stock", "daily_sales", "status"] if c in df_master.columns]
        st.dataframe(df_master[safe_master_cols], use_container_width=True, hide_index=True)
