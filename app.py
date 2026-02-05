import streamlit as st
import pandas as pd
import io

# 網頁外觀優化
st.set_page_config(page_title="康橋菜單極速審核", page_icon="🍱", layout="centered")
st.title("🚀 康橋菜單自動審核 (極速版)")
st.markdown("---")

# 核心審核引擎
def audit_engine(content):
    res = {"err": [], "warn": [], "ok": []}
    text = str(content)
    
    # 模式辨識
    if "小學菜單" in text: mode = "新北-小學"
    elif "美食街" in text: mode = "新北-美食街"
    elif "輕食菜單" in text: mode = "暖禾-輕食"
    else: mode = "通用偵測"

    # 1. 符號頻次 (△, ◎)
    p_count = text.count("△")
    f_count = text.count("◎")
    if p_count > 1: res["err"].append(f"❌ 加工品(△)本週 {p_count} 次 (限1次)")
    if f_count > 1: res["err"].append(f"❌ 油炸類(◎)本週 {f_count} 次 (限1次)")

    # 2. 晚餐禁辣 (週一二四)
    for d in ["週一", "週二", "週四"]:
        if d in text and "辣" in text:
            res["err"].append(f"❌ {d} 晚餐禁止辛辣菜餚")

    # 3. 高級魚類
    fishes = ["鮪魚", "鬼頭刀", "旗魚", "鮭魚", "扁鱈", "鯛魚"]
    if not any(f in text for f in fishes):
        res["err"].append("❌ 未偵測到高級魚類")
    
    return mode, res

# 上傳介面
uploaded_file = st.file_uploader("請上傳 Excel 檔案", type=["xlsx"])

if uploaded_file:
    with st.spinner('系統正在極速掃描中...'):
        try:
            # 只讀取文字，不讀取樣式，速度最快
            df_list = pd.read_excel(uploaded_file, sheet_name=None, dtype=str)
            all_txt = ""
            for name, df in df_list.items():
                all_txt += df.to_string()
            
            mode, report = audit_engine(all_txt)
            
            st.success(f"✅ 掃描完成！目前模式：{mode}")
            
            # 顯示結果
            if report["err"]:
                for e in report["err"]: st.error(e)
            else:
                st.balloons()
                st.success("🎉 完美！符合合約規範。")
                
            if report["warn"]:
                for w in report["warn"]: st.warning(w)
                
        except Exception as e:
            st.error(f"讀取失敗，請確認檔案是否正確。錯誤訊息: {e}")

st.markdown("---")
st.caption("提示：若上傳後沒反應，請重新整理網頁再試一次。")
