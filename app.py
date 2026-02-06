import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="林口康橋國際學校菜單審核", layout="wide")

# --- 合約規範設定 ---
CONTRACT_RULES = {
    "spicy_days": ["週一", "週二", "週四"],
    "specs": {"現撈小卷": "80|100", "無刺白帶魚": "120|150", "手作獅子頭": "60", "手作漢堡排": "150", "手作烤肉串": "80"}
}

# 💡 排除字眼 (絕對不計入重複)
EXEMPT = ["季節水果", "時令蔬菜", "履歷蔬菜", "有機蔬菜", "Fruit", "Vegetable"]

def clean_chinese(text):
    """只保留中文，徹底排除英文、數字與符號干擾判讀"""
    if pd.isna(text): return ""
    return "".join(re.findall(r'[\u4e00-\u9fa5]+', str(text)))

def run_audit(df, vendor_type):
    df = df.fillna("")
    results = []
    
    # 1. 尋找「日期」與「星期」的列索引
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
            
            # 💡 關鍵：只抓取該欄中長度大於 2 的中文字串 (確保是菜名而非雜訊)
            daily_dishes = []
            for val in df.iloc[:, col]:
                s = str(val).strip()
                if len(s) > 2 and not any(ex in s for ex in ["套餐", "熱量", "份量", "份", "雜糧", "油脂"]):
                    daily_dishes.append(s)

            # --- 判讀 A: 湯品比對 ---
            soups = list(set([d for d in daily_dishes if "湯" in d or "羹" in d]))
            if len(soups) > 1:
                results.append({"日期": this_date, "週幾": this_day, "項目": "湯品一致性", "判讀結果": f"❌ 湯品不同：出現 {soups}"})

            # --- 判讀 B: 食材重複 (精準中文比對) ---
            seen = {}
            for dish in daily_dishes:
                if any(ex in dish for ex in EXEMPT) or "湯" in dish or "羹" in dish:
                    continue
                
                # 提取核心中文 (例如: 「牛肉咖哩」->「牛肉」)
                core = clean_chinese(dish)[:2] 
                if len(core) >= 2:
                    if core in seen:
                        results.append({"日期": this_date, "週幾": this_day, "項目": "食材重複", "判讀結果": f"❌ 「{dish}」與「{seen[core]}」主料重複"})
                    seen[core] = dish

                # --- 判讀 C: 禁辣 (週一二四) ---
                if this_day in CONTRACT_RULES["spicy_days"] and ("🌶️" in dish or "●" in dish):
                    results.append({"日期": this_date, "週幾": this_day, "項目": dish, "判讀結果": "🚫 禁辣日違規 (週一二四禁辣)"})

    return results

# --- UI 介面 ---
st.title("🛡️ 林口康橋國際學校菜單審核")
st.info("系統已校準：僅針對當日垂直欄位進行「中文主料」比對，排除英文與營養標示干擾。")

up = st.file_uploader("👉 請上傳 2.3月試營運菜單 (xlsx)", type=["xlsx"])

if up:
    is_light = "輕食" in up.name
    excel = pd.read_excel(up, sheet_name=None, header=None)
    for sheet, df in excel.items():
        st.subheader(f"📊 審核分頁：{sheet}")
        res = run_audit(df, "輕食" if is_light else "團膳")
        if res:
            st.error("🚩 發現違規項目：")
            st.table(pd.DataFrame(res))
        else:
            st.success("🎉 本頁審核通過，無食材重複或違規。")
        st.divider()
