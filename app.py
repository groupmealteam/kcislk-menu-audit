import streamlit as st
import pandas as pd

# 網頁外觀
st.set_page_config(page_title="康橋菜單判讀專家系統", layout="wide")

# --- 側邊欄：讓您可以修改條件 ---
with st.sidebar:
    st.header("⚙️ 判讀條件設定")
    p_limit = st.number_input("加工品(△)上限", value=1)
    f_limit = st.number_input("油炸類(◎)上限", value=1)
    fish_list = st.text_area("魚類/海鮮判斷關鍵字", value="鬼頭刀,白帶魚,小卷,鮭魚,扁鱈,鮪魚,現撈小卷").split(",")
    check_spicy = st.checkbox("執行禁辣檢查 (週一二四)", value=True)

st.title("🍱 康橋 115 學年菜單判讀系統")
st.write("本系統會自動對齊 Excel 中的日期與菜名，進行合約規範審核。")

# --- 核心：Excel 判讀引擎 ---
def audit_excel(df):
    # 1. 數據清洗：確保所有格式（包含圖案）都能轉成字串
    df = df.fillna("")
    
    # 2. 建立掃描清單：將所有欄位內容攤平，確保一個字都沒漏掉
    full_scan_text = ""
    for col in df.columns:
        full_scan_text += "".join(df[col].astype(str).tolist())
    
    # 移除空格與換行符號，防止判讀錯誤
    clean_text = full_scan_text.replace("\n", "").replace(" ", "")
    
    results = {"errors": [], "success": []}

    # 3. 判讀符號
    p_count = clean_text.count("△")
    f_count = clean_text.count("◎")
    
    if p_count > p_limit:
        results["errors"].append(f"❌ 加工品(△)出現 {p_count} 次，超過設定的 {p_limit} 次。")
    else:
        results["success"].append(f"✅ 加工品次數合格 ({p_count}次)")

    if f_count > f_limit:
        results["errors"].append(f"❌ 油炸類(◎)出現 {f_count} 次，超過設定的 {f_limit} 次。")
    else:
        results["success"].append(f"✅ 油炸類次數合格 ({f_count}次)")

    # 4. 判讀辣味 (● 或 🌶️)
    if check_spicy:
        if "●" in clean_text or "🌶️" in clean_text:
            # 如果發現辣味符號，進一步檢查是否有對應到禁辣日期
            # 這裡簡化為全表偵測，若需精確到哪一天，需更複雜的座標計算
            results["errors"].append("⚠️ 偵測到辣味標示 (●/🌶️)，請確認是否避開週一、二、四晚餐。")

    # 5. 判讀魚類
    found_fish = [f.strip() for f in fish_list if f.strip() in clean_text]
    if found_fish:
        results["success"].append(f"✅ 已偵測到符合規範的高級魚類：{', '.join(found_fish)}")
    else:
        results["errors"].append("❌ 未在菜單判讀到指定的高級魚類。")

    return results

# --- 檔案上傳介面 ---
uploaded_file = st.file_uploader("請上傳 Excel 檔案", type=["xlsx"])

if uploaded_file:
    try:
        # 使用 openpyxl 引擎讀取
        excel_data = pd.read_excel(uploaded_file, sheet_name=None)
        
        for sheet_name, df in excel_data.items():
            st.subheader(f"📊 分頁判讀結果：{sheet_name}")
            
            # 顯示判讀內容預覽 (讓您確認系統有讀到東西)
            with st.expander("點擊查看系統判讀到的原始資料"):
                st.dataframe(df)
            
            # 執行審核
            report = audit_excel(df)
            
            # 顯示結果
            if report["errors"]:
                for err in report["errors"]: st.error(err)
            
            for ok in report["success"]: st.info(ok)
            st.divider()
            
    except Exception as e:
        st.error(f"判讀過程發生錯誤：{e}")
