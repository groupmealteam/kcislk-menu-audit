import streamlit as st
import pandas as pd

st.set_page_config(page_title="康橋菜單合約精準審核系統", layout="wide")

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

st.sidebar.header("🏢 廠商模式選擇")
mode = st.sidebar.selectbox("請手動選擇或讓系統自動偵測", ["自動偵測", "新北食品", "暖禾輕食"])

def get_rule_by_sheet(sheet_name):
    for vendor, r in RULES.items():
        if any(key in sheet_name for key in r["keywords"]):
            return vendor, r
    return "未知", None

def audit_logic(df, rule):
    df = df.fillna("").astype(str)
    report = {"err": [], "info": []}
    
    # 尋找日期列
    day_row = next((i for i, r in df.iterrows() if any("週" in cell for cell in r)), None)
    if day_row is None: return {"err": ["❌ 找不到日期列"], "info": []}

    for col_idx in range(len(df.columns)):
        day_name = df.iloc[day_row, col_idx].strip()
        if any(d in day_name for d in ["週一", "週二", "週三", "週四", "週五"]):
            content = "".join(df.iloc[:, col_idx])
            
            # 1. 禁辣檢查 (週一、二、四)
            if any(d in day_name for d in rule["spicy_days"]) and ("🌶️" in content or "●" in content):
                report["err"].append(f"❌ {day_name}：合約禁辣日出現辣味標示")
            
            # 2. 魚類規格檢查
            found = [f for f in rule["fish_specs"] if f in content]
            if found:
                report["info"].append(f"✅ {day_name} 合約魚類：{', '.join(found)}")
            
            # 3. 油炸/加工統計
            f_cnt = content.count("◎")
            p_cnt = content.count("△")
            report["info"].append(f"📊 {day_name}：油炸 {f_cnt} | 加工 {p_cnt}")

    return report

st.title("🍱 康橋菜單合約自動化審核")
up = st.file_uploader("請上傳您的 Excel 菜單", type=["xlsx"])

if up:
    sheets = pd.read_excel(up, sheet_name=None, header=None)
    for name, df in sheets.items():
        vendor, r = get_rule_by_sheet(name) if mode == "自動偵測" else (mode, RULES[mode])
        
        st.subheader(f"📄 分頁：{name} (廠商識別：{vendor})")
        if r:
            res = audit_logic(df, r)
            for e in res["err"]: st.error(e)
            if not res["err"]: st.success("🎉 初步審核符合合約規範")
            with st.expander("查看判讀細節"):
                for i in res["info"]: st.write(i)
        else:
            st.warning("⚠️ 此分頁名稱不含指定關鍵字，跳過自動審核。")
