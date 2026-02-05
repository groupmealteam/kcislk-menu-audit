import streamlit as st
import pandas as pd

# 網頁外觀設定
st.set_page_config(page_title="康橋菜單審核-115專用版", layout="wide")
st.title("🍱 康橋校內菜單自動審核系統")
st.markdown("#### 適用範圍：新北食品 (美食街) / 暖禾餐飲 (輕食)")

def start_audit(df):
    # 1. 深度清洗資料：將所有格子轉為字串，並移除換行與空格
    all_cells = df.astype(str).values.flatten()
    clean_text = "".join(all_cells).replace("\n", "").replace(" ", "")
    
    report = {"err": [], "warn": [], "ok": []}

    # --- 規範一：符號頻次 (△ 加工, ◎ 油炸) ---
    p_count = clean_text.count("△")
    f_count = clean_text.count("◎")
    if p_count > 1: 
        report["err"].append(f"❌ 違規：加工品(△)本週共 {p_count} 次 (合約限1次)")
    if f_count > 1: 
        report["err"].append(f"❌ 違規：油炸類(◎)本週共 {f_count} 次 (合約限1次)")

    # --- 規範二：辣味標示 (●, 🌶️) ---
    # 根據合約：週一、二、四晚餐禁辣 (此處為全域掃描提醒)
    if "●" in clean_text or "🌶️" in clean_text:
        days_found = [d for d in ["週一", "週二", "週四"] if d in clean_text]
        if days_found:
            report["err"].append(f"❌ 禁忌：{'/'.join(days_found)} 偵測到辣味標示(●/🌶️)，請確認晚餐是否供應。")

    # --- 規範三：高級魚類 (依合約增補協議) ---
    fish_list = ["鮪魚", "鬼頭刀", "旗魚", "鮭魚", "扁鱈", "海鸚哥魚", "鯛魚", "白帶魚", "小卷"]
    found_fishes = [f for f in fish_list if f in clean_text]
    if not found_fishes:
        report["err"].append("❌ 缺項：本週未偵測到合約定義之「高級魚類」(如：白帶魚、小卷)。")
    else:
        report["ok"].append(f"✅ 已配置高級魚/海鮮：{', '.join(found_fishes)}")

    # --- 規範四：有機/履歷蔬菜 ---
    if "有機蔬菜" in clean_text: report["ok"].append("✅ 已包含有機蔬菜 (依二、四規範)")
    if "履歷蔬菜" in clean_text: report["ok"].append("✅ 已包含履歷蔬菜 (依一、三、五規範)")

    return report

# --- 介面 ---
up = st.file_uploader("👉 請上傳 115-1 試菜 Excel 檔案", type=["xlsx"])

if up:
    try:
        # 讀取所有 Sheet (2月, 3月...)
        excel_file = pd.ExcelFile(up)
        for sheet_name in excel_file.sheet_names:
            df = excel_file.parse(sheet_name)
            st.markdown(f"### 📋 審核分頁：{sheet_name}")
            
            res = start_audit(df)
            
            if res["err"]:
                for e in res["err"]: st.error(e)
            else:
                st.balloons()
                st.success(f"🎉 分頁 【{sheet_name}】 合約基礎規範審核通過！")
            
            with st.expander("查看詳細通過項目"):
                for o in res["ok"]: st.write(o)
            st.divider()
            
    except Exception as e:
        st.error(f"讀取失敗。請確認是否為標準 Excel 檔案。錯誤訊息：{e}")

st.markdown("---")
st.caption("提示：系統會自動偵測「●」與「🌶️」符號。若符號為圖片格式則無法辨識。")
