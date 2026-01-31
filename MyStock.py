import streamlit as st
import akshare as ak
import pandas as pd
import os
import time

# 确保无代理干扰
os.environ['HTTP_PROXY'] = ""
os.environ['HTTPS_PROXY'] = ""

st.set_page_config(page_title="A股高级决策看板", layout="wide")

# --- 核心算法：计算建议 ---
def get_analysis(codes):
    results = []
    # 获取全市场实时快照（一次性获取比循环获取快）
    try:
        all_spot = ak.stock_zh_a_spot_em()
    except:
        st.error("无法连接实时行情接口，请检查网络")
        return pd.DataFrame()

    for code in codes:
        try:
            # 1. 提取实时数据
            row = all_spot[all_spot['代码'] == code].iloc[0]
            price = float(row['最新价'])
            
            # 2. 获取历史数据计算 ATR 止损 (近20日)
            hist = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq").tail(20)
            # 计算波动率 (最高-最低的平均值)
            atr = (hist['最高'] - hist['最低']).mean()
            ma20 = hist['收盘'].mean()
            
            # 3. 止损位：跌破近5日最低价或 MA20
            support_level = min(hist['最低'].tail(5).min(), ma20)
            stop_loss = support_level * 0.98 # 预留2%容错
            
            # 4. 建议逻辑
            if price <= stop_loss:
                status = "🔴 立即止损/减仓"
            elif price > ma20:
                status = "🟢 趋势走强/持股"
            else:
                status = "🟡 震荡磨底/观察"
            
            results.append({
                "代码": code,
                "名称": row['名称'],
                "最新价": price,
                "涨跌幅": f"{row['涨跌幅']}%",
                "20日均线": round(ma20, 2),
                "建议止损位": round(stop_loss, 2),
                "操作状态": status
            })
        except:
            continue
    return pd.DataFrame(results)

# --- UI 界面 ---
st.title("🍎 我的 A股 自动决策看板")
st.sidebar.header("自选监控配置")
input_codes = st.sidebar.text_area("输入6位股票代码 (英文逗号分隔)", "600519, 000001, 300033")
auto_refresh = st.sidebar.checkbox("开启自动刷新 (60秒)")

codes = [c.strip() for c in input_codes.replace('，', ',').split(',') if len(c.strip()) == 6]

if st.button("🚀 手动执行分析"):
    with st.spinner('正在分析市场数据...'):
        df = get_analysis(codes)
        if not df.empty:
            # 列表展示并根据状态染色
            def color_status(val):
                color = 'red' if '止损' in val else 'green' if '持股' in val else 'orange'
                return f'color: {color}; font-weight: bold'
            
            st.dataframe(df.style.applymap(color_status, subset=['操作状态']), use_container_width=True)
            st.toast("分析完成！", icon='✅')
        else:
            st.warning("选股池为空或数据源无响应")

# 自动刷新逻辑
if auto_refresh:
    time.sleep(60)
    st.rerun()
