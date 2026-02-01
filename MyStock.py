import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="A股纯代码监控看板", layout="wide")
st.title("📊 A股多均线决策决策看板 (2026版)")

# --- 侧边栏：纯代码配置 ---
with st.sidebar:
    st.header("监控配置")
    raw_input = st.text_area("输入6位股票代码 (逗号分隔)", "600519, 000001, 300033")
    
    # 纯代码解析逻辑
    processed_codes = []
    items = [i.strip() for i in raw_input.replace('，', ',').split(',') if i.strip()]
    
    for item in items:
        if item.isdigit() and len(item) == 6:
            # 自动补全 yfinance 后缀
            suffix = ".SS" if item.startswith('6') else ".SZ"
            processed_codes.append(f"{item}{suffix}")

    st.success(f"已识别：{len(processed_codes)} 只标的")

# --- 核心函数：计算多均线数据 ---
def get_ma_analysis(symbols):
    results = []
    for sym in symbols:
        try:
            # 获取最近 30 天的历史数据，足以计算 MA5, MA10, MA20
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="30d")
            
            if hist.empty: continue
            
            # 当前数据
            curr_price = hist['Close'].iloc[-1]
            prev_price = hist['Close'].iloc[-2]
            change = (curr_price / prev_price - 1) * 100
            
            # 计算多周期均线
            ma5 = hist['Close'].tail(5).mean()
            ma10 = hist['Close'].tail(10).mean()
            ma20 = hist['Close'].tail(20).mean()
            
            # 综合决策逻辑 (站稳5日线且5日线上穿10日线)
            if curr_price > ma5 and ma5 > ma10:
                advice = "🟢 多头强势"
            elif curr_price < ma5:
                advice = "🔴 跌破5日线"
            else:
                advice = "🟡 震荡整理"
            
            results.append({
                "代码": sym.split('.')[0],
                "最新价": round(curr_price, 2),
                "涨跌幅": f"{change:.2f}%",
                "5日线": round(ma5, 2),
                "10日线": round(ma10, 2),
                "20日线": round(ma20, 2),
                "偏离MA5": f"{((curr_price/ma5)-1)*100:.2f}%",
                "决策状态": advice
            })
        except:
            continue
    return pd.DataFrame(results)

# --- 主界面展示 ---
if st.button("🔄 刷新全网行情与均线数据"):
    if not processed_codes:
        st.warning("请输入有效的6位股票代码。")
    else:
        with st.spinner("数据穿透获取中..."):
            df = get_ma_analysis(processed_codes)
            if not df.empty:
                # 定义染色逻辑
                def color_advice(val):
                    if '强势' in val: return 'color: #00ff00; font-weight: bold'
                    if '跌破' in val: return 'color: #ff4b4b; font-weight: bold'
                    return 'color: #ffa500'

                st.dataframe(
                    df.style.applymap(color_advice, subset=['决策状态']),
                    use_container_width=True,
                    hide_index=True
                )
                st.caption(f"数据源：Yahoo Finance | 更新时间：{datetime.now().strftime('%H:%M:%S')}")
            else:
                st.error("未获取到数据，请检查代码格式。")

st.divider()
st.info("""
💡 **操作指南：**
1. **买入参考**：股价站上5日线且5日线 > 10日线时，短期趋势向好。
2. **止损参考**：股价收盘有效跌破5日线或10日线，建议离场。
""")
