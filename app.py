import streamlit as st
from datetime import datetime
import os
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image

# إعداد الصفحة
st.set_page_config(page_title="منصة إيداع المذكرات", page_icon="📚", layout="centered")

# تحديد تاريخ نهاية الإيداع

deadline = datetime(2025, 9, 15, 23, 59)


if datetime.now() > deadline:
    st.error("❌ انتهت فترة إيداع المذكرات. الرجاء الاتصال بالإدارة لمزيد من المعلومات.")
    st.stop()

# إعداد الاتصال بـ Google Sheets و Google Drive
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
info = st.secrets["service_account"]
credentials = Credentials.from_service_account_info(info, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)
sheets_service = build('sheets', 'v4', credentials=credentials)

SPREADSHEET_ID = "1Ycx-bUscF7rEpse4B5lC4xCszYLZ8uJyPJLp6bFK8zo"
DRIVE_FOLDER_ID = "1TfhvUA9oqvSlj9TuLjkyHi5xsC5svY1D"

@st.cache_data(ttl=300)
def load_data():
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="Feuille 1!A1:Z1000"
        ).execute()
        values = result.get('values', [])
        if not values:
            st.error("❌ لا توجد بيانات في الشيت.")
            st.stop()
        df = pd.DataFrame(values[1:], columns=values[0])
        return df
    except Exception as e:
        st.error(f"❌ خطأ في تحميل البيانات من Google Sheets: {e}")
        st.stop()

def is_already_submitted(note_number):
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="Feuille 1!A1:Z1000"
        ).execute()
        values = result.get('values', [])
        df = pd.DataFrame(values[1:], columns=values[0])
        memo = df[df["رقم المذكرة"].astype(str).str.strip() == str(note_number).strip()]
        if memo.empty:
            return False, None
        deposit_status = memo.iloc[0]["تم الإيداع"]
        submission_date = memo.iloc[0]["تاريخ الإيداع"]
        if (isinstance(deposit_status, str) and deposit_status.strip() == "نعم") or \
           (isinstance(submission_date, str) and submission_date.strip() != ""):
            return True, submission_date
        return False, None
    except Exception as e:
        st.error(f"❌ خطأ في التحقق من حالة الإيداع: {e}")
        return False, None

def update_submission_status(note_number):
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="Feuille 1!A1:Z1000"
        ).execute()
        values = result.get('values', [])
        df = pd.DataFrame(values[1:], columns=values[0])
        row_idx = df[df["رقم المذكرة"].astype(str).str.strip() == str(note_number).strip()].index
        if row_idx.empty:
            st.error("❌ رقم المذكرة غير موجود في الشيت أثناء التحديث.")
            return False
        idx = row_idx[0] + 2
        col_names = df.columns.tolist()
        deposit_col = col_names.index("تم الإيداع") + 1
        date_col = col_names.index("تاريخ الإيداع") + 1
        updates = {
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range": f"Feuille 1!{chr(64+deposit_col)}{idx}", "values": [["نعم"]]},
                {"range": f"Feuille 1!{chr(64+date_col)}{idx}", "values": [[datetime.now().strftime('%Y-%m-%d %H:%M')]]},
            ]
        }
        sheets_service.spreadsheets().values().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body=updates
        ).execute()
        return True
    except Exception as e:
        st.error(f"❌ فشل تحديث حالة الإيداع: {e}")
        return False

def upload_to_drive(filepath, note_number):
    try:
        new_name = f"memoire_{note_number}.pdf"
        media = MediaFileUpload(filepath, mimetype='application/pdf', resumable=True)
        file_metadata = {
            'name': new_name,
            'parents': [DRIVE_FOLDER_ID]
        }
        uploaded = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        return uploaded.get('id')
    except Exception as e:
        st.error(f"❌ خطأ في رفع الملف إلى Google Drive: {e}")
        return None

# واجهة المستخدم
st.markdown("""<style>/* ... نفس التنسيقات السابقة ... */</style>""", unsafe_allow_html=True)
logo = Image.open("logo.png")
st.image(logo, width=70)
st.markdown("<h1 style='text-align: center;'>📥 منصة إيداع مذكرات التخرج</h1>", unsafe_allow_html=True)
st.markdown("<div style='text-align: center;'>جامعة محمد البشير الإبراهيمي - برج بوعريريج<br>كلية الحقوق والعلوم السياسية</div>", unsafe_allow_html=True)

df = load_data()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "file_uploaded" not in st.session_state:
    st.session_state.file_uploaded = False

# التحقق وتسجيل الدخول ورفع الملفات (نفس المنطق الموجود في كودك الحالي)
# ...

