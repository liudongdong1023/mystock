import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime
import os
import re

# --- 1. 页面样式配置 ---
st.set_page_config(page_title="2026 AI Quant Master", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .buy-signal { background-color: #004d00; color: #00ff00; padding: 5px; border-radius: 5px; font-weight: bold; }
    .sell-signal { background-color: #4d0000; color: #ff4b4b; padding: 5px; border-radius: 5px; font-weight: bold; }
    .metric-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心量化决策引擎 ---
@st.cache_data(ttl=300)
def fetch_stock_analysis(symbol):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y", interval="1d", timeout=10)
        if df.empty: return None, "Unknown"
        
        # 计算均线系统
        df.ta.sma(length=5, append=True)
        df.ta.sma(length=10, append=True)
        df.ta.sma(length=20, append=True)
        df.ta.ema(length=60, append=True)
        # 计算动量与风险
        df.ta.rsi(length=14, append=True)
        df.ta.macd(append=True)
        df.ta.atr(length=14, append=True)
        
        return df, ticker.info.get('shortName', symbol)
    except:
        return None, "Error"

def generate_decision(df):
    """
    三级决策逻辑：基于均线、RSI、MACD
    """
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    signals = []
    advice = "观望"
    color = "white"
    
    # 1. 均线金叉逻辑 (5日/10日)
    is_gold = prev['SMA_5'] <= prev['SMA_10'] and last['SMA_5'] > last['SMA_10']
    is_death = prev['SMA_5'] >= prev['SMA_10'] and last['SMA_5'] < last['SMA_10']
    
    if is_gold:
        signals.append("✨ 形成5/10日金叉")
    elif is_death:
        signals.append("💀 形成5/10日死叉")
    
    # 2. 综合评分建议
    score = 0
    if last['Close'] > last['SMA_5']: score += 1
    if last['SMA_5'] > last['SMA_10']: score += 1
    if last['MACDh_12_26_9'] > 0: score += 1
    if last['RSI_14'] < 30: score += 2 # 超卖加分
    
    if is_gold or score >= 3:
        advice = "🚀 强烈建议买入/持股"
        color = "#00ff00"
    elif is_death or score <= 0:
        advice = "⚠️ 建议止损/清仓"
        color = "#ff4b4b"
    elif last['RSI_14'] > 75:
        advice = "🔥 严重超买，建议减仓"
        color = "#ffa500"
    else:
        advice = "💎 震荡格局，持币观望"
        
    return advice, signals, color

# --- 3. 侧边栏交互 ---
with st.sidebar:
    st.header("🎯 智能监控配置")
    raw_input = st.text_area("输入监控列表 (002657 | 中科金财)", value="002657 | 中科金财\n688256 | 寒武纪\n300750 | 宁德时代\n600519 | 贵州茅台")
    target_symbols = []
    for line in raw_input.split('\n'):
        match = re.search(r'(\d{6})', line)
        if match:
            code = match.group(1)
            name = line.split('|')[-1].strip() if '|' in line else code
            suffix = ".SS" if code.startswith('6') else ".SZ"
            target_symbols.append((f"{code}{suffix}", code, name))

# --- 4. 主页面展示 ---
st.title("🛡️ 2026 AI 智能买卖辅助系统")

if not target_symbols:
    st.warning("👈 请在侧边栏输入股票代码")
else:
    # A. 实时决策矩阵
    summary_list = []
    for sym_yf, code, user_name in target_symbols:
        data, t_name = fetch_stock_analysis(sym_yf)
        if data is not None:
            advice, signals, color = generate_decision(data)
            last = data.iloc[-1]
            prev = data.iloc[-2]
            change = (last['Close'] / prev['Close'] - 1) * 100
            
            summary_list.append({
                "代码": code,
                "名称": user_name,
                "最新价": round(last['Close'], 2),
                "今日涨跌": f"{change:+.2f}%",
                "均线状态": " | ".join(signals) if signals else "趋势延续",
                "决策建议": advice
            })
    
    if summary_list:
        st.subheader("🚩 实时金叉预警与决策快照")
        df_summary = pd.DataFrame(summary_list)
        
        def style_decision(val):
            if '买入' in val: return 'color: #00ff00; font-weight: bold'
            if '卖出' in val or '止损' in val: return 'color: #ff4b4b; font-weight: bold'
            return 'color: #ffa500'

        st.dataframe(df_summary.style.applymap(style_decision, subset=['决策建议']), 
                     use_container_width=True, hide_index=True)

    st.divider()

    # B. 深度图形化穿透
    target_tuple = st.selectbox("🎯 重点个股技术形态透视", target_symbols, format_func=lambda x: f"{x} ({x})")
    df_t, _ = fetch_stock_analysis(target_tuple)
    
    if df_t is not None:
        col1, col2 = st.columns()
        with col1:
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df_t.index, open=df_t['Open'], high=df_t['High'], low=df_t['Low'], close=df_t['Close'], name='K线'))
            fig.add_trace(go.Scatter(x=df_t.index, y=df_t['SMA_5'], name='MA5', line=dict(color='white', width=1)))
            fig.add_trace(go.Scatter(x=df_t.index, y=df_t['SMA_10'], name='MA10', line=dict(color='yellow', width=1)))
            fig.add_trace(go.Scatter(x=df_t.index, y=df_t['EMA_60'], name='生命线', line=dict(color='magenta', width=2, dash='dot')))
            fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            advice, signals, color = generate_decision(df_t)
            st.markdown(f"### 核心决策：<span style='color:{color}'>{advice}</span>", unsafe_allow_html=True)
            
            st.write("---")
            st.write("**技术面因子：**")
            for s in signals:
                st.write(f"- {s}")
            
            last_t = df_t.iloc[-1]
            st.write(f"- 当前价格: ¥{last_t['Close']:.2f}")
            st.write(f"- 5日均线: ¥{last_t['SMA_5']:.2f}")
            st.write(f"- RSI(14): {last_t['RSI_14']:.1f}")
            
            st.divider()
            # 动态止损位
            st.metric("动态离场参考 (2xATR)", f"¥{last_t['Close'] - 2*last_t['ATRr_14']:.2f}", help="如果收盘价跌破此线，必须离场。")
            st.caption("注：本系统建议基于技术面，请结合基本面操作。")

st.info("💡 提示：'刚形成金叉' 指今日收盘均线完成穿越，是极强的转势信号。")
