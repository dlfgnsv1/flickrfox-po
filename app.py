import streamlit as st
import pandas as pd
import numpy as np
import requests
import os
import json
import math
from datetime import datetime, date, timedelta

# ==========================================
# 1. 페이지 설정 및 다크 사이버-텍 스타일 정의
# ==========================================
st.set_page_config(
    page_title="FLICKRFOX 발주 시스템",
    page_icon="https://ecimg.cafe24img.com/pg429b97198991081/nontidy/web/upload/favicon-c5fdfdd80324a6bed8d56b18fbd7ef0b.ico",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark Cyber-Tech UI CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, sans-serif;
    }
    
    .stApp {
        background-color: #0b0f14;
        color: #e6edf3;
    }
    
    .tabular-num {
        font-family: 'JetBrains Mono', monospace;
        font-variant-numeric: tabular-nums;
    }

    .hero-banner {
        background: linear-gradient(135deg, rgba(16, 24, 32, 0.95) 0%, rgba(13, 31, 28, 0.95) 100%);
        border: 1px solid #1f3a34;
        border-radius: 14px;
        padding: 24px 28px;
        margin-bottom: 24px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    }
    .hero-tag {
        display: inline-block;
        background: rgba(0, 255, 163, 0.12);
        color: #00ffa3;
        border: 1px solid rgba(0, 255, 163, 0.3);
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1px;
        margin-bottom: 10px;
    }
    .hero-title {
        font-size: 26px;
        font-weight: 800;
        color: #ffffff;
        margin: 0 0 6px 0;
        letter-spacing: -0.5px;
    }
    .hero-desc {
        color: #8b949e;
        font-size: 13px;
        margin: 0;
    }

    .kpi-card {
        background: #121820;
        border: 1px solid #212d3b;
        border-radius: 12px;
        padding: 16px 20px;
        transition: transform 0.15s ease, border-color 0.15s ease;
    }
    .kpi-card:hover {
        border-color: #00ffa3;
    }
    .kpi-label {
        font-size: 12px;
        font-weight: 600;
        color: #8b949e;
        margin-bottom: 6px;
    }
    .kpi-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 24px;
        font-weight: 700;
        color: #f0f6fc;
    }

    .po-card {
        background: #11171f;
        border: 1px solid #222d3d;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
    }
    .po-card.urgent { border-left: 4px solid #ff4d4f; }
    .po-card.warning { border-left: 4px solid #faad14; }
    .po-card.normal { border-left: 4px solid #00ffa3; }
    
    .badge-urgent {
        background: rgba(255, 77, 79, 0.15);
        color: #ff4d4f;
        border: 1px solid rgba(255, 77, 79, 0.3);
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 700;
    }
    .badge-warning {
        background: rgba(250, 173, 20, 0.15);
        color: #faad14;
        border: 1px solid rgba(250, 173, 20, 0.3);
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 700;
    }
    .badge-normal {
        background: rgba(0, 255, 163, 0.15);
        color: #00ffa3;
        border: 1px solid rgba(0, 255, 163, 0.3);
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 데이터 영구 저장 및 플리커폭스 주요 품목 초기화
# ==========================================
MASTER_FILE = "master_products.json"
HISTORY_FILE = "po_history.json"

# 이지어드민 실제 바코드와 주간 판매량 기반 핵심 주요 품목
DEFAULT_PRODUCTS = [
    {"name": "[Mag-Link PRO] Black", "barcode": "FLCK00894", "supplier": "제조협력A", "lead_time": 14, "moq": 1000, "unit_price": 12500, "stock": 294, "daily_sales": 44.6, "status": "정상"},
    {"name": "[Mag-Link PRO] Silver", "barcode": "FLCK00746", "supplier": "제조협력A", "lead_time": 14, "moq": 1000, "unit_price": 12500, "stock": 386, "daily_sales": 24.1, "status": "정상"},
    {"name": "[360 TurnStand Wallet PLUS] Black", "barcode": "FLCK00587", "supplier": "제조협력B", "lead_time": 30, "moq": 1000, "unit_price": 8500, "stock": 466, "daily_sales": 37.7, "status": "정상"},
    {"name": "[360 TurnStand Wallet PLUS] Green", "barcode": "FLCK00824", "supplier": "제조협력B", "lead_time": 30, "moq": 500, "unit_price": 8500, "stock": 370, "daily_sales": 10.3, "status": "정상"},
    {"name": "[360 TurnStand Wallet PLUS] Brown", "barcode": "FLCK00825", "supplier": "제조협력B", "lead_time": 30, "moq": 500, "unit_price": 8500, "stock": 110, "daily_sales": 3.9, "status": "정상"},
    {"name": "[OctoLock]", "barcode": "FLCK00609", "supplier": "제조협력C", "lead_time": 25, "moq": 1000, "unit_price": 6800, "stock": 173, "daily_sales": 28.4, "status": "정상"},
    {"name": "[OctoLock PRO] Black", "barcode": "FLCK00659", "supplier": "제조협력C", "lead_time": 25, "moq": 500, "unit_price": 7900, "stock": 0, "daily_sales": 0.5, "status": "정상"},
    {"name": "[MATTE-ONE] Z Fold 8", "barcode": "FLCK00867", "supplier": "케이스공장", "lead_time": 20, "moq": 500, "unit_price": 9500, "stock": 9, "daily_sales": 8.1, "status": "정상"},
    {"name": "[MATTE-ONE] Z Fold 7", "barcode": "FLCK00868", "supplier": "케이스공장", "lead_time": 20, "moq": 500, "unit_price": 9500, "stock": 123, "daily_sales": 5.0, "status": "정상"},
    {"name": "[MATTE-ONE] Z Fold 8 U", "barcode": "FLCK00869", "supplier": "케이스공장", "lead_time": 20, "moq": 500, "unit_price": 9500, "stock": 139, "daily_sales": 1.0, "status": "정상"},
    {"name": "[Matte-Shield/MB] Z Fold 8", "barcode": "FLCK00890", "supplier": "케이스공장", "lead_time": 20, "moq": 1000, "unit_price": 9800, "stock": 391, "daily_sales": 25.1, "status": "정상"},
    {"name": "[Matte-Shield/CW] Z Fold 8", "barcode": "FLCK00902", "supplier": "케이스공장", "lead_time": 20, "moq": 500, "unit_price": 9800, "stock": 14, "daily_sales": 11.9, "status": "정상"},
    {"name": "[Matte-Shield] Z Fold 7", "barcode": "FLCK00895", "supplier": "케이스공장", "lead_time": 20, "moq": 500, "unit_price": 9800, "stock": 87, "daily_sales": 12.9, "status": "정상"},
    {"name": "[Matte-Shield] Z Fold 8U", "barcode": "FLCK00891", "supplier": "케이스공장", "lead_time": 20, "moq": 500, "unit_price": 9800, "stock": 121, "daily_sales": 3.6, "status": "정상"},
    {"name": "[Aim Mag-Holder Pro]", "barcode": "FLCK00755", "supplier": "제조협력A", "lead_time": 30, "moq": 500, "unit_price": 10500, "stock": 400, "daily_sales": 10.9, "status": "정상"},
    {"name": "[Spring strap] Black", "barcode": "FLCK00838", "supplier": "부자재공장", "lead_time": 15, "moq": 1000, "unit_price": 1800, "stock": 302, "daily_sales": 37.4, "status": "정상"},
    {"name": "[Spider mag stand] Arctic Silver", "barcode": "FLCK00728", "supplier": "제조협력A", "lead_time": 30, "moq": 500, "unit_price": 7500, "stock": 200, "daily_sales": 0.9, "status": "정상"},
    {"name": "[SHIFT-GO]", "barcode": "FLCK00856", "supplier": "제조협력B", "lead_time": 30, "moq": 500, "unit_price": 8000, "stock": 0, "daily_sales": 0.0, "status": "정상"}
]

def load_master_data():
    if os.path.exists(MASTER_FILE):
        try:
            with open(MASTER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 이전 샘플 데이터(8809... 가짜 바코드)가 남아있다면 신규 마스터로 교체
                if data and "88090001" not in str(data):
                    return data
        except Exception:
            pass
    return DEFAULT_PRODUCTS

def save_master_data(data):
    with open(MASTER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    st.session_state.products = data

def load_history_data():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_history_data(data):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    st.session_state.po_history = data

if "products" not in st.session_state:
    st.session_state.products = load_master_data()
if "po_history" not in st.session_state:
    st.session_state.po_history = load_history_data()

# ==========================================
# 3. 사이드바 - 운영 파라미터 및 슬랙 연동
# ==========================================
with st.sidebar:
    st.markdown("### ⚙️ 발주 환경 파라미터")
    holiday_buffer = st.number_input("명절/연휴 추가 지연일 (일)", min_value=0, max_value=60, value=7, step=1)
    safety_stock_days = st.slider("안전재고 확보일수 (일)", min_value=7, max_value=60, value=14, step=1)
    target_coverage_days = st.slider("목표 충족일수 (일)", min_value=14, max_value=120, value=45, step=1)
    
    st.markdown("---")
    st.markdown("### 📢 슬랙(Slack) 연동")
    slack_webhook = st.text_input("Webhook URL", type="password", placeholder="https://hooks.slack.com/services/...", help="슬랙 채널 연동 웹훅 주소")

# ==========================================
# 4. 상단 배너
# ==========================================
st.markdown("""
<div class="hero-banner">
    <div class="hero-tag">FLICKRFOX SUPPLY CHAIN</div>
    <div class="hero-title">실시간 재고 & 발주 운영 시스템</div>
    <div class="hero-desc">거래처별 리드타임 동적 가산 및 이지어드민 연동 품절 방어 자동화 대시보드</div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📊 발주 대시보드", "📜 발주 히스토리", "📦 품목 마스터"])

# ==========================================
# TAB 1: 발주 대시보드
# ==========================================
with tab1:
    uploaded_file = st.file_uploader("이지어드민 [현재고조회] 엑셀 드래그 & 드롭 (.xlsx)", type=["xlsx", "xls"])
    
    if uploaded_file is not None:
        try:
            df_ez = pd.read_excel(uploaded_file)
            df_ez.columns = [str(c).strip().replace(" ", "") for c in df_ez.columns]

            barcode_col = next((c for c in df_ez.columns if any(k in c for k in ['바코드', '상품코드', '자체코드'])), None)
            stock_col = next((c for c in df_ez.columns if any(k in c for k in ['가용재고', '가용', '현재고', '정상재고'])), None)
            sales_col = next((c for c in df_ez.columns if any(k in c for k in ['1주발주합계', '주간발주', '출고량'])), None)

            if not barcode_col or not stock_col:
                st.error("❌ 엑셀에서 '바코드' 또는 '가용재고' 열을 찾지 못했습니다.")
            else:
                df_ez[barcode_col] = df_ez[barcode_col].astype(str).str.strip()
                matched_items = []

                # 마스터에 등록된 주요 품목 바코드만 선별 동기화
                for p in st.session_state.products:
                    target_bc = str(p.get("barcode", "")).strip()
                    match = df_ez[df_ez[barcode_col] == target_bc]
                    
                    if not match.empty:
                        # 재고 업데이트
                        val = match[stock_col].values[0]
                        p["stock"] = max(0, int(pd.to_numeric(val, errors='coerce') or 0))
                        
                        # 1주 발주합계가 있을 경우 일평균 판매량 자동 갱신 (1주 합계 ÷ 7)
                        if sales_col:
                            s_val = match[sales_col].values[0]
                            weekly_sales = float(pd.to_numeric(s_val, errors='coerce') or 0.0)
                            if weekly_sales > 0:
                                p["daily_sales"] = round(weekly_sales / 7.0, 1)

                        matched_items.append(f"{p['name']} ({p['stock']:,}개)")

                if matched_items:
                    save_master_data(st.session_state.products)
                    st.success(f"✅ 주요 품목 {len(matched_items)}건의 실시간 재고 및 판매량이 동기화되었습니다!")
                    with st.expander("동기화된 주요 품목 목록 확인"):
                        st.write(", ".join(matched_items))
                    st.rerun()
                else:
                    st.warning("⚠️ 엑셀은 정상 인식되었으나 등록된 주요 품목 바코드와 일치하는 데이터가 없습니다.")
        except Exception as e:
            st.error(f"엑셀 처리 오류: {e}")

    # 발주 수량 및 위험도 계산
    dashboard_items = []
    total_suggested_cost = 0
    urgent_count = 0
    warning_count = 0

    pending_stock_map = {}
    for h in st.session_state.po_history:
        if h.get("status") == "입고대기":
            bc = str(h.get("barcode", "")).strip()
            pending_stock_map[bc] = pending_stock_map.get(bc, 0) + int(h.get("po_qty", 0))

    for p in st.session_state.products:
        bc = str(p.get("barcode", "")).strip()
        stock = int(p.get("stock", 0))
        daily_sales = float(p.get("daily_sales", 0.0))
        base_lt = int(p.get("lead_time", 20))
        effective_lt = base_lt + holiday_buffer
        moq = int(p.get("moq", 500))
        unit_price = int(p.get("unit_price", 0))
        pending_stock = pending_stock_map.get(bc, 0)

        days_left = (stock / daily_sales) if daily_sales > 0 else 999.0
        safety_stock_qty = daily_sales * safety_stock_days
        target_stock_qty = daily_sales * target_coverage_days
        reorder_point = (daily_sales * effective_lt) + safety_stock_qty
        current_position = stock + pending_stock

        needs_po = False
        suggested_qty = 0
        urgency = "normal"
        badge_text = "재고 안정"

        if current_position <= reorder_point:
            needs_po = True
            shortage = target_stock_qty - current_position
            if shortage > 0:
                suggested_qty = math.ceil(shortage / moq) * moq
                suggested_qty = max(suggested_qty, moq)
            else:
                suggested_qty = moq

            if stock <= (daily_sales * effective_lt):
                urgency = "urgent"
                badge_text = "🚨 긴급 품절위험"
                urgent_count += 1
            else:
                urgency = "warning"
                badge_text = "⚠️ 발주 검토"
                warning_count += 1

        est_cost = suggested_qty * unit_price
        if needs_po:
            total_suggested_cost += est_cost

        dashboard_items.append({
            "product": p,
            "stock": stock,
            "pending_stock": pending_stock,
            "daily_sales": daily_sales,
            "effective_lt": effective_lt,
            "days_left": days_left,
            "needs_po": needs_po,
            "suggested_qty": suggested_qty,
            "est_cost": est_cost,
            "urgency": urgency,
            "badge_text": badge_text
        })

    urgency_order = {"urgent": 0, "warning": 1, "normal": 2}
    dashboard_items.sort(key=lambda x: (urgency_order[x["urgency"]], x["days_left"]))

    # 상단 4대 핵심 지표
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">🚨 긴급 발주 품목</div>
            <div class="kpi-value" style="color: #ff4d4f;">{urgent_count} <span style="font-size:14px; color:#8b949e;">건</span></div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">⚠️ 발주 검토 품목</div>
            <div class="kpi-value" style="color: #faad14;">{warning_count} <span style="font-size:14px; color:#8b949e;">건</span></div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">⏳ 연휴 가산 버퍼</div>
            <div class="kpi-value" style="color: #00ffa3;">+{holiday_buffer} <span style="font-size:14px; color:#8b949e;">일</span></div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">💰 총 예상 발주 예산</div>
            <div class="kpi-value">{total_suggested_cost:,} <span style="font-size:14px; color:#8b949e;">원</span></div>
        </div>
        """, unsafe_allow_html=True)

    # 슬랙 알림 발송 버튼
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 슬랙으로 발주 권고요약 전송", type="primary", use_container_width=True):
        if not slack_webhook:
            st.error("사이드바에 슬랙 Webhook URL을 먼저 입력해 주세요.")
        else:
            urgent_lines = [
                f"• *{item['product']['name']}* : 제안 {item['suggested_qty']:,}개 (소진예상 {item['days_left']:.1f}일 후, 가용 {item['stock']}개)"
                for item in dashboard_items if item["urgency"] == "urgent"
            ]
            msg_payload = {
                "text": "📢 [FLICKRFOX] 실시간 발주 권고 리포트",
                "blocks": [
                    {"type": "header", "text": {"type": "plain_text", "text": "⚡ FLICKRFOX 재고 & 발주 현황 요약"}},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*긴급 발주:* `{urgent_count}건` | *발주 검토:* `{warning_count}건` | *예상 소요예산:* `{total_suggested_cost:,}원`\n(연휴 버퍼 +{holiday_buffer}일 가산 반영됨)"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*🚨 긴급 품절 위험 품목*\n" + ("\n".join(urgent_lines) if urgent_lines else "현재 긴급 품절 위험 품목이 없습니다.")
                        }
                    }
                ]
            }
            try:
                res = requests.post(slack_webhook, json=msg_payload, timeout=5)
                if res.status_code == 200:
                    st.success("✅ 슬랙 채널로 리포트가 전송되었습니다!")
                else:
                    st.error(f"전송 실패 (코드: {res.status_code})")
            except Exception as e:
                st.error(f"슬랙 전송 오류: {e}")

    st.markdown("---")

    # 품목별 발주 결정 카드
    for idx, item in enumerate(dashboard_items):
        p = item["product"]
        card_class = item["urgency"]
        badge_html = f'<span class="badge-{card_class}">{item["badge_text"]}</span>'
        
        st.markdown(f"""
        <div class="po-card {card_class}">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div>
                    <span style="font-size: 13px; font-weight:700; color: #8b949e; margin-right: 8px;">#{idx+1}</span>
                    <strong style="font-size: 18px; color: #ffffff;">{p['name']}</strong>
                    <span style="font-size: 12px; color: #8b949e; margin-left: 8px;">({p['supplier']} · 바코드: {p['barcode']})</span>
                </div>
                <div>{badge_html}</div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin-bottom: 14px; font-size: 13px;">
                <div><span style="color:#8b949e;">가용 재고:</span> <strong class="tabular-num">{item['stock']:,}개</strong></div>
                <div><span style="color:#8b949e;">입고 대기:</span> <strong class="tabular-num" style="color:#00ffa3;">{item['pending_stock']:,}개</strong></div>
                <div><span style="color:#8b949e;">일평균 판매:</span> <strong class="tabular-num">{item['daily_sales']:.1f}개</strong></div>
                <div><span style="color:#8b949e;">유효 LT:</span> <strong class="tabular-num">{item['effective_lt']}일</strong></div>
                <div><span style="color:#8b949e;">소진 예상:</span> <strong class="tabular-num" style="color:{'#ff4d4f' if item['days_left'] < 10 else '#f0f6fc'};">{item['days_left']:.1f}일 후</strong></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_act1, col_act2, col_act3 = st.columns([2, 2, 4])
        with col_act1:
            order_qty = st.number_input(
                f"발주 수량 (MOQ {p.get('moq', 500):,}개)",
                min_value=0,
                step=int(p.get("moq", 500)),
                value=int(item["suggested_qty"]),
                key=f"po_input_{p['barcode']}"
            )
        with col_act2:
            st.write("")
            st.write("")
            if st.button("✅ 발주 확정", key=f"btn_confirm_{p['barcode']}", use_container_width=True):
                if order_qty <= 0:
                    st.warning("수량을 1개 이상 입력해 주세요.")
                else:
                    exp_date = (date.today() + timedelta(days=item["effective_lt"])).strftime("%Y-%m-%d")
                    new_order = {
                        "order_id": f"PO-{datetime.now().strftime('%y%m%d%H%M%S')}",
                        "date": date.today().strftime("%Y-%m-%d"),
                        "name": p["name"],
                        "barcode": p["barcode"],
                        "supplier": p["supplier"],
                        "po_qty": int(order_qty),
                        "unit_price": int(p["unit_price"]),
                        "total_price": int(order_qty * p["unit_price"]),
                        "expected_arrival": exp_date,
                        "status": "입고대기"
                    }
                    st.session_state.po_history.append(new_order)
                    save_history_data(st.session_state.po_history)
                    st.success(f"[{p['name']}] {order_qty:,}개 발주 확정 (입고예정: {exp_date})")
                    st.rerun()
        with col_act3:
            calc_cost = order_qty * p.get("unit_price", 0)
            st.write("")
            st.caption(f"💰 발주 금액: **{calc_cost:,}원** (단가: {p.get('unit_price', 0):,}원)")

# ==========================================
# TAB 2: 발주 히스토리
# ==========================================
with tab2:
    st.markdown("### 📜 발주 진행 및 입고 관리 히스토리")
    if not st.session_state.po_history:
        st.info("아직 등록된 발주 내역이 없습니다. [발주 대시보드]에서 발주를 확정해 보세요.")
    else:
        df_hist = pd.DataFrame(st.session_state.po_history)
        st.dataframe(df_hist, use_container_width=True)

        st.markdown("#### 📦 물품 입고 완료 처리")
        pending_list = [h for h in st.session_state.po_history if h.get("status") == "입고대기"]
        
        if not pending_list:
            st.success("🎉 현재 입고 대기 중인 발주 건이 없습니다.")
        else:
            col_sel, col_btn = st.columns([3, 1])
            with col_sel:
                selected_po = st.selectbox(
                    "입고 완료할 발주 건 선택",
                    options=[h["order_id"] for h in pending_list],
                    format_func=lambda x: next((f"[{h['order_id']}] {h['name']} ({h['po_qty']:,}개) - 예정: {h['expected_arrival']}" for h in pending_list if h['order_id'] == x), x)
                )
            with col_btn:
                st.write("")
                st.write("")
                if st.button("📦 입고 완료 종결", type="primary", use_container_width=True):
                    for h in st.session_state.po_history:
                        if h["order_id"] == selected_po:
                            h["status"] = "입고완료"
                            for p in st.session_state.products:
                                if str(p["barcode"]).strip() == str(h["barcode"]).strip():
                                    p["stock"] = p.get("stock", 0) + h["po_qty"]
                            break
                    save_history_data(st.session_state.po_history)
                    save_master_data(st.session_state.products)
                    st.success("✅ 입고 처리가 완료되어 실재고에 반영되었습니다!")
                    st.rerun()

# ==========================================
# TAB 3: 품목 마스터
# ==========================================
with tab3:
    st.markdown("### 📦 FLICKRFOX 주요 품목 마스터 관리")
    st.caption("💡 표의 셀을 더블클릭하여 품목명, 바코드, 리드타임(LT), MOQ, 단가 등을 직접 수정할 수 있습니다. (신규 품목은 맨 아래 빈 줄에 직접 추가)")

    df_master = pd.DataFrame(st.session_state.products)
    cols_order = ["name", "barcode", "supplier", "lead_time", "moq", "unit_price", "stock", "daily_sales", "status"]
    for col in cols_order:
        if col not in df_master.columns:
            df_master[col] = 0 if col in ["lead_time", "moq", "unit_price", "stock", "daily_sales"] else ""
    df_master = df_master[cols_order]

    edited_df = st.data_editor(
        df_master,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "name": st.column_config.TextColumn("품목명 (Product)", required=True),
            "barcode": st.column_config.TextColumn("바코드 (Barcode)", help="이지어드민과 매칭되는 고유 바코드", required=True),
            "supplier": st.column_config.TextColumn("거래처 (공장/협력사)"),
            "lead_time": st.column_config.NumberColumn("기본 리드타임 (일)", min_value=1, step=1, format="%d일"),
            "moq": st.column_config.NumberColumn("최소발주수량 (MOQ)", min_value=1, step=100, format="%d개"),
            "unit_price": st.column_config.NumberColumn("입고 단가 (원)", min_value=0, step=100, format="₩%d"),
            "stock": st.column_config.NumberColumn("현재고 (개)", min_value=0, step=1, format="%d개"),
            "daily_sales": st.column_config.NumberColumn("일평균 판매량", min_value=0.0, step=0.1, format="%.1f개"),
            "status": st.column_config.SelectboxColumn("운영 상태", options=["정상", "단종예정", "일시품절"], default="정상")
        },
        key="master_data_editor_v2"
    )

    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        if st.button("💾 품목 마스터 저장", type="primary", use_container_width=True):
            cleaned_records = edited_df.dropna(subset=["name", "barcode"]).to_dict("records")
            save_master_data(cleaned_records)
            st.success("✅ 품목 마스터가 영구 저장되었습니다!")
            st.rerun()

    with col_btn2:
        st.info("ℹ️ 바코드가 일치하는 주력 품목만 엑셀에서 추출되며, 리드타임과 MOQ, 입고단가는 여기서 언제든 수정 후 저장하실 수 있습니다.")
