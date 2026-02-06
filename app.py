import streamlit as st
import pandas as pd

st.set_page_config(page_title="康橋菜單合約精準審核系統", layout="wide")

# --- 合約資料庫設定 ---
RULES = {
    "新北食品": {
        "keywords": ["小學菜單", "幼兒餐菜單", "美食街素食菜單", "美食街"],
        "fish_specs": ["現撈小卷", "無刺白帶魚", "鬼頭刀", "白蝦", "淡菜", "水鯊", "帶皮鯰魚"],
        "fried_limit": 1,
        "spicy_days": ["週一", "週二", "週四"],
        "desc": "團膳合約規範 (含增補協議克重要求)"
    },
    "暖禾輕食": {
        "keywords": ["輕食", "菜單"],
        "fish_specs": ["鮭魚", "鯖魚", "鱸魚", "蝦仁", "小卷"],
        "fried_limit": 1,
        "spicy_days": ["週一", "週二", "週四"],
        "desc": "輕食供應合約規範 (符合校園飲品點心準則)"
    }
}

def audit_logic(df, rule):
    df = df.fillna("").astype(str)
    violations = [] 
    
    # 1. 定位日期列
    day_row_idx = next((i for i, r in df.iterrows() if any("週" in str(cell) for cell in r)), None)
    if day_row_idx is None:
        return None, "❌ 找不到日期列（週一至週五），請檢查 Excel 格式。"

    header_cells = df.iloc[day_row_idx].tolist()
    
    for col_idx, cell_value in enumerate(header_cells):
        day_name = str(cell_value).strip()
        if any(d in day_name for d in ["週一", "週二", "週三", "週四", "週五"]):
            column_data = df.iloc[:, col_idx].tolist()
            
            # --- 逐一檢查每一道菜 ---
            for row_idx, dish_name in enumerate(column_data):
                dish_clean = dish_name.strip().replace("\n", " ")
                if not dish_clean or row_idx == day_row_idx:
                    continue

                # A. 禁辣檢查
                if any(d in day_name for d in rule["spicy_days"]):
                    if "🌶️" in dish_clean or "●" in dish_clean:
                        violations.append({
                            "日期": day_name,
                            "異常餐點名稱": dish_clean,
                            "違規原因": "🚫 禁辣日出現辣味標示"
                        })

                # B. 油炸符號檢查 (單一菜色檢查)
                if dish_clean.count("◎") > rule["fried_limit"]:
                    violations.append({
                        "日期": day_name,
                        "異常餐點名稱": dish_clean,
                        "違規原因": f"🍟 油炸次數超過上限"
                    })

    return violations, "OK"

# --- 網頁主程式 ---
st.title("🍱 康橋菜單合約異常精準定位系統")

up = st.file_uploader("👉 請上傳您的 Excel 菜單", type=["xlsx"])

if up:
    file_name = up.name
    st.info(f"📂 偵測到檔案名稱：`{file_name}`")
    
    # --- 關鍵識別邏輯 ---
    # 優先判斷檔名是否有「輕食」
    is_light_meal_file = "輕食" in file_name
    
    try:
        excel = pd.ExcelFile(up)
        for sheet_name in excel.sheet_names:
            # 判斷廠商
            if is_light_meal_file:
                vendor = "暖禾輕食"
            else:
                # 若檔名沒寫，則根據分頁關鍵字判斷
                if any(k in sheet_name for k in RULES["暖禾輕食"]["keywords"]):
                    vendor = "暖禾輕食"
                elif any(k in sheet_name for k in RULES["新北食品"]["keywords"]):
                    vendor = "新北食品"
                else:
                    vendor = "新北食品" # 預設

            rule = RULES[vendor]
            df = pd.read_excel(up, sheet_name=sheet_name, header=None)
            
            st.subheader(f"📊 審核分頁：{sheet_name} (廠商規則：{vendor})")
            
            violations, msg = audit_logic(df, rule)
            
            if violations:
                st.error(f"🚩 發現 {len(violations)} 項異常！請要求廠商修改：")
                # 這裡就是你要的：清楚告訴你哪一天、哪道菜、為什麼異常
                st.table(pd.DataFrame(violations))
            elif violations is None:
                st.warning(msg)
            else:
                st.success("🎉 完美！本頁所有餐點均符合合約規範。")
            st.divider()

    except Exception as e:
        st.error(f"系統故障：{e}")
