import streamlit as st
import pandas as pd
import yfinance as yf
import akshare as ak
from datetime import datetime

# 设置页面
st.set_page_config(page_title="A股全市场监控", layout="wide")

# --- 1. 缓存：获取全市场股票清单 ---
@st.cache_data(ttl=86400) # 每天更新一次清单即可
def get_all_stock_names():
    try:
        # 获取实时行情快照作为基础清单
        df = ak.stock_zh_a_spot_em()
        # 构造“代码 | 名称”格式，方便搜索
        df['display_name'] = df['代码'] + " | " + df['名称']
        return df[['display_name', '代码', '名称']]
    except:
        st.error("初始化全市场清单失败，请检查网络。")
        return pd.DataFrame()

all_stocks = get_all_stock_names()

# --- 2. 侧边栏：搜索与添加功能 ---
with st.sidebar:
    st.header("🔍 股票搜索与添加")
    
    if not all_stocks.empty:
        # 核心：支持模糊搜索的多选框
        selected_display = st.multiselect(
            "输入名称或代码搜索：",
            options=all_stocks['display_name'].tolist(),
            default=["600519 | 贵州茅台", "000001 | 平安银行"] # 默认值
        )
        
        # 提取选中的 6 位代码
        selected_codes = [item.split(' | ')[0] for item in selected_display]
    else:
        selected_codes = []
        
    st.divider()
    st.info(f"当前已选择 {len(selected_codes)} 只股票")

# --- 3. 核心函数：获取行情与计算指标 ---
def get_stock_analysis(codes):
    results = []
    for c in codes:
        try:
            # 自动转换 yfinance 格式
            sym = f"{c}.SS" if c.startswith('6') else f"{c}.SZ"
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="30d")
            
            if hist.empty: continue
            
            curr_price = hist['Close'].iloc[-1]
            prev_price = hist['Close'].iloc[-2]
            change = (curr_price / prev_price - 1) * 100
            
            # 计算多周期均线
            ma5 = hist['Close'].tail(5).mean()
            ma10 = hist['Close'].tail(10).mean()
            ma20 = hist['Close'].tail(20).mean()
            
            # 获取股票名称
            name = all_stocks[all_stocks['代码'] == c]['名称'].values[0]
            
            # 决策逻辑
            if curr_price > ma5 and ma5 > ma10:
                advice = "🟢 多头向上"
            elif curr_price < ma5:
                advice = "🔴 跌破5日线"
            else:
                advice = "🟡 震荡整理"
                
            results.append({
                "代码": c,
                "名称": name,
                "最新价": round(curr_price, 2),
                "涨跌幅": f"{change:.2f}%",
                "5日线": round(ma5, 2),
                "10日线": round(ma10, 2),
                "20日线": round(ma20, 2),
                "偏离MA5": f"{((curr_price/ma5)-1)*100:.2f}%",
                "操作状态": advice
            })
        except:
            continue
    return pd.DataFrame(results)

# --- 4. 主界面：展示分析 ---
st.title("🚀 A股实时决策看板 (2026 搜索版)")

if st.button("🔄 刷新选定股票行情"):
    if not selected_codes:
        st.warning("请在左侧搜索并添加股票。")
    else:
        with st.spinner("正在穿透网络同步实时数据..."):
            df = get_stock_analysis(selected_codes)
            if not df.empty:
                # 染色逻辑
                def color_advice(val):
                    if '向上' in val: return 'color: #00ff00; font-weight: bold'
                    if '跌破' in val: return 'color: #ff4b4b; font-weight: bold'
                    return 'color: #ffa500'

                st.dataframe(
                    df.style.applymap(color_status := color_advice, subset=['操作状态']),
                    use_container_width=True,
                    hide_index=True
                )
                st.caption(f"数据更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                st.error("数据抓取失败，请检查 yfinance 网络。")

st.divider()
st.caption("提示：在左侧输入拼音首字母或中文关键词（如 '宁德'）即可快速查找并添加。")
