import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# إعداد الاتصال بـ Google Sheets و Google Drive
SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive']
info = st.secrets["service_account"]
credentials = Credentials.from_service_account_info(info, scopes=SCOPES)
gc = gspread.authorize(credentials)
drive_service = build('drive', 'v3', credentials=credentials)

# إعداد معرف الشيت ومجلد الدرايف
SPREADSHEET_ID = "1Ycx-bUscF7rEpse4B5lC4xCszYLZ8uJyPJLp6bFK8zo"
DRIVE_FOLDER_ID = "YOUR_FOLDER_ID_HERE"  # ضع هنا معرف مجلد Drive الذي تُرفع فيه المذكرات

# تحميل البيانات من Google Sheets
@st.cache_data
def load_data():
    worksheet = gc.open_by_key(SPREADSHEET_ID).sheet1
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    return df, worksheet

# تحديث حالة وتاريخ الإيداع
def update_submission_status(worksheet, note_number):
    df = pd.DataFrame(worksheet.get_all_records())
    row_index = df[df["رقم المذكرة"].astype(str).str.strip() == str(note_number).strip()].index
    if not row_index.empty:
        idx = row_index[0] + 2  # الصف الأول للعناوين
        worksheet.update_cell(idx, df.columns.get_loc("تم الإيداع") + 1, "نعم")
        worksheet.update_cell(idx, df.columns.get_loc("تاريخ الإيداع") + 1, datetime.now().strftime("%Y-%m-%d %H:%M"))

# رفع ملف إلى Google Drive
def upload_to_drive(file, filename):
    file_stream = io.BytesIO(file.read())
    media = MediaIoBaseUpload(file_stream, mimetype='application/pdf')
    file_metadata = {
        'name': filename,
        'parents': [DRIVE_FOLDER_ID]
    }
    uploaded = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return uploaded.get('id')

# واجهة التطبيق
st.title("📥 منصة إيداع مذكرات التخرج")
st.markdown("جامعة برج بوعريريج")

# تحميل البيانات
try:
    df, worksheet = load_data()
except Exception as e:
    st.error(f"فشل تحميل البيانات من Google Sheets: {e}")
    st.stop()

# حالة التحقق
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "file_uploaded" not in st.session_state:
    st.session_state.file_uploaded = False

if not st.session_state.authenticated:
    note_number = st.text_input("🔢 أدخل رقم المذكرة:")
    password = st.text_input("🔐 أدخل كلمة السر:", type="password")

    if st.button("✅ تحقق"):
        if note_number and password:
            memo_info = df[df["رقم المذكرة"].astype(str).str.strip() == str(note_number).strip()]
            if not memo_info.empty:
                if memo_info.iloc[0]["كلمة السر"] == password:
                    st.session_state.authenticated = True
                    st.session_state.note_number = note_number
                    st.success("تم التحقق بنجاح، يمكنك رفع المذكرة الآن")
                else:
                    st.error("❌ كلمة السر غير صحيحة")
            else:
                st.error("❌ رقم المذكرة غير موجود")
        else:
            st.warning("الرجاء إدخال رقم المذكرة وكلمة السر")
else:
    st.success("تم التحقق بنجاح، يمكنك رفع المذكرة الآن")
    uploaded_file = st.file_uploader("📤 رفع ملف المذكرة (PDF فقط)", type="pdf")

    if uploaded_file is not None and not st.session_state.file_uploaded:
        try:
            file_id = upload_to_drive(uploaded_file, uploaded_file.name)
            update_submission_status(worksheet, st.session_state.note_number)
            st.session_state.file_uploaded = True
            st.success("✅ تم إيداع المذكرة بنجاح!")
            st.markdown(f"📎 معرف الملف على Drive: `{file_id}`")
        except Exception as e:
            st.error(f"فشل رفع الملف أو تحديث الحالة: {e}")

    elif st.session_state.file_uploaded:
        st.info("📌 تم رفع الملف وتحديث الحالة مسبقًا.")

    if st.button("🔄 إنهاء"):
        st.session_state.authenticated = False
        st.session_state.file_uploaded = False
        st.experimental_rerun()
