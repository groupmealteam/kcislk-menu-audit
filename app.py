import streamlit as st
import pandas as pd

st.set_page_config(page_title="康橋菜單審核專用", layout="wide")
st.title("🍱 康橋校內菜單自動審核系統")

# 這裡就是那個「超級掃描儀」的邏輯
def 執行審核(df):
    # 把整張表所有格子變成一串長文字
    全部內容 = df.astype(str).values.flatten()
    文字串 = "".join(全部內容).replace("\n", "").replace(" ", "")
    
    錯誤 = []
    通過 = []

    # 1. 數符號：◎(炸) 跟 △(加工)
    炸 = 文字串.count("◎")
    加工 = 文字串.count("△")
    if 炸 > 1: 錯誤.append(f"❌ 違規：油炸(◎)一週出現 {炸} 次 (限1次)")
    if 加工 > 1: 錯誤.append(f"❌ 違規：加工品(△)一週出現 {加工} 次 (限1次)")

    # 2. 抓辣椒：● 跟 🌶️
    if "●" in 文字串 or "🌶️" in 文字串:
        if any(d in 文字串 for d in ["週一", "週二", "週四"]):
            錯誤.append("❌ 禁忌：週一/二/四 出現辣味標示(●/🌶️)，請確認晚餐。")

    # 3. 找高級魚
    魚類清單 = ["鬼頭刀", "白帶魚", "小卷", "鮭魚", "扁鱈", "鮪魚", "現撈小卷"]
    找到的魚 = [f for f in 魚類清單 if f in 文字串]
    if not 找到的魚:
        錯誤.append("❌ 缺項：沒看到高級魚類 (如鬼頭刀、白帶魚等)")
    else:
        通過.append(f"✅ 已配置魚類：{', '.join(找到的魚)}")

    return 錯誤, 通過

# 網頁畫面
檔案 = st.file_uploader("請上傳您的 115 學年 Excel 菜單", type=["xlsx"])

if 檔案:
    try:
        # 讀取 Excel 裡面所有的分頁 (2月, 3月...)
        所有分頁 = pd.read_excel(檔案, sheet_name=None)
        for 分頁名稱, 內容 in 所有分頁.items():
            st.subheader(f"📊 正在審核：{分頁名稱}")
            錯誤清單, 通過清單 = 執行審核(內容)
            
            if 錯誤清單:
                for e in 錯誤清單: st.error(e)
            else:
                st.success(f"🎉 分頁 {分頁名稱} 基礎檢查通過！")
            
            for t in 通過清單: st.info(t)
            st.divider()
    except Exception as e:
        st.error(f"檔案讀不到，請確定是 Excel 檔喔！錯誤原因：{e}")
