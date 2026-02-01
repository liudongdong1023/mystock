import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime
import os

# --- 1. 页面样式美化 ---
st.set_page_config(page_title="2026 AI Quant Pro", layout="wide")

# 针对云端环境的 CSS 注入
st.markdown("""
    <style>
    .stApp { background-color: #0b0d14; color: #e0e0e0; }
    .metric-card { background-color: #161b22; border-radius: 10px; padding: 20px; border: 1px solid #30363d; }
    .signal-buy { color: #238636; font-weight: bold; font-size: 20px; }
    .signal-sell { color: #da3633; font-weight: bold; font-size: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心量化引擎 ---
@st.cache_data(ttl=600) # 云端缓存10分钟，大幅提升响应速度
def fetch_and_calc(symbol):
    try:
        # yfinance 获取数据 (2026云端最稳源)
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if df.empty: return None
        
        # 移除多级索引（yfinance新版特性处理）
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 引入 pandas_ta 计算技术矩阵
        # 趋势：SMA5, SMA10, EMA60(生命线)
        df.ta.sma(length=5, append=True)
        df.ta.sma(length=10, append=True)
        df.ta.ema(length=60, append=True)
        # 动量：RSI
        df.ta.rsi(length=14, append=True)
        # 能量：MACD
        df.ta.macd(append=True)
        # 波动：ATR (用于动态止损)
        df.ta.atr(length=14, append=True)
        # 空间：布林带
        df.ta.bbands(length=20, append=True)
        
        return df
    except:
        return None

def get_pro_score(df):
    """多维度评分系统 (0-100)"""
    last = df.iloc[-1]
    prev = df.iloc[-2]
    score = 50
    reasons = []

    # 维度1：趋势 (MA金叉)
    if last['SMA_5'] > last['SMA_10'] and prev['SMA_5'] <= prev['SMA_10']:
        score += 20; reasons.append("🟢 5/10日均线完成金叉")
    if last['Close'] > last['EMA_60']:
        score += 10; reasons.append("🟢 股价站上60日生命线")
    
    # 维度2：动量 (RSI)
    if last['RSI_14'] < 35:
        score += 15; reasons.append("🔵 RSI进入超卖区 (低吸机会)")
    elif last['RSI_14'] > 75:
        score -= 20; reasons.append("🔴 RSI严重超买 (规避风险)")

    # 维度3：动能 (MACD)
    if last['MACDh_12_26_9'] > 0:
        score += 10; reasons.append("🟢 MACD红柱放量")

    # 决策建议
    if score >= 70: advice = "强烈推荐买入"
    elif score >= 55: advice = "适量建仓/持有"
    elif score <= 35: advice = "减仓/离场"
    else: advice = "区间震荡/观望"

    return score, advice, reasons

# --- 3. 侧边栏交互 ---
with st.sidebar:
    st.title("🛡️ 监控配置")
    st.caption("2026-02-01 云端运行中")
    # 支持纯代码输入，后台自动适配后缀
    raw_input = st.text_area("输入A股代码 (每行一个)", "600519\n000001\n300750\n688256")
    codes = [c.strip() for c in raw_input.split('\n') if len(c.strip()) == 6]
    
    symbols = []
    for c in codes:
        suffix = ".SS" if c.startswith('6') else ".SZ"
        symbols.append(f"{c}{suffix}")

    st.divider()
    st.info("数据源：yfinance | 计算库：pandas_ta")

# --- 4. 主界面渲染 ---
st.title("🍎 Pro 级 A股量化决策仪表盘")

if not symbols:
    st.warning("请在左侧输入股票代码（如 600519）")
else:
    # 扫描摘要表格
    with st.expander("📊 多股扫描结果摘要", expanded=True):
        summary_list = []
        for s in symbols:
            data = fetch_and_calc(s)
            if data is not None:
                sc, adv, _ = get_pro_score(data)
                summary_list.append({
                    "标的": s,
                    "分值": sc,
                    "操作建议": adv,
                    "最新价": round(data['Close'].iloc[-1], 2),
                    "RSI": round(data['RSI_14'].iloc[-1], 1)
                })
        st.dataframe(pd.DataFrame(summary_list), use_container_width=True, hide_index=True)

    st.divider()

    # 深度图表分析
    target = st.selectbox("🎯 选择标的查看深度指标与K线", symbols)
    df_target = fetch_and_calc(target)

    if df_target is not None:
        c1, c2 = st.columns([2, 1])
        
        with c1:
            # 高级交互式 K 线
            fig = go.Figure(data=[go.Candlestick(
                x=df_target.index, open=df_target['Open'], high=df_target['High'],
                low=df_target['Low'], close=df_target['Close'], name='K线'
            )])
            fig.add_trace(go.Scatter(x=df_target.index, y=df_target['EMA_60'], name='EMA60生命线', line=dict(color='magenta', width=1.5)))
            fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,b=0,t=30))
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            # 评分卡片
            score, advice, reasons = get_pro_score(df_target)
            st.markdown(f"### 量化评分: `{score}`")
            
            # 指标亮色显示
            advice_color = "signal-buy" if score >= 55 else "signal-sell"
            st.markdown(f"<p class='{advice_color}'>{advice}</p>", unsafe_allow_html=True)
            
            for r in reasons:
                st.write(r)
            
            st.divider()
            # 止损决策参考
            last_price = df_target['Close'].iloc[-1]
            atr = df_target['ATRr_14'].iloc[-1]
            st.metric("建议止损位 (2xATR)", f"￥{last_price - 2*atr:.2f}", delta="-2.0 ATR")
            st.caption("注：ATR止损能有效避开盘中震仓。")
