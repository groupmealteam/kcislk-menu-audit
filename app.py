import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="林口康橋國際學校菜單審核", layout="wide")

# --- 核心規範設定 ---
CONTRACT_RULES = {
    "spicy_days": ["週一", "週二", "週四"],
    "exempt_keywords": ["季節水果", "時令蔬菜", "履歷蔬菜", "有機蔬菜", "Fruit", "Vegetable"]
}

def clean_chinese(text):
    """只抓中文，排除英文與符號干擾"""
    if pd.isna(text): return ""
    return "".join(re.findall(r'[\u4e00-\u9fa5]+', str(text)))

def run_audit(df):
    df = df.fillna("")
    audit_results = []
    
    # 1. 定位日期與星期列
    date_row = next((i for i, r in df.iterrows() if any(re.search(r"\d{1,2}/\d{1,2}|\d{4}-\d{2}", str(c)) for c in r)), None)
    day_row = next((i for i, r in df.iterrows() if any("週" in str(c) for c in r)), None)
    
    if date_row is None or day_row is None: return None

    # 2. 逐天(逐欄)審核
    for col in range(len(df.columns)):
        date_val = str(df.iloc[date_row, col])
        day_val = str(df.iloc[day_row, col])
        
        date_m = re.search(r"(\d{1,2}/\d{1,2})|(\d{4}-\d{2}-\d{2})", date_val)
        day_m = re.search(r"週[一二三四五]", day_val)
        
        if date_m and day_m:
            this_date = date_m.group()
            this_day = day_m.group()
            
            # --- 分組抓取餐點內容，避免「主食」與「食材內容」自我重複 ---
            # 抓取輕食 A 餐範圍 (假設 A 餐在上方，B 餐在下方)
            # 這裡改為：抓取該欄所有內容，但將「成對」的資訊合併處理
            
            all_text_in_col = []
            soups = []
            
            # 遍歷該欄每一格
            for i, val in enumerate(df.iloc[:, col]):
                if i in [date_row, day_row]: continue
                cell = str(val).strip()
                if not cell or any(k in cell for k in ["熱量", "份量", "份", "雜糧", "油脂", "奶類"]): continue
                
                # 區分湯品
                if "湯" in cell or "羹" in cell:
                    soups.append(cell)
                else:
                    all_text_in_col.append(cell)

            # --- A. 湯品檢查 (不同才報) ---
            unique_soups = list(set(soups))
            if len(unique_soups) > 1:
                audit_results.append({
                    "日期": this_date, "週幾": this_day, "項目": "湯品一致性", 
                    "判讀結果": f"❌ 湯品不同：出現 {unique_soups}"
                })

            # --- B. 食材重複 (精準比對) ---
            # 我們不再對每一格報錯，而是對「整天」的食材清單進行掃描
            seen_cores = {}
            for dish in all_text_in_col:
                # 排除水果蔬菜
                if any(ex in dish for ex in CONTRACT_RULES["exempt_keywords"]): continue
                
                # 提取核心字 (如：雞丁、牛肉)
                core = clean_chinese(dish)[:2]
                if len(core) >= 2:
                    # 如果這個核心字已經出現過，且「不是來自同一道菜的描述」
                    if core in seen_cores:
                        # 檢查：如果兩個字串長度落差很大，通常是「主食」與「食材內容」的關係，跳過不報
                        if dish not in seen_cores[core] and seen_cores[core] not in dish:
                            audit_results.append({
                                "日期": this_date, "週幾": this_day, "項目": "食材重複", 
                                "判讀結果": f"❌ 「{dish}」與「{seen_cores[core]}」主料重複使用"
                            })
                    seen_cores[core] = dish

            # --- C. 禁辣檢查 ---
            for dish in all_text_in_col:
                if this_day in CONTRACT_RULES["spicy_days"] and ("🌶️" in dish or "●" in dish):
                    audit_results.append({
                        "日期": this_date, "週幾": this_day, "項目": dish, "判讀結果": "🚫 禁辣日違規"
                    })
                    break # 同一天同個菜報一次就好

    return audit_results

# ---介面---
st.title("🛡️ 林口康橋國際學校菜單審核")
up = st.file_uploader("👉 請上傳 Excel 檔案", type=["xlsx"])

if up:
    excel = pd.read_excel(up, sheet_name=None, header=None)
    for sheet, df in excel.items():
        st.subheader(f"📊 審核分頁：{sheet}")
        res = run_audit(df)
        if res:
            st.error(f"🚩 偵測到 {len(res)} 項違規：")
            st.table(pd.DataFrame(res))
        else:
            st.success("🎉 完美！本頁無任何違規。")
