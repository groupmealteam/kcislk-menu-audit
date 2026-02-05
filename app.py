import streamlit as st
import pandas as pd

# 設置網頁外觀
st.set_page_config(page_title="康橋菜單審核系統", layout="wide")
st.title("🍱 康橋校內菜單自動審核系統")
st.write("請直接上傳您的菜單 Excel 檔案，系統會自動掃描所有內容。")

# --- 核心審核邏輯 (根據合約與原則) ---
def 執行審核(text, school_level):
    report = {"errors": [], "warnings": [], "success": []}
    
    # 模式判斷
    mode = "通用模式"
    if "小學菜單" in text or "幼兒餐" in text: mode = "新北食品-小學部"
    elif "美食街" in text: mode = "新北食品-美食街"
    elif "輕食菜單" in text: mode = "暖禾輕食"

    # 1. 加工與油炸次數 (△, ◎)
    proc_count = text.count("△")
    fried_count = text.count("◎")
    if proc_count > 1: report["errors"].append(f"❌ 違規：加工品(△)本週共 {proc_count} 次 (限1次)")
    if fried_count > 1: report["errors"].append(f"❌ 違規：油炸(◎)本週共 {fried_count} 次 (限1次)")

    # 2. 禁忌日期 (週一二四晚不辣)
    for day in ["週一", "週二", "週四"]:
        if day in text and "辣" in text:
            report["errors"].append(f"❌ 禁忌：偵測到 {day} 出現「辣」味菜餚 (依合約禁止)")

    # 3. 高級魚類檢查
    fish_list = ["鮪魚", "鬼頭刀", "旗魚", "鮭魚", "扁鱈", "海鸚哥魚"]
    found_fish = [f for f in fish_list if f in text]
    if not found_fish:
        report["errors"].append("❌ 缺項：本週菜單未偵測到合約定義之高級魚類")
    else:
        report["success"].append(f"✅ 已配置高級魚類：{', '.join(found_fish)}")

    # 4. 沙茶與過敏原
    if "沙茶" in text and "★" not in text:
        report["warnings"].append("⚠️ 提醒：有「沙茶」料理但未標註「★」，請確認。")

    return mode, report

# --- 網頁介面區 ---
uploaded_file = st.file_uploader("👉 請將 Excel 檔案拖曳至此", type=["xlsx", "xls"])

if uploaded_file:
    try:
        # 讀取 Excel 的所有工作表
        all_sheets = pd.read_excel(uploaded_file, sheet_name=None)
        combined_text = ""
        
        for sheet_name, df in all_sheets.items():
            # 將表格轉成文字，並忽略掉空白格
            combined_text += df.to_string()
            
        st.success("✅ 檔案讀取成功！")
        
        if st.button("🚀 開始自動審核檔案"):
            mode, res = 執行審核(combined_text, "中學部")
            
            st.divider()
            st.header(f"🔍 診斷模式：{mode}")
            
            # 顯示報告
            if res["errors"]:
                for e in res["errors"]: st.error(e)
            else:
                st.balloons()
                st.success("🎉 合約基礎規範初步檢查通過！")
                
            with st.expander("查看詳細提醒與通過項"):
                for w in res["warnings"]: st.warning(w)
                for s in res["success"]: st.write(s)
                
    except Exception as e:
        st.error(f"檔案讀取失敗，可能是格式不相符。錯誤代碼: {e}")

st.write("---")
st.caption("備註：若 Excel 內有圖片或手寫文字，系統無法辨識。請確保菜名、△、◎ 等資訊為儲存格文字。")
