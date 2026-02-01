import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os
import re

# 彻底禁用环境代理，防止 yfinance 连接拦截
os.environ['HTTP_PROXY'] = ""
os.environ['HTTPS_PROXY'] = ""

st.set_page_config(page_title="A股金叉预警看板", layout="wide")

# --- 1. 核心解析与名称匹配逻辑 ---
def parse_input(raw_text):
    """
    解析输入并尝试提取代码和名称
    返回字典 {代码: 名称}
    """
    # 提取所有 "6位数字 | 名称" 格式
    name_matches = re.findall(r'(\d{6})\s*\|\s*([\u4e00-\u9fa5\w]+)', raw_text)
    # 提取所有纯 6 位数字
    pure_codes = re.findall(r'\b\d{6}\b', raw_text)
    
    stock_dict = {}
    # 先填充带名称的
    for code, name in name_matches:
        stock_dict[code] = name
    # 再补充纯代码（如果字典里还没这个代码）
    for code in pure_codes:
        if code not in stock_dict:
            stock_dict[code] = "查询中..." # 初始占位
            
    return stock_dict

# --- 2. 侧边栏配置 ---
with st.sidebar:
    st.header("🎯 监控配置")
    st.markdown("支持：`002498 | 汉缆股份` 或 `600519`")
    
    default_value = "002498 | 汉缆股份\n600519 | 贵州茅台\n300750 | 宁德时代\n002657 | 中科金财"
    raw_input = st.text_area("输入监控列表：", value=default_value, height=200)
    
    # 实时解析
    target_stocks = parse_input(raw_input)
    st.success(f"已识别 {len(target_stocks)} 只股票")
    
    st.divider()
    ma_choice = st.radio("金叉预警类型", ["5日/10日金叉", "10日/20日金叉"])
    st.caption("数据源：Yahoo Finance (2026)")

# --- 3. 数据获取与计算函数 ---
def get_analysis(stock_dict, ma_short_n, ma_long_n):
    results = []
    
    for code, name in stock_dict.items():
        try:
            # yfinance 后缀适配
            symbol = f"{code}.SS" if code.startswith('6') else f"{code}.SZ"
            ticker = yf.Ticker(symbol)
            
            # 获取 60 天历史数据
            hist = ticker.history(period="60d", interval="1d", timeout=10)
            if len(hist) < ma_long_n + 2:
                continue
            
            # 如果名称是“查询中...”，尝试从 yfinance info 中获取（仅限云端网络好的情况）
            display_name = name
            if display_name == "查询中...":
                try:
                    # 备选：如果 yfinance 拿不到中文名，就显示代码
                    display_name = ticker.info.get('shortName', code)
                except:
                    display_name = code

            # 计算均线
            hist['MA_S'] = hist['Close'].rolling(window=ma_short_n).mean()
            hist['MA_L'] = hist['Close'].rolling(window=ma_long_n).mean()
            
            curr_s, curr_l = hist['MA_S'].iloc[-1], hist['MA_L'].iloc[-1]
            prev_s, prev_l = hist['MA_S'].iloc[-2], hist['MA_L'].iloc[-2]
            curr_price = hist['Close'].iloc[-1]
            
            # 信号逻辑
            status = "无明显信号"
            if prev_s <= prev_l and curr_s > curr_l:
                status = "✨ 形成金叉"
            elif prev_s >= prev_l and curr_s < curr_l:
                status = "💀 死叉警示"
            
            results.append({
                "代码": code,
                "名称": display_name,
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
st.title("📈 A股趋势决策看板 (含名称显示)")
st.caption(f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if st.button("🔄 刷新监控信号"):
    if not target_stocks:
        st.warning("请输入有效的股票信息。")
    else:
        with st.spinner("正在获取国际行情数据并解析名称..."):
            short_n, long_n = (5, 10) if "5日" in ma_choice else (10, 20)
            df = get_analysis(target_stocks, short_n, long_n)
            
            if not df.empty:
                # 信号高亮
                def color_status(val):
                    if '金叉' in val: return 'background-color: #004d00; color: white'
                    if '死叉' in val: return 'background-color: #4d0000; color: white'
                    return ''
                
                # 调整列顺序，将名称放在代码后面
                cols = ["代码", "名称", "最新价", f"MA{short_n}", f"MA{long_n}", "信号状态", "5日乖离"]
                st.dataframe(
                    df[cols].style.applymap(color_status, subset=['信号状态']), 
                    use_container_width=True, 
                    hide_index=True
                )
                
                # 弹窗提示金叉
                gold_count = len(df[df['信号状态'] == "✨ 形成金叉"])
                if gold_count > 0:
                    st.toast(f"检测到 {gold_count} 个新形成的金叉信号！", icon="🚀")
            else:
                st.error("未获取到有效行情，请检查代码或网络。")

st.divider()
st.info("提示：如果直接输入 6 位代码，系统会尝试从 Yahoo Finance 抓取英文缩写名称；建议输入 `代码 | 名称` 格式以获得最佳显示效果。")
