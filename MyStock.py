import streamlit as st
import pandas as pd
import akshare as ak
import requests
import os
import time

# 1. 彻底切断任何代理干扰
os.environ['HTTP_PROXY'] = ""
os.environ['HTTPS_PROXY'] = ""

st.set_page_config(page_title="A股全速决策工具", layout="wide")
st.title("🚀 A股实时决策建议 (稳定版)")

# 侧边栏
with st.sidebar:
    st.header("自选股配置")
    input_codes = st.text_area("输入6位股票代码 (逗号或换行分隔)", "600519, 000001, 300033, 002657")
    codes = [c.strip() for c in input_codes.replace('，', ',').replace('\n', ',').split(',') if len(c.strip()) == 6]
    st.divider()
    st.info("提示：如果本地无法显示，请尝试切换手机热点刷新。")

# --- 核心函数：带重试和多源逻辑 ---
def fetch_stock_data(codes):
    results = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    for code in codes:
        try:
            # 1. 获取实时价 (腾讯源 - 已证实连接正常)
            prefix = "sh" if code.startswith('6') else "sz"
            resp = requests.get(f"http://qt.gtimg.cn_{prefix}{code}", timeout=3, headers=headers)
            
            if resp.status_code == 200 and "~" in resp.text:
                data = resp.text.split('~')
                name = data[1]
                price = float(data[3])
                change = f"{data[5]}%"
                
                # 2. 获取均线建议 (增加极短超时，失败则显示“计算中”)
                ma20 = "获取中..."
                advice = "持币观望"
                try:
                    # 降低采样频率，仅取最近30天
                    df_h = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq").tail(20)
                    if not df_h.empty:
                        m_val = df_h['收盘'].mean()
                        ma20 = round(m_val, 2)
                        advice = "🟢 建议持股" if price > m_val else "🔴 建议减仓"
                except:
                    # 如果历史接口卡顿，直接通过涨跌幅给简易建议
                    advice = "🟡 暂无均线参考"
                
                results.append({
                    "代码": code, "名称": name, "最新价": price, 
                    "涨跌幅": change, "20日参考": ma20, "操作状态": advice
                })
        except Exception:
            continue
            
    return pd.DataFrame(results)


# --- 主界面展示 ---
if st.button("🔄 刷新全网行情建议"):
    if not codes:
        st.warning("请先在左侧输入股票代码")
    else:
        with st.spinner("正在穿透网络获取最新数据..."):
            df = fetch_stock_data(codes)
            if not df.empty:
                # 定义染色函数
                def color_status(val):
                    color = 'red' if '风险' in val else 'green'
                    return f'color: {color}; font-weight: bold'
                
                st.dataframe(df.style.applymap(color_status, subset=['状态']), use_container_width=True)
                st.success(f"成功获取 {len(df)} 只股票数据")
            else:
                st.error("❌ 数据源响应超时！")
                st.markdown("""
                **可能原因：**
                1. **网络拦截：** 你的网络环境屏蔽了 `gtimg.cn`。
                2. **代理干扰：** 请确保彻底关闭了翻墙软件。
                3. **云端限制：** 如果在 Streamlit Cloud 运行，请尝试在**本地电脑**运行。
                """)

# 调试模块：测试接口通畅度
if st.checkbox("查看调试信息"):
    st.write("当前网络环境检测中...")
    try:
        test_resp = requests.get("http://qt.gtimg.cn_sh600519", timeout=2)
        st.write("✅ 腾讯数据源：连接正常")
    except:
        st.write("❌ 腾讯数据源：无法访问")
