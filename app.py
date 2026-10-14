import streamlit as st
import pandas as pd
import numpy as np
import requests
import os
import json
import math
from datetime import datetime, date, timedelta

# ==========================================
# 1. 페이지 환경설정 및 다크 사이버-텍 스타일 정의
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
    
    /* 숫자 전용 폰트 (Tabular Nums) */
    .tabular-num {
        font-family: 'JetBrains Mono', monospace;
        font-variant-numeric: tabular-nums;
    }

    /* 메인 배너 카드 */
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

    /* KPI 지표 카드 */
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

    /* 발주 카드 컴포넌트 */
    .po-card {
        background: #11171f;
        border: 1px solid #222d3d;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
    }
    .po-card.urgent {
        border-left: 4px solid #ff4d4f;
    }
    .po-card.warning {
        border-left: 4px solid #faad14;
    }
    .po-card.normal {
        border-left: 4px solid #00ffa3;
    }
    
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
# 2. 데이터 영구 저장 및 세션 초기화
# ==========================================
MASTER_FILE = "master_products.json"
HISTORY_FILE = "po_history.json"

DEFAULT_PRODUCTS = [
    {"name": "OctoLock PRO", "barcode": "88090001", "supplier": "A사", "lead_time": 30, "moq": 1000, "unit_price": 7560, "stock": 120, "daily_sales": 25.0, "status": "정상"},
    {"name": "맥링크 에어", "barcode": "88090002", "supplier": "B사", "lead_time": 45, "moq": 500, "unit_price": 5400, "stock": 40, "daily_sales": 10.0, "status": "정상"},
    {"name": "티타늄 카드지갑", "barcode": "88090003", "supplier": "C사", "lead_time": 20, "moq": 2000, "unit_price": 3200, "stock": 0, "daily_sales": 60.0, "status": "정상"}
]

def load_master_data():
    if os.path.exists(MASTER_FILE):
        try:
            with open(MASTER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
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
# 4. 상단 히어로 배너
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
    # 1. 이지어드민 엑셀 업로더 (가짜 .xls, .xlsx 자동 호환)
    uploaded_file = st.file_uploader("이지어드민 [현재고조회] 엑셀 드래그 & 드롭 (.xlsx, .xls)", type=["xlsx", "xls"])
    
    if uploaded_file is not None:
        try:
            df_ez = None
            try:
                df_ez = pd.read_excel(uploaded_file, engine='openpyxl')
            except Exception:
                try:
                    uploaded_file.seek(0)
                    df_ez = pd.read_excel(uploaded_file, engine='xlrd')
                except Exception:
                    uploaded_file.seek(0)
                    for enc in ['utf-8', 'cp949', 'euc-kr']:
                        try:
                            tables = pd.read_html(uploaded_file, encoding=enc)
                            if tables:
                                df_ez = tables[0]
                                break
                        except Exception:
                            uploaded_file.seek(0)

            if df_ez is None:
                st.error("❌ 엑셀 형식을 읽을 수 없습니다. 엑셀 프로그램에서 'Excel 통합 문서(.xlsx)'로 다시 저장해 주세요.")
            else:
                df_ez.columns = [str(c).strip().replace(" ", "") for c in df_ez.columns]
                barcode_col = next((c for c in df_ez.columns if any(k in c for k in ['바코드', '상품코드', '자체코드', '자체상품코드'])), None)
                stock_col = next((c for c in df_ez.columns if any(k in c for k in ['가용재고', '가용', '현재고', '정상재고', '재고'])), None)

                if not barcode_col or not stock_col:
                    st.error(f"❌ 엑셀에서 '바코드' 또는 '가용재고' 열을 찾지 못했습니다. (인식된 열: {list(df_ez.columns)[:5]})")
                else:
                    df_ez[barcode_col] = df_ez[barcode_col].astype(str).str.strip()
                    matched_items = []
                    
                    for p in st.session_state.products:
                        target_bc = str(p.get("barcode", "")).strip()
                        match = df_ez[df_ez[barcode_col] == target_bc]
                        if not match.empty:
                            val = match[stock_col].values[0]
                            p["stock"] = max(0, int(pd.to_numeric(val, errors='coerce') or 0))
                            matched_items.append(p["name"])

                    if matched_items:
                        save_master_data(st.session_state.products)
                        st.success(f"✅ 마스터 등록 품목 중 {len(matched_items)}건의 재고가 성공적으로 동기화되었습니다! ({', '.join(matched_items)})")
                        st.rerun()
                    else:
                        st.warning("⚠️ 엑셀은 정상 인식되었으나, [품목 마스터]에 등록된 바코드와 일치하는 주요 품목이 없습니다.")
        except Exception as e:
            st.error(f"엑셀 처리 오류: {e}")

    # 2. 발주 알고리즘 계산
    dashboard_items = []
    total_suggested_cost = 0
    urgent_count = 0
    warning_count = 0

    # 입고 대기 수량 사전 계산 (히스토리 참조)
    pending_stock_map = {}
    for h in st.session_state.po_history:
        if h.get("status") == "입고대기":
            bc = str(h.get("barcode", "")).strip()
            pending_stock_map[bc] = pending_stock_map.get(bc, 0) + int(h.get("po_qty", 0))

    for p in st.session_state.products:
        bc = str(p.get("barcode", "")).strip()
        stock = int(p.get("stock", 0))
        daily_sales = float(p.get("daily_sales", 0.0))
        base_lt = int(p.get("lead_time", 30))
        effective_lt = base_lt + holiday_buffer
        moq = int(p.get("moq", 100))
        unit_price = int(p.get("unit_price", 0))
        pending_stock = pending_stock_map.get(bc, 0)

        # 소진 일수 계산
        days_left = (stock / daily_sales) if daily_sales > 0 else 999.0

        # 발주 기준점 (리드타임 소진량 + 안전재고 확보량)
        safety_stock_qty = daily_sales * safety_stock_days
        target_stock_qty = daily_sales * target_coverage_days
        reorder_point = (daily_sales * effective_lt) + safety_stock_qty
        current_position = stock + pending_stock

        # 발주 필요량 및 상태 산정
        needs_po = False
        suggested_qty = 0
        urgency = "normal"
        badge_text = "재고 안정"

        if current_position <= reorder_point:
            needs_po = True
            shortage = target_stock_qty - current_position
            if shortage > 0:
                # MOQ 단위 올림
                suggested_qty = math.ceil(shortage / moq) * moq
                suggested_qty = max(suggested_qty, moq)
            else:
                suggested_qty = moq

            # 품절 위험도 판별
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

    # 정렬: 긴급 -> 검토 -> 안정 (소진일수 오름차순)
    urgency_order = {"urgent": 0, "warning": 1, "normal": 2}
    dashboard_items.sort(key=lambda x: (urgency_order[x["urgency"]], x["days_left"]))

    # 3. 상단 4대 KPI 카드
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

    # 4. 슬랙 알림 발송 버튼
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
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": "⚡ FLICKRFOX 재고 & 발주 현황 요약"}
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*긴급 발주:* `{urgent_count}건` | *발주 검토:* `{warning_count}건` | *예상 소요예산:* `{total_suggested_cost:,}원`\n(명절/연휴 버퍼 +{holiday_buffer}일 가산 반영됨)"
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
                    st.success("✅ 슬랙 채널로 리포트가 성공적으로 전송되었습니다!")
                else:
                    st.error(f"슬랙 전송 실패 (상태 코드: {res.status_code})")
            except Exception as e:
                st.error(f"슬랙 전송 오류: {e}")

    st.markdown("---")

    # 5. 품목별 발주 결정 카드 목록
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
                f"발주 수량 (MOQ {p.get('moq', 100):,}개)",
                min_value=0,
                step=int(p.get("moq", 100)),
                value=int(item["suggested_qty"]),
                key=f"po_input_{p['barcode']}"
            )
        with col_act2:
            st.write("")
            st.write("")
            if st.button("✅ 발주 확정", key=f"btn_confirm_{p['barcode']}", use_container_width=True):
                if order_qty <= 0:
                    st.warning("발주 수량을 1개 이상 입력해 주세요.")
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
                            # 마스터 실재고에 수량 가산
                            for p in st.session_state.products:
                                if str(p["barcode"]).strip() == str(h["barcode"]).strip():
                                    p["stock"] = p.get("stock", 0) + h["po_qty"]
                            break
                    save_history_data(st.session_state.po_history)
                    save_master_data(st.session_state.products)
                    st.success("✅ 입고 처리가 완료되어 마스터 재고에 반영되었습니다!")
                    st.rerun()

# ==========================================
# TAB 3: 품목 마스터
# ==========================================
with tab3:
    st.markdown("### 📦 FLICKRFOX 주요 품목 마스터 관리")
    st.caption("💡 표의 셀을 더블클릭하여 품목명, 바코드, 리드타임(LT), MOQ, 단가 등을 직접 수정할 수 있습니다. (하단 빈 줄에 신규 품목 추가 가능)")

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
            "barcode": st.column_config.TextColumn("바코드 (Barcode)", help="이지어드민과 매칭될 고유 바코드", required=True),
            "supplier": st.column_config.TextColumn("거래처 (공장/협력사)"),
            "lead_time": st.column_config.NumberColumn("기본 리드타임 (일)", min_value=1, step=1, format="%d일"),
            "moq": st.column_config.NumberColumn("최소발주수량 (MOQ)", min_value=1, step=100, format="%d개"),
            "unit_price": st.column_config.NumberColumn("입고 단가 (원)", min_value=0, step=100, format="₩%d"),
            "stock": st.column_config.NumberColumn("현재고 (개)", min_value=0, step=1, format="%d개"),
            "daily_sales": st.column_config.NumberColumn("일평균 판매량", min_value=0.0, step=0.5, format="%.1f개"),
            "status": st.column_config.SelectboxColumn("운영 상태", options=["정상", "단종예정", "일시품절"], default="정상")
        },
        key="master_data_editor_final"
    )

    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        if st.button("💾 품목 마스터 저장", type="primary", use_container_width=True):
            cleaned_records = edited_df.dropna(subset=["name", "barcode"]).to_dict("records")
            save_master_data(cleaned_records)
            st.success("✅ 품목 마스터가 영구 저장되었습니다!")
            st.rerun()

    with col_btn2:
        st.info("ℹ️ 바코드를 실제 이지어드민 바코드와 일치시켜 두시면, 엑셀 업로드 시 해당 주력 품목들의 재고만 자동으로 업데이트됩니다.")
