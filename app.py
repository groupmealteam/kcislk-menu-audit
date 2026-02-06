import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="康橋菜單合約精準定位系統", layout="wide")

# --- 合約資料庫設定 ---
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

def audit_logic(df, rule):
    df = df.fillna("").astype(str)
    violations = [] 
    
    # 1. 定位日期列 (基準列)
    day_row_idx = next((i for i, r in df.iterrows() if any("週" in str(cell) for cell in r)), None)
    if day_row_idx is None:
        return None, "❌ 找不到日期標記列（週一至週五）。"

    header_cells = df.iloc[day_row_idx].tolist()
    
    for col_idx, cell_value in enumerate(header_cells):
        full_date_str = str(cell_value).strip().replace("\n", " ")
        # 提取日期 (如 3/31) 與 週幾 (如 週二)
        match_day = re.search(r"週[一二三四五]", full_date_str)
        if match_day:
            day_of_week = match_day.group()
            # 嘗試抓取日期部分 (例如 3/31)
            date_part = full_date_str.replace(day_of_week, "").strip()
            
            column_data = df.iloc[:, col_idx].tolist()
            
            # --- 垂直掃描每一道菜 ---
            for row_idx, dish_name in enumerate(column_data):
                dish_clean = dish_name.strip().replace("\n", " ")
                if not dish_clean or row_idx == day_row_idx:
                    continue

                # ⚠️ 判讀 A：禁辣違規 (定位到菜名)
                if any(d in day_of_week for d in rule["spicy_days"]):
                    if "🌶️" in dish_clean or "●" in dish_clean:
                        violations.append({
                            "日期": date_part,
                            "週幾": day_of_week,
                            "異常餐點名稱": dish_clean,
                            "異常問題": "🚫 禁辣日提供辣味標示"
                        })

                # ⚠️ 判讀 B：油炸超標 (單道菜偵測)
                if dish_clean.count("◎") > rule["fried_limit"]:
                    violations.append({
                        "日期": date_part,
                        "週幾": day_of_week,
                        "異常餐點名稱": dish_clean,
                        "異常問題": f"🍟 單品油炸標示超過 {rule['fried_limit']} 次"
                    })

            # ⚠️ 判讀 C：當日全天油炸統計
            all_col_text = "".join(column_data)
            total_f_count = all_col_text.count("◎")
            if total_f_count > rule["fried_limit"] + 1: # 假設全天總量寬限度
                violations.append({
                    "日期": date_part,
                    "週幾": day_of_week,
                    "異常餐點名稱": "--- 當日整欄統計 ---",
                    "異常問題": f"⚠️ 全天油炸共 {total_f_count} 次，疑超標"
                })

    return violations

# --- 網頁主程式 ---
st.title("🍱 康橋菜單合約異常精準定位系統")

up = st.file_uploader("👉 請上傳您的 Excel 菜單", type=["xlsx"])

if up:
    file_name = up.name
    is_light_file = "輕食" in file_name
    
    try:
        excel = pd.ExcelFile(up)
        for sheet_name in excel.sheet_names:
            # 識別廠商
            if is_light_file:
                vendor = "暖禾輕食"
            else:
                if any(k in sheet_name for k in RULES["暖禾輕食"]["keywords"]):
                    vendor = "暖禾輕食"
                elif any(k in sheet_name for k in RULES["新北食品"]["keywords"]):
                    vendor = "新北食品"
                else:
                    vendor = "新北食品"

            rule = RULES[vendor]
            df = pd.read_excel(up, sheet_name=sheet_name, header=None)
            
            st.subheader(f"📊 審核分頁：{sheet_name} (規則：{vendor})")
            
            violations = audit_logic(df, rule)
            
            if violations is None:
                st.warning("❌ 格式異常，無法定位日期。")
            elif violations:
                st.error(f"🚩 發現 {len(violations)} 項異常，請要求廠商修改：")
                # --- 這是您要求的優化表格格式 ---
                err_df = pd.DataFrame(violations)
                st.table(err_df[["日期", "週幾", "異常餐點名稱", "異常問題"]])
            else:
                st.success("🎉 本頁初步審核符合合約規範。")
            st.divider()

    except Exception as e:
        st.error(f"系統錯誤：{e}")
