import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="康橋菜單合約終極稽核系統", layout="wide")

# --- 合約細節與稽核標準資料庫 ---
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

# 💡 食材重複性稽核的「豁免名單」（出現這些字眼不報錯）
EXEMPT_KEYWORDS = ["季節水果", "Fruit", "時令蔬菜", "Seasonal Vegetable", "履歷蔬菜", "Fresh Vegetable", "有機蔬菜", "Organic Vegetable"]

def clean_text(text):
    """處理 Excel 中的換行與空白，並將 NaN 轉為空字串"""
    if pd.isna(text): return ""
    return str(text).replace("\n", " ").strip()

def run_audit(df, rule, vendor):
    df = df.fillna("") 
    violations = []
    
    # 1. 尋找含有「週」字眼的日期基準列
    day_row = next((i for i, row in df.iterrows() if any("週" in str(c) for c in row)), None)
    if day_row is None: return None

    # 2. 按欄(Column)掃描，每一欄代表一天
    for col in range(len(df.columns)):
        header = clean_text(df.iloc[day_row, col])
        weekday_m = re.search(r"週[一二三四五]", header)
        
        if weekday_m:
            weekday = weekday_m.group()
            # 提取日期 (如 2/3)
            date_m = re.search(r"\d{1,2}/\d{1,2}", header)
            date_str = date_m.group() if date_m else "未定"
            
            # 獲取該天所有填寫了內容的儲存格
            raw_dishes = [clean_text(df.iloc[i, col]) for i in range(len(df)) if i != day_row and clean_text(df.iloc[i, col])]
            
            # --- 稽核項目 A: 輕食湯品一致性 ---
            if vendor == "暖禾輕食":
                # 抓取包含「湯」或「羹」的名稱
                soups = [d for d in raw_dishes if "湯" in d or "羹" in d]
                if len(set(soups)) > 1:
                    violations.append({
                        "日期": date_str, "週幾": weekday, "項目": "湯品比對",
                        "異常": f"❌ 輕食湯品不一致：A/B餐須共用同種湯品 ({', '.join(set(soups))})"
                    })

            # --- 稽核項目 B: 食材重複性 & 禁辣 & 克重 ---
            seen_ingredients = {}
            for dish in raw_dishes:
                # 跳過豁免字眼與湯品(湯品已在上面檢查過)
                is_exempt = any(k in dish for k in EXEMPT_KEYWORDS)
                is_soup = "湯" in dish or "羹" in dish
                
                if not is_exempt and not is_soup:
                    # 提取核心字眼(前2個字)做重複比對
                    core = re.sub(r"[◎🌶️●△() \d gG克/]", "", dish)[:2]
                    if len(core) >= 2:
                        if core in seen_ingredients:
                            violations.append({"日期": date_str, "週幾": weekday, "項目": dish, "異常": f"❌ 食材重複 (與 {seen_ingredients[core]} 使用相似主料)"})
                        seen_ingredients[core] = dish

                # 禁辣檢查 (週一、二、四)
                if weekday in rule["spicy_days"] and ("🌶️" in dish or "●" in dish):
                    violations.append({"日期": date_str, "週幾": weekday, "項目": dish, "異常": "🚫 禁辣日違規：當天不應提供辣味餐點"})
                
                # 新北食品克重規格檢查
                if vendor == "新北食品":
                    for s_name, s_reg in rule.get("specs", {}).items():
                        if s_name in dish and not re.search(s_reg, dish):
                            violations.append({"日期": date_str, "週幾": weekday, "項目": dish, "異常": f"⚠️ 規格缺失：未依合約標註 {s_reg}g"})

            # --- 稽核項目 C: 油炸次數統計 ---
            total_fried = "".join(raw_dishes).count("◎")
            if total_fried > rule["fried_limit"]:
                violations.append({"日期": date_str, "週幾": weekday, "項目": "當日統計", "異常": f"🍟 油炸超標：當天出現 {total_fried} 次油炸項目"})

    return violations

# --- Streamlit 網頁介面 ---
st.title("⚖️ 康橋菜單合約全自動稽核系統")
st.markdown("### 依據合約條款：SE1140316、SE1140803、SE1141205")

up = st.file_uploader("👉 請上傳您的 Excel 菜單檔案", type=["xlsx"])

if up:
    is_light_file = "輕食" in up.name
    excel = pd.read_excel(up, sheet_name=None, header=None)
    
    for sheet_name, df in excel.items():
        # 廠商識別邏輯：檔名有輕食 or 分頁有輕食關鍵字
        vendor = "暖禾輕食" if (is_light_file or "輕食" in sheet_name) else "新北食品"
        rule = CONTRACT_DATA[vendor]
        
        st.subheader(f"📊 分頁：{sheet_name} (採用規則：{vendor})")
        
        results = run_audit(df, rule, vendor)
        
        if results:
            st.error(f"🚩 發現 {len(results)} 項不符規範項目，請通知廠商修改：")
            st.table(pd.DataFrame(results)[["日期", "週幾", "項目", "異常"]])
        elif results is None:
            st.warning("⚠️ 此分頁無法辨識日期格式。")
        else:
            st.success("🎉 完美！經深度稽核，此分頁完全符合合約條件。")
        st.divider()
