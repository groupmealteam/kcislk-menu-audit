import streamlit as st
import pandas as pd

# 網頁基本設定
st.set_page_config(page_title="康橋菜單審核-Excel專用版", layout="wide")
st.title("🍱 康橋校內菜單自動審核系統")
st.markdown("### 支援：新北食品 (團膳/美食街) & 暖禾餐飲 (輕食)")

# --- 核心邏輯函數 ---
def run_audit(full_text):
    report = {"errors": [], "warnings": [], "success": []}
    
    # 模式自動判定
    mode = "通用模式"
    if "小學菜單" in full_text or "幼兒餐" in full_text: mode = "新北食品-小學部"
    elif "美食街" in full_text: mode = "新北食品-美食街"
    elif "輕食菜單" in full_text: mode = "暖禾輕食"

    # 1. 頻次檢核 (原則五、七)
    proc_count = full_text.count("△")
    fried_count = full_text.count("◎")
    if proc_count > 1: report["errors"].append(f"❌ 違規：加工品(△)本週出現 {proc_count} 次 (合約限1次)")
    if fried_count > 1: report["errors"].append(f"❌ 違規：油炸類(◎)本週出現 {fried_count} 次 (合約限1次)")

    # 2. 禁忌日期檢核 (週一二四晚不辣)
    for day in ["週一", "週二", "週四"]:
        if day in full_text and "辣" in full_text:
            report["errors"].append(f"❌ 禁忌：{day} 偵測到「辣」味菜餚 (依合約晚餐禁止)")

    # 3. 高級魚類檢核 (原則二、三)
    fish_list = ["鮪魚", "鬼頭刀", "旗魚", "鮭魚", "扁鱈", "海鸚哥魚", "鯛魚"]
    found_fish = [f for f in fish_list if f in full_text]
    if not found_fish:
        report["errors"].append("❌ 缺項：本週未偵測到合約定義之「高級魚類」")
    else:
        report["success"].append(f"✅ 已配置高級魚類：{', '.join(found_fish)}")

    # 4. 美食街專項 (增補協議)
    if mode == "新北食品-美食街":
        if "100g" not in full_text and "150g" not in full_text:
            report["warnings"].append("⚠️ 提醒：美食街主菜生重需符合 100g-150g 規範，請確認 Excel 標註。")

    return mode, report

# --- 網頁上傳介面 ---
st.info("請將您的菜單 Excel 檔案 (xlsx) 拖曳到下方方框內。")
file = st.file_uploader("上傳菜單檔案", type=["xlsx", "xls"])

if file:
    try:
        # 強大讀取模式：讀取所有分頁
        all_content = []
        excel_data = pd.read_excel(file, sheet_name=None)
        
        for sheet, df in excel_data.items():
            # 將每一頁轉成純文字並合併
            all_content.append(df.to_string())
        
        final_text = "\n".join(all_content)
        
        st.success(f"✅ 成功讀取檔案！共偵測到 {len(excel_data)} 個分頁。")
        
        if st.button("🚀 執行合約自動審核"):
            current_mode, res = run_audit(final_text)
            
            st.divider()
            st.header(f"🔍 診斷模式：{current_mode}")
            
            if res["errors"]:
                for e in res["errors"]: st.error(e)
            else:
                st.balloons()
                st.success("🎉 恭喜！本週菜單基礎規範審核通過。")
            
            if res["warnings"]:
                with st.expander("💡 改善建議 (點擊展開)"):
                    for w in res["warnings"]: st.warning(w)
            
            with st.expander("✨ 通過項目"):
                for s in res["success"]: st.write(s)
                
    except Exception as err:
        st.error(f"❌ 讀取失敗。原因：{err}")
        st.write("請確認您的 Excel 檔案是否被加密，或嘗試另存新檔後再上傳。")

st.divider()
st.caption("備註：本系統會搜尋 Excel 內的所有文字內容。若菜單為圖片格式，系統將無法辨識。")
