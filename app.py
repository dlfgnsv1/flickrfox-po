import streamlit as st
import pandas as pd
import numpy as np
import datetime
import json
import os
import requests
import io

# ==========================================
# 0. 플리커폭스(FLICKRFOX) 다크 텍 테마 설정
# ==========================================
st.set_page_config(
    page_title="FLICKRFOX 발주 운영 시스템",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 브랜드 가이드 v5 기반 완전 커스텀 CSS
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

    /* 전역 다크 텍 톤앤매너 */
    html, body, [class*="css"], .stApp {
        background: radial-gradient(circle at top left, rgba(17,241,93,.06), transparent 28%),
                    linear-gradient(180deg, #05090a 0%, #071012 50%, #0a1113 100%) !important;
        color: #f4f7f8 !important;
        font-family: 'Pretendard', -apple-system, sans-serif !important;
        letter-spacing: -0.02em;
    }

    /* 사이드바 다크 스타일링 */
    section[data-testid="stSidebar"] {
        background-color: #0d171a !important;
        border-right: 1px solid #253137 !important;
    }

    /* 브랜드 히어로 헤더 */
    .hero-card {
        background: linear-gradient(180deg, #10191d 0%, #141f24 100%);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 20px;
        padding: 26px 30px;
        margin-bottom: 24px;
        box-shadow: 0 20px 50px rgba(0,0,0,0.35);
    }
    .hero-tag {
        display: inline-flex;
        align-items: center;
        padding: 4px 12px;
        border-radius: 999px;
        border: 1px solid rgba(17,241,93,0.3);
        background: rgba(17,241,93,0.11);
        color: #11f15d;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        margin-bottom: 12px;
    }
    .hero-title {
        font-size: 26px;
        font-weight: 900;
        letter-spacing: -0.03em;
        margin: 0;
        color: #f4f7f8;
    }
    .hero-line {
        width: 60px;
        height: 3px;
        border-radius: 999px;
        background: #11f15d;
        box-shadow: 0 0 16px rgba(17,241,93,0.5);
        margin: 10px 0 14px;
    }

    /* KPI 대시보드 카드 */
    div[data-testid="stMetric"] {
        background: linear-gradient(180deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.02) 100%) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 16px !important;
        padding: 16px 20px !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.25);
    }
    div[data-testid="stMetricLabel"] p {
        color: #b8c2c8 !important;
        font-size: 13px !important;
        font-weight: 600;
    }
    div[data-testid="stMetricValue"] {
        color: #f4f7f8 !important;
        font-size: 24px !important;
        font-weight: 900 !important;
        font-variant-numeric: tabular-nums;
    }

    /* 상품 카드 */
    .product-box {
        background: linear-gradient(180deg, #10191d 0%, #141f24 100%);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 18px;
        padding: 20px 24px;
        margin-bottom: 14px;
        box-shadow: 0 15px 35px rgba(0,0,0,0.25);
    }
    .product-box.urgent {
        border-left: 4px solid #ff8a8a;
    }
    .product-box.warning {
        border-left: 4px solid #ffd56b;
    }
    .product-box.safe {
        border-left: 4px solid #11f15d;
    }

    /* 상태 뱃지 */
    .chip {
        display: inline-flex;
        align-items: center;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 11.5px;
        font-weight: 800;
    }
    .chip-red { background: rgba(255,138,138,0.12); color: #ff8a8a; border: 1px solid rgba(255,138,138,0.3); }
    .chip-yellow { background: rgba(255,213,107,0.12); color: #ffd56b; border: 1px solid rgba(255,213,107,0.3); }
    .chip-green { background: rgba(17,241,93,0.11); color: #11f15d; border: 1px solid rgba(17,241,93,0.3); }

    /* 플리커폭스 네온 액션 버튼 */
    .stButton > button {
        background: #11f15d !important;
        color: #071012 !important;
        border-radius: 12px !important;
        border: none !important;
        font-weight: 800 !important;
        padding: 8px 20px !important;
        letter-spacing: -0.01em;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 0 18px rgba(17,241,93,0.3);
    }
    .stButton > button:hover {
        background: #2fff74 !important;
        box-shadow: 0 0 26px rgba(17,241,93,0.6);
        transform: translateY(-1px);
    }

    /* 탭 헤더 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
        border-bottom: 1px solid #253137;
    }
    .stTabs [data-baseweb="tab"] {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 999px !important;
        color: #b8c2c8 !important;
        padding: 6px 18px !important;
        font-weight: 700 !important;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(17,241,93,0.15) !important;
        border-color: #11f15d !important;
        color: #11f15d !important;
    }

    /* 입력 폼 필드 */
    input, select, textarea {
        background-color: #0d171a !important;
        color: #f4f7f8 !important;
        border: 1px solid #253137 !important;
        border-radius: 10px !important;
    }
</style>
""", unsafe_allow_html=True)

# 파일 저장 경로
MASTER_FILE = "product_master.json"
HISTORY_FILE = "order_history.json"

# ==========================================
# 1. 데이터 입출력 (영구 저장)
# ==========================================
DEFAULT_PRODUCTS = [
    {"barcode": "88090001", "name": "MATTE-ONE Z Fold 8", "vendor": "A공장", "daily_sales": 15.0, "base_lt": 25, "moq": 500, "price": 6500, "current_stock": 0},
    {"barcode": "88090002", "name": "Mag-Link PRO Black", "vendor": "B사", "daily_sales": 45.0, "base_lt": 21, "moq": 1000, "price": 5550, "current_stock": 400},
    {"barcode": "88090003", "name": "OctoLock PRO", "vendor": "C사", "daily_sales": 60.0, "base_lt": 30, "moq": 1500, "price": 7560, "current_stock": 0},
    {"barcode": "88090004", "name": "360 TurnStand Black", "vendor": "A공장", "daily_sales": 34.6, "base_lt": 20, "moq": 500, "price": 5200, "current_stock": 677},
    {"barcode": "88090005", "name": "360 TurnStand Brown", "vendor": "A공장", "daily_sales": 4.4, "base_lt": 20, "moq": 200, "price": 5200, "current_stock": 106},
    {"barcode": "88090006", "name": "360 TurnStand Green", "vendor": "A공장", "daily_sales": 8.1, "base_lt": 20, "moq": 200, "price": 5200, "current_stock": 408},
    {"barcode": "88090007", "name": "Mag-Link PRO Silver", "vendor": "B사", "daily_sales": 17.0, "base_lt": 21, "moq": 500, "price": 5550, "current_stock": 510},
    {"barcode": "88090008", "name": "Matte-Shield Fold 8", "vendor": "D사", "daily_sales": 25.0, "base_lt": 18, "moq": 600, "price": 3800, "current_stock": 450},
]

def load_master_data():
    if os.path.exists(MASTER_FILE):
        with open(MASTER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    save_master_data(DEFAULT_PRODUCTS)
    return DEFAULT_PRODUCTS

def save_master_data(data):
    with open(MASTER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_history_data():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_history_data(data):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==========================================
# 2. 슬랙 Webhook 알림 발송 함수
# ==========================================
def send_slack_message(webhook_url, urgent_items, total_budget, holiday_buffer):
    if not webhook_url:
        return False, "슬랙 Webhook URL이 설정되지 않았습니다."
    
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    
    if not urgent_items:
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": f"🟢 [{today_str}] FLICKRFOX 재고 정상 보고", "emoji": True}},
            {"type": "section", "text": {"type": "mrkdwn", "text": "현재 긴급 발주 품목이 없습니다. 모든 파이프라인이 안정적입니다."}}
        ]
    else:
        items_text_list = []
        for i, item in enumerate(urgent_items[:8], start=1):
            line = (
                f"*{i}. {item['name']}* ({item['vendor']})\n"
                f"• 유효 가용재고: `{item['effective_stock']:,}개` (소진 예상: 약 {item['days_of_supply']:.1f}일)\n"
                f"• 👉 *추천 발주량:* `{item['order_qty']:,}개` | 예상 금액: `{item['order_amount']:,}원`"
            )
            items_text_list.append(line)
        
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": f"🚨 [{today_str}] FLICKRFOX 긴급 발주 알림", "emoji": True}},
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*긴급 품목 수:*\n총 {len(urgent_items)}건"},
                    {"type": "mrkdwn", "text": f"*예상 소요 예산:*\n{total_budget:,.0f}원"},
                    {"type": "mrkdwn", "text": f"*연휴 가산:*\n+{holiday_buffer}일 적용"},
                    {"type": "mrkdwn", "text": "*상태:*\n즉시 발주 필요"}
                ]
            },
            {"type": "divider"},
            {"type": "section", "text": {"type": "mrkdwn", "text": "\n\n".join(items_text_list)}},
            {"type": "divider"}
        ]

    try:
        res = requests.post(webhook_url, json={"blocks": blocks}, headers={"Content-Type": "application/json"}, timeout=5)
        return (True, "슬랙 채널로 발주 알림이 전송되었습니다.") if res.status_code == 200 else (False, f"전송 실패: {res.text}")
    except Exception as e:
        return False, f"오류: {str(e)}"

# ==========================================
# 3. 사이드바 - 파라미터 및 환경 설정
# ==========================================
with st.sidebar:
    st.markdown('<div class="hero-tag">OPERATIONS</div>', unsafe_allow_html=True)
    st.subheader("⚙️ 발주 환경 파라미터")
    
    holiday_buffer = st.number_input("명절/연휴 추가 지연일 (일)", min_value=0, max_value=30, value=7)
    safety_days = st.slider("안전재고 확보일수 (일)", 7, 30, 14)
    target_cover_days = st.slider("목표 충족일수 (일)", 30, 90, 45)
    
    st.divider()
    st.subheader("📢 슬랙(Slack) 연동")
    slack_webhook = st.text_input("Webhook URL", placeholder="https://hooks.slack.com/services/...", type="password")

# ==========================================
# 4. 데이터 로드 및 미입고 집계
# ==========================================
products = load_master_data()
history = load_history_data()

in_transit_map = {}
for po in history:
    if po.get("status") == "생산/배송중":
        b = po.get("barcode")
        in_transit_map[b] = in_transit_map.get(b, 0) + po.get("order_qty", 0)

# ==========================================
# 5. 브랜드 히어로 헤더 & 탭 구성
# ==========================================
st.markdown("""
<div class="hero-card">
    <div class="hero-tag">FLICKRFOX SUPPLY CHAIN</div>
    <h1 class="hero-title">실시간 재고 & 발주 운영 시스템</h1>
    <div class="hero-line"></div>
    <div style="font-size:14px; color:#b8c2c8;">
        거래처별 리드타임 동적 가산 및 이지어드민 연동 품절 방어 자동화 대시보드
    </div>
</div>
""", unsafe_allow_html=True)

tab_dashboard, tab_history, tab_master = st.tabs(["📊 발주 대시보드", "📜 발주 히스토리", "📦 품목 마스터"])

# ----------------------------------------------------
# TAB 1: 발주 대시보드
# ----------------------------------------------------
with tab_dashboard:
    col_up, col_btn = st.columns([3, 1])
    with col_up:
        uploaded_file = st.file_uploader("이지어드민 [재고현황] 엑셀 드래그 & 드롭 (.xlsx)", type=["xlsx", "xls"])
    
    stock_map = {}
    if uploaded_file is not None:
        try:
            ez_df = pd.read_excel(uploaded_file)
            b_col = [c for c in ez_df.columns if "바코드" in str(c) or "상품코드" in str(c)][0]
            s_col = [c for c in ez_df.columns if "가용재고" in str(c) or "현재고" in str(c)][0]
            
            for _, r in ez_df.iterrows():
                b_code = str(r[b_col]).strip()
                stk_val = pd.to_numeric(r[s_col], errors="coerce")
                stock_map[b_code] = 0 if pd.isna(stk_val) else int(stk_val)
            st.success(f"⚡ 이지어드민 엑셀 데이터 매핑 완료 (총 {len(stock_map)}개 품목)")
        except Exception as e:
            st.error(f"엑셀 읽기 오류: {e}")

    # 연산 엔진
    calc_rows = []
    for p in products:
        b = str(p["barcode"])
        current_stk = stock_map.get(b, p.get("current_stock", 0))
        p["current_stock"] = current_stk
        
        in_transit = in_transit_map.get(b, 0)
        effective_lt = p["base_lt"] + holiday_buffer
        effective_stock = current_stk + in_transit
        daily = p["daily_sales"]
        rop = (daily * effective_lt) + (daily * safety_days)
        
        days_of_supply = (effective_stock / daily) if daily > 0 else 999.0
        urgency_margin = days_of_supply - effective_lt
        
        order_qty = 0
        if effective_stock < rop:
            raw_need = (daily * target_cover_days) - effective_stock
            if raw_need > 0:
                moq = p["moq"]
                order_qty = int(np.ceil(max(raw_need, moq) / moq) * moq)
        
        order_amount = order_qty * p["price"]
        
        if effective_stock <= (daily * effective_lt):
            status = "🔴 긴급 품절위험"
            badge_class = "chip-red"
            border_class = "urgent"
            p_score = 1
        elif effective_stock < rop:
            status = "🟡 발주 검토"
            badge_class = "chip-yellow"
            border_class = "warning"
            p_score = 2
        else:
            status = "🟢 재고 안전"
            badge_class = "chip-green"
            border_class = "safe"
            p_score = 3

        calc_rows.append({
            "barcode": b, "name": p["name"], "vendor": p["vendor"],
            "current_stock": current_stk, "in_transit": in_transit,
            "effective_stock": effective_stock, "daily_sales": daily,
            "effective_lt": effective_lt, "rop": rop,
            "days_of_supply": days_of_supply, "urgency_margin": urgency_margin,
            "order_qty": order_qty, "price": p["price"],
            "order_amount": order_amount, "status": status,
            "badge_class": badge_class, "border_class": border_class,
            "p_score": p_score
        })

    save_master_data(products)
    calc_df = pd.DataFrame(calc_rows).sort_values(by=["p_score", "urgency_margin"], ascending=[True, True]).reset_index(drop=True)
    calc_df["순위"] = calc_df.index + 1

    # 상단 메트릭
    urgent_cnt = len(calc_df[calc_df["p_score"] == 1])
    review_cnt = len(calc_df[calc_df["p_score"] == 2])
    total_order_amt = calc_df["order_amount"].sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🚨 긴급 발주 품목", f"{urgent_cnt} 건")
    m2.metric("⚠️ 발주 검토 품목", f"{review_cnt} 건")
    m3.metric("⏳ 연휴 가산 버퍼", f"+{holiday_buffer} 일")
    m4.metric("💰 총 예상 발주 예산", f"{total_order_amt:,.0f} 원")

    # 슬랙 전송 버튼
    col_l, col_r = st.columns([3, 1])
    with col_r:
        if st.button("🚀 슬랙으로 발주 알림 전송", use_container_width=True):
            urgent_targets = calc_df[calc_df["order_qty"] > 0].to_dict(orient="records")
            ok, msg = send_slack_message(slack_webhook, urgent_targets, total_order_amt, holiday_buffer)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    st.write("")

    # 품목별 카드 렌더링
    for _, r in calc_df.iterrows():
        b_code = r["barcode"]
        st.markdown(f"""
        <div class="product-box {r['border_class']}">
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div>
                    <span style="font-size:12px; font-weight:800; color:#11f15d;">{r['순위']}순위</span>
                    <h3 style="margin:2px 0 4px; font-size:18px; font-weight:900; color:#f4f7f8;">{r['name']}</h3>
                    <div style="font-size:12.5px; color:#b8c2c8;">
                        {r['vendor']} · 바코드 {b_code} · 일판매 {r['daily_sales']}개 · 유효LT {r['effective_lt']}일
                    </div>
                </div>
                <span class="chip {r['badge_class']}">{r['status']}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-top:14px; padding-top:12px; border-top:1px solid rgba(255,255,255,0.06); font-size:13px;">
                <div>가용재고: <b>{r['current_stock']:,}개</b> (입고대기: {r['in_transit']:,}개)</div>
                <div style="color:{'#ff8a8a' if r['p_score']==1 else '#b8c2c8'};">소진 예상: 약 <b>{r['days_of_supply']:.1f}일분</b></div>
                <div style="color:#11f15d; font-weight:800;">
                    {f"👉 제안 발주량: {r['order_qty']:,}개 ({r['order_amount']:,.0f}원)" if r['order_qty'] > 0 else "재고 안전"}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if r["order_qty"] > 0:
            with st.expander(f"⚡ {r['name']} 실제 발주 수량 수정 및 발주 완료 처리"):
                with st.form(key=f"po_{b_code}"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        final_qty = st.number_input("최종 발주 수량", min_value=1, value=r["order_qty"], step=100)
                    with c2:
                        exp_in_date = datetime.date.today() + datetime.timedelta(days=int(r["effective_lt"]))
                        final_date = st.date_input("예상 입고일", value=exp_in_date)
                    with c3:
                        final_memo = st.text_input("발주 메모 / PO 코드", value=f"PO-{datetime.date.today().strftime('%m%d')}-{r['vendor']}")
                    
                    if st.form_submit_button("✅ 발주 확정 (입고대기 전환)"):
                        new_po = {
                            "po_id": f"PO-{len(history)+1:03d}",
                            "barcode": b_code,
                            "name": r["name"],
                            "vendor": r["vendor"],
                            "order_qty": final_qty,
                            "order_amount": final_qty * r["price"],
                            "order_date": datetime.date.today().strftime("%Y-%m-%d"),
                            "expected_date": final_date.strftime("%Y-%m-%d"),
                            "memo": final_memo,
                            "status": "생산/배송중"
                        }
                        history.insert(0, new_po)
                        save_history_data(history)
                        st.success(f"'{r['name']}' {final_qty:,}개 발주가 등록되어 '입고대기'로 전환되었습니다.")
                        st.rerun()

# ----------------------------------------------------
# TAB 2: 발주 히스토리
# ----------------------------------------------------
with tab_history:
    st.subheader("📜 발주 및 입고 파이프라인")
    
    if not history:
        st.info("등록된 발주 이력이 없습니다.")
    else:
        for idx, po in enumerate(history):
            st.markdown(f"""
            <div class="product-box">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span style="color:#11f15d; font-size:12px; font-weight:800;">{po.get('po_id')}</span>
                        <h4 style="margin:2px 0; color:#f4f7f8;">{po.get('name')} ({po.get('vendor')})</h4>
                        <div style="font-size:12.5px; color:#b8c2c8;">
                            발주일: {po.get('order_date')} | 예상입고일: <b>{po.get('expected_date')}</b> | 메모: {po.get('memo', '-')}
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:16px; font-weight:900; color:#f4f7f8;">{po.get('order_qty'):,}개</div>
                        <div style="font-size:12px; color:#b8c2c8;">{po.get('order_amount', 0):,}원</div>
                        <span class="chip {'chip-yellow' if po.get('status')=='생산/배송중' else 'chip-green'}">{po.get('status')}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if po.get("status") == "생산/배송중":
                if st.button(f"📦 창고 입고 완료 확인 ({po.get('po_id')})", key=f"btn_h_{idx}"):
                    po["status"] = "입고완료"
                    save_history_data(history)
                    st.success("입고 완료 종결되었습니다.")
                    st.rerun()

# ----------------------------------------------------
# TAB 3: 품목 마스터 관리
# ----------------------------------------------------
with tab_master:
    st.subheader("📦 플리커폭스 품목 마스터")
    
    with st.expander("➕ 신규 주요 품목 등록"):
        with st.form(key="master_add"):
            c1, c2 = st.columns(2)
            with c1:
                n_bar = st.text_input("상품 바코드 (고유값)")
                n_name = st.text_input("품목명 / 옵션")
                n_vendor = st.text_input("거래처(공장명)")
                n_sales = st.number_input("일평균 판매량", min_value=0.1, value=15.0, step=0.5)
            with c2:
                n_lt = st.number_input("기본 리드타임(일)", min_value=1, value=20, step=1)
                n_moq = st.number_input("최소 발주 단위(MOQ)", min_value=1, value=500, step=50)
                n_price = st.number_input("매입 단가(원)", min_value=0, value=5500, step=500)
                n_stk = st.number_input("초기 현재고", min_value=0, value=0, step=10)
            
            if st.form_submit_button("💾 마스터 품목 추가"):
                if n_bar and n_name:
                    products.append({
                        "barcode": n_bar, "name": n_name, "vendor": n_vendor,
                        "daily_sales": n_sales, "base_lt": n_lt, "moq": n_moq,
                        "price": n_price, "current_stock": n_stk
                    })
                    save_master_data(products)
                    st.success(f"'{n_name}' 등록 완료")
                    st.rerun()
                else:
                    st.error("바코드와 품목명은 필수입니다.")

    st.dataframe(pd.DataFrame(products), use_container_width=True)