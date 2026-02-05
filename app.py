import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="康橋菜單審核系統-Excel版", layout="wide")
st.title("🍱 康橋校內菜單自動審核系統 (Excel 支援)")

# --- 核心審核邏輯 ---
def audit_logic(df_text, school_level):
    text = str(df_text) # 將表格內容轉為文字進行關鍵字掃描
    results = {"mode": "通用", "errors": [], "warnings": [], "success": []}
    
    # 模式偵測
    if "小學菜單" in text or "幼兒餐" in text: results["mode"] = "新北食品-小學部"
    elif "美食街" in text: results["mode"] = "新北食品-美食街"
    elif "輕食菜單" in text: results["mode"] = "暖禾輕食"

    # 1. 頻次檢查 (△ 與 ◎)
    proc_count = text.count("△")
    fried_count = text.count("◎")
    if proc_count > 1: results["errors"].append(f"❌ 違規：加工品(△)本週 {proc_count} 次 (限1次)")
    if fried_count > 1: results["errors"].append(f"❌ 違規：油炸(◎)本週 {fried_count} 次 (限1次)")

    # 2. 禁忌檢查 (週一二四晚不辣)
    if any(d in text for d in ["週一", "週二", "週四"]) and "辣" in text:
        results["errors"].append("❌ 禁忌：週一、二、四晚餐禁止供應辛辣菜餚。")

    # 3. 高級魚類檢查
    fish_list = ["鮪魚", "鬼頭刀", "旗魚", "鮭魚", "扁鱈"] # 綜合清單
    if not any(f in text for f in fish_list):
        results["errors"].append(f"❌ 缺項：本週未偵測到高級魚類。")
    
    return results

# --- 網頁介面 ---
st.info("💡 您現在可以直接上傳 Excel 檔案，或是在下方貼上文字。")

# 檔案上傳器
uploaded_file = st.file_uploader("選擇您的菜單 Excel 檔案", type=["xlsx", "xls"])

if uploaded_file:
    try:
        # 讀取 Excel
        df = pd.read_excel(uploaded_file)
        st.write("📂 檔案預覽：")
        st.dataframe(df.head(10)) # 顯示前10列參考
        
        # 將整份表格轉成文字來審核
        all_text = df.to_string()
        
        if st.button("🚀 執行 Excel 自動審核"):
            res = audit_logic(all_text, "中學部")
            st.divider()
            st.subheader(f"🔍 偵測模式：{res['mode']}")
            for e in res["errors"]: st.error(e)
            for w in res["warnings"]: st.warning(w)
            if not res["errors"]: st.success("✅ 合約基本規範檢查通過！")
    except Exception as e:
        st.error(f"檔案讀取失敗，請確認格式。錯誤訊息: {e}")

st.divider()
st.caption("備註：系統會掃描 Excel 內所有文字。請確保「△」、「◎」等符號有正確標註在格子裡。")
