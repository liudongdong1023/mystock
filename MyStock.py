import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os

# 彻底禁用环境代理，防止 yfinance 连接本地拦截
os.environ['HTTP_PROXY'] = ""
os.environ['HTTPS_PROXY'] = ""

# 设置页面
st.set_page_config(page_title="A股金叉预警看板", layout="wide")

# --- 1. 手动维护股票清单 (不使用接口，防封禁) ---
COMMON_STOCKS = {
    "600519": "贵州茅台", "000001": "平安银行", "300750": "宁德时代", 
    "002657": "中科金财", "002315": "焦点科技", "688041": "海光信息",
    "688256": "寒武纪", "300033": "同花顺", "002230": "科大讯飞",
    "300058": "蓝色光标", "688095": "福昕软件", "300624": "万兴科技",
    "000702": "正虹科技", "603019": "中科曙光"
}

# --- 2. UI 侧边栏 ---
with st.sidebar:
    st.header("🎯 监控配置")
    
    # 允许手动添加代码
    custom_input = st.text_input("手动增加代码(6位数字, 逗号分隔)", "")
    if custom_input:
        for c in custom_input.replace('，', ',').split(','):
            c = c.strip()
            if len(c) == 6 and c not in COMMON_STOCKS:
                COMMON_STOCKS[c] = "自定义添加"

    # 构建选择列表
    stock_options = [f"{k} | {v}" for k, v in COMMON_STOCKS.items()]
    selected_display = st.multiselect(
        "选择监控池：",
        options=stock_options,
        default=stock_options[:8]
    )
    
    st.divider()
    ma_choice = st.radio("金叉预警类型", ["5日/10日金叉", "10日/20日金叉"])
    st.info("数据源：Yahoo Finance (2026版)")

# --- 3. 核心计算函数 ---
def check_golden_cross(display_list, ma_short_n, ma_long_n):
    results = []
    # 提取代码
    codes = [item.split(' | ')[0] for item in display_list]
    
    for code in codes:
        try:
            # yfinance 后缀转换
            symbol = f"{code}.SS" if code.startswith('6') else f"{code}.SZ"
            
            # 获取 60 天数据确保均线计算完整
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="60d", interval="1d", timeout=10)
            
            if len(hist) < ma_long_n + 2:
                continue
                
            # 计算均线
            hist['MA_S'] = hist['Close'].rolling(window=ma_short_n).mean()
            hist['MA_L'] = hist['Close'].rolling(window=ma_long_n).mean()
            
            # 获取数值
            curr_s = hist['MA_S'].iloc[-1]
            curr_l = hist['MA_L'].iloc[-1]
            prev_s = hist['MA_S'].iloc[-2]
            prev_l = hist['MA_L'].iloc[-2]
            curr_price = hist['Close'].iloc[-1]
            
            # 判断逻辑
            status = "无明显信号"
            if prev_s <= prev_l and curr_s > curr_l:
                status = "✨ 刚形成金叉"
            elif prev_s >= prev_l and curr_s < curr_l:
                status = "💀 死叉警示"
            
            results.append({
                "代码": code,
                "名称": COMMON_STOCKS.get(code, "未知"),
                "最新价": round(curr_price, 2),
                f"MA{ma_short_n}": round(curr_s, 2),
                f"MA{ma_long_n}": round(curr_l, 2),
                "信号状态": status,
                "乖离率(MA5)": f"{((curr_price/hist['MA_S'].iloc[-1])-1)*100:.2f}%"
            })
        except:
            continue
    return pd.DataFrame(results)

# --- 4. 主展示区 ---
st.title("📈 A股趋势自动决策看板")
st.caption(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 数据源：Yahoo国际接口")

if st.button("🔄 立即扫描监控池信号"):
    if not selected_display:
        st.warning("请在左侧侧边栏选择监控股票。")
    else:
        with st.spinner("正在获取国际行情数据，请稍候..."):
            short_n, long_n = (5, 10) if "5日" in ma_choice else (10, 20)
            df = check_golden_cross(selected_display, short_n, long_n)
            
            if not df.empty:
                # 1. 重点信号提取
                signals = df[df['信号状态'] != "无明显信号"]
                if not signals.empty:
                    st.subheader("🚩 关键预警信号")
                    
                    def color_status(val):
                        if '金叉' in val: return 'background-color: #004d00; color: white'
                        if '死叉' in val: return 'background-color: #4d0000; color: white'
                        return ''
                    
                    st.table(signals.style.applymap(color_status, subset=['信号状态']))
                else:
                    st.info("当前监控池内暂未发现趋势拐点信号。")
                
                # 2. 全量监控清单
                st.subheader("📋 实时运行看板")
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.error("数据抓取失败。请尝试：1. 彻底关闭本地翻墙代理；2. 检查网络是否能访问 finance.yahoo.com")

st.divider()
st.caption("提示：由于 Yahoo Finance 行情有约 15 分钟延迟，本工具建议用于波段趋势参考，而非分时短线抢单。")
