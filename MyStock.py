import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="A股云端看板", layout="wide")
st.title("🍎 A股实时决策建议 (云端稳定版)")

# 侧边栏
with st.sidebar:
    st.header("监控配置")
    input_codes = st.text_area("输入代码 (逗号分隔)", "600519, 000001, 300033")
    # yfinance 格式：6开头的加 .SS，其他加 .SZ
    codes = []
    for c in input_codes.replace('，', ',').split(','):
        c = c.strip()
        if len(c) == 6:
            codes.append(f"{c}.SS" if c.startswith('6') else f"{c}.SZ")

# --- 核心函数：使用 yfinance ---
def get_cloud_data(symbols):
    results = []
    for sym in symbols:
        try:
            # yfinance 获取数据（海外服务器直连，极稳）
            ticker = yf.Ticker(sym)
            # 获取最近2天数据
            hist = ticker.history(period="20d")
            if hist.empty: continue
            
            price = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2]
            change = (price / prev_close - 1) * 100
            ma20 = hist['Close'].mean()
            
            advice = "🟢 强于均线" if price > ma20 else "🔴 弱于均线"
            
            results.append({
                "代码": sym.split('.')[0],
                "最新价": round(price, 2),
                "涨跌幅": f"{change:.2f}%",
                "20日线": round(ma20, 2),
                "决策": advice
            })
        except:
            continue
    return pd.DataFrame(results)

if st.button("🔄 刷新云端行情"):
    if not codes:
        st.warning("请先输入股票代码")
    else:
        with st.spinner("正在通过国际专线获取数据..."):
            df = get_cloud_data(codes)
            if not df.empty:
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.success(f"2026年{datetime.now().strftime('%m-%d %H:%M')} 数据同步成功")
            else:
                st.error("数据源无响应，请确认代码是否正确（如 600519, 000001）")

st.info("💡 提示：该版本使用 yfinance 接口，专为海外云端环境优化，无需担心 IP 屏蔽。")
