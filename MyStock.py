import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os
import re

# 1. 环境配置
os.environ['HTTP_PROXY'] = ""
os.environ['HTTPS_PROXY'] = ""
DB_FILE = "my_monitors.txt"  # 持久化存储文件

st.set_page_config(page_title="A股持久化预警看板", layout="wide")

# --- 2. 持久化读写函数 ---
def load_saved_stocks():
    """从本地文件加载股票列表"""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return "002498 | 汉缆股份\n600519 | 贵州茅台\n300750 | 宁德时代"

def save_stocks(text):
    """保存股票列表到本地文件"""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        f.write(text)

def parse_input(raw_text):
    """解析输入并提取 {代码: 名称}"""
    name_matches = re.findall(r'(\d{6})\s*\|\s*([\u4e00-\u9fa5\w\s]+)', raw_text)
    pure_codes = re.findall(r'\b\d{6}\b', raw_text)
    
    stock_dict = {}
    for code, name in name_matches:
        stock_dict[code] = name.strip()
    for code in pure_codes:
        if code not in stock_dict:
            stock_dict[code] = "查询中..."
    return stock_dict

# --- 3. 侧边栏配置 ---
with st.sidebar:
    st.header("🎯 监控配置 (自动保存)")
    st.markdown("格式：`代码 | 名称` 或 `纯代码`")
    
    # 加载已保存的数据
    saved_data = load_saved_stocks()
    
    # 用户输入框
    raw_input = st.text_area("监控列表：", value=saved_data, height=300)
    
    # 只要内容变化，就自动保存
    if raw_input != saved_data:
        save_stocks(raw_input)
        st.toast("配置已自动保存", icon="💾")
    
    target_stocks = parse_input(raw_input)
    st.success(f"已识别 {len(target_stocks)} 只股票")
    
    st.divider()
    ma_choice = st.radio("均线预警类型", ["5/10日金叉", "10/20日金叉"])

# --- 4. 行情获取与计算 ---
def get_analysis(stock_dict, ma_short_n, ma_long_n):
    results = []
    for code, name in stock_dict.items():
        try:
            symbol = f"{code}.SS" if code.startswith('6') else f"{code}.SZ"
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="60d", timeout=10)
            
            if len(hist) < ma_long_n + 2: continue
            
            # 均线计算
            hist['MA_S'] = hist['Close'].rolling(window=ma_short_n).mean()
            hist['MA_L'] = hist['Close'].rolling(window=ma_long_n).mean()
            
            curr_s, curr_l = hist['MA_S'].iloc[-1], hist['MA_L'].iloc[-1]
            prev_s, prev_l = hist['MA_S'].iloc[-2], hist['MA_L'].iloc[-2]
            curr_price = hist['Close'].iloc[-1]
            
            # 信号判断
            status = "无信号"
            if prev_s <= prev_l and curr_s > curr_l:
                status = "✨ 形成金叉"
            elif prev_s >= prev_l and curr_s < curr_l:
                status = "💀 死叉警示"
            
            results.append({
                "代码": code,
                "名称": name if name != "查询中..." else code,
                "最新价": round(curr_price, 2),
                f"MA{ma_short_n}": round(curr_s, 2),
                f"MA{ma_long_n}": round(curr_l, 2),
                "信号状态": status,
                "5日偏离": f"{((curr_price/hist['MA_S'].iloc[-1])-1)*100:.2f}%"
            })
        except: continue
    return pd.DataFrame(results)

# --- 5. 主展示区 ---
st.title("📈 A股持久化决策看板")
st.caption(f"最后刷新: {datetime.now().strftime('%H:%M:%S')} | 数据源: Yahoo Finance")

if st.button("🔄 执行全量扫描", use_container_width=True):
    if not target_stocks:
        st.warning("请在左侧添加股票。")
    else:
        with st.spinner("正在穿透网络同步数据..."):
            s_n, l_n = (5, 10) if "5/10" in ma_choice else (10, 20)
            df = get_analysis(target_stocks, s_n, l_n)
            
            if not df.empty:
                # 信号高亮函数
                def style_status(val):
                    if '金叉' in val: return 'background-color: #004d00; color: white'
                    if '死叉' in val: return 'background-color: #4d0000; color: white'
                    return ''

                cols = ["代码", "名称", "最新价", f"MA{s_n}", f"MA{l_n}", "信号状态", "5日偏离"]
                st.dataframe(
                    df[cols].style.applymap(style_status, subset=['信号状态']),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.error("获取行情失败，请确保网络可直连 Yahoo Finance。")

st.divider()
st.info("💡 **持久化提示**：你在左侧输入的列表会实时保存到同目录下的 `my_monitors.txt` 中。")
