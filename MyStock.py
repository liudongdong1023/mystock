import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime
import os
import re

# --- 1. 页面配置与美化 ---
st.set_page_config(page_title="2026 AI Quant Master", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .buy-signal { color: #00ff00; font-weight: bold; }
    .sell-signal { color: #ff4b4b; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心板块与初始化列表配置 ---
SECTORS = {
    "AI算力/应用": ["688041.SS", "688256.SS", "002230.SZ", "603019.SS", "300033.SZ"],
    "存储/脑机/芯片": ["603986.SS", "603160.SS", "002422.SZ", "688981.SS"],
    "石油/化工/能源": ["601857.SS", "600028.SS", "600309.SS", "002493.SZ"],
    "电池/电力/航天": ["002594.SZ", "600900.SS", "600118.SS", "600487.SZ"],
    "机器人/贵金属": ["002031.SZ", "601899.SS", "600547.SS", "002155.SZ"]
}

DEFAULT_TEXT = """[AI算力/核心芯片/算力基建]
603019 | 中科曙光
603986 | 兆易创新
603160 | 汇顶科技
002230 | 科大讯飞
000977 | 浪潮信息
600584 | 长电科技
[AI应用/数字金融/传媒]
002657 | 中科金财
002315 | 焦点科技
600088 | 中视传媒
002131 | 利欧股份
601949 | 中国出版
[低空经济/商业航天/机器人]
600118 | 中国卫星
600893 | 航发动力
002031 | 巨轮智能
002664 | 万安科技
600391 | 航发科技
[固态电池/新材料/新能源]
002594 | 比亚迪
002074 | 国轩高科
603659 | 璞泰来
002812 | 恩捷股份
603799 | 华友钴业
[石油/石化/基础化工]
601857 | 中国石油
600028 | 中国石化
600309 | 万华化学
002493 | 荣盛石化
600346 | 恒力石化
[电力/核能/高股息能源]
600900 | 长江电力
601985 | 中国核电
601088 | 中国神华
601225 | 陕西煤业
600023 | 浙能电力
[贵金属/有色金属/稀土]
601899 | 紫金矿业
600547 | 山东黄金
002155 | 湖南黄金
601600 | 中国铝业
600111 | 北方稀土
[医药生物/高端医疗/脑机]
603233 | 大博医疗
002422 | 科伦药业
600276 | 恒瑞医药
000538 | 云南白药
[通信/光纤基建/量子]
600487 | 亨通光电
600498 | 烽火通信
600105 | 永鼎股份
600050 | 中国联通
[大金融/证券/资产管理]
600036 | 招商银行
601318 | 中国平安
601211 | 东方证券
000776 | 广发证券
600030 | 中信证券
"""


# --- 3. 核心量化算法 ---
@st.cache_data(ttl=300)
def fetch_analysis(symbol):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y", interval="1d", timeout=10)
        if df.empty: return None, "Unknown"
        # 均线系统 MA5, MA10, MA20
        df.ta.sma(length=5, append=True)
        df.ta.sma(length=10, append=True)
        df.ta.sma(length=20, append=True)
        # 辅助指标 RSI, ATR
        df.ta.rsi(length=14, append=True)
        df.ta.atr(length=14, append=True)
        return df, ticker.info.get('shortName', symbol)
    except:
        return None, "Error"

def get_strategy(df):
    """均线金叉决策策略"""
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 5/10日金叉判断
    is_gold = prev['SMA_5'] <= prev['SMA_10'] and last['SMA_5'] > last['SMA_10']
    is_death = prev['SMA_5'] >= prev['SMA_10'] and last['SMA_5'] < last['SMA_10']
    
    score = 0
    if last['Close'] > last['SMA_5']: score += 1
    if last['SMA_5'] > last['SMA_10']: score += 1
    if last['Close'] > last['SMA_20']: score += 1
    
    if is_gold or score == 3:
        return "🚀 强烈买入建议", ["✨ 5/10日金叉" if is_gold else "🟢 多头趋势"], "#00ff00"
    elif is_death or last['Close'] < last['SMA_10']:
        return "⚠️ 减仓/止损建议", ["💀 5/10日死叉" if is_death else "🔴 趋势破位"], "#ff4b4b"
    return "💎 持股/观望", [], "#ffa500"

# --- 4. 侧边栏交互 ---
with st.sidebar:
    st.header("🎯 策略监控配置")
    raw_input = st.text_area("自选股监控列表", value=DEFAULT_TEXT, height=450)
    target_list = []
    for line in raw_input.split('\n'):
        match = re.search(r'(\d{6})', line)
        if match:
            code = match.group(1)
            name = line.split('|')[-1].strip() if '|' in line else code
            suffix = ".SS" if code.startswith('6') else ".SZ"
            target_list.append((f"{code}{suffix}", code, name))
    st.divider()
    st.caption("2026.02.01 Cloud Native Version")

# --- 5. 主页面渲染 ---
st.title("🛡️ 2026 A股量化决策辅助看板")

# --- A. 板块强弱对比雷达图 ---
col_radar, col_info = st.columns([1.5, 1])
with col_radar:
    st.subheader("🌐 板块强度对比 (5日相对涨跌%)")
    radar_data = []
    for sector, syms in SECTORS.items():
        rets = []
        for s in syms:
            d, _ = fetch_analysis(s)
            if d is not None:
                rets.append((d['Close'].iloc[-1] / d['Close'].iloc[-5] - 1) * 100)
        avg_r = sum(rets) / len(rets) if rets else 0
        radar_data.append({"板块": sector, "强度": avg_r})
    
    df_radar = pd.DataFrame(radar_data)
    fig_radar = go.Figure(data=go.Scatterpolar(
        r=df_radar['强度'], theta=df_radar['板块'], fill='toself', line_color='#00ff00'
    ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[-8, 8]), bgcolor="#161b22"), 
        template="plotly_dark", height=380, margin=dict(l=60, r=60, t=20, b=20)
    )
    st.plotly_chart(fig_radar, use_container_width=True)

with col_info:
    st.markdown("""
    **📈 操盘指引：**
    1. **雷达图扩张**：代表该行业处于资金风口，可重点选股。
    2. **均线交叉**：MA5 上穿 MA10 是趋势由弱转强的核心信号。
    3. **离场点位**：系统自动计算 **2xATR 止损位**，破位须坚决执行。
    4. **数据更新**：yfinance 接口 A 股约有 15 分钟延迟。
    """)

st.divider()

# --- B. 实时监控看板 ---
if target_list:
    summary = []
    for syf, code, name in target_list:
        data, _ = fetch_analysis(syf)
        if data is not None:
            adv, sigs, _ = get_strategy(data)
            last = data.iloc[-1]
            prev = data.iloc[-2]
            chg = (last['Close'] / prev['Close'] - 1) * 100
            summary.append({
                "代码": code, "名称": name, "价格": round(last['Close'], 2), "涨幅": f"{chg:+.2f}%",
                "MA5": round(last['SMA_5'], 2), "MA10": round(last['SMA_10'], 2), "MA20": round(last['SMA_20'], 2),
                "综合建议": adv
            })
    
    st.subheader("🏁 全量扫描：买卖信号实时列表")
    df_res = pd.DataFrame(summary)
    
    def style_adv(val):
        if '买入' in val: return 'color: #00ff00; font-weight: bold'
        if '止损' in val: return 'color: #ff4b4b; font-weight: bold'
        return 'color: #ffa500'
    
    st.dataframe(df_res.style.applymap(style_adv, subset=['综合建议']), use_container_width=True, hide_index=True)

    # --- C. 深度个股技术透视 ---
    st.divider()
    target_sel = st.selectbox("🎯 选择标的查看深度 5/10/20 趋势形态", target_list, format_func=lambda x: f"{x} ({x})")
    df_t, _ = fetch_analysis(target_sel)
    
    if df_t is not None:
        c1, c2 = st.columns([2, 1])
        with c1:
            fig_k = go.Figure(data=[go.Candlestick(
                x=df_t.index, open=df_t['Open'], high=df_t['High'], low=df_t['Low'], close=df_t['Close'], name='K线'
            )])
            # 添加你要求的 5, 10, 20 日线
            for m, col in zip(['SMA_5', 'SMA_10', 'SMA_20'], ['white', 'yellow', 'orange']):
                fig_k.add_trace(go.Scatter(x=df_t.index, y=df_t[m], name=m, line=dict(color=col, width=1.5)))
            
            fig_k.update_layout(template="plotly_dark", height=550, xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,b=0,t=0))
            st.plotly_chart(fig_k, use_container_width=True)
        
        with c2:
            adv, sigs, col = get_strategy(df_t)
            st.markdown(f"### 核心决策建议：<span style='color:{col}'>{adv}</span>", unsafe_allow_html=True)
            for s in sigs:
                st.write(f"🔹 {s}")
            
            st.divider()
            last_p = df_t['Close'].iloc[-1]
            atr_val = df_t['ATRr_14'].iloc[-1]
            st.metric("动态风控离场位 (2xATR)", f"￥{last_p - 2*atr_val:.2f}", delta="-2.0 ATR")
            st.caption("注：ATR 止损位能有效过滤盘中震荡，保护利润。")

st.caption(f"数据实时更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 基于 yfinance 接口协议")

