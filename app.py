import streamlit as st
import pandas as pd
import re
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import PatternFill

st.set_page_config(page_title="林口康橋菜單審核結果回傳", layout="wide")

# 規範設定
SPICY_DAYS = ["週一", "週二", "週四"]
RED_FILL = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid") # 禁辣紅
YELLOW_FILL = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid") # 重複黃

def clean_cn(text):
    return "".join(re.findall(r'[\u4e00-\u9fa5]+', str(text)))

def process_excel(uploaded_file):
    # 讀取分析用
    all_sheets = pd.read_excel(uploaded_file, sheet_name=None, header=None)
    # 標色回傳用
    wb = load_workbook(uploaded_file)
    output = BytesIO()
    audit_summary = []

    for sheet_name, df in all_sheets.items():
        df = df.fillna("")
        ws = wb[sheet_name]
        
        # 1. 定位日期與主副食列
        date_row = None
        target_rows = [] # 只看主食和副菜這兩列，避開食材內容的雜訊
        for i, row in df.iterrows():
            row_str = "".join([str(c) for c in row])
            if date_row is None and re.search(r"\d{1,2}/\d{1,2}", row_str): date_row = i
            if any(k in str(row[1]) for k in ["主食", "副菜"]): target_rows.append(i)
        
        if date_row is None: continue

        # 2. 逐欄 (日期) 審核
        for col_idx in range(2, len(df.columns)):
            date_label = str(df.iloc[date_row, col_idx])
            day_label = str(df.iloc[date_row+1, col_idx]) if date_row+1 < len(df) else ""
            
            if not re.search(r"\d{1,2}/\d{1,2}", date_label): continue
            
            # 檢查禁辣 (週一二四)
            is_spicy_day = any(d in day_label for d in SPICY_DAYS)
            
            seen_cores = {}
            for r_idx in target_rows:
                cell_val = str(df.iloc[r_idx, col_idx]).strip()
                if not cell_val or "時令蔬菜" in cell_val or "履歷蔬菜" in cell_val: continue
                
                # --- A. 禁辣判定 ---
                if is_spicy_day and ("●" in cell_val or "🌶️" in cell_val):
                    ws.cell(row=r_idx+1, column=col_idx+1).fill = RED_FILL
                    audit_summary.append({"日期": date_label, "問題": f"🚫禁辣日違規: {cell_val}"})
                
                # --- B. 食材重複判定 (當天垂直比對) ---
                core = clean_cn(cell_val)[:2]
                if len(core) >= 2:
                    if core in seen_cores:
                        ws.cell(row=r_idx+1, column=col_idx+1).fill = YELLOW_FILL
                        ws.cell(row=seen_cores[core]+1, column=col_idx+1).fill = YELLOW_FILL
                        audit_summary.append({"日期": date_label, "問題": f"❌食材重複: {cell_val}"})
                    seen_cores[core] = r_idx

    wb.save(output)
    return audit_summary, output.getvalue()

# --- 網頁介面 ---
st.title("🛡️ 林口康橋菜單自動審核系統")
file = st.file_uploader("👉 請上傳原始菜單 Excel (.xlsx)", type=["xlsx"])

if file:
    summary, processed_data = process_excel(file)
    if summary:
        st.error(f"🚩 偵測到 {len(summary)} 處異常。")
        st.write("請點擊下方按鈕下載「已標註顏色」的檔案回傳給廠商。")
        st.download_button(
            label="📥 下載審核後的標註檔案",
            data=processed_data,
            file_name=f"審核建議_{file.name}",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.table(pd.DataFrame(summary))
    else:
        st.success("🎉 審核完成！這份菜單沒有問題。")
