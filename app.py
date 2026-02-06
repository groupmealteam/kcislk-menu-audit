import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="林口康橋國際學校菜單審核", layout="wide")

# --- 合約詳細規範與克重數據 ---
CONTRACT_DATA = {
    "新北食品": {
        "specs": {
            "現撈小卷": r"80|100",
            "無刺白帶魚": r"120|150",
            "手作獅子頭": r"60",
            "手作漢堡排": r"150",
            "手作烤肉串": r"80",
            "帶皮鯰魚": r"120"
        },
        "spicy_days": ["週一", "週二", "週四"],
        "fried_limit": 1
    },
    "暖禾輕食": {
        "spicy_days": ["週一", "週二", "週四"],
        "fried_limit": 1
    }
}

# 💡 重複性稽核豁免名單 (蔬菜水果不計入重複)
EXEMPT_KEYWORDS = ["季節水果", "Fruit", "時令蔬菜", "Seasonal Vegetable", "履歷蔬菜", "Fresh Vegetable", "有機蔬菜", "Organic Vegetable"]

def clean_text(text):
    if pd.isna(text): return ""
    return str(text).replace("\n", " ").strip()

def run_audit(df, rule, vendor):
    df = df.fillna("") 
    violations = []
    
    # 尋找日期基準列
    day_row = next((i for i, row in df.iterrows() if any("週" in str(c) for c in row)), None)
    if day_row is None: return None

    for col in range(len(df.columns)):
        header = clean_text(df.iloc[day_row, col])
        weekday_m = re.search(r"週[一二三四五]", header)
        
        if weekday_m:
            weekday = weekday_m.group()
            date_m = re.search(r"\d{1,2}/\d{1,2}", header)
            date_str = date_m.group() if date_m else "未定"
            
            # 💡 精準抓取菜名：排除標題、熱量、雜糧等干擾項
            raw_dishes = []
            for i in range(len(df)):
                cell_val = clean_text(df.iloc[i, col])
                if i != day_row and cell_val and not any(k in cell_val for k in ["套餐", "熱量", "份", "雜糧"]):
                    raw_dishes.append(cell_val)
            
            # --- 稽核 A: 輕食湯品一致性 ---
            if vendor == "暖禾輕食":
                soups = [d for d in raw_dishes if "湯" in d or "羹" in d]
                if len(set(soups)) > 1:
                    violations.append({
                        "日期": date_str, "週幾": weekday, "稽核項目": "湯品一致性",
                        "異常原因與位置": f"❌ A/B餐湯品不同：同時出現「{soups[0]}」與「{soups[1]}」"
                    })

            # --- 稽核 B: 食材重複性 (顯示具體菜名比對) ---
            seen_ingredients = {} 
            for dish in raw_dishes:
                # 跳過豁免字眼與湯品(湯品已獨立檢查)
                if any(k in dish for k in EXEMPT_KEYWORDS) or "湯" in dish or "羹" in dish:
                    continue
                
                # 提取主料核心字 (例如: 牛肉、雞丁)
                core = re.sub(r"[◎🌶️●△() \d gG克/]", "", dish)[:2]
                if len(core) >= 2:
                    if core in seen_ingredients:
                        violations.append({
                            "日期": date_str, "週幾": weekday, 
                            "稽核項目": "食材重複性檢查", 
                            "異常原因與位置": f"❌ 「{dish}」與「{seen_ingredients[core]}」食材重複使用"
                        })
                    seen_ingredients[core] = dish

                # --- 稽核 C: 禁辣 & 克重 ---
                if weekday in rule["spicy_days"] and ("🌶️" in dish or "●" in dish):
                    violations.append({"日期": date_str, "週幾": weekday, "稽核項目": dish, "異常原因與位置": "🚫 禁辣日違規：不得供應辣味標示餐點"})
                
                if vendor == "新北食品":
                    for s_name, s_reg in rule.get("specs", {}).items():
                        if s_name in dish and not re.search(s_reg, dish):
                            violations.append({"日期": date_str, "週幾": weekday, "稽核項目": dish, "異常原因與位置": f"⚠️ 規格缺失：未依合約標註 {s_reg}g"})

            # --- 稽核 D: 油炸統計 ---
            total_fried = "".join(raw_dishes).count("◎")
            if total_fried > rule["fried_limit"]:
                violations.append({"日期": date_str, "週幾": weekday, "稽核項目": "當日油炸統計", "異常原因與位置": f" Fries 油炸超標：當天共計 {total_fried} 次"})

    return violations

# --- 網頁介面 ---
st.title("🛡️ 林口康橋國際學校菜單審核")
st.caption("合約規範自動化比對系統：支援 A/B 餐湯品一致、食材重複偵測、禁辣日稽核、克重標示校對。")

up = st.file_uploader("👉 請上傳 Excel 菜單檔案", type=["xlsx"])

if up:
    is_light_file = "輕食" in up.name
    excel = pd.read_excel(up, sheet_name=None, header=None)
    for sheet_name, df in excel.items():
        vendor = "暖禾輕食" if (is_light_file or "輕食" in sheet_name) else "新北食品"
        rule = CONTRACT_DATA[vendor]
        
        st.subheader(f"📑 審核分頁：{sheet_name} (廠商規則：{vendor})")
        results = run_audit(df, rule, vendor)
        
        if results:
            st.error(f"🚩 偵測到 {len(results)} 項異常項目：")
            st.table(pd.DataFrame(results)[["日期", "週幾", "稽核項目", "異常原因與位置"]])
        elif results is None:
            st.warning("⚠️ 格式無法辨識，請檢查日期列。")
        else:
            st.success("🎉 經深度稽核，本分頁所有餐點均符合合約規範！")
        st.divider()
