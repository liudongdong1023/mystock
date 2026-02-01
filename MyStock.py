import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime
import os

# --- 1. 界面与样式配置 ---
st.set_page_config(page_title="2026 AI Quant Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .status-buy { color: #00ff00; font-weight: bold; }
    .status-sell { color: #ff4b4b; font-weight: bold; }
    .metric-box { border: 1px solid #30363d; padding: 10px; border-radius: 5px; background: #161b22; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 离线股票名称映射 (解决云端获取中文名难的问题) ---
# 建议将常用股放入此字典，若不在其中则显示代码
STOCK_NAMES = {
    "600519": "贵州茅台", "000001": "平安银行", "300750": "宁德时代",
    "688256": "寒武纪", "002657": "中科金财", "688041": "海光信息",
    "300033": "同花顺", "002230": "科大讯飞", "300418": "昆仑万维"
}

# --- 3. 核心量化引擎 ---
@st.cache_data(ttl=600)
def fetch_data(symbol):
    try:
        # 2026年 yfinance 对 A 股最稳后缀：.SS(沪) .SZ(深)
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if df.empty: return None
        
        # 处理 yfinance 可能返回的多级索引
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 使用 pandas_ta 计算均线系统 (MA5, MA10, MA20, EMA60)
        df.ta.sma(length=5, append=True)
        df.ta.sma(length=10, append=True)
        df.ta.sma(length=20, append=True)
        df.ta.ema(length=60, append=True)
        
        # 计算辅助决策指标
        df.ta.rsi(length=14, append=True)
        df.ta.macd(append=True)
        df.ta.atr(length=14, append=True)
        
        return df
    except:
        return None

def get_pro_score(df):
    """多维度量化决策系统"""
    last = df.iloc[-1]
    prev = df.iloc[-2]
    score = 50
    tips = []

    # 均线多头排列判断 (MA5 > MA10)
    if last['SMA_5'] > last['SMA_10']:
        score += 15
        if prev['SMA_5'] <= prev['SMA_10']:
            tips.append("🚀 触发 5/10日均线金叉")
        else:
            tips.append("📈 均线多头排列中")
    else:
        score -= 10
        tips.append("⚠️ 均线空头排列")

    # 股价与均线位置
    if last['Close'] > last['SMA_5']:
        score += 10; tips.append("✅ 股价站稳5日线")
    else:
        score -= 10; tips.append("❌ 跌破5日线（短期走弱）")

    # RSI 强弱
    if last['RSI_14'] > 70:
        score -= 15; tips.append("🔥 RSI超买（不宜追高）")
    elif last['RSI_14'] < 30:
        score += 15; tips.append("❄️ RSI超卖（关注反弹）")

    # 决策逻辑
    if score >= 65: advice = "建议买入/持股"
    elif score <= 40: advice = "建议卖出/空仓"
    else: advice = "震荡观望"

    return score, advice, tips

# --- 4. 侧边栏 ---
with st.sidebar:
    st.title("🛡️ 2026 策略看板")
    st.write("---")
    raw_input = st.text_area("输入监控代码 (每行一个)", "600519\n300750\n688256\n002657")
    codes = [c.strip() for c in raw_input.split('\n') if len(c.strip()) == 6]
    
    symbols = []
    for c in codes:
        suffix = ".SS" if c.startswith('6') else ".SZ"
        symbols.append(f"{c}{suffix}")
    
    st.divider()
    st.caption("提示：代码会自动识别沪深后缀。")

# --- 5. 主页面渲染 ---
st.title("📊 Pro 级 A股量化买卖看板")

if not symbols:
    st.warning("👈 请在左侧侧边栏输入 A 股 6 位代码")
else:
    # A. 全量概览表
    summary_data = []
    for s in symbols:
        data = fetch_data(s)
        if data is not None:
            pure_code = s.split('.')[0]
            name = STOCK_NAMES.get(pure_code, "未知标的")
            sc, adv, _ = get_pro_score(data)
            
            summary_data.append({
                "代码": pure_code,
                "名称": name,
                "分值": sc,
                "最新建议": adv,
                "现价": round(data['Close'].iloc[-1], 2),
                "MA5": round(data['SMA_5'].iloc[-1], 2),
                "MA10": round(data['SMA_10'].iloc[-1], 2),
                "RSI": round(data['RSI_14'].iloc[-1], 1)
            })
    
    if summary_data:
        st.subheader("🏁 选股池状态快照")
        df_summary = pd.DataFrame(summary_data)
        
        # 渲染美化表格
        def color_advice(val):
            if '买入' in val: return 'color: #00ff00'
            if '卖出' in val: return 'color: #ff4b4b'
            return ''
        
        st.dataframe(df_summary.style.applymap(color_advice, subset=['最新建议']), use_container_width=True, hide_index=True)

    st.divider()

    # B. 深度分析区
    target_sym = st.selectbox("🎯 选择标的进行 K 线穿透分析", symbols)
    df_target = fetch_data(target_sym)

    if df_target is not None:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # 高级交互 K 线图
            fig = go.Figure(data=[go.Candlestick(
                x=df_target.index, open=df_target['Open'], high=df_target['High'],
                low=df_target['Low'], close=df_target['Close'], name='K线'
            )])
            # 叠加均线
            fig.add_trace(go.Scatter(x=df_target.index, y=df_target['SMA_5'], name='MA5', line=dict(color='white', width=1)))
            fig.add_trace(go.Scatter(x=df_target.index, y=df_target['SMA_10'], name='MA10', line=dict(color='yellow', width=1)))
            fig.add_trace(go.Scatter(x=df_target.index, y=df_target['EMA_60'], name='生命线', line=dict(color='magenta', width=2, dash='dot')))
            
            fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,b=0,t=30))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # 评分与止损建议
            score, advice, tips = get_pro_score(df_target)
            st.subheader(f"量化评分: {score}")
            
            status_class = "status-buy" if score >= 60 else ("status-sell" if score <= 40 else "")
            st.markdown(f"### 当前建议：<span class='{status_class}'>{advice}</span>", unsafe_allow_html=True)
            
            for t in tips:
                st.write(f"- {t}")
            
            st.divider()
            last_p = df_target['Close'].iloc[-1]
            atr_p = df_target['ATRr_14'].iloc[-1]
            st.metric("动态离场点 (2xATR)", f"￥{last_p - 2*atr_p:.2f}", delta="-2.0 ATR")
            st.caption("风险提示：若收盘价低于此离场点，建议减仓规避风险。")

st.caption(f"数据更新于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 基于 yfinance 接口")
