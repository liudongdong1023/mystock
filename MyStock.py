import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime
import os
import re

# --- 1. 页面样式配置 ---
st.set_page_config(page_title="2026 Quant Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .price-up { color: #ff4b4b; font-weight: bold; }
    .price-down { color: #00ff00; font-weight: bold; }
    .metric-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心量化引擎 ---
@st.cache_data(ttl=300) # 缓存5分钟，适配云端实时性
def fetch_stock_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        # 获取1年数据以确保MA60准确
        df = ticker.history(period="1y", interval="1d", timeout=10)
        if df.empty: return None, "Unknown"
        
        # 计算均线矩阵 (MA5, 10, 20, 60)
        df.ta.sma(length=5, append=True)
        df.ta.sma(length=10, append=True)
        df.ta.sma(length=20, append=True)
        df.ta.ema(length=60, append=True)
        
        # 计算风险指标
        df.ta.atr(length=14, append=True)
        df.ta.rsi(length=14, append=True)
        
        # 模拟机构流向因子 (RVOL)
        df['RVOL'] = df['Volume'] / df['Volume'].rolling(20).mean()
        
        return df, ticker.info.get('shortName', symbol)
    except:
        return None, "Error"

# --- 3. 侧边栏：多格式解析 ---
with st.sidebar:
    st.header("🛡️ 监控配置")
    st.caption("支持格式: '002657 | 中科金财' 或 '002657'")
    raw_input = st.text_area("输入监控列表", value="002657 | 中科金财\n600519 | 贵州茅台\n300750\n688256")
    
    # 解析代码
    target_symbols = []
    lines = raw_input.split('\n')
    for line in lines:
        match = re.search(r'(\d{6})', line)
        if match:
            code = match.group(1)
            name = line.split('|')[-1].strip() if '|' in line else code
            suffix = ".SS" if code.startswith('6') else ".SZ"
            target_symbols.append((f"{code}{suffix}", code, name))

# --- 4. 主页面：看板展示 ---
st.title("🛡️ 2026 Pro 量化决策看板")
st.caption(f"数据同步时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (延迟行情)")

if not target_symbols:
    st.warning("👈 请在侧边栏输入监控标的")
else:
    # A. 核心行情矩阵 (实时价格 + 涨幅 + 均线)
    summary_list = []
    for sym_yf, code, user_name in target_symbols:
        data, t_name = fetch_stock_data(sym_yf)
        if data is not None:
            last = data.iloc[-1]
            prev = data.iloc[-2]
            
            # 计算涨幅
            price = last['Close']
            change = (price / prev['Close'] - 1) * 100
            
            summary_list.append({
                "代码": code,
                "名称": user_name if user_name != code else t_name,
                "最新价": round(price, 2),
                "涨跌幅": f"{change:+.2f}%",
                "MA5": round(last['SMA_5'], 2),
                "MA10": round(last['SMA_10'], 2),
                "MA20": round(last['SMA_20'], 2),
                "MA60": round(last['EMA_60'], 2),
                "机构RVOL": round(last['RVOL'], 2)
            })
    
    if summary_list:
        st.subheader("📊 实时行情与均线扫描")
        df_summary = pd.DataFrame(summary_list)
        
        # 涨跌幅染色逻辑
        def style_change(val):
            color = '#ff4b4b' if '+' in val else '#00ff00'
            return f'color: {color}; font-weight: bold'

        st.dataframe(df_summary.style.applymap(style_change, subset=['涨跌幅']), 
                     use_container_width=True, hide_index=True)

    st.divider()

    # B. 单股深度分析
    target_tuple = st.selectbox("🎯 重点标的决策分析", target_symbols, format_func=lambda x: f"{x} ({x})")
    df_t, _ = fetch_stock_data(target_tuple)
    
    if df_t is not None:
        col1, col2 = st.columns([2, 1])
        with col1:
            # 叠加多维均线的 K 线图
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df_t.index, open=df_t['Open'], high=df_t['High'], low=df_t['Low'], close=df_t['Close'], name='K线'))
            fig.add_trace(go.Scatter(x=df_t.index, y=df_t['SMA_5'], name='MA5', line=dict(color='white', width=1)))
            fig.add_trace(go.Scatter(x=df_t.index, y=df_t['SMA_20'], name='MA20', line=dict(color='orange', width=1)))
            fig.add_trace(go.Scatter(x=df_t.index, y=df_t['EMA_60'], name='生命线', line=dict(color='magenta', width=2, dash='dot')))
            fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            last_t = df_t.iloc[-1]
            st.markdown("### 🛠️ 量化决策因子")
            
            # 均线多头判定
            if last_t['SMA_5'] > last_t['SMA_10']:
                st.success("🟢 5/10日均线金叉：上升趋势")
            else:
                st.error("🔴 5/10日均线死叉：震荡/回调")
            
            # RSI 提示
            if last_t['RSI_14'] > 70: st.warning("⚠️ RSI超买：不建议追高")
            elif last_t['RSI_14'] < 30: st.info("🌀 RSI超卖：关注反弹")
            
            st.divider()
            # 风控止损位
            atr = last_t['ATRr_14']
            st.metric("动态离场价 (2xATR)", f"￥{last_t['Close'] - 2*atr:.2f}", delta="-2.0 ATR")
            st.caption("提示：当收盘价跌破离场价时，建议执行卖出指令。")

st.info("💡 提示：本工具使用 yfinance 雅虎财经接口，适合中长线趋势决策，A 股行情约有 15 分钟延迟。")
