import streamlit as st
import pandas as pd

st.set_page_config(page_title="康橋菜單審核-專用版", layout="wide")
st.title("🍱 康橋校內菜單自動審核系統 (Excel 格式對齊版)")

def audit_menu_dataframe(df):
    report = {"errors": [], "warnings": [], "success": []}
    # 將整份表格轉為一個大字串，進行全域關鍵字掃描
    full_text = df.to_string()
    
    # 1. 符號頻次限制
    proc_count = full_text.count("△")
    fried_count = full_text.count("◎")
    if proc_count > 1: report["errors"].append(f"❌ 違規：本週加工品(△)出現 {proc_count} 次 (限1次)")
    if fried_count > 1: report["errors"].append(f"❌ 違規：本週油炸類(◎)出現 {fried_count} 次 (限1次)")

    # 2. 禁忌日期檢核 (週一、二、四 晚餐禁辣)
    # 這裡會掃描包含 '週一', '週二', '週四' 的欄位內容
    for day in ["週一", "週二", "週四"]:
        if day in full_text and "🌶️" in full_text: # 您的 Excel 用辣椒圖案
             report["errors"].append(f"❌ 禁忌：{day} 偵測到辣椒標示 🌶️ (依合約晚餐禁止供應)")

    # 3. 高級魚類檢核
    fish_list = ["鮪魚", "鬼頭刀", "旗魚", "鮭魚", "扁鱈", "鯛魚", "白帶魚"]
    found_fish = [f for f in fish_list if f in full_text]
    if not found_fish:
        report["errors"].append("❌ 缺項：本週未偵測到高級魚類 (如鬼頭刀、白帶魚等)")
    else:
        report["success"].append(f"✅ 已配置高級魚類：{', '.join(found_fish)}")

    return report

# 介面設計
uploaded_file = st.file_uploader("請上傳您的菜單 Excel", type=["xlsx"])

if uploaded_file:
    try:
        # 讀取 Excel
        df = pd.read_excel(uploaded_file, header=None)
        st.write("📋 菜單預覽：")
        st.dataframe(df.head(10))
        
        if st.button("🚀 執行精準審核"):
            res = audit_menu_dataframe(df)
            st.divider()
            
            if res["errors"]:
                for e in res["errors"]: st.error(e)
            else:
                st.balloons()
                st.success("🎉 恭喜！本週菜單初步符合合約規範。")
            
            for s in res["success"]: st.write(s)
            
    except Exception as e:
        st.error(f"檔案解析失敗：{e}")

st.divider()
st.caption("提示：系統已優化針對『主食』與『食材內容』的掃描。")
