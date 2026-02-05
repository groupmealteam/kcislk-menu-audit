import streamlit as st
import pandas as pd

st.set_page_config(page_title="康橋菜單審核-穩定版", layout="wide")
st.title("🍱 康橋菜單自動審核 (穩定版)")

# --- 核心邏輯 ---
def audit(text):
    res = {"err": [], "warn": []}
    # 1. 檢查 △ 和 ◎
    p = text.count("△")
    f = text.count("◎")
    if p > 1: res["err"].append(f"❌ 加工品(△)本週 {p} 次 (限1次)")
    if f > 1: res["err"].append(f"❌ 油炸類(◎)本週 {f} 次 (限1次)")
    
    # 2. 禁辣檢查
    for d in ["週一", "週二", "週四"]:
        if d in text and "辣" in text:
            res["err"].append(f"❌ {d} 晚餐依約禁止辛辣菜餚")
            
    # 3. 高級魚類
    fishes = ["鮪魚", "鬼頭刀", "旗魚", "鮭魚", "扁鱈", "鯛魚"]
    if not any(fish in text for fish in fishes):
        res["err"].append("❌ 缺項：未偵測到高級魚類")
    return res

# --- 介面 ---
tab1, tab2 = st.tabs(["📁 上傳 Excel", "✍️ 直接貼上文字"])

with tab1:
    up = st.file_uploader("請選擇 Excel 檔案", type=["xlsx"])
    if up:
        try:
            # 強制轉成字串讀取
            df_dict = pd.read_excel(up, sheet_name=None, dtype=str)
            all_t = ""
            for sn in df_dict:
                all_t += df_dict[sn].to_string()
            
            if st.button("執行 Excel 審核"):
                r = audit(all_t)
                if not r["err"]: st.success("✅ 合規")
                for e in r["err"]: st.error(e)
        except Exception as ex:
            st.error(f"Excel 讀取失敗，建議改用『貼上文字』功能。錯誤：{ex}")

with tab2:
    txt_input = st.text_area("請直接從 Excel 複製內容貼到這裡", height=300)
    if st.button("執行文字審核"):
        if txt_input:
            r = audit(txt_input)
            if not r["err"]: st.success("✅ 合規")
            for e in r["err"]: st.error(e)
