import streamlit as st
import pandas as pd
import re
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import PatternFill

# 設定標色顏色 (符合原則四與原則九)
RED_FILL = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid") # 紅色：禁辣/標示違規
YELLOW_FILL = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid") # 黃色：食材重複

def clean_dish_core(text):
    if pd.isna(text): return ""
    # 僅抓取中文字，排除符號與日期干擾
    return "".join(re.findall(r'[\u4e00-\u9fa5]+', str(text)))

def audit_process(file):
    wb = load_workbook(file)
    summary = []
    
    # 讀取分析用 DataFrame
    all_sheets = pd.read_excel(file, sheet_name=None, header=None)
    
    for sheet_name, df in all_sheets.items():
        ws = wb[sheet_name]
        df = df.fillna("")
        
        # 1. 搜尋日期列 (座標定位)
        date_row = None
        for i, row in df.iterrows():
            if any(re.search(r"\d{1,2}/\d{1,2}", str(c)) for c in row):
                date_row = i
                break
        
        # 2. 鎖定主副食列 (原則二：判斷主副食整體性)
        dish_rows = [i for i, row in df.iterrows() if any(k in str(row[1]) for k in ["主食", "副菜", "主菜"])]
        
        if date_row is None: continue

        # 3. 逐日掃描
        for col in range(2, len(df.columns)):
            date_val = str(df.iloc[date_row, col])
            day_val = str(df.iloc[date_row+1, col]) if (date_row+1) < len(df) else ""
            
            if not re.search(r"\d{1,2}/\d{1,2}", date_val): continue
            
            # 原則四：禁辣日 (週一二四)
            is_restricted = any(d in day_val for d in ["週一", "週二", "週四"])
            seen_today = {}

            for r_idx in dish_rows:
                cell_val = str(df.iloc[r_idx, col]).strip()
                if not cell_val or any(ex in cell_val for ex in ["季節", "時令"]): continue
                
                # --- A. 標註禁辣違規 (原則四) ---
                if is_restricted and ("●" in cell_val or "🌶️" in cell_val):
                    ws.cell(row=r_idx+1, column=col+1).fill = RED_FILL
                    summary.append({"日期": date_val, "違規項目": cell_val, "原因": "禁辣日標示違規"})

                # --- B. 標註食材重複 (原則九) ---
                core = clean_dish_core(cell_val)[:2]
                if len(core) >= 2:
                    if core in seen_today:
                        ws.cell(row=r_idx+1, column=col+1).fill = YELLOW_FILL
                        prev_r = seen_today[core]
                        ws.cell(row=prev_r+1, column=col+1).fill = YELLOW_FILL
                        summary.append({"日期": date_val, "違規項目": cell_val, "原因": f"食材重複({core})"})
                    seen_today[core] = r_idx

    output = BytesIO()
    wb.save(output)
    return summary, output.getvalue()

# --- 介面實作 ---
st.title("🛡️ 林口康橋菜單合約稽核系統 (產出修正版)")
st.write("此版本強化了 Excel 的顏色寫入功能，確保 2/3 週二等違規項會正確標色。")

uploaded_file = st.file_uploader("請上傳菜單 Excel", type=["xlsx"])

if uploaded_file:
    results, excel_data = audit_process(uploaded_file)
    if results:
        st.error(f"🚩 偵測到 {len(results)} 項異常！請下載下方檔案查看。")
        st.download_button(
            label="📥 下載標註完成之檔案 (回傳廠商)",
            data=excel_data,
            file_name=f"審核結果_{uploaded_file.name}",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.table(pd.DataFrame(results))
    else:
        st.success("🎉 經系統檢測，未發現明顯違規。")
