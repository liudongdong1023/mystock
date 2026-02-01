import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

# 设置页面配置
st.set_page_config(page_title="A股金叉预警(yfinance版)", layout="wide")

# --- 1. 手动配置常用股票池 (不使用接口拉取清单) ---
# 你可以根据需要在此列表中添加或删除代码
COMMON_STOCKS = {
    "600519": "贵州茅台", "000001": "平安银行", "300750": "宁德时代", 
    "002657": "中科金财", "002315": "焦点科技", "688041": "海光信息",
    "688256": "寒武纪", "300033": "同花顺", "002230": "科大讯飞",
    "300058": "蓝色光标", "688095": "福昕软件", "300624": "万兴科技"
}

# --- 2. 侧边栏：监控池设定 ---
with st.sidebar:
    st.header("🎯 自动预警设置")
    
    # 允许手动输入代码，增加灵活性
    custom_input = st.text_input("手动增加代码(逗号分隔)", "")
    if custom_input:
        for c in custom_input.replace('，', ',').split(','):
            c = c.strip()
            if len(c) == 6 and c not in COMMON_STOCKS:
                COMMON_STOCKS[c] = "自定义"

    # 构建选择列表
    stock_options = [f"{k} | {v}" for k, v in COMMON_STOCKS.items()]
    selected_display = st.multiselect(
        "选择监控池：",
        options=stock_options,
        default=stock_options[:5] # 默认选前5个
    )
    
    st.divider()
    ma_type = st.radio("监控周期", ["5日/10日金叉", "10日/20日金叉"])
    st.info("数据源：Yahoo Finance (海外直连)")

# --- 3. 核心算法：基于 yfinance 的金叉检测 ---
def check_signals(display_list, ma_short_n, ma_long_n):
    results = []
    for item in display_list:
        try:
            code = item.split(' | ')
            # 格式转换：6开头.SS，其他.SZ
            sym = f"{code}.SS" if code.startswith('6') else f"{code}.SZ"
            
            # 获取历史K线
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="60d") # 拿到60天数据计算均线
            
            if len(hist) < ma_long_n + 2: continue
            
            # 计算均线
            hist['MA_S'] = hist['Close'].rolling(window=ma_short_n).mean()
            hist['MA_L'] = hist['Close'].rolling(window=ma_long_n).mean()
            
            # 提取当前和昨日数据
            curr_s, curr_l = hist['MA_S'].iloc[-1], hist['MA_L'].iloc[-1]
            prev_s, prev_l = hist['MA_S'].iloc[-2], hist['MA_L'].iloc[-2]
            curr_price = hist['Close'].iloc[-1]
            
            # 逻辑判断
            status = "无信号"
            if prev_s <= prev_l and curr_s > curr_l:
                status = "✨ 形成金叉"
            elif prev_s >= prev_l and curr_s < curr_l:
                status = "💀 死叉预警"
            
            results.append({
                "代码": code,
                "名称": COMMON_STOCKS.get(code, "未知"),
                "最新价": round(curr_price, 2),
                f"MA{ma_short_n}": round(curr_s, 2),
                f"MA{ma_long_n}": round(curr_l, 2),
                "当日信号": status,
                "距MA5偏离": f"{((curr_price/hist['MA_S'].iloc[-1])-1)*100:.2f}%"
            })
        except:
            continue
    return pd.DataFrame(results)

# --- 4. 主界面展示 ---
st.title("📈 A股均线信号自动监控系统")
st.caption(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (每15分钟更新一次延迟行情)")

if st.button("🚀 扫描实时金叉信号"):
    if not selected_display:
        st.warning("请在左侧选择股票。")
    else:
        with st.spinner("正在通过 Yahoo Finance 穿透获取行情..."):
            short_n, long_n = (5, 10) if "5日" in ma_type else (10, 20)
            df = check_signals(selected_display, short_n, long_n)
            
            if not df.empty:
                # 1. 优先展示触发信号的个股
                signals = df[df['当日信号'] != "无信号"]
                if not signals.empty:
                    st.subheader("🚩 关键预警")
                    
                    def color_status(val):
                        if '金叉' in val: return 'background-color: #004d00; color: white'
                        if '死叉' in val: return 'background-color: #4d0000; color: white'
                        return ''
                    
                    st.table(signals.style.applymap(color_status, subset=['当日信号']))
                else:
                    st.info("当前监控池内暂未发现穿越信号。")
                
                # 2. 展示完整监控清单
                st.subheader("📋 实时监控清单")
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.error("无法获取行情数据，请检查网络或代码后缀是否正确。")

st.divider()
st.caption("提示：yfinance 获取的 A 股行情有约 15 分钟延迟，适合趋势参考，不适合分秒必争的短线抢单。")
