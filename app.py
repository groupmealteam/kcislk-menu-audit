import streamlit as st
import pandas as pd

st.set_page_config(page_title="康橋菜單精準審核系統", layout="wide")

# --- 從 PDF 合約提取的精準規則資料庫 ---
RULES = {
    "新北食品": {
        "keywords": ["小學菜單", "幼兒餐菜單", "美食街素食菜單", "美食街"],
        "fish_specs": ["現撈小卷", "無刺白帶魚", "鬼頭刀", "白蝦", "淡菜", "水鯊", "帶皮鯰魚"],
        "fried_limit": 1,
        "spicy_days": ["週一", "週二", "週四"],
        "contracts": "增補協議要求：小卷 80-100g、白帶魚 120-150g"
    },
    "暖禾輕食": {
        "keywords": ["輕食菜單"],
        "fish_specs": ["鮭魚", "鯖魚", "鱸魚", "蝦仁", "小卷"],
        "fried_limit": 1,
        "spicy_days": ["週一", "週二", "週四"],
        "contracts": "輕食合約要求：符合校園飲品點心規範，限油炸。"
    }
}

def get_rule_by_sheet(sheet_name):
    for vendor, r in RULES.items():
        if any(key in sheet_name for key in r["keywords"]):
            return vendor, r
    return "未知分頁", None

def audit_logic(df, rule):
    df = df.fillna("").astype(str)
    results = {"errors": [], "passed_items": []}
    
    # 1. 尋找日期列 (基準列)
    day_row_idx = next((i for i, r in df.iterrows() if any("週" in cell for cell in r)), None)
    if day_row_idx is None:
        results["errors"].append({"type": "格式錯誤", "msg": "找不到日期列（週一至週五）"})
        return results

    # 2. 垂直掃描每一天 (Column)
    header_cells = df.iloc[day_row_idx].tolist()
    for col_idx, cell_value in enumerate(header_cells):
        day_name = cell_value.strip()
        if any(d in day_name for d in ["週一", "週二", "週三", "週四", "週五"]):
            
            # 獲取該天整欄所有餐點 (排除日期列)
            column_data = df.iloc[:, col_idx].tolist()
            
            # --- 逐一檢查每一道菜 (Row) ---
            for row_idx, dish_name in enumerate(column_data):
                dish_clean = dish_name.strip().replace("\n", " ")
                if not dish_clean or row_idx == day_row_idx:
                    continue

                # ⚠️ 判讀 A：禁辣違規 (精確定位到菜名)
                if any(d in day_name for d in rule["spicy_days"]):
                    if "🌶️" in dish_clean or "●" in dish_clean:
                        results["errors"].append({
                            "day": day_name,
                            "dish": dish_clean,
                            "reason": f"合約禁辣日（{day_name}）不可提供辣味餐點"
                        })

                # ✅ 判讀 B：合約高級魚偵測
                found_fish = [f for f in rule["fish_specs"] if f in dish_clean]
                if found_fish:
                    results["passed_items"].append({
                        "day": day_name,
                        "dish": dish_clean,
                        "match": ", ".join(found_fish)
                    })

            # ⚠️ 判讀 C：油炸次數統計 (全天彙整)
            col_text = "".join(column_data)
            f_count = col_text.count("◎")
            if f_count > rule["fried_limit"]:
                results["errors"].append({
                    "day": day_name,
                    "dish": "當日整欄統計",
                    "reason": f"油炸次數 ({f_count}) 超過合約上限 ({rule['fried_limit']} 次)"
                })

    return results

# --- 網頁介面 ---
st.title("🍱 康橋菜單合約精準審核系統")
st.info("系統將根據分頁名稱自動識別廠商：\n- **新北食品**：小學、幼兒餐、美食街\n- **暖禾**：輕食菜單")

up = st.file_uploader("👉 請上傳 Excel 菜單", type=["xlsx"])

if up:
    try:
        excel = pd.ExcelFile(up)
        for sheet_name in excel.sheet_names:
            df = pd.read_excel(up, sheet_name=sheet_name, header=None)
            vendor, r = get_rule_by_sheet(sheet_name)

            st.subheader(f"📊 分頁：{sheet_name} (廠商：{vendor})")
            
            if r:
                res = audit_logic(df, r)
                
                # 🔴 顯示異常報警
                if res["errors"]:
                    st.error(f"⚠️ 偵測到 {len(res['errors'])} 項合約違規：")
                    # 建立表格顯示異常，讓用戶一眼看清
                    err_df = pd.DataFrame(res["errors"])
                    st.table(err_df[["day", "dish", "reason"]].rename(
                        columns={"day": "日期", "dish": "異常餐點內容", "reason": "違反規則"}
                    ))
                else:
                    st.success(f"🎉 {sheet_name} 分頁初步審核完全符合合約規範！")

                # 🔵 顯示合格明細
                with st.expander("🔍 查看合格食材與統計"):
                    if res["passed_items"]:
                        st.write("已偵測到下列合約指定食材：")
                        st.table(pd.DataFrame(res["passed_items"]).rename(
                            columns={"day": "日期", "dish": "餐點名稱", "match": "匹配關鍵字"}
                        ))
                    else:
                        st.write("未在菜名中偵測到合約指定魚類。")
            else:
                st.warning("無法辨識此分頁名稱，請確認是否包含關鍵字（如：小學菜單、輕食菜單）。")
            st.divider()
            
    except Exception as e:
        st.error(f"判讀過程發生錯誤：{e}")
