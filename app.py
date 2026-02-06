import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="康橋菜單精準定位系統", layout="wide")

# --- 合約規則設定 ---
RULES = {
    "新北食品": {
        "keywords": ["小學菜單", "幼兒餐菜單", "美食街素食菜單", "美食街"],
        "fish_specs": ["現撈小卷", "無刺白帶魚", "鬼頭刀", "白蝦", "淡菜", "水鯊", "帶皮鯰魚"],
        "fried_limit": 1,
        "spicy_days": ["週一", "週二", "週四"]
    },
    "暖禾輕食": {
        "keywords": ["輕食", "菜單"],
        "fish_specs": ["鮭魚", "鯖魚", "鱸魚", "蝦仁", "小卷"],
        "fried_limit": 1,
        "spicy_days": ["週一", "週二", "週四"]
    }
}

def parse_date_and_weekday(cell_value):
    """
    精準拆解日期與星期。例如：將 '3/31 週二' 拆成 ('3/31', '週二')
    """
    text = str(cell_value).strip().replace("\n", " ")
    # 找「週幾」
    weekday_match = re.search(r"週[一二三四五]", text)
    # 找「日期」(數字/數字)
    date_match = re.search(r"\d{1,2}/\d{1,2}", text)
    
    weekday = weekday_match.group() if weekday_match else ""
    date_val = date_match.group() if date_match else text.replace(weekday, "").strip()
    
    return date_val, weekday

def audit_logic(df, rule):
    df = df.fillna("").astype(str)
    violations = [] 
    
    # 1. 搜尋含有「週」字眼的基準列
    day_row_idx = None
    for i, row in df.iterrows():
        if any("週" in str(cell) for cell in row):
            day_row_idx = i
            break
            
    if day_row_idx is None:
        return None

    # 2. 垂直掃描
    for col_idx in range(len(df.columns)):
        cell_content = df.iloc[day_row_idx, col_idx]
        date_str, weekday_str = parse_date_and_weekday(cell_content)
        
        # 只要有找到星期，就開始掃描該欄位
        if weekday_str:
            column_data = df.iloc[:, col_idx].tolist()
            for row_idx, dish_name in enumerate(column_data):
                dish_clean = dish_name.strip().replace("\n", " ")
                if not dish_clean or row_idx == day_row_idx: continue

                # A. 禁辣檢查
                if any(d in weekday_str for d in rule["spicy_days"]):
                    if "🌶️" in dish_clean or "●" in dish_clean:
                        violations.append({
                            "日期": date_str,
                            "週幾": weekday_str,
                            "異常餐點名稱": dish_clean,
                            "異常問題": "🚫 禁辣日提供辣味標示"
                        })

                # B. 油炸檢查
                if dish_clean.count("◎") > rule["fried_limit"]:
                    violations.append({
                        "日期": date_str,
                        "週幾": weekday_str,
                        "異常餐點名稱": dish_clean,
                        "異常問題": f"🍟 油炸標示超過 {rule['fried_limit']} 次"
                    })
    return violations

# --- 網頁主程式 ---
st.title("🍱 康橋菜單精準定位系統")

up = st.file_uploader("👉 請上傳 Excel 菜單", type=["xlsx"])

if up:
    is_light = "輕食" in up.name
    try:
        excel = pd.ExcelFile(up)
        for sheet in excel.sheet_names:
            vendor = "暖禾輕食" if is_light or any(k in sheet for k in RULES["暖禾輕食"]["keywords"]) else "新北食品"
            rule = RULES[vendor]
            df = pd.read_excel(up, sheet_name=sheet, header=None)
            
            st.subheader(f"📊 審核分頁：{sheet} ({vendor}模式)")
            
            results = audit_logic(df, rule)
            
            if results is None:
                st.warning("⚠️ 找不到日期標記，請確認分頁格式是否正確。")
            elif results:
                st.error(f"🚩 偵測到 {len(results)} 項異常：")
                st.table(pd.DataFrame(results)) # 顯示您要求的四個欄位
            else:
                st.success("🎉 審核通過，未發現異常。")
            st.divider()
    except Exception as e:
        st.error(f"系統故障：{e}")
