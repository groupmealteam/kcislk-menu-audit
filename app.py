import streamlit as st
import pandas as pd
import re
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import PatternFill

# 設定標註顏色
RED_FILL = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")    # 禁辣違規
YELLOW_FILL = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid") # 食材重複

def clean_dish(text):
    """提取中文字主料，排除日期與雜訊"""
    if pd.isna(text) or re.search(r"\d{2,4}", str(text)): return ""
    return "".join(re.findall(r'[\u4e00-\u9fa5]+', str(text)))

def run_audit(file):
    wb = load_workbook(file)
    all_sheets = pd.read_excel(file, sheet_name=None, header=None)
    results = []
    output = BytesIO()

    for sheet_name, df in all_sheets.items():
        df = df.fillna("")
        ws = wb[sheet_name]
        
        # 定位日期行與主要餐點行 (Column B 必須含「主食/副菜」)
        target_rows = [i for i, row in df.iterrows() if any(k in str(row[1]) for k in ["主食", "副菜", "主菜"])]
        date_row = next((i for i, row in df.iterrows() if any(re.search(r"\d{1,2}/\d{1,2}", str(c)) for c in row)), None)
        
        if date_row is None: continue

        for col in range(2, len(df.columns)):
            date_val = str(df.iloc[date_row, col])
            day_val = str(df.iloc[date_row+1, col]) if (date_row+1) < len(df) else ""
            if not re.search(r"\d{1,2}/\d{1,2}", date_val): continue
            
            # 原則四：禁辣日 (週一、二、四)
            is_spicy_restricted = any(d in day_val for d in ["週一", "週二", "週四"])
            seen_today = {}

            for r_idx in target_rows:
                cell_val = str(df.iloc[r_idx, col]).strip()
                if not cell_val or len(cell_val) < 2: continue

                # 1. 判定禁辣違規 (原則四)
                if is_spicy_restricted and ("●" in cell_val or "🌶️" in cell_val):
                    ws.cell(row=r_idx+1, column=col+1).fill = RED_FILL
                    results.append({"日期": date_val, "違規": cell_val, "說明": "🚫 禁辣日不得提供●餐點"})

                # 2. 判定食材重複 (原則九)
                core = clean_dish(cell_val)[:2]
                if len(core) >= 2:
                    if core in seen_today:
                        ws.cell(row=r_idx+1, column=col+1).fill = YELLOW_FILL
                        prev_r = seen_today[core]
                        ws.cell(row=prev_r+1, column=col+1).fill = YELLOW_FILL
                        results.append({"日期": date_val, "違規": cell_val, "說明": f"❌ 與同日項目「{core}」重複"})
                    seen_today[core] = r_idx

    wb.save(output)
    return results, output.getvalue()

# --- 網頁介面 ---
st.title("🛡️ 林口康橋菜單審核回傳系統")
st.markdown("### 本系統會自動產出標色 Excel 檔案供您下載")

uploaded = st.file_uploader("👉 請上傳原始菜單 (.xlsx)", type=["xlsx"])

if uploaded:
    with st.spinner("正在對齊校內審閱原則..."):
        logs, final_file = run_audit(uploaded)
        if logs:
            st.error(f"🚩 偵測到 {len(logs)} 項實質違規，請下載標註檔：")
            st.download_button(
                label="📥 下載審核標註檔 (回傳廠商修正)",
                data=final_file,
                file_name=f"審核標註_{uploaded.name}",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.table(pd.DataFrame(logs))
        else:
            st.success("🎉 審核完成，未發現違反原則之項目。")
