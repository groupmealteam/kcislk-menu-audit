import streamlit as st
import pandas as pd
import re
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import PatternFill

st.set_page_config(page_title="林口康橋菜單終極稽核", layout="wide")

# 原則標註顏色
RED_FILL = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid") # 原則四
YELLOW_FILL = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid") # 原則九

def clean_pure_dish_name(text):
    """移除日期、符號，僅保留核心菜名"""
    if pd.isna(text) or re.search(r"\d{2,4}", str(text)): return ""
    return "".join(re.findall(r'[\u4e00-\u9fa5]+', str(text)))

def run_final_audit(uploaded_file):
    wb = load_workbook(uploaded_file)
    all_sheets = pd.read_excel(uploaded_file, sheet_name=None, header=None)
    output = BytesIO()
    final_logs = []

    for sheet_name, df in all_sheets.items():
        df = df.fillna("")
        ws = wb[sheet_name]
        
        # 1. 定位日期行與主要餐點行 (Column B 必須含「主食/副菜」)
        target_rows = [i for i, row in df.iterrows() if any(k in str(row[1]) for k in ["主食", "副菜", "主菜"])]
        date_row = next((i for i, row in df.iterrows() if any(re.search(r"\d{1,2}/\d{1,2}", str(c)) for c in row)), None)
        
        if date_row is None or not target_rows: continue

        # 2. 逐欄 (日期) 審核
        for col in range(2, len(df.columns)):
            date_val = str(df.iloc[date_row, col])
            day_val = str(df.iloc[date_row+1, col]) if (date_row+1) < len(df) else ""
            if not re.search(r"\d{1,2}/\d{1,2}", date_val): continue
            
            # 原則四：禁辣日判定
            is_restricted = any(d in day_val for d in ["週一", "週二", "週四"])
            
            seen_today = {}
            for r_idx in target_rows:
                cell_val = str(df.iloc[r_idx, col]).strip()
                if not cell_val or len(cell_val) < 2: continue

                # 判定：禁辣違規 (標紅)
                if is_restricted and ("●" in cell_val or "🌶️" in cell_val):
                    ws.cell(row=r_idx+1, column=col+1).fill = RED_FILL
                    final_logs.append({"日期": date_val, "項目": cell_val, "異常": "🚫 禁辣日違規 (原則四)"})

                # 判定：同日食材重複 (標黃)
                dish_core = clean_pure_dish_name(cell_val)[:2]
                if len(dish_core) >= 2:
                    if dish_core in seen_today:
                        ws.cell(row=r_idx+1, column=col+1).fill = YELLOW_FILL
                        prev_r = seen_today[dish_core]
                        ws.cell(row=prev_r+1, column=col+1).fill = YELLOW_FILL
                        final_logs.append({"日期": date_val, "項目": cell_val, "異常": f"❌ 食材重複: {dish_core} (原則九)"})
                    seen_today[dish_core] = r_idx

    wb.save(output)
    return final_logs, output.getvalue()

# --- 介面 ---
st.title("🛡️ 林口康橋菜單審核 (回傳檔案專用版)")
st.warning("本版本已排除日期重複、週一重複等雜訊，僅標註真正的原則違規項目。")

up = st.file_uploader("👉 請上傳原始菜單 (xlsx)", type=["xlsx"])

if up:
    logs, file_bytes = run_final_audit(up)
    if logs:
        st.error(f"🚩 發現 {len(logs)} 項實質違規，請務必下載下方檔案：")
        st.download_button("📥 下載審核標註檔 (回傳廠商用)", file_bytes, f"審核建議_{up.name}", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.table(pd.DataFrame(logs))
    else:
        st.success("🎉 本份菜單符合原則。")
