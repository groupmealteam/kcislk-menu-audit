import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="康橋菜單合約終極稽核系統", layout="wide")

# --- 合約詳細規範與克重數據 ---
CONTRACT_DATA = {
    "新北食品": {
        "specs": {
            "現撈小卷": r"80|100",
            "無刺白帶魚": r"120|150",
            "手作獅子頭": r"60",
            "手作漢堡排": r"150",
            "手作烤肉串": r"80",
            "帶皮鯰魚": r"120",
            "水鯊魚丁": r"100|250"
        },
        "spicy_days": ["週一", "週二", "週四"],
        "fried_limit": 1
    },
    "暖禾輕食": {
        "specs": {"鮭魚": r"", "鯖魚": r"", "鱸魚": r""},
        "spicy_days": ["週一", "週二", "週四"],
        "fried_limit": 1
    }
}

def clean_text(text):
    return str(text).replace("\n", " ").strip()

def run_audit(df, rule, vendor):
    df = df.fillna("") # 處理 NaN
    violations = []
    
    # 搜尋基準日期列
    day_row = None
    for i, row in df.iterrows():
        if any("週" in str(c) for c in row):
            day_row = i
            break
    if day_row is None: return None

    for col in range(len(df.columns)):
        header = clean_text(df.iloc[day_row, col])
        weekday_m = re.search(r"週[一二三四五]", header)
        if weekday_m:
            weekday = weekday_m.group()
            date_str = re.search(r"\d{1,2}/\d{1,2}", header).group() if re.search(r"\d{1,2}/\d{1,2}", header) else ""
            
            # 獲取該日菜單內容
            dishes = [clean_text(d) for i, d in df.iloc[:, col].items() if i != day_row and clean_text(d)]
            
            # --- 稽核 A: 食材重複性 ---
            seen_items = {}
            for d in dishes:
                core = re.sub(r"[◎🌶️●△() \d gG克/]", "", d)[:2]
                if len(core) >= 2:
                    if core in seen_items:
                        violations.append({"日期": date_str, "週幾": weekday, "異常餐點": d, "原因": f"❌ 食材重複(與{seen_items[core]})"})
                    seen_items[core] = d

                # --- 稽核 B: 禁辣 (週一二四) ---
                if weekday in rule["spicy_days"] and ("🌶️" in d or "●" in d):
                    violations.append({"日期": date_str, "週幾": weekday, "異常餐點": d, "原因": "🚫 禁辣日提供辣味"})

                # --- 稽核 C: 克重與規格 (新北) ---
                if vendor == "新北食品":
                    for s_name, s_reg in rule["specs"].items():
                        if s_name in d and s_reg and not re.search(s_reg, d):
                            violations.append({"日期": date_str, "週幾": weekday, "異常餐點": d, "原因": f"⚠️ 克重缺失：須標註{s_reg}g"})

            # --- 稽核 D: 當日油炸次數 ---
            if "".join(dishes).count("◎") > rule["fried_limit"]:
                violations.append({"日期": date_str, "週幾": weekday, "異常餐點": "當日整欄", "原因": "🍟 油炸次數超標"})

    return violations

# --- Streamlit UI ---
st.title("⚖️ 康橋國際學校：菜單合約合規自動稽核")
up = st.file_uploader("請上傳 Excel 菜單檔案", type=["xlsx"])

if up:
    is_light = "輕食" in up.name
    excel = pd.ExcelFile(up)
    for sheet in excel.sheet_names:
        vendor = "暖禾輕食" if (is_light or "輕食" in sheet) else "新北食品"
        rule = CONTRACT_DATA[vendor]
        df = pd.read_excel(up, sheet_name=sheet, header=None)
        
        st.subheader(f"📑 稽核分頁：{sheet} (廠商：{vendor})")
        results = run_audit(df, rule, vendor)
        
        if results:
            st.error(f"🚩 發現 {len(results)} 項違規，請通知廠商修改：")
            st.table(pd.DataFrame(results))
        elif results is None:
            st.warning("⚠️ 此分頁格式不符，跳過偵測。")
        else:
            st.success("🎉 完美！經全規範審核，此分頁完全合規。")
        st.divider()
