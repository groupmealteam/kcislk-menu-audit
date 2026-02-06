import streamlit as st
import pandas as pd
import re
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import PatternFill

# --- 核心規則定義 ---
SPICY_DAYS = ["週一", "週二", "週四"] # 禁辣日
RED_FILL = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid") # 禁辣/違規紅
YELLOW_FILL = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid") # 食材重複黃

def clean_cn(text):
    """提取中文主料，避免英文翻譯干擾"""
    if pd.isna(text): return ""
    return "".join(re.findall(r'[\u4e00-\u9fa5]+', str(text)))

def process_and_mark_menu(uploaded_file):
    wb = load_workbook(uploaded_file)
    all_sheets = pd.read_excel(uploaded_file, sheet_name=None, header=None)
    output = BytesIO()
    audit_log = []

    for sheet_name, df in all_sheets.items():
        df = df.fillna("")
        ws = wb[sheet_name]
        
        # 1. 精準定位日期行 (搜尋 2/3 或 3/3 格式)
        date_row_idx = None
        for i, row in df.iterrows():
            if any(re.search(r"\d{1,2}/\d{1,2}", str(c)) for c in row):
                date_row_idx = i
                break
        
        if date_row_idx is None: continue

        # 2. 定位「主食」與「副菜」列索引 (確保不抓到下方的食材組成雜訊)
        main_dish_indices = []
        for i, row in df.iterrows():
            if any(k in str(row[1]) for k in ["主食", "副菜", "主菜"]):
                main_dish_indices.append(i)

        # 3. 逐欄審核 (日期欄位)
        for col in range(2, len(df.columns)):
            date_val = str(df.iloc[date_row_idx, col])
            day_val = str(df.iloc[date_row_idx + 1, col]) if (date_row_idx + 1) < len(df) else ""
            
            if not re.search(r"\d{1,2}/\d{1,2}", date_val): continue

            # --- A. 禁辣判定 (原則四) ---
            is_restricted_day = any(d in day_label for d in SPICY_DAYS for day_label in [date_val, day_val])
            
            seen_ingredients = {}
            for r_idx in main_dish_indices:
                cell_val = str(df.iloc[r_idx, col]).strip()
                if not cell_val or "時令" in cell_val or "季節" in cell_val: continue

                # 禁辣檢查 (標記 ● 或 🌶️)
                if is_restricted_day and ("●" in cell_val or "🌶️" in cell_val):
                    ws.cell(row=r_idx + 1, column=col + 1).fill = RED_FILL
                    audit_log.append({"日期": date_val, "項目": cell_val, "異常": "🚫 禁辣日違規"})

                # --- B. 食材重複判定 (原則九) ---
                core_ingredient = clean_cn(cell_val)[:2]
                if len(core_ingredient) >= 2:
                    if core_ingredient in seen_ingredients:
                        # 標色當前格與重複格
                        ws.cell(row=r_idx + 1, column=col + 1).fill = YELLOW_FILL
                        prev_r = seen_ingredients[core_ingredient]
                        ws.cell(row=prev_r + 1, column=col + 1).fill = YELLOW_FILL
                        audit_log.append({"日期": date_val, "項目": cell_val, "異常": f"❌ 與「{core_ingredient}」相關主料重複"})
                    seen_ingredients[core_ingredient] = r_idx

    wb.save(output)
    return audit_log, output.getvalue()

# --- Streamlit UI ---
st.title("🛡️ 林口康橋菜單合約稽核系統")
st.markdown("### 本系統將產出「標註異常顏色」的 Excel 檔供您回傳廠商")

file = st.file_uploader("👉 請上傳原始菜單 (.xlsx)", type=["xlsx"])

if file:
    with st.spinner("正在根據《校內菜單審閱原則》深度稽核中..."):
        logs, final_excel = process_and_mark_menu(file)
        
        if logs:
            st.error(f"🚩 偵測到 {len(logs)} 項異常！")
            st.download_button(
                label="📥 下載標註完成的 Excel (回傳廠商用)",
                data=final_excel,
                file_name=f"審核結果_{file.name}",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.table(pd.DataFrame(logs))
        else:
            st.success("🎉 經座標深度掃描，未發現明顯違規。")
