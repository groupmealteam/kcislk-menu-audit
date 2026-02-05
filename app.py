import streamlit as st
import pandas as pd

st.set_page_config(page_title="康橋菜單審核-115學年專用版", layout="wide")
st.title("🍱 康橋校內菜單自動審核系統")
st.subheader("適用：新北食品美食街 / 暖禾輕食")

def start_audit(df):
    # 將整個表格內容合併，並移除掉所有空格與斷行，確保搜尋準確
    full_content = df.astype(str).values.flatten()
    combined_text = "".join(full_content).replace("\n", "").replace(" ", "")
    
    report = {"err": [], "warn": [], "ok": []}

    # 1. 加工與油炸 (原則五、七)
    p_count = combined_text.count("△")
    f_count = combined_text.count("◎")
    if p_count > 1: report["err"].append(f"❌ 違規：加工品(△)本週共 {p_count} 次 (限1次)")
    if f_count > 1: report["err"].append(f"❌ 違規：油炸類(◎)本週共 {f_count} 次 (限1次)")

    # 2. 辣椒標示與禁辣日期 (週一、二、四 晚餐)
    # 這裡我們掃描是否有包含 🌶️ 或 ●
    has_spicy = "🌶️" in combined_text or "●" in combined_text
    # 簡單邏輯：如果整份表有辣，且內容包含週一/二/四
    if has_spicy:
        for day in ["週一", "週二", "週四"]:
            if day in combined_text:
                report["err"].append(f"❌ 禁忌：{day} 偵測到辣味標示(●/🌶️)，依合約晚餐禁止。")

    # 3. 高級魚類檢核 (依據美食街合約增補協議)
    fish_list = ["鮪魚", "鬼頭刀", "旗魚", "鮭魚", "扁鱈", "海鸚哥魚", "鯛魚", "白帶魚", "小卷"]
    found_fishes = [f for f in fish_list if f in combined_text]
    if not found_fishes:
        report["err"].append("❌ 缺項：本週未偵測到合約定義之高級魚類項目。")
    else:
        report["ok"].append(f"✅ 已配置高級魚/海鮮：{', '.join(found_fishes)}")

    return report

# --- 介面 ---
up = st.file_uploader("請上傳您的 115-1 菜單 Excel", type=["xlsx"])

if up:
    try:
        # 讀取所有 Sheet，因為您的檔案可能有多個月份
        all_sheets = pd.read_excel(up, sheet_name=None)
        
        for name, df in all_sheets.items():
            st.write(f"### 📋 正在審核分頁：{name}")
            res = start_audit(df)
            
            if res["err"]:
                for e in res["err"]: st.error(e)
            else:
                st.success(f"🎉 分頁【{name}】合約基礎規範檢查通過！")
            
            for o in res["ok"]: st.info(o)
            st.divider()
            
    except Exception as e:
        st.error(f"檔案讀取失敗，請確認檔案格式是否正確。錯誤原因：{e}")

st.caption("備註：本系統會自動過濾斷行符號。請確保符號標註於儲存格文字中。")
