import streamlit as st
import pandas as pd
import re
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import PatternFill

# 設定標色顏色 (符合原則四與原則九)
RED_FILL = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid") # 紅色：禁辣日違規
YELLOW_FILL = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid") # 黃色：食材重複

def clean_dish_name(text):
    """提取中文字主料，排除日期與翻譯雜訊"""
    if pd.isna(text) or re.search(r"\d{2,4}", str(text)): return ""
    return "".join(re.findall(r'[\u4e00-\u9fa5]+', str(text)))

def run_audit_logic(file):
    wb = load_workbook(file)
    all_sheets = pd.read_excel(file, sheet_name=None, header=None)
    audit_summary = []
    output = BytesIO()

    for sheet_name, df in all_sheets.items():
        df = df.fillna("")
        ws = wb[sheet_name]
        
        # 定位日期行與主要餐點行 (Column B 含「主食/副菜」)
        target_rows = [i for i, row in df.iterrows() if any(k in str(row[1]) for k in ["主食", "副菜", "主菜"])]
        date_row = next((i for i, row in df.iterrows() if any(re.search(r"\d{1,2}/\d{1,2}", str(c)) for c in row)), None)
        
        if date_row is None: continue

        for col in range(2, len(df.columns)):
            date_val = str(df.iloc[date_row, col])
            day_val = str(df.iloc[date_row+1, col]) if (date_row+1) < len(df) else ""
            if not re.search(r"\d{1,2}/\d{1,2}", date_val): continue
            
            # 原則四：禁辣日 (週一、二、四)
            is_restricted = any(d in day_val for d in ["週一", "週二", "週四"])
            seen_today = {}

            for r_idx in target_rows:
                cell_val = str(df.iloc[r_idx, col]).strip()
                if not cell_val or len(cell_val) < 2: continue

                # 判定：禁辣違規 (原則四)
                if is_restricted and ("●" in cell_val or "🌶️" in cell_val):
                    ws.cell(row=r_idx+1, column=col+1).fill = RED_FILL
                    audit_summary.append({"日期": date_val, "違規項目": cell_val, "原因": "🚫禁辣日標示違規"})

                # 判定：食材重複 (原則九)
                core = clean_dish_name(cell_val)[:2]
                if len(core) >= 2:
                    if core in seen_today:
                        ws.cell(row=r_idx+1, column=col+1).fill = YELLOW_FILL
                        prev_r = seen_today[core]
                        ws.cell(row=prev_r+1, column=col+1).fill = YELLOW_FILL
                        audit_summary.append({"日期": date_val, "違規項目": cell_val, "原因": f"❌食材重複: {core}"})
                    seen_today[core] = r_idx

    wb.save(output)
    return audit_summary, output.getvalue()

# --- 網頁介面 ---
st.title("🛡️ 林口康橋菜單審核回傳系統")
st.info("系統將標註異常顏色：紅色(禁辣違規)、黃色(食材重複)。")

up_file = st.file_uploader("請上傳您的 2.3月試營運菜單 (xlsx)", type=["xlsx"])

if up_file:
    with st.spinner("稽核中..."):
        logs, final_excel = run_audit_logic(up_file)
        if logs:
            st.error(f"🚩 偵測到 {len(logs)} 項實質違規項目。")
            st.download_button(
                label="📥 下載審核標註檔 (回傳廠商用)",
                data=final_excel,
                file_name=f"審核建議_{up_file.name}",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.table(pd.DataFrame(logs))
        else:
            st.success("🎉 經系統稽核，本份菜單符合規範。")
