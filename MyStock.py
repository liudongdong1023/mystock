import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime
import os
import re

# --- 1. 页面配置 ---
st.set_page_config(page_title="2026 AI Quant Master", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .buy-signal { color: #00ff00; font-weight: bold; }
    .sell-signal { color: #ff4b4b; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 初始数据配置 (涵盖 11 大板块主板龙头) ---
DEFAULT_MONITOR = """[AI算力与芯片]
603019 | 中科曙光
603986 | 兆易创新
603160 | 汇顶科技
002230 | 科大讯飞
000977 | 浪潮信息
[AI应用与传媒]
002657 | 中科金财
002315 | 焦点科技
600088 | 中视传媒
002131 | 利欧股份
[低空经济与航天]
600118 | 中国卫星
600893 | 航发动力
002031 | 巨轮智能
002664 | 万安科技
[电池与新能源]
002594 | 比亚迪
002074 | 国轩高科
603659 | 璞泰来
002812 | 恩捷股份
[石油与基础化工]
601857 | 中国石油
600028 | 中国石化
600309 | 万华化学
002493 | 荣盛石化
[电力与高股息]
600900 | 长江电力
601985 | 中国核电
601088 | 中国神华
601225 | 陕西煤业
[贵金属与有色]
601899 | 紫金矿业
600547 | 山东黄金
002155 | 湖南黄金
601600 | 中国铝业
[医药与脑机接口]
603233 | 大博医疗
002422 | 科伦药业
600276 | 恒瑞医药
[通信与光纤]
600487 | 亨通光电
600498 | 烽火通信
600050 | 中国联通
[大金融与证券]
600036 | 招商银行
601318 | 中国平安
601211 | 东方证券
000776 | 广发证券
"""

# --- 3. 核心量化引擎 ---
@st.cache_data(ttl=300)
def fetch_analysis(symbol):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y", interval="1d", timeout=10)
        if df.empty: return None
        # 计算 5, 10, 20 日均线
        df.ta.sma(length=5, append=True)
        df.ta.sma(length=10, append=True)
        df.ta.sma(length=20, append=True)
        df.ta.rsi(length=14, append=True)
        df.ta.atr(length=14, append=True)
        return df
    except:
        return None

def get_decision(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    # 金叉逻辑
    is_gold = prev['SMA_5'] <= prev['SMA_10'] and last['SMA_5'] > last['SMA_10']
    is_death = prev['SMA_5'] >= prev['SMA_10'] and last['SMA_5'] < last['SMA_10']
    
    score = 0
    if last['Close'] > last['SMA_5']: score += 1
    if last['SMA_5'] > last['SMA_10']: score += 1
    if last['Close'] > last['SMA_20']: score += 1
    
    if is_gold or score == 3:
        return "🚀 强烈买入", "#00ff00", "✨5/10日金叉" if is_gold else "趋势多头"
    elif is_death or last['Close'] < last['SMA_10']:
        return "⚠️ 建议止损", "#ff4b4b", "💀5/10日死叉" if is_death else "趋势破位"
    return "💎 持股观望", "#ffa500", "震荡整理"

# --- 4. 侧边栏：解析分门别类的数据 ---
with st.sidebar:
    st.header("🎯 策略监控池")
    raw_input = st.text_area("监控列表 (支持 [板块] 标记)", value=DEFAULT_MONITOR, height=400)
    
    # 解析逻辑：按板块切分
    sector_dict = {}
    current_sector = "默认观察"
    for line in raw_input.split('\n'):
        line = line.strip()
        if not line: continue
        # 识别 [板块]
        if line.startswith('[') and line.endswith(']'):
            current_sector = line[1:-1]
            sector_dict[current_sector] = []
        else:
            match = re.search(r'(\d{6})', line)
            if match:
                code = match.group(1)
                name = line.split('|')[-1].strip() if '|' in line else code
                suffix = ".SS" if code.startswith('6') else ".SZ"
                if current_sector not in sector_dict: sector_dict[current_sector] = []
                sector_dict[current_sector].append({"yf": f"{code}{suffix}", "code": code, "name": name})

# --- 5. 主页面：Tab 标签页展示 ---
st.title("🛡️ 2026 AI 趋势决策仪表盘 (分类版)")

if not sector_dict:
    st.warning("👈 请在左侧配置监控列表")
else:
    # 动态创建 Tab
    tabs = st.tabs(list(sector_dict.keys()))
    
    for i, (sector_name, stocks) in enumerate(sector_dict.items()):
        with tabs[i]:
            st.subheader(f"📊 {sector_name} 实时扫描")
            summary = []
            for s in stocks:
                df = fetch_analysis(s['yf'])
                if df is not None:
                    adv, color, sig = get_decision(df)
                    last = df.iloc[-1]
                    chg = (last['Close']/df.iloc[-2]['Close']-1)*100
                    summary.append({
                        "名称": s['name'], "代码": s['code'], 
                        "价格": round(last['Close'], 2), "涨幅": f"{chg:+.2f}%",
                        "MA5": round(last['SMA_5'], 2), "MA10": round(last['SMA_10'], 2),
                        "信号": sig, "决策": adv
                    })
            
            if summary:
                res_df = pd.DataFrame(summary)
                def style_adv(val):
                    if '买入' in val: return 'color: #00ff00; font-weight: bold'
                    if '止损' in val: return 'color: #ff4b4b; font-weight: bold'
                    return 'color: #ffa500'
                st.dataframe(res_df.style.applymap(style_adv, subset=['决策']), use_container_width=True, hide_index=True)
                
                # 下方增加该板块的详情选择
                target = st.selectbox(f"🎯 穿透分析 ({sector_name})", [f"{x['code']} | {x['name']}" for x in stocks], key=f"sel_{i}")
                t_code = target.split(' | ')
                t_yf = f"{t_code}.SS" if t_code.startswith('6') else f"{t_code}.SZ"
                df_t = fetch_analysis(t_yf)
                
                if df_t is not None:
                    col_k, col_d = st.columns([2, 1])
                    with col_k:
                        fig = go.Figure(data=[go.Candlestick(x=df_t.index, open=df_t['Open'], high=df_t['High'], low=df_t['Low'], close=df_t['Close'], name='K线')])
                        for m, c in zip(['SMA_5', 'SMA_10', 'SMA_20'], ['white', 'yellow', 'orange']):
                            fig.add_trace(go.Scatter(x=df_t.index, y=df_t[m], name=m, line=dict(color=c, width=1)))
                        fig.update_layout(template="plotly_dark", height=400, xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,b=0,t=0))
                        st.plotly_chart(fig, use_container_width=True)
                    with col_d:
                        adv, color, sig = get_decision(df_t)
                        st.metric("实时评分", sig, delta=adv)
                        st.divider()
                        last_p = df_t['Close'].iloc[-1]
                        atr = df_t['ATRr_14'].iloc[-1]
                        st.metric("动态止损(2xATR)", f"￥{last_p - 2*atr:.2f}")

st.caption(f"数据更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 基于 yfinance 接口")
