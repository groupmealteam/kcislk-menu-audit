import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="康橋菜單合約全功能稽核系統", layout="wide")

# --- 合約詳細規範資料庫 ---
CONTRACT_DATA = {
    "新北食品": {
        "specs": {
            "現撈小卷": r"80|100",
            "無刺白帶魚": r"120|150",
            "手作獅子頭": r"60",
            "手作漢堡排": r"150",
            "手作烤肉串": r"80"
        },
        "spicy_days": ["週一", "週二", "週四"],
        "fried_limit": 1
    },
    "暖禾輕食": {
        "spicy_days": ["週一", "週二", "週四"],
        "fried_limit": 1
    }
}

# 💡 重複性檢查的豁免名單
EXEMPT_KEYWORDS = ["季節水果", "Fruit", "時令蔬菜", "Seasonal Vegetable", "履歷蔬菜", "有機蔬菜"]

def clean_text(text):
    return str(text).replace("\n", " ").strip() if pd.notna(text) else ""

def run_audit(df, rule, vendor):
    df = df.fillna("") 
    violations = []
    
    day_row = next((i for i, row in df.iterrows() if any("週" in str(c) for c in row)), None)
    if day_row is None: return None

    for col in range(len(df.columns)):
        header = clean_text(df.iloc[day_row, col])
        weekday_m = re.search(r"週[一二三四五]", header)
        
        if weekday_m:
            weekday = weekday_m.group()
            date_str = re.search(r"\d{1,2}/\d{1,2}", header).group() if re.search(r"\d{1,2}/\d{1,2}", header) else ""
            
            # 獲取該日所有非空餐點
            dishes = [clean_text(d) for i, d in df.iloc[:, col].items() if i != day_row and clean_text(d)]
            
            # --- 輕食模式：湯品一致性檢查 ---
            if vendor == "暖禾輕食":
                soups = [d for d in dishes if "湯" in d or "羹" in d]
                if len(set(soups)) > 1:
                    violations.append({"日期": date_str, "週幾": weekday, "項目": "湯品比對", "異常": f"❌ 湯品不一致：A/B餐須共用一種湯品 ({', '.join(set(soups))})"})

            # --- 核心稽核：食材重複性 (含豁免邏輯) ---
            seen_items = {}
            for d in dishes:
                # 1. 如果是湯品 (輕食模式) 或是 豁免關鍵字，則跳過重複性檢查
                if (vendor == "暖禾輕食" and ("湯" in d or "羹" in d)) or any(k in d for k in EXEMPT_KEYWORDS):
                    pass 
                else:
                    core = re.sub(r"[◎🌶️●△() \d gG克/]", "", d)[:2]
                    if len(core) >= 2:
                        if core in seen_items:
                            violations.append({"日期": date_str, "週幾": weekday, "項目": d, "異常": f"❌ 食材重複 (與 {seen_items[core]} 雷同)"})
                        seen_items[core] = d

                # --- 禁辣 & 克重 & 油炸 ---
                if weekday in rule["spicy_days"] and ("🌶️" in d or "●" in d):
                    violations.append({"日期": date_str, "週幾": weekday, "項目": d, "異常": "🚫 禁辣日提供辣味"})
                
                if vendor == "新北食品":
                    for s_name, s_reg in rule.get("specs", {}).items():
                        if s_name in d and not re.search(s_reg, d):
                            violations.append({"日期": date_str, "週幾": weekday, "項目": d, "異常": f"⚠️ 規格缺失：未標註 {s_reg}g"})

            if "".join(dishes).count("◎") > rule["fried_limit"]:
                violations.append({"日期": date_str, "週幾": weekday, "項目": "當日統計", "異常": "🍟 油炸次數超標"})

    return violations

# --- UI ---
st.title("🛡️ 康橋菜單合約全功能稽核系統")
st.info("已設定：蔬菜、水果類排除重複性偵測；輕食湯品須一致；增補協議克重稽核。")

up = st.file_uploader("請上傳您的 Excel 菜單", type=["xlsx"])

if up:
    is_light = "輕食" in up.name
    excel = pd.read_excel(up, sheet_name=None, header=None)
    for sheet_name, df in excel.items():
        vendor = "暖禾輕食" if (is_light or "輕食" in sheet_name) else "新北食品"
        rule = CONTRACT_DATA[vendor]
        
        st.subheader(f"📑 稽核分頁：{sheet_name} (廠商：{vendor})")
        results = run_audit(df, rule, vendor)
        
        if results:
            st.error(f"🚩 偵測到 {len(results)} 項合約違規：")
            st.table(pd.DataFrame(results)[["日期", "週幾", "項目", "異常"]])
        elif results is None:
            st.warning("⚠️ 格式不符。")
        else:
            st.success("🎉 本分頁審核通過！")
        st.divider()
