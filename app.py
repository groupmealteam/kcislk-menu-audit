import streamlit as st
import pandas as pd
import re
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import PatternFill

st.set_page_config(page_title="林口康橋菜單審核-標註版", layout="wide")

# --- 核心規範 (根據您的手冊) ---
EXEMPT = ["季節水果", "時令蔬菜", "履歷蔬菜", "有機蔬菜", "Fruit", "Vegetable"]
SPICY_DAYS = ["週一", "週二", "週四"]

def clean_chinese(text):
    if pd.isna(text): return ""
    # 只留中文，排除英文翻譯干擾
    return "".join(re.findall(r'[\u4e00-\u9fa5]+', str(text)))

def run_audit_and_mark(uploaded_file):
    all_sheets = pd.read_excel(uploaded_file, sheet_name=None, header=None)
    output = BytesIO()
    wb = load_workbook(uploaded_file)
    
    # 設定顏色：紅色(禁辣)、黃色(食材重複)
    red_fill = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")
    yellow_fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
    
    audit_summary = []

    for sheet_name, df in all_sheets.items():
        df = df.fillna("")
        ws = wb[sheet_name]
        
        # 1. 自動定位關鍵列索引
        date_row = None
        main_dish_rows = [] # 可能有輕食A、輕食B
        
        for i, row in df.iterrows():
            row_str = "".join([str(c) for c in row])
            if date_row is None and re.search(r"\d{1,2}/\d{1,2}", row_str):
                date_row = i
            if "主食" in str(row[1]) or "副菜" in str(row[1]):
                main_dish_rows.append(i)
        
        if date_row is None: continue

        # 2. 逐欄 (日期) 審核
        for col_idx in range(len(df.columns)):
            date_val = str(df.iloc[date_row, col_idx])
            if not re.search(r"\d{1,2}/\d{1,2}", date_val): continue
            
            # 取得星期
            day_text = str(df.iloc[date_row+1, col_idx])
            is_spicy_day = any(d in day_text for d in SPICY_DAYS)
            
            # 3. 檢查重複與禁辣 (只看主食與副菜列)
            seen_in_day = {}
            for r_idx in main_dish_rows:
                cell_content = str(df.iloc[r_idx, col_idx]).strip()
                if not cell_content or any(ex in cell_content for ex in EXEMPT): continue
                
                # --- 禁辣判讀 ---
                if is_spicy_day and ("🌶️" in cell_content or "●" in cell_content):
                    ws.cell(row=r_idx+1, column=col_idx+1).fill = red_fill
                    audit_summary.append({"日期": date_val, "項目": cell_content, "原因": "🚫禁辣日標記"})

                # --- 重複判讀 (中文字比對) ---
                core = clean_chinese(cell_content)[:2]
                if len(core) >= 2:
                    if core in seen_in_day:
                        # 標註當前格與重複格
                        ws.cell(row=r_idx+1, column=col_idx+1).fill = yellow_fill
                        prev_r = seen_in_day[core]
                        ws.cell(row=prev_r+1, column=col_idx+1).fill = yellow_fill
                        audit_summary.append({"日期": date_val, "項目": f"{cell_content} 重複", "原因": f"❌食材與同日其他餐點重複"})
                    seen_in_day[core] = r_idx

    wb.save(output)
    return audit_summary, output.getvalue()

# --- UI ---
st.title("🛡️ 林口康橋國際學校菜單審核")
st.info("本系統會產出「自動標註顏色」的 Excel 檔。紅色代表禁辣違規，黃色代表食材重複。")

file = st.file_uploader("請上傳您的 2.3月試營運菜單 (xlsx)", type=["xlsx"])

if file:
    try:
        summary, processed_file = run_audit_and_mark(file)
        if summary:
            st.error(f"🚩 偵測到 {len(summary)} 項異常，請下載檔案查看顏色標註：")
            st.table(pd.DataFrame(summary))
            st.download_button(label="📥 下載標色版 Excel 進行修改", data=processed_file, file_name="菜單修正導航版.xlsx")
        else:
            st.success("🎉 完美！經系統掃描，未發現任何違規。")
    except Exception as e:
        st.warning(f"解析發生錯誤：{e}。請確保 Excel 格式未變動。")
