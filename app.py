import streamlit as st
import re

# 系統標題
st.set_page_config(page_title="康橋校內菜單審核系統", layout="wide")
st.title("🍱 康橋校內菜單自動審核系統")
st.caption("版本：2026 最終合約整合版 (含新北食品、暖禾輕食)")

# 側邊欄設定
with st.sidebar:
    st.header("⚙️ 審核設定")
    school_level = st.selectbox("學部選擇", ["小學部", "中學部"])
    target_date = st.date_input("菜單週別起始日")

# 核心邏輯區：根據關鍵字切換合約模式
def audit_logic(text):
    results = {"mode": "通用", "errors": [], "warnings": [], "success": []}
    
    # 偵測模式
    if "小學菜單" in text or "幼兒餐" in text:
        results["mode"] = "新北食品-小學部"
    elif "美食街" in text:
        results["mode"] = "新北食品-美食街"
    elif "輕食菜單" in text:
        results["mode"] = "暖禾輕食"

    # --- 通用原則 (△ 與 ◎ 限制) ---
    proc_count = text.count("△")
    fried_count = text.count("◎")
    if proc_count > 1: results["errors"].append(f"❌ 違規：加工品(△)本週 {proc_count} 次 (限1次)")
    if fried_count > 1: results["errors"].append(f"❌ 違規：油炸(◎)本週 {fried_count} 次 (限1次)")

    # --- 新北食品：美食街增補協議邏輯 ---
    if results["mode"] == "新北食品-美食街":
        if "100g" not in text and "生重" not in text:
            results["warnings"].append("⚠️ 提醒：美食街主菜生重需達 100g-150g，請確認標註。")
        if text.count("全肉") < 3:
            results["warnings"].append("⚠️ 提醒：根據協議，每週應有至少 3 天全肉主菜(肉含量95%)。")
    
    # --- 高級魚類檢查 ---
    high_fish_jr = ["鯛魚", "鮪魚", "鬼頭刀", "鮭魚", "扁鱈", "海鸚哥魚"]
    high_fish_elem = ["鮪魚", "鬼頭刀", "旗魚"]
    check_list = high_fish_jr if school_level == "中學部" else high_fish_elem
    
    if not any(f in text for f in check_list):
        results["errors"].append(f"❌ 缺項：本週未偵測到{school_level}定義之高級魚類。")
    else:
        results["success"].append("✅ 已配置高級魚類。")

    # --- 禁忌檢查 ---
    if any(d in text for d in ["週一", "週二", "週四"]) and "辣" in text:
        results["errors"].append("❌ 禁忌：週一、二、四晚餐禁止供應辛辣菜餚。")

    return results

# 網頁輸入介面
st.info("請貼上菜單內容（需包含關鍵字如：小學菜單、美食街、輕食菜單）")
menu_input = st.text_area("在此輸入菜單文字...", height=300, placeholder="例如：\\n美食街菜單\\n週一：◎炸雞腿(100g)...")

if st.button("🚀 開始自動審核"):
    if menu_input:
        mode, res = audit_logic(menu_input)["mode"], audit_logic(menu_input)
        st.subheader(f"🔍 偵測模式：{mode}")
        
        col1, col2 = st.columns(2)
        with col1:
            if res["errors"]:
                for e in res["errors"]: st.error(e)
            else:
                st.success("✅ 結構與頻次檢查通過！")
        
        with col2:
            for w in res["warnings"]: st.warning(w)
            for s in res["success"]: st.write(s)
    else:
        st.warning("請先貼上內容再執行。")
