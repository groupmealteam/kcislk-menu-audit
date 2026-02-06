import streamlit as st
import pandas as pd

st.set_page_config(page_title="康橋菜單判讀系統", layout="wide")

# --- 側邊欄設定 ---
with st.sidebar:
    st.header("⚙️ 審核條件設定")
    target_spicy_days = st.multiselect("禁辣日期", ["週一", "週二", "週三", "週四", "週五"], default=["週一", "週二", "週四"])
    fish_list = st.text_input("魚類關鍵字", "鬼頭刀,白帶魚,小卷,鮭魚,扁鱈,鮪魚").split(",")
    fried_limit = st.number_input("油炸上限", value=1)

st.title("🍱 康橋校內菜單自動審核系統")

def audit_logic(df):
    # 核心修正：強制把整張表變文字，防止 float 報錯
    df = df.fillna("").astype(str)
    
    report = {"err": [], "ok": []}
    
    # 找「週」字所在的列
    day_row = None
    for idx, row in df.iterrows():
        if any("週" in cell for cell in row):
            day_row = idx
            break
            
    if day_row is None:
        return {"err": ["❌ 找不到日期列，請檢查格式"], "ok": []}

    # 按欄位掃描
    for col_idx in range(len(df.columns)):
        day_name = df.iloc[day_row, col_idx].strip()
        if any(d in day_name for d in ["週一", "週二", "週三", "週四", "週五"]):
            col_content = "".join(df.iloc[:, col_idx])
            
            # 辣味檢查
            if any(d in day_name for d in target_spicy_days):
                if "🌶️" in col_content or "●" in col_content:
                    report["err"].append(f"❌ {day_name} 偵測到辣椒標示")
            
            # 魚類檢查
            found = [f for f in fish_list if f.strip() in col_content and f.strip() != ""]
            if found:
                report["ok"].append(f"✅ {day_name} 魚類：{', '.join(found)}")

    # 油炸檢查
    f_count = "".join(df.values.flatten()).count("◎")
    if f_count > fried_limit:
        report["err"].append(f"❌ 油炸次數 ({f_count}) 超標")
        
    return report

# --- 上傳區 ---
up = st.file_uploader("請上傳 Excel 菜單", type=["xlsx"])

if up:
    try:
        sheets = pd.read_excel(up, sheet_name=None, header=None)
        for name, df in sheets.items():
            st.subheader(f"📊 分頁：{name}")
            res = audit_logic(df)
            if res["err"]:
                for e in res["err"]: st.error(e)
            else:
                st.success(f"🎉 審核通過！")
            with st.expander("詳細明細"):
                for o in res["ok"]: st.info(o)
    except Exception as e:
        st.error(f"錯誤：{e}")
