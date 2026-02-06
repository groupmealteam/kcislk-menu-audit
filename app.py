import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="康橋菜單合約全功能稽核系統", layout="wide")

# --- 合約詳細規範與克重數據 ---
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

def clean_text(text):
    return str(text).replace("\n", " ").strip() if pd.notna(text) else ""

def run_audit(df, rule, vendor):
    df = df.fillna("") 
    violations = []
    
    # 搜尋基準日期列
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
            
            # --- 輕食模式專屬：湯品一致性檢查 ---
            if vendor == "暖禾輕食":
                # 假設湯品名稱通常包含「湯」或「羹」字眼
                soups = [d for d in dishes if "湯" in d or "羹" in d]
                if len(set(soups)) > 1:
                    violations.append({
                        "日期": date_str, "週幾": weekday, "項目": "湯品比對",
                        "異常": f"❌ 湯品不一致：當天 A/B 餐僅限供應一種湯品 ({', '.join(set(soups))})"
                    })

            # --- 核心稽核：食材重複性 ---
            seen_items = {}
            for d in dishes:
                # 排除湯品不計入重複食材（因為湯本來就一樣）
                if vendor == "暖禾輕食" and ("湯" in d or "羹" in d): continue
                
                core = re.sub(r"[◎🌶️●△() \d gG克/]", "", d)[:2]
                if len(core) >= 2:
                    if core in seen_items:
                        violations.append({"日期": date_str, "週幾": weekday, "項目": d, "異常": f"❌ 食材重複 (與 {seen_items[core]} 雷同)"})
                    seen_items[core] = d

                # --- 禁辣 & 克重稽核 ---
                if weekday in rule["spicy_days"] and ("🌶️" in d or "●" in d):
                    violations.append({"日期": date_str, "週幾": weekday, "項目": d, "異常": "🚫 禁辣日提供辣味"})
                
                if vendor == "新北食品":
                    for s_name, s_reg in rule.get("specs", {}).items():
                        if s_name in d and not re.search(s_reg, d):
                            violations.append({"日期": date_str, "週幾": weekday, "項目": d, "異常": f"⚠️ 規格缺失：須標註 {s_reg}g"})

            # --- 油炸次數 ---
            if "".join(dishes).count("◎") > rule["fried_limit"]:
                violations.append({"日期": date_str, "週幾": weekday, "項目": "當日統計", "異常": "🍟 油炸次數超標"})

    return violations

# --- UI 介面 ---
st.title("🛡️ 康橋菜單合約全自動稽核系統")
st.caption("已更新：輕食 A/B 餐湯品一致性偵測、當日食材重複、增補協議克重標示、禁辣日稽核。")

up = st.file_uploader("請上傳您的 Excel 菜單", type=["xlsx"])

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
            st.error(f"🚩 偵測到 {len(results)} 項合約違規：")
            st.table(pd.DataFrame(results)[["日期", "週幾", "項目", "異常"]])
        elif results is None:
            st.warning("⚠️ 此分頁格式不符或找不到日期標記。")
        else:
            st.success("🎉 經深度審核，本分頁完全符合合約規範！")
        st.divider()
