import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# --- إعداد الاتصال بـ Google Sheets و Google Drive ---
SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive']

info = st.secrets["service_account"]
credentials = Credentials.from_service_account_info(info, scopes=SCOPES)

# خدمة gspread للقراءة فقط (باستخدام credentials)
gc = gspread.authorize(credentials)

# خدمات Google APIs (Drive و Sheets) للرفع والتحديث
drive_service = build('drive', 'v3', credentials=credentials)
sheets_service = build('sheets', 'v4', credentials=credentials)

# --- معرف الشيت ومجلد الدرايف ---
SPREADSHEET_ID = "1Ycx-bUscF7rEpse4B5lC4xCszYLZ8uJyPJLp6bFK8zo"
DRIVE_FOLDER_ID = "1TfhvUA9oqvSlj9TuLjkyHi5xsC5svY1D"

# --- تحميل البيانات من Google Sheets ---
@st.cache_data(ttl=300)
def load_data():
    try:
        sheet = gc.open_by_key(SPREADSHEET_ID).worksheet("Feuille 1")
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        return df, sheet
    except Exception as e:
        st.error(f"❌ خطأ في تحميل البيانات من Google Sheets: {e}")
        st.stop()

# --- تحديث حالة الإيداع في Google Sheets باستخدام Sheets API ---
def update_submission_status(sheets_service, spreadsheet_id, note_number):
    try:
        # للحصول على البيانات ولتحديد الصف والعمود
        sheet = gc.open_by_key(spreadsheet_id).worksheet("Feuille 1")
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        # البحث عن الصف الخاص برقم المذكرة
        row_idx = df[df["رقم المذكرة"].astype(str).str.strip() == str(note_number).strip()].index
        if row_idx.empty:
            st.error("❌ رقم المذكرة غير موجود في الشيت أثناء التحديث.")
            return False
        
        idx = row_idx[0] + 2  # تعويض صف العنوان وبدء العد من 1
        
        # تحديد الأعمدة
        col_deposit = df.columns.get_loc("تم الإيداع") + 1
        col_date = df.columns.get_loc("تاريخ الإيداع") + 1

        # بناء نطاقات الخلايا حسب الأعمدة والصفوف
        range_deposit = f"Feuille 1!{chr(64+col_deposit)}{idx}"
        range_date = f"Feuille 1!{chr(64+col_date)}{idx}"

        # تحديث "تم الإيداع"
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_deposit,
            valueInputOption="RAW",
            body={"values": [["نعم"]]}
        ).execute()

        # تحديث "تاريخ الإيداع"
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_date,
            valueInputOption="RAW",
            body={"values": [[datetime.now().strftime("%Y-%m-%d %H:%M")]]}
        ).execute()

        return True
    except Exception as e:
        st.error(f"❌ فشل تحديث حالة الإيداع: {e}")
        return False

# --- رفع ملف PDF إلى Google Drive ---
def upload_to_drive(file, filename):
    try:
        file_stream = io.BytesIO(file.read())
        media = MediaIoBaseUpload(file_stream, mimetype='application/pdf')
        file_metadata = {
            'name': filename,
            'parents': [DRIVE_FOLDER_ID]
        }
        uploaded = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return uploaded.get('id')
    except Exception as e:
        st.error(f"❌ خطأ في رفع الملف إلى Google Drive: {e}")
        return None

# --- تهيئة الصفحة ---
st.set_page_config(page_title="إيداع مذكرات التخرج", page_icon="📥", layout="centered")

st.markdown("<h1 style='text-align:center; color:#4B8BBE;'>📥 منصة إيداع مذكرات التخرج</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; font-size:18px;'>جامعة برج بوعريريج</p>", unsafe_allow_html=True)
st.markdown("---")

# --- تحميل بيانات الطلبة ---
df, worksheet = load_data()

# --- إدارة حالة الجلسة ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "file_uploaded" not in st.session_state:
    st.session_state.file_uploaded = False

# --- واجهة التحقق ---
if not st.session_state.authenticated:
    note_number = st.text_input("🔢 أدخل رقم المذكرة:", key="note_input")
    password = st.text_input("🔐 أدخل كلمة السر:", type="password", key="pass_input")

    if st.button("✅ تحقق", key="btn_check"):
        if not note_number or not password:
            st.warning("⚠️ الرجاء إدخال رقم المذكرة وكلمة السر.")
        else:
            memo_info = df[df["رقم المذكرة"].astype(str).str.strip() == str(note_number).strip()]
            if memo_info.empty:
                st.error("❌ رقم المذكرة غير موجود.")
            elif memo_info.iloc[0]["كلمة السر"] != password:
                st.error("❌ كلمة السر غير صحيحة.")
            else:
                st.session_state.authenticated = True
                st.session_state.note_number = note_number
                st.success("✅ تم التحقق بنجاح، يمكنك رفع المذكرة الآن.")

else:
    st.success(f"✅ مرحبًا! رقم المذكرة: {st.session_state.note_number}")
    uploaded_file = st.file_uploader("📤 رفع ملف المذكرة (PDF فقط)", type="pdf", key="file_uploader")

    if uploaded_file and not st.session_state.file_uploaded:
        with st.spinner("⏳ جاري رفع الملف..."):
            file_id = upload_to_drive(uploaded_file, uploaded_file.name)
            if file_id:
                updated = update_submission_status(sheets_service, SPREADSHEET_ID, st.session_state.note_number)
                if updated:
                    st.success("✅ تم إيداع المذكرة وتحديث الحالة بنجاح!")
                    st.markdown(f"📎 معرف الملف على Drive: `{file_id}`")
                    st.session_state.file_uploaded = True
                else:
                    st.error("❌ فشل تحديث حالة الإيداع في الشيت.")
            else:
                st.error("❌ فشل رفع الملف.")

    elif st.session_state.file_uploaded:
        st.info("📌 تم رفع الملف وتحديث الحالة مسبقًا.")

    if st.button("🔄 إنهاء", key="btn_reset"):
        for key in ["authenticated", "file_uploaded", "note_number"]:
            if key in st.session_state:
                del st.session_state[key]
        st.experimental_rerun()
