import streamlit as st
import pandas as pd

st.set_page_config(page_title="康橋菜單判讀專家", layout="wide")

# --- 側邊欄：條件修改區 ---
with st.sidebar:
    st.header("⚙️ 審核條件自定義")
    target_spicy_days = st.multiselect("哪些日子要『禁辣』？", 
                                       ["週一", "週二", "週三", "週四", "週五"], 
                                       default=["週一", "週二", "週四"])
    
    fish_input = st.text_input("高級魚類關鍵字 (用逗號隔開)", "鬼頭刀,白帶魚,小卷,鮭魚,扁鱈,鮪魚")
    fish_list = [f.strip() for f in fish_input.split(",")]
    
    fried_limit = st.number_input("每週油炸(◎)上限次數", value=1)

st.title("🍱 康橋校內菜單自動審核系統")

def check_menu_logic(df):
    report = {"err": [], "ok": []}
    
    # 修正錯誤：先將整張表強制轉換成字串 (String)，避免 float 報錯
    df = df.astype(str).replace("nan", "")
    
    # 1. 判讀「星期」在哪一列
    day_row_index = None
    for idx, row in df.iterrows():
        if any("週" in str(cell) for cell in row):
            day_row_index = idx
            break
            
    if day_row_index is None:
        return {"err": ["❌ 判讀失敗：找不到『星期』標記列，請確認 Excel 格式。"], "ok": []}

    # 2. 開始按「欄 (Column)」判讀
    days_in_menu = df.iloc[day_row_index]
    
    for col_idx, day_name in enumerate(days_in_menu):
        day_str = str(day_name).strip()
        
        if any(d in day_str for d in ["週一", "週二", "週三", "週四", "週五"]):
            # 抓取這一欄底下的所有內容並結合成一個大字串
            column_content = "".join(df.iloc[:, col_idx])
            
            # 判讀辣味
            if day_str in target_spicy_days:
                if "🌶️" in column_content or "●" in column_content:
                    report["err"].append(f"❌ 違規：{day_str} 偵測到辣味標示 (●/🌶️)。")
            
            # 判讀魚類
            found_fish = [f for f in fish_list if f in column_content]
            for fish in found_fish:
                report["ok"].append(f"✅ {day_str} 已配置魚類：{fish}")

    # 3. 全局判讀油炸次數
    all_text = "".join(df.values.flatten())
    f_count = all_text.count("◎")
    if f_count > fried_limit:
        report["err"].append(f"❌ 違規：本週油炸(◎)共 {f_count} 次，超過上限 {fried_limit} 次。")

    return report

# --- 檔案上傳 ---
up = st.file_uploader("👉 請上傳您的 Excel 菜單", type=["xlsx"])

if up:
    try:
        # 讀取 Excel 所有的分頁
        excel_data = pd.read_excel(up, sheet_name=None, header=None)
        for name, df in excel_data.items():
            st.subheader(f"📊 分頁判讀：{name}")
            res = check_menu_logic(df)
            
            if res["err"]:
                for e in res["err"]: st.error(e)
            else:
                st.success(f"🎉 分頁 【{name}】 審核通過！")
            
            with st.expander("查看詳細結果"):
                for o in res["ok"]: st.info(o)
            st.divider()
    except Exception as e:
        st.error(f"檔案讀取失敗，錯誤原因：{e}")
