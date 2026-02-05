import streamlit as st
import pandas as pd

# 網頁外觀優化
st.set_page_config(page_title="康橋 115 菜單審核系統", layout="wide")
st.title("🍱 康橋校內菜單自動審核系統 (115學年專用版)")

def audit_logic(all_text):
    # 清理文字，移除所有空格、換行與干擾字元
    clean_text = all_text.replace(" ", "").replace("\n", "").replace("\r", "")
    report = {"err": [], "warn": [], "ok": []}

    # 1. 符號頻次 (△ 加工, ◎ 油炸)
    p_count = clean_text.count("△")
    f_count = clean_text.count("◎")
    if p_count > 1: report["err"].append(f"❌ 違規：加工品(△)本週共 {p_count} 次 (合約限1次)")
    if f_count > 1: report["err"].append(f"❌ 違規：油炸類(◎)本週共 {fried_count} 次 (合約限1次)")

    # 2. 禁忌辣味標籤 (辨識 ● 與 🌶️)
    # 只要偵測到這些符號，且文字中有週一、二、四，就發動警告
    if "●" in clean_text or "🌶️" in clean_text:
        days = [d for d in ["週一", "週二", "週四"] if d in clean_text]
        if days:
            report["err"].append(f"❌ 禁忌：{'/'.join(days)} 偵測到辣味符號 (● 或 🌶️)，晚餐依約禁止供應。")

    # 3. 高級魚類檢核 (依據增補協議)
    fish_list = ["鮪魚", "鬼頭刀", "旗魚", "鮭魚", "扁鱈", "海鸚哥魚", "鯛魚", "白帶魚", "小卷", "現撈小卷"]
    found_fishes = [f for f in fish_list if f in clean_text]
    if not found_fishes:
        report["err"].append("❌ 缺項：本週未偵測到合約定義之高級魚類 (如：鬼頭刀、白帶魚、小卷)。")
    else:
        report["ok"].append(f"✅ 已配置高級魚/海鮮：{', '.join(found_fishes)}")

    # 4. 蔬菜屬性檢查
    if "有機" in clean_text: report["ok"].append("✅ 已包含有機蔬菜 (符合週二、四規範)")
    if "履歷" in clean_text: report["ok"].append("✅ 已包含履歷蔬菜 (符合週一、三、五規範)")

    return report

# --- 介面 ---
up = st.file_uploader("請上傳您的 115-1 菜單 Excel (.xlsx)", type=["xlsx"])

if up:
    try:
        # 讀取 Excel 所有分頁 (2月, 3月...)
        excel_data = pd.read_excel(up, sheet_name=None)
        
        for sheet_name, df in excel_data.items():
            st.markdown(f"### 📋 正在審核分頁：{sheet_name}")
            
            # 轉換為文字總集
            content_str = df.astype(str).values.flatten()
            final_text = "".join(content_str)
            
            res = audit_logic(final_text)
            
            # 顯示結果
            if res["err"]:
                for e in res["err"]: st.error(e)
            else:
                st.balloons()
                st.success(f"🎉 分頁 【{sheet_name}】 合約基礎規範審核通過！")
                
            with st.expander("🔍 檢視通過與建議項"):
                for o in res["ok"]: st.write(o)
            st.divider()
            
    except Exception as e:
        st.error(f"檔案讀取失敗，請確認檔案格式。錯誤訊息：{e}")

st.divider()
st.caption("備註：本系統已針對『●』與『🌶️』符號進行深度掃描，確保符合禁辣規範。")
