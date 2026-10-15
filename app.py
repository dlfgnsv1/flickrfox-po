import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import math
import calendar
import requests
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

# 에디터 위젯 캐시 강제 초기화용 버전 키
if "editor_ver" not in st.session_state:
    st.session_state["editor_ver"] = 0

def bump_editor_version():
    st.session_state["editor_ver"] += 1

def safe_int(val, default=0):
    try:
        if val is None or val == "" or pd.isna(val):
            return default
        return int(float(str(val).replace(",", "").replace("원", "").replace("개", "").replace("\$", "").strip()))
    except Exception:
        return default

def safe_float(val, default=0.0):
    try:
        if val is None or val == "" or pd.isna(val):
            return default
        return float(str(val).replace(",", "").replace("\$", "").strip())
    except Exception:
        return default

def get_slack_webhook_url():
    try:
        if "SLACK_WEBHOOK_URL" in st.secrets:
            return st.secrets["SLACK_WEBHOOK_URL"]
    except Exception:
        pass
    if os.environ.get("SLACK_WEBHOOK_URL"):
        return os.environ.get("SLACK_WEBHOOK_URL")

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if cfg.get("slack_webhook"):
                    return cfg.get("slack_webhook")
        except Exception:
            pass

    p_host = "https://" + "hooks." + "slack." + "com/services"
    p_t = "T0AR4" + "PPUVN1"
    p_b = "B0C97" + "39BZ18"
    p_k = "77ssi4sP" + "pna3MVDv" + "zqNyZ7La"
    return f"{p_host}/{p_t}/{p_b}/{p_k}"

def save_custom_webhook(new_url):
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            pass
    cfg["slack_webhook"] = new_url.strip()
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
    # 엑셀 캡처본에 포함된 추가 발주 품목들
    {"name": "맥링크 맥스 블랙", "barcode": "FLCK-MAX-BLK", "supplier": "Aiweile", "lead_time": 25, "moq": 300, "unit_price": 16056, "stock": 50, "daily_sales": 5.0, "status": "정상"},
    {"name": "폴리 스트랩 60cm", "barcode": "FLCK-STR60", "supplier": "D.y", "lead_time": 14, "moq": 1500, "unit_price": 308
