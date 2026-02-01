import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime
import os
import re

# --- 1. 配置与样式 ---
st.set_page_config(page_title="2026 Pro Quant Master", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .heat-high { color: #ff4b4b; font-weight: bold; }
    .inst-in { color: #00ff00; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 行业基准池 (用于计算板块热度) ---
SECTOR_BENCHMARKS = {
    "AI算力": "688041.SS",   # 海光信息
    "生物医药": "688506.SS", # 百利天恒
    "半导体": "688981.SS",   # 中芯国际
    "核心资产": "600519.SS"  # 贵州茅台
}

# --- 3. 核心量化引擎 ---
@st.cache_data(ttl=600)
def fetch_analysis(symbol):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y", interval="1d")
        if df.empty: return None, "Unknown"
        
        # 计算基础均线
        df.ta.sma(length=5, append=True)
        df.ta.sma(length=10, append=True)
        df.ta.sma(length=20, append=True)
        df.ta.atr(length=14, append=True)
        
        # --- 核心新增：机构流向与热度因子 ---
        # A. 相对成交量 (Relative Volume): 今日成交量/20日平均成交量
        df['RVOL'] = df['Volume'] / df['Volume'].rolling(window=20).mean()
        
        # B. 机构吸筹指数 (Accumulation): (收盘价-最低价)/(最高价-最低价) * 成交量因子
        df['Inst_Flow'] = (df['Close'] - df['Low']) / (df['High'] - df['Low'])
        
        return df, ticker.info.get('shortName', symbol)
    except:
        return None, "Error"

def get_pro_signals(df, sector_df=None):
    """多维评分：包含热度与流向"""
    last = df.iloc[-1]
    score, reasons = 50, []
    
    # 1. 机构大单流向维度 (基于 RVOL 和 收盘位置)
    if last['RVOL'] > 2.0 and last['Inst_Flow'] > 0.7:
        score += 20; reasons.append("🔥 机构爆量吸筹 (RVOL > 2.0)")
    elif last['RVOL'] > 1.5:
        score += 10; reasons.append("🟢 机构资金活跃")
        
    # 2. 板块热度维度 (相对强度)
    if sector_df is not None:
        stock_ret = (df['Close'].iloc[-1] / df['Close'].iloc[-5]) - 1
        sect_ret = (sector_df['Close'].iloc[-1] / sector_df['Close'].iloc[-5]) - 1
        if stock_ret > sect_ret:
            score += 15; reasons.append("⚡ 强于所属板块龙头")

    # 3. 传统技术面
    if last['SMA_5'] > last['SMA_10']:
        score += 10; reasons.append("📈 5/10日线多头")
    
    advice = "强烈建议买入" if score >= 75 else ("建议离场" if score <= 35 else "观望/持有")
    return score, advice, reasons

# --- 4. 侧边栏：多维度配置 ---
with st.sidebar:
    st.header("🛡️ 2026 策略中枢")
    sector_sel = st.selectbox("核心板块参考", list(SECTOR_BENCHMARKS.keys()))
    
    st.divider()
    raw_input = st.text_area("监控列表 (代码 | 名称)", 
                             value="002657 | 中科金财\n688256 | 寒武纪\n300058 | 蓝色光标")
    
    target_symbols = []
    lines = raw_input.split('\n')
    for line in lines:
        match = re.search(r'(\d{6})', line)
        if match:
            code = match.group(1)
            name = line.split('|')[-1].strip() if '|' in line else code
            suffix = ".SS" if code.startswith('6') else ".SZ"
            target_symbols.append((f"{code}{suffix}", code, name))

# --- 5. 主页面：看板展示 ---
st.title("🛡️ Pro 级量化看板：流向与热度分析")

if not target_symbols:
    st.warning("👈 请在侧边栏输入监控标的")
else:
    # A. 板块龙头数据预取
    sector_data, _ = fetch_analysis(SECTOR_BENCHMARKS[sector_sel])

    # B. 监控列表摘要
    summary_list = []
    for sym_yf, code, user_name in target_symbols:
        data, t_name = fetch_analysis(sym_yf)
        if data is not None:
            sc, adv, _ = get_pro_signals(data, sector_data)
            
            summary_list.append({
                "代码": code,
                "名称": user_name,
                "最新价": round(data['Close'].iloc[-1], 2),
                "MA5/10": "多头" if data['SMA_5'].iloc[-1] > data['SMA_10'].iloc[-1] else "空头",
                "相对量(RVOL)": round(data['RVOL'].iloc[-1], 2),
                "机构评分": sc,
                "操作决策": adv
            })
    
    if summary_list:
        st.subheader(f"📊 当前板块：{sector_sel} 联动扫描")
        df_summary = pd.DataFrame(summary_list)
        
        def color_score(val):
            if val >= 70: return 'background-color: #004d00; color: white'
            if val <= 40: return 'background-color: #4d0000; color: white'
            return ''

        st.dataframe(df_summary.style.applymap(color_score, subset=['机构评分']), 
                     use_container_width=True, hide_index=True)

    st.divider()

    # C. 单股深度穿透（含流向可视化）
    t_tuple = st.selectbox("🎯 选择标的查看机构动作", target_symbols, format_func=lambda x: f"{x} ({x})")
    df_t, _ = fetch_analysis(t_tuple)
    
    if df_t is not None:
        col1, col2 = st.columns([2, 1])
        with col1:
            # K线与成交量对比
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df_t.index, open=df_t['Open'], high=df_t['High'], low=df_t['Low'], close=df_t['Close'], name='K线'))
            fig.add_trace(go.Bar(x=df_t.index, y=df_t['RVOL']*10, name='相对量(x10)', marker_color='rgba(100, 100, 100, 0.3)'))
            fig.update_layout(template="plotly_dark", height=550, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            score, advice, reasons = get_pro_signals(df_t, sector_data)
            st.metric("机构介入评分", score, delta=advice)
            st.write("---")
            st.write("**核心异动分析：**")
            for r in reasons:
                st.write(r)
            
            st.divider()
            # 止损风控
            last_p = df_t['Close'].iloc[-1]
            atr_p = df_t['ATRr_14'].iloc[-1]
            st.metric("动态止损位", f"￥{last_p - 1.5*atr_p:.2f}", delta="-1.5 ATR")

st.caption(f"2026-02-01 专业版 | 板块参考标的：{SECTOR_BENCHMARKS[sector_sel]} | 算法基于 yFinance 延迟数据")
