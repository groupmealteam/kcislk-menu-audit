import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="康橋菜單合約全功能稽核系統", layout="wide")

# --- 合約詳細規範資料庫 ---
CONTRACT_RULES = {
    "新北食品": {
        "fish_specs": {
            "現撈小卷": r"小卷.*(80|100)\s?[gG克]",
            "無刺白帶魚": r"白帶魚.*(120|150)\s?[gG克]",
            "帶皮鯰魚": r"鯰魚.*120\s?[gG克]",
            "手作獅子頭": r"獅子頭.*60\s?[gG克]",
            "手作漢堡排": r"漢堡排.*150\s?[gG克]",
            "手作烤肉串": r"烤肉串.*80\s?[gG克]",
            "水鯊魚丁": r"水鯊.*(100|250)\s?[gG克]"
        },
        "spicy_days": ["週一", "週二", "週四"],
        "fried_limit": 1
    },
    "暖禾輕食": {
        "spicy_days": ["週一", "週二", "週四"],
        "fried_limit": 1,
        "forbidden_keywords": ["可樂", "汽水", "含糖飲料", "油炸超過"]
    }
}

def audit_day(df_col, weekday, date_str, rule, vendor):
    violations = []
    dish_list = [str(d).strip() for d in df_col if str(d).strip() and "週" not in str(d)]
    
    # 1. 食材重複性檢查 (當日不重複原則)
    seen_ingredients = {}
    for dish in dish_list:
        core_name = re.sub(r"[◎🌶️●△() \d gG克/]", "", dish)
        if len(core_name) >= 2:
            key = core_name[:2] # 取前兩個字當核心食材識別
            if key in seen_ingredients:
                violations.append({"日期": date_str, "週幾": weekday, "項目": dish, "異常": f"❌ 食材重複：與「{seen_ingredients[key]}」食材雷同"})
            seen_ingredients[key] = dish

        # 2. 禁辣檢查
        if weekday in rule["spicy_days"] and ("🌶️" in dish or "●" in dish):
            violations.append({"日期": date_str, "週幾": weekday, "項目": dish, "異常": "🚫 禁辣日提供辣味"})

        # 3. 規格與克重稽核 (新北食品增補協議專屬)
        if vendor == "新北食品":
            for spec, pattern in rule["fish_specs"].items():
                if spec in dish:
                    if not re.search(pattern, dish):
                        violations.append({"日期": date_str, "週幾": weekday, "項目": dish, "異常": f"⚠️ 規格缺失：未標註或克重不符合約要求"})

    # 4. 整日油炸次數檢查
    total_fried = "".join(dish_list).count("◎")
    if total_fried > rule["fried_limit"]:
        violations.append({"日期": date_str, "週幾": weekday, "項目": "當日統計", "異常": f"🍟 油炸次數 ({total_fried}) 超標"})

    return violations

# --- 主程式 ---
st.title("🛡️ 康橋菜單合約合規稽核系統")
st.info("系統已根據 SE1140316、SE1140803、SE1141205 三份合約條款設定審核條件。")

up = st.file_uploader("請上傳 Excel 菜單", type=["xlsx"])

if up:
    is_light = "輕食" in up.name
    excel = pd.ExcelFile(up)
    for sheet in excel.sheet_names:
        # 廠商判定
        vendor = "暖禾輕食" if (is_light or "輕食" in sheet) else "新北食品"
        rule = CONTRACT_RULES[vendor]
        df = pd.read_excel(up, sheet_name=sheet, header=None)
        
        # 定位基準日期列
        day_row = next((i for i, r in df.iterrows() if any("週" in str(c) for c in r)), None)
        if day_row is None: continue

        st.subheader(f"📑 稽核對象：{sheet} (適用規則：{vendor})")
        all_results = []
        for col in range(len(df.columns)):
            header = str(df.iloc[day_row, col])
            weekday_m = re.search(r"週[一二三四五]", header)
            if weekday_m:
                date_m = re.search(r"\d{1,2}/\d{1,2}", header)
                v = audit_day(df.iloc[:, col], weekday_m.group(), date_m.group() if date_m else "", rule, vendor)
                all_results.extend(v)

        if all_results:
            st.error(f"發現 {len(all_results)} 項不符規範項目：")
            st.table(pd.DataFrame(all_results)[["日期", "週幾", "項目", "異常"]])
        else:
            st.success("🎉 經深度稽核，本分頁完全符合合約規範條件。")
        st.divider()
