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
    for code in codes:
        try:
            # 方案：使用腾讯财经接口（对海外 IP 兼容性更好）
            # 沪市 6 开头加 sh，深市 0/3 开头加 sz
            symbol = f"sh{code}" if code.startswith('6') else f"sz{code}"
            url = f"http://qt.gtimg.cn_{symbol}"
            
            # 增加随机 Header 模拟浏览器，防止被封
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            resp = requests.get(url, timeout=5, headers=headers)
            
            if resp.status_code == 200 and 'v_s_' in resp.text:
                data = resp.text.split('~')
                name = data[1]
                price = float(data[3])
                change_pct = f"{data[5]}%"
                
                # 获取历史数据（Akshare 的历史数据接口目前海外访问尚可）
                # 如果这一步卡住，说明历史接口也被封，建议先注释掉止损计算
                hist = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq").tail(20)
                ma20 = hist['收盘'].mean()
                stop_loss = hist['最低'].tail(5).min() * 0.98
                
                status = "🟢 持股" if price > ma20 else "🔴 风险"
                
                results.append({
                    "代码": code, "名称": name, "最新价": price, 
                    "涨跌幅": change_pct, "建议止损位": round(stop_loss, 2), "状态": status
                })
        except Exception as e:
            # st.write(f"调试：{code} 获取失败") # 仅供调试
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

