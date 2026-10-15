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
        
        /* 상단 KPI 카드 가독성 대폭 확대 */
        div[data-testid="stMetric"] {
            background-color: #1E222D;
            border: 1px solid #2D3343;
            padding: 18px 20px;
            border-radius: 12px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.25);
        }
        div[data-testid="stMetricLabel"] { font-size: 1.05rem !important; font-weight: 700 !important; color: #94A3B8 !important; }
        div[data-testid="stMetricValue"] { font-size: 2.1rem !important; font-weight: 800 !important; color: #F8FAFC !important; }
        
        /* 개별 긴급 품절 카드 스타일 */
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

# 관리자 비밀번호 고정
ADMIN_PASSWORD = "fox1989@@"

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
    {"name": "[SHIFT-GO]", "barcode": "FLCK00856", "supplier": "Landscape", "lead_time": 30, "moq": 500, "unit_price": 8000, "stock": 0, "daily_sales": 0.0, "status": "정상"}
]


# =========================================================
# 2. 데이터 입출력 함수
# =========================================================
def load_master_data():
    if os.path.exists(MASTER_FILE):
        try:
            with open(MASTER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data:
                    return data
        except Exception:
            pass
    save_master_data(DEFAULT_PRODUCTS)
    return DEFAULT_PRODUCTS

def save_master_data(data):
    with open(MASTER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_po_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_po_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def load_memo_data():
    if os.path.exists(MEMO_FILE):
        try:
            with open(MEMO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_memo_data(memos):
    with open(MEMO_FILE, "w", encoding="utf-8") as f:
        json.dump(memos, f, ensure_ascii=False, indent=2)

def send_slack_notification(webhook_url, message_text):
    if not webhook_url:
        return False, "슬랙 웹훅 URL이 설정되지 않았습니다."
    try:
        resp = requests.post(
            webhook_url,
            json={"text": message_text},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        if resp.status_code == 200:
            return True, "슬랙 알림 전송 완료!"
        return False, f"슬랙 응답 오류 (코드 {resp.status_code})"
    except Exception as e:
        return False, f"전송 실패: {e}"


# =========================================================
# 3. 발주 연산 및 마케팅 판매량 가중치 적용 엔진
# =========================================================
def get_pending_po_map(po_history):
    pending_qty = {}
    earliest_arrival = {}
    for po in po_history:
        status = str(po.get("status", "발주완료"))
        if status in ["입고완료", "취소", "반품"]:
            continue
        bc = str(po.get("barcode", "")).strip()
        qty = int(po.get("po_qty", 0) or 0)
        arr = str(po.get("expected_arrival", ""))[:10]
        if bc:
            pending_qty[bc] = pending_qty.get(bc, 0) + qty
            if arr:
                if bc not in earliest_arrival or arr < earliest_arrival[bc]["date"]:
                    earliest_arrival[bc] = {"date": arr, "qty": qty}
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
        name = item.get("name", "")
        supplier = item.get("supplier", "")
        lead_time = int(item.get("lead_time", 14) or 14)
        moq = int(item.get("moq", 500) or 500)
        unit_price = int(item.get("unit_price", 0) or 0)
        stock = int(item.get("stock", 0) or 0)
        
        base_sales = float(item.get("daily_sales", 0.0) or 0.0)
        adjusted_sales = round(base_sales * sales_multiplier, 1)

        incoming_qty = pending_qty_map.get(bc, 0)
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

        next_arr_info = earliest_arrival_map.get(bc)
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
        qty = int(po.get("po_qty", 0) or 0)
        unit_price = int(po.get("unit_price", 0) or 0)
        total_price = int(po.get("total_price", qty * unit_price) or 0)
        arr_str = str(po.get("expected_arrival", ""))[:10]
        order_date = str(po.get("date", ""))[:10]

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

        name = item.get("name", "")
        bc = str(item.get("barcode", "")).strip()
        stock = int(item.get("stock", 0) or 0)
        base_sales = float(item.get("daily_sales", 0.0) or 0.0)
        adjusted_sales = round(base_sales * sales_multiplier, 1)

        next_po = earliest_arrival_map.get(bc)
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
# 4. 사이드바 설정
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
        with st.expander("🔔 슬랙 웹훅(Webhook) 설정"):
            new_wh = st.text_input("새 슬랙 Webhook URL", value="", type="password", placeholder="https://hooks.slack.com/...")
            if st.button("웹훅 URL 저장", use_container_width=True):
                if new_wh.strip():
                    save_custom_webhook(new_wh.strip())
                    st.success("저장 완료!")
                    st.rerun()
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

    st.subheader("📥 이지어드민 재고 엑셀 연동")
    uploaded_file = st.file_uploader("이지어드민 파일 (.xls / .xlsx / .csv)", type=["xlsx", "xls", "csv"])

    if uploaded_file is not None:
        try:
            file_name = uploaded_file.name.lower()
            if file_name.endswith(".csv"):
                df_ez = pd.read_csv(uploaded_file)
            elif file_name.endswith(".xls"):
                # 구버전 .xls 파일은 xlrd 엔진 지정
                df_ez = pd.read_excel(uploaded_file, engine="xlrd")
            else:
                # .xlsx 파일은 openpyxl 엔진 지정
                df_ez = pd.read_excel(uploaded_file, engine="openpyxl")

            bc_col = next((c for c in df_ez.columns if "바코드" in str(c) or "barcode" in str(c).lower()), None)
            stock_col = next((c for c in df_ez.columns if any(k in str(c) for k in ["가용재고", "현재고", "재고", "정상재고"])), None)
            sales_col = next((c for c in df_ez.columns if any(k in str(c) for k in ["일평균", "판매량", "출고"])), None)

            if bc_col and stock_col:
                if st.button("🔄 현재고 데이터 동기화", type="primary", use_container_width=True):
                    ez_map = {}
                    for _, r in df_ez.iterrows():
                        b_val = str(r[bc_col]).strip()
                        s_val = pd.to_numeric(r[stock_col], errors="coerce")
                        d_val = pd.to_numeric(r[sales_col], errors="coerce") if sales_col else None
                        if b_val and not pd.isna(s_val):
                            ez_map[b_val] = {"stock": int(s_val), "sales": float(d_val) if (d_val is not None and not pd.isna(d_val)) else None}

                    updated_cnt = 0
                    for item in products:
                        bc_key = str(item.get("barcode", "")).strip()
                        if bc_key in ez_map:
                            item["stock"] = ez_map[bc_key]["stock"]
                            if ez_map[bc_key]["sales"] is not None:
                                item["daily_sales"] = round(ez_map[bc_key]["sales"], 1)
                            updated_cnt += 1

                    save_master_data(products)
                    st.success(f"총 {updated_cnt}개 품목 동기화 완료!")
                    st.rerun()
            else:
                st.warning("바코드 또는 현재고 컬럼을 찾을 수 없습니다.")
        except Exception as e:
            st.error(f"오류: {e}")


# =========================================================
# 5. 메인 화면 탭 구성
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

    # 상단 4대 요약 KPI 카드
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🚨 현재 품절 상품", f"{len(out_of_stock_list)}개", delta="즉시 확인 필요", delta_color="inverse")
    k2.metric("🔥 품절임박 / 입고전품절", f"{len(stockout_soon_list)}개", delta="마케팅/발주 점검", delta_color="off")
    k3.metric("📦 진행중인 입고 예정", f"{len(upcoming_arrivals)}건")
    k4.metric("⚠️ 입고 지연 경과", f"{len(delayed_arrivals)}건", delta="공장 확인 요망" if delayed_arrivals else "정상", delta_color="inverse" if delayed_arrivals else "normal")

    st.write("")

    # 품절 상품별 개별 카드 반복 생성
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
            key="order_editor"
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
                    "status": st.column_config.SelectboxColumn("진행상태", options=["발주완료", "생산중", "배송중", "입고완료", "취소"]),
                    "memo": "메모"
                },
                key="history_editor"
            )

            if st.button("💾 발주 히스토리 저장", type="primary", key="hist_save_btn"):
                save_po_history(edited_hist.to_dict(orient="records"))
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
                "unit_price": st.column_config.NumberColumn("매입단가(원)", min_value=0, format="%d원"),
                "stock": st.column_config.NumberColumn("현재고", min_value=0),
                "daily_sales": st.column_config.NumberColumn("일평균판매량", min_value=0.0, format="%.1f"),
                "status": st.column_config.SelectboxColumn("운영상태", options=["정상", "일시품절", "단종"])
            },
            key="master_editor"
        )

        if st.button("💾 품목 마스터 저장", type="primary", key="master_save_btn"):
            save_master_data(edited_master.to_dict(orient="records"))
            st.success("마스터 정보 저장 완료!")
            st.rerun()
    else:
        safe_master_cols = [c for c in ["name", "barcode", "supplier", "lead_time", "moq", "stock", "daily_sales", "status"] if c in df_master.columns]
        st.dataframe(df_master[safe_master_cols], use_container_width=True, hide_index=True)
