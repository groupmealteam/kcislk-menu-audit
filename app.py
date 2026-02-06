import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="林口康橋菜單審核", layout="wide")

def run_audit(df):
    results = []
    # 這裡鎖定 2.3 月菜單的結構：第 5 列通常是主食，第 8 列是副菜
    # 但為了通用，我們用關鍵字定位
    main_dish_row = None
    side_dish_row = None
    for i, row in df.iterrows():
        cell_head = str(row[1]) # 第二欄通常是「主食」、「副菜」等標題
        if "主食" in cell_head: main_dish_row = i
        if "副菜" in cell_head: side_dish_row = i

    # 找到日期列
    date_row = next((i for i, r in df.iterrows() if any(re.search(r"\d{1,2}/\d{1,2}", str(c)) for c in r)), None)
    
    if date_row is None: return None

    # 遍歷每一天 (欄)
    for col in range(3, len(df.columns)): # 從第 D 欄開始是資料
        date_label = str(df.iloc[date_row, col])
        if not re.search(r"\d{1,2}/\d{1,2}", date_label): continue
        
        day_issues = []
        
        # 1. 抓取該欄位關鍵格內容
        main_dish = str(df.iloc[main_dish_row, col]) if main_dish_row else ""
        side_dish = str(df.iloc[side_dish_row, col]) if side_dish_row else ""
        
        # 2. 判讀：禁辣 (假設日期包含週二)
        if "週二" in str(df.iloc[date_row+1, col]) or "週一" in str(df.iloc[date_row+1, col]):
             if "●" in main_dish or "🌶️" in main_dish:
                 results.append({
                     "位置": f"第 {main_dish_row+1} 列", 
                     "日期": date_label,
                     "原始內容": main_dish,
                     "修正建議": "🚫 禁辣日不可提供此餐點"
                 })

        # 3. 判讀：食材重複 (主食 vs 副菜)
        m_core = "".join(re.findall(r'[\u4e00-\u9fa5]+', main_dish))[:2]
        s_core = "".join(re.findall(r'[\u4e00-\u9fa5]+', side_dish))[:2]
        if len(m_core) >=2 and m_core == s_core:
             results.append({
                 "位置": f"第 {side_dish_row+1} 列", 
                 "日期": date_label,
                 "原始內容": side_dish,
                 "修正建議": f"❌ 與主食「{m_core}」重複"
             })

    return results

# UI 部分省略，重點在於讓表格產出「位置」列
