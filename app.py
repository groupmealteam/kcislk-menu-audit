import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="康橋菜單審核-115專用版", layout="wide")
st.title("🍱 康橋校內菜單自動審核系統")
st.caption("針對 115 學年美食街與輕食菜單格式優化")

def start_audit(df):
    # 1. 數據清洗：將所有儲存格轉為字串並去除多餘空格
    df_clean = df.fillna("").astype(str)
    # 將整張表打平，過濾掉空的儲存格
    all_data = df_clean.values.flatten()
    combined_text = "".join(all_data).replace(" ", "").replace("\n", "")
    
    report = {"err": [], "warn": [], "ok": []}

    # --- 規範一：符號頻次 (△, ◎) ---
    p_count = combined_text.count("△")
    f_count = combined_text.count("◎")
    if p_count > 1: report["err"].append(f"❌ 違規：加工品(△)本週共 {p_count} 次 (合約限1次)")
    if f_count > 1: report["err"].append(f"❌ 違規：油炸類(◎)本週共 {f_count} 次 (合約限1次)")

    # --- 規範二：辣味標示 (●, 🌶️) ---
    # 掃描特定的日期欄位與辣味符號的關聯
    if "●" in combined_text or "🌶️" in combined_text:
        # 簡單判定：只要該表有辣，且包含週一、二、四
        for day in ["週一", "週二", "週四"]:
            if day in combined_text:
                report["err"].append(f"❌ 禁忌：{day} 偵測到辣味標示(●/🌶️)，合約規範晚餐禁止。")

    # --- 規範三：高級魚類 (依合約清單) ---
    fish_list = ["鮪魚", "鬼頭刀", "旗魚", "鮭魚", "扁鱈", "海鸚哥魚", "鯛魚", "白帶魚", "小卷"]
    found_fishes = [f for f in fish_list if f in combined_text]
    if not found_fishes:
        report["err"].append("❌ 缺項：本週未偵測到合約定義之「高級魚類」。")
    else:
        report["ok"].append(f"✅ 已配置高級魚/海鮮：{', '.join(found_fishes)}")

    return report

# --- 介面設計 ---
up = st.file_uploader("請上傳您的 Excel 菜單 (115學年格式)", type=["xlsx"])

if up:
    try:
        # 讀取 Excel 的所有分頁
        all_sheets = pd.read_excel(up, sheet_name=None)
        
        for name, df in all_sheets.items():
            st.markdown(f"### 📋 分頁審核：{name}")
            # 顯示預覽，讓使用者知道系統讀到了什麼
            with st.expander(f"查看 {name} 資料預覽"):
                st.dataframe(df.head(10))
            
            res = start_audit(df)
            
            # 呈現審核結果
            if res["err"]:
                for e in res["err"]: st.error(e)
            else:
                st.success(f"🎉 分頁 【{name}】 基礎規範檢查通過！")
                st.balloons()
            
            for o in res["ok"]: st.info(o)
            st.divider()
            
    except Exception as e:
        st.error(f"檔案讀取失敗。原因：{e}")

st.info("💡 提示：若 Excel 內有圖片或複雜公式可能影響速度，建議將菜單區域另存為純文字 Excel。")
