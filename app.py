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

# 💡 豁免名單
EXEMPT_KEYWORDS = ["季節水果", "Fruit", "時令蔬菜", "Seasonal Vegetable", "履歷蔬菜", "Fresh Vegetable", "有機蔬菜", "Organic Vegetable"]

def clean_text(text):
    if pd.isna(text): return ""
    return str(text).replace("\n", " ").strip()

def run_audit(df, rule, vendor):
    df = df.fillna("") 
    final_report = []
    
    # 尋找基準列
    day_row = next((i for i, row in df.iterrows() if any("週" in str(c) for c in row)), None)
    if day_row is None: return None

    for col in range(len(df.columns)):
        header = clean_text(df.iloc[day_row, col])
        weekday_m = re.search(r"週[一二三四五]", header)
        
        if weekday_m:
            weekday = weekday_m.group()
            date_m = re.search(r"\d{1,2}/\d{1,2}", header)
            date_str = date_m.group() if date_m else "未定"
            
            day_issues = [] # 用於收集當天所有問題
            
            # 抓取菜名
            raw_dishes = []
            for i in range(len(df)):
                cell_val = clean_text(df.iloc[i, col])
                if i != day_row and cell_val and not any(k in cell_val for k in ["套餐", "熱量", "份", "雜糧"]):
                    raw_dishes.append(cell_val)
            
            # --- 1. 湯品一致性 (僅在「不同」時報錯) ---
            if vendor == "暖禾輕食":
                soups = list(set([d for d in raw_dishes if "湯" in d or "羹" in d]))
                if len(soups) > 1:
                    day_issues.append(f"❌ 湯品不一致：同時出現「{soups[0]}」與「{soups[1]}」")

            # --- 2. 食材重複性 ---
            seen_ingredients = {} 
            for dish in raw_dishes:
                if any(k in dish for k in EXEMPT_KEYWORDS) or "湯" in dish or "羹" in dish:
                    continue
                core = re.sub(r"[◎🌶️●△() \d gG克/]", "", dish)[:2]
                if len(core) >= 2:
                    if core in seen_ingredients:
                        day_issues.append(f"❌ 食材重複：「{dish}」與「{seen_ingredients[core]}」主料雷同")
                    seen_ingredients[core] = dish

                # --- 3. 禁辣 & 克重 ---
                if weekday in rule["spicy_days"] and ("🌶️" in dish or "●" in dish):
                    day_issues.append(f"🚫 禁辣日違規：{dish} (週一二四禁辣)")
                
                if vendor == "新北食品":
                    for s_name, s_reg in rule.get("specs", {}).items():
                        if s_name in dish and not re.search(s_reg, dish):
                            day_issues.append(f"⚠️ 規格缺失：{dish} 須標註 {s_reg}g")

            # --- 4. 油炸統計 ---
            total_fried = "".join(raw_dishes).count("◎")
            if total_fried > rule["fried_limit"]:
                day_issues.append(f" Fries 油炸超標：當天共計 {total_fried} 次")

            # 💡 關鍵優化：將當天所有問題合併到同一個格位
            if day_issues:
                final_report.append({
                    "日期": date_str,
                    "週幾": weekday,
                    "異常判讀結果 (請廠商依此修正)": "\n\n".join(day_issues)
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
        st.subheader(f"📊 分頁：{sheet_name} ({vendor})")
        results = run_audit(df, CONTRACT_DATA[vendor], vendor)
        
        if results:
            st.error(f"🚩 偵測到違規項目：")
            # 使用 Markdown 渲染以換行顯示合併的問題
            report_df = pd.DataFrame(results)
            st.table(report_df)
        else:
            st.success("🎉 本頁審核通過，完全符合規範。")
        st.divider()
