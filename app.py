import streamlit as st
import pandas as pd

st.set_page_config(page_title="康橋菜單判讀專家", layout="wide")

with st.sidebar:
    st.header("⚙️ 審核條件自定義")
    target_spicy_days = st.multiselect("哪些日子要『禁辣』？", 
                                       ["週一", "週二", "週三", "週四", "週五"], 
                                       default=["週一", "週二", "週四"])
    fish_list = st.text_input("高級魚類關鍵字 (用逗號隔開)", "鬼頭刀,白帶魚,小卷,鮭魚,扁鱈,鮪魚").split(",")
    fried_limit = st.number_input("每週油炸(◎)上限次數", value=1)

st.title("🍱 康橋校內菜單自動審核系統")

def check_menu_logic(df):
    df = df.fillna("").astype(str)
    report = {"err": [], "ok": []}
    
    # 找「週」所在列
    day_row = None
    for idx, row in df.iterrows():
        if any("週" in cell for cell in row):
            day_row = idx
            break
            
    if day_row is None:
        return {"err": ["❌ 判讀失敗：找不到日期標記列。"], "ok": ["無法判讀內容"]}

    # 按欄位掃描
    for col_idx in range(len(df.columns)):
        day_name = df.iloc[day_row, col_idx].strip()
        if any(d in day_name for d in ["週一", "週二", "週三", "週四", "週五"]):
            col_content = "".join(df.iloc[:, col_idx])
            
            # 1. 辣味檢查
            has_spicy = "🌶️" in col_content or "●" in col_content
            if any(d in day_name for d in target_spicy_days) and has_spicy:
                report["err"].append(f"❌ 違規：{day_name} 偵測到辣味標示 (●/🌶️)。")
            
            # 2. 魚類檢查 (放入詳細結果)
            found_fish = [f.strip() for f in fish_list if f.strip() in col_content and f.strip() != ""]
            fish_msg = f"🐟 {day_name} 魚類：{', '.join(found_fish) if found_fish else '未偵測到'}"
            
            # 3. 符號統計 (放入詳細結果)
            fried_cnt = col_content.count("◎")
            proc_cnt = col_content.count("△")
            stat_msg = f" (炸:{fried_cnt} | 加工:{proc_cnt})"
            
            report["ok"].append(fish_msg + stat_msg)

    return report

# --- 檔案上傳 ---
up = st.file_uploader("👉 請上傳您的 Excel 菜單", type=["xlsx"])

if up:
    try:
        sheets = pd.read_excel(up, sheet_name=None, header=None)
        for name, df in sheets.items():
            st.subheader(f"📊 分頁判讀：{name}")
            res = check_menu_logic(df)
            
            if res["err"]:
                for e in res["err"]: st.error(e)
            else:
                st.success(f"🎉 分頁 【{name}】 審核通過！")
            
            # 讓詳細結果永遠有東西看
            with st.expander("🔍 查看詳細日判讀明細"):
                for info in res["ok"]:
                    st.write(info)
            st.divider()
    except Exception as e:
        st.error(f"讀取失敗：{e}")
