import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os
import re

# 彻底禁用代理
os.environ['HTTP_PROXY'] = ""
os.environ['HTTPS_PROXY'] = ""

st.set_page_config(page_title="A股全格式监控看板", layout="wide")

# --- 1. 核心解析函数 ---
def parse_stock_codes(raw_text):
    """
    支持解析:
    1. 002498 | 汉缆股份
    2. 002498
    3. 600519, 000001 (逗号或换行分隔)
    """
    # 使用正则提取文本中所有的 6 位数字
    codes = re.findall(r'\b\d{6}\b', raw_text)
    # 去重
    return list(dict.fromkeys(codes))

# --- 2. UI 侧边栏 ---
with st.sidebar:
    st.header("🎯 监控配置")
    
    # 修改输入框描述，引导用户支持多种格式
    st.markdown("支持格式：`002498 | 汉缆股份` 或 `600519`")
    raw_input = st.text_area(
        "输入监控列表：", 
        value="002498 | 汉缆股份\n600519 | 贵州茅台\n300750\n002657",
        height=200
    )
    
    # 解析出纯代码列表
    processed_codes = parse_stock_codes(raw_input)
    
    st.success(f"已识别 {len(processed_codes)} 只股票")
    
    st.divider()
    ma_choice = st.radio("金叉预警类型", ["5日/10日金叉", "10日/20日金叉"])
    st.caption("数据源：Yahoo Finance (2026)")

# --- 3. 核心计算函数 ---
def check_golden_cross(codes, ma_short_n, ma_long_n):
    results = []
    
    for code in codes:
        try:
            # yfinance 后缀转换
            symbol = f"{code}.SS" if code.startswith('6') else f"{code}.SZ"
            
            # 获取历史K线
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="60d", interval="1d", timeout=10)
            
            if len(hist) < ma_long_n + 2:
                continue
                
            # 计算均线
            hist['MA_S'] = hist['Close'].rolling(window=ma_short_n).mean()
            hist['MA_L'] = hist['Close'].rolling(window=ma_long_n).mean()
            
            curr_s = hist['MA_S'].iloc[-1]
            curr_l = hist['MA_L'].iloc[-1]
            prev_s = hist['MA_S'].iloc[-2]
            prev_l = hist['MA_L'].iloc[-2]
            curr_price = hist['Close'].iloc[-1]
            
            # 信号逻辑
            status = "持平"
            if prev_s <= prev_l and curr_s > curr_l:
                status = "✨ 金叉形成"
            elif prev_s >= prev_l and curr_s < curr_l:
                status = "💀 死叉警示"
            elif curr_s > curr_l:
                status = "📈 多头排列"
            else:
                status = "📉 空头排列"
            
            results.append({
                "代码": code,
                "最新价": round(curr_price, 2),
                f"MA{ma_short_n}": round(curr_s, 2),
                f"MA{ma_long_n}": round(curr_l, 2),
                "信号状态": status,
                "5日乖离": f"{((curr_price/hist['MA_S'].iloc[-1])-1)*100:.2f}%"
            })
        except:
            continue
    return pd.DataFrame(results)

# --- 4. 主展示区 ---
st.title("📈 A股趋势决策看板 (2026版)")
st.caption(f"当前自选池：{', '.join(processed_codes)}")

if st.button("🚀 刷新监控信号"):
    if not processed_codes:
        st.warning("请输入有效的代码。")
    else:
        with st.spinner("正在获取行情数据..."):
            short_n, long_n = (5, 10) if "5日" in ma_choice else (10, 20)
            df = check_golden_cross(processed_codes, short_n, long_n)
            
            if not df.empty:
                # 信号高亮
                def color_status(val):
                    if '金叉' in val: return 'background-color: #004d00; color: white'
                    if '死叉' in val: return 'background-color: #4d0000; color: white'
                    return ''
                
                st.dataframe(
                    df.style.applymap(color_status, subset=['信号状态']), 
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.error("未获取到数据，请检查网络。")

st.info("提示：您可以直接从其他软件复制 `代码 | 名称` 格式的文本粘贴到左侧。")
