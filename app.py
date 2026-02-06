import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="林口康橋國際學校菜單審核", layout="wide")

# --- 合約詳細規範 ---
CONTRACT_DATA = {
    "新北食品": {
        "specs": {"現撈小卷": r"80|100", "無刺白帶魚": r"120|150", "手作獅子頭": r"60", "手作漢堡排": r"150", "手作烤肉串": r"80"},
        "spicy_days": ["週一", "週二", "週四"],
        "fried_limit": 1
    },
    "暖禾輕食": {
        "spicy_days": ["週一", "週二", "週四"],
        "fried_limit": 1
    }
}

# 💡 豁免名單 (這些字眼不計入食材重複)
EXEMPT_KEYWORDS = ["季節水果", "Fruit", "時令蔬菜", "Seasonal Vegetable", "履歷蔬菜", "Fresh Vegetable", "有機蔬菜", "Organic Vegetable"]

def clean_text(text):
    if pd.isna(text): return ""
    return str(text).replace("\n", " ").strip()

def run_audit(df, rule, vendor):
    df = df.fillna("") 
    final_report = []
    
    # 1. 重新定位日期與星期列
    date_row_idx = None
    day_row_idx = None
    for i, row in df.iterrows():
        row_str = " ".join([str(c) for c in row])
        if date_row_idx is None and re.search(r"\d{1,2}/\d{1,2}|\d{4}-\d{2}", row_str):
            date_row_idx = i
        if day_row_idx is None and any(d in row_str for d in ["週一", "週二", "週三", "週四", "週五"]):
            day_row_idx = i

    if date_row_idx is None or day_row_idx is None:
        return None

    # 2. 逐欄(Column)掃描：嚴格限制垂直範圍
    for col in range(len(df.columns)):
        date_raw = clean_text(df.iloc[date_row_idx, col])
        day_raw = clean_text(df.iloc[day_row_idx, col])
        
        date_match = re.search(r"(\d{1,2}/\d{1,2})|(\d{4}-\d{2}-\d{2})", date_raw)
        weekday_match = re.search(r"週[一二三四五]", day_raw)
        
        if date_match and weekday_match:
            date_label = date_match.group()
            weekday = weekday_match.group()
            
            # 💡 抓取該欄(Column)的菜名，僅限當日垂直內容
            dishes_in_day = []
            for i in range(len(df)):
                if i in [date_row_idx, day_row_idx]: continue
                cell_val = clean_text(df.iloc[i, col])
                # 排除標題與數值格，確保只抓到「菜名」
                if cell_val and not any(k in cell_val for k in ["套餐", "熱量", "份", "雜糧", "油脂", "奶類"]):
                    # 避免抓到表頭文字
                    if len(cell_val) > 1: 
                        dishes_in_day.append(cell_val)
            
            # --- 判讀 A: 湯品比對 (A/B餐不同時才報錯) ---
            if vendor == "暖禾輕食":
                soups = list(set([d for d in dishes_in_day if "湯" in d or "羹" in d]))
                if len(soups) > 1:
                    final_report.append({
                        "日期": date_label, "週幾": weekday, "異常項目": "湯品一致性", 
                        "判讀結果": f"❌ 湯品不一致：同時出現「{soups[0]}」與「{soups[1]}」"
                    })

            # --- 判讀 B: 食材重複性 (僅限該欄位內部) ---
            seen_ingredients = {} 
            for dish in dishes_in_day:
                if any(k in dish for k in EXEMPT_KEYWORDS) or "湯" in dish or "羹" in dish:
                    continue
                
                # 提取關鍵食材名 (排除符號與數字)
                core = re.sub(r"[◎🌶️●△★() \d gG克/a-zA-Z]", "", dish)[:2]
                if len(core) >= 2:
                    if core in seen_ingredients:
                        final_report.append({
                            "日期": date_label, "週幾": weekday, "異常項目": "食材重複", 
                            "判讀結果": f"❌ 「{dish}」與「{seen_ingredients[core]}」主料重複使用"
                        })
                    seen_ingredients[core] = dish

                # --- 判讀 C: 禁辣與符號 ---
                if weekday in rule["spicy_days"] and ("🌶️" in dish or "●" in dish):
                    final_report.append({
                        "日期": date_label, "週幾": weekday, "異常項目": dish, 
                        "判讀結果": "🚫 禁辣日違規：週一二四不得供應含辣或標記 ● 之餐點"
                    })
                
                if vendor == "新北食品":
                    for s_name, s_reg in rule.get("specs", {}).items():
                        if s_name in dish and not re.search(s_reg, dish):
                            final_report.append({
                                "日期": date_label, "週幾": weekday, "異常項目": dish, 
                                "判讀結果": f"⚠️ 規格缺失：須依協議標註 {s_reg}g"
                            })

            # --- 判讀 D: 油炸統計 ---
            total_fried = "".join(dishes_in_day).count("◎")
            if total_fried > rule["fried_limit"]:
                final_report.append({
                    "日期": date_label, "週幾": weekday, "異常項目": "油炸統計", 
                    "判讀結果": f"🍟 油炸超標：當天共計 {total_fried} 次標記 (◎)"
                })

    return final_report

# --- UI ---
st.title("🛡️ 林口康橋國際學校菜單審核")
up = st.file_uploader("👉 請上傳 Excel 菜單檔案", type=["xlsx"])

if up:
    is_light_file = "輕食" in up.name
    excel = pd.read_excel(up, sheet_name=None, header=None)
    for sheet_name, df in excel.items():
        vendor = "暖禾輕食" if (is_light_file or "輕食" in sheet_name) else "新北食品"
        st.subheader(f"📊 審核對象：{sheet_name}")
        results = run_audit(df, CONTRACT_DATA[vendor], vendor)
        
        if results:
            st.error(f"🚩 偵測到違規項目 (一事一列)：")
            st.table(pd.DataFrame(results))
        else:
            st.success("🎉 本頁審核通過！")
        st.divider()
