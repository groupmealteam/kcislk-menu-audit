import streamlit as st
import pandas as pd

st.set_page_config(page_title="康橋菜單合約精準審核", layout="wide")

# --- 合約資料庫設定 ---
RULES = {
    "新北食品": {
        "keywords": ["小學菜單", "幼兒餐菜單", "美食街素食菜單", "美食街"],
        "fish_specs": ["現撈小卷", "無刺白帶魚", "鬼頭刀", "白蝦", "淡菜", "水鯊", "鯰魚"],
        "fried_limit": 1,
        "spicy_days": ["週一", "週二", "週四"]
    },
    "暖禾輕食": {
        "keywords": ["輕食菜單"],
        "fish_specs": ["鮭魚", "鯖魚", "鱸魚", "蝦仁", "小卷"],
        "fried_limit": 1,
        "spicy_days": ["週一", "週二", "週四"]
    }
}

def get_rule_by_sheet(sheet_name):
    for vendor, r in RULES.items():
        if any(key in sheet_name for key in r["keywords"]):
            return vendor, r
    return "未知分頁", None

def audit_logic(df, rule):
    df = df.fillna("").astype(str)
    report = {"err": [], "info": []}
    
    # 1. 定位日期列
    day_row_idx = next((i for i, r in df.iterrows() if any("週" in cell for cell in r)), None)
    if day_row_idx is None:
        return {"err": ["❌ 格式錯誤：找不到日期列（週一~週五）。"], "info": []}

    # 2. 垂直掃描每一欄 (每一天)
    header_cells = df.iloc[day_row_idx].tolist()
    for col_idx, cell_value in enumerate(header_cells):
        day_name = cell_value.strip()
        if any(d in day_name for d in ["週一", "週二", "週三", "週四", "週五"]):
            
            # 取得該欄當天所有的餐點格子 (排除日期列)
            day_items = df.iloc[:, col_idx].tolist()
            
            day_has_fish = False
            for row_idx, item_content in enumerate(day_items):
                item_clean = item_content.strip().replace("\n", " ")
                if not item_clean or row_idx == day_row_idx: continue

                # A. 辣味檢查 (精確到哪一道餐)
                if any(d in day_name for d in rule["spicy_days"]):
                    if "🌶️" in item_clean or "●" in item_clean:
                        report["err"].append(f"🔴 **【禁辣違規】** {day_name} ➜ 異常餐點：`{item_clean}`")

                # B. 魚類檢查
                found_fish = [f for f in rule["fish_specs"] if f in item_clean]
                if found_fish:
                    day_has_fish = True
                    report["info"].append(f"🐟 **【合約食材】** {day_name} ➜ 偵測到：`{item_clean}`")

            # C. 油炸/加工品總計 (以天為單位)
            col_text = "".join(day_items)
            f_cnt = col_text.count("◎")
            if f_cnt > rule["fried_limit"]:
                report["err"].append(f"⚠️ **【油炸超標】** {day_name} ➜ 總共 {f_cnt} 次油炸，超過合約上限 {rule['fried_limit']} 次。")

    return report

st.title("🍱 康橋菜單精準審核系統")
up = st.file_uploader("👉 請上傳 Excel 菜單檔案", type=["xlsx"])

if up:
    try:
        excel = pd.ExcelFile(up)
        for name in excel.sheet_names:
            df = pd.read_excel(up, sheet_name=name, header=None)
            vendor, r = get_rule_by_sheet(name)

            st.subheader(f"📄 分頁：{name} (廠商：{vendor})")
            if r:
                res = audit_logic(df, r)
                
                # 顯示異常結果
                if res["err"]:
                    for e in res["err"]: st.error(e)
                else:
                    st.success("🎉 本分頁初步審核符合合約規範")
                
                # 顯示明細
                with st.expander("🔍 查看詳細餐點判讀結果"):
                    for i in res["info"]: st.info(i)
            else:
                st.warning("⚠️ 無法識別此分頁的廠商規則，請確認分頁名稱是否包含關鍵字。")
            st.divider()
    except Exception as e:
        st.error(f"檔案讀取失敗：{e}")
