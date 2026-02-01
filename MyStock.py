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
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心量化决策引擎 ---
@st.cache_data(ttl=300)
def fetch_analysis(symbol):
    try:
        ticker = yf.Ticker(symbol)
        # 获取1年数据确保均线准确
        df = ticker.history(period="1y", interval="1d", timeout=10)
        if df.empty: return None, "Unknown"
        
        # 精准计算 5, 10, 20 日均线
        df.ta.sma(length=5, append=True)
        df.ta.sma(length=10, append=True)
        df.ta.sma(length=20, append=True)
        # 辅助指标
        df.ta.rsi(length=14, append=True)
        df.ta.atr(length=14, append=True)
        
        return df, ticker.info.get('shortName', symbol)
    except:
        return None, "Error"

def generate_decision(df):
    """
    基于 MA5/10/20 的买卖决策逻辑
    """
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    signals = []
    
    # A. 金叉/死叉逻辑 (5日/10日)
    is_gold = prev['SMA_5'] <= prev['SMA_10'] and last['SMA_5'] > last['SMA_10']
    is_death = prev['SMA_5'] >= prev['SMA_10'] and last['SMA_5'] < last['SMA_10']
    
    # B. 综合决策建议
    score = 0
    # 站稳5日线 +1
    if last['Close'] > last['SMA_5']: score += 1
    # 5/10线多头排列 +1
    if last['SMA_5'] > last['SMA_10']: score += 1
    # 股价上行且放量 (此处简化为均线支撑)
    if last['Close'] > last['SMA_20']: score += 1
    
    # 判定文字
    if is_gold or score == 3:
        advice = "🚀 强烈建议买入"
        color = "#00ff00"
    elif is_death or last['Close'] < last['SMA_10']:
        advice = "⚠️ 建议止损/卖出"
        color = "#ff4b4b"
    else:
        advice = "💎 震荡/持股观望"
        color = "#ffa500"
        
    if is_gold: signals.append("✨ 5/10日金叉")
    if is_death: signals.append("💀 5/10日死叉")
    if last['Close'] > last['SMA_20'] and prev['Close'] <= prev['SMA_20']:
        signals.append("突破20日生命线")
        
    return advice, signals, color

# --- 3. 侧边栏配置 ---
with st.sidebar:
    st.header("🎯 决策列表配置")
    raw_input = st.text_area("输入监控列表 (代码 | 名称)", 
                             value="600519 | 贵州茅台
688041 | 海光信息
688256 | 寒武纪
002230 | 科大讯飞
603019 | 中科曙光
002031 | 巨轮智能
603233 | 大博医疗
002422 | 科伦药业
600118 | 中国卫星
600487 | 亨通光电
600498 | 烽火通信
603986 | 兆易创新
603160 | 汇顶科技
002594 | 比亚迪
600900 | 长江电力
600023 | 浙能电力
002074 | 国轩高科
601857 | 中国石油
600028 | 中国石化
600309 | 万华化学
002493 | 荣盛石化
601899 | 紫金矿业
600547 | 山东黄金")
    target_symbols = []
    for line in raw_input.split('\n'):
        match = re.search(r'(\d{6})', line)
        if match:
            code = match.group(1)
            name = line.split('|')[-1].strip() if '|' in line else code
            suffix = ".SS" if code.startswith('6') else ".SZ"
            target_symbols.append((f"{code}{suffix}", code, name))

# --- 4. 主界面展示 ---
st.title("🛡️ 2026 AI 趋势决策仪表盘")

if not target_symbols:
    st.warning("👈 请在左侧侧边栏添加监控标的")
else:
    # A. 实时行情与决策矩阵
    summary_list = []
    for sym_yf, code, user_name in target_symbols:
        data, t_name = fetch_analysis(sym_yf)
        if data is not None:
            advice, signals, color = generate_decision(data)
            last = data.iloc[-1]
            prev = data.iloc[-2]
            change = (last['Close'] / prev['Close'] - 1) * 100
            
            summary_list.append({
                "代码": code,
                "名称": user_name,
                "价格": round(last['Close'], 2),
                "涨幅": f"{change:+.2f}%",
                "MA5": round(last['SMA_5'], 2),
                "MA10": round(last['SMA_10'], 2),
                "MA20": round(last['SMA_20'], 2),
                "信号预警": " | ".join(signals) if signals else "趋势稳定",
                "决策建议": advice
            })
    
    if summary_list:
        st.subheader("🏁 实时扫描：金叉预警与买卖建议")
        df_summary = pd.DataFrame(summary_list)
        
        def style_advice(val):
            if '买入' in val: return 'color: #00ff00; font-weight: bold'
            if '卖出' in val or '止损' in val: return 'color: #ff4b4b; font-weight: bold'
            return 'color: #ffa500'

        st.dataframe(df_summary.style.applymap(style_advice, subset=['决策建议']), 
                     use_container_width=True, hide_index=True)

    st.divider()

    # B. 单股深度图形分析
    target_sel = st.selectbox("🎯 重点个股 5/10/20 趋势分析", target_symbols, format_func=lambda x: f"{x} ({x})")
    df_t, _ = fetch_analysis(target_sel)
    
    if df_t is not None:
        col1, col2 = st.columns()
        with col1:
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df_t.index, open=df_t['Open'], high=df_t['High'], low=df_t['Low'], close=df_t['Close'], name='K线'))
            # 绘制你要求的均线指标
            fig.add_trace(go.Scatter(x=df_t.index, y=df_t['SMA_5'], name='5日线', line=dict(color='white', width=1)))
            fig.add_trace(go.Scatter(x=df_t.index, y=df_t['SMA_10'], name='10日线', line=dict(color='yellow', width=1)))
            fig.add_trace(go.Scatter(x=df_t.index, y=df_t['SMA_20'], name='20日线', line=dict(color='orange', width=1.5)))
            
            fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            advice, signals, color = generate_decision(df_t)
            st.markdown(f"### 操作决策：<span style='color:{color}'>{advice}</span>", unsafe_allow_html=True)
            st.write("---")
            st.write("**技术面信号：**")
            for s in signals:
                st.write(f"- {s}")
            
            last_t = df_t.iloc[-1]
            st.write(f"- 最新成交: ¥{last_t['Close']:.2f}")
            st.write(f"- RSI(14)强度: {last_t['RSI_14']:.1f}")
            
            st.divider()
            # 动态止损计算
            st.metric("实战离场参考 (2xATR)", f"¥{last_t['Close'] - 2*last_t['ATRr_14']:.2f}", help="价格跌破此线建议无条件减仓。")

st.info("💡 提示：本工具使用 yfinance 接口。'5/10日金叉' 是技术面确认转强的典型标志。")

