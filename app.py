import streamlit as st
import pandas as pd
import io
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# إعداد الصفحة
st.set_page_config(page_title="منصة إيداع المذكرات", page_icon="📚", layout="centered")

# إعدادات Google
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = "1Ycx-bUscF7rEpse4B5lC4xCszYLZ8uJyPJLp6bFK8zo"
DRIVE_FOLDER_ID = "1TfhvUA9oqvSlj9TuLjkyHi5xsC5svY1D"

info = st.secrets["service_account"]
credentials = Credentials.from_service_account_info(info, scopes=SCOPES)
gc = build('sheets', 'v4', credentials=credentials)
drive_service = build('drive', 'v3', credentials=credentials)

# استدعاء بيانات من Google Sheets
@st.cache_data(ttl=300)
def load_data():
    sheet = gc.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range="Feuille 1").execute()
    values = result.get('values', [])
    if not values:
        return pd.DataFrame()
    df = pd.DataFrame(values[1:], columns=values[0])
    return df

# رفع ملف إلى Google Drive
def upload_to_drive(file, filename):
    file_stream = io.BytesIO(file.read())
    media = MediaIoBaseUpload(file_stream, mimetype='application/pdf')
    metadata = {'name': filename, 'parents': [DRIVE_FOLDER_ID]}
    file = drive_service.files().create(body=metadata, media_body=media, fields='id').execute()
    return file.get('id')

# تحديث حالة الإيداع في Google Sheets
def update_status(note_number):
    # هذه وظيفة تجريبية — يمكنك تطويرها حسب هيكلة الشيت لديك
    pass

# --- تصميم CSS لتحسين الشكل ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo&display=swap');
    html, body, [class*="css"]  {
        font-family: 'Cairo', sans-serif;
    }
    .header {
        text-align: center;
        color: #007ACC;
        margin-bottom: 20px;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        padding: 15px;
        border-radius: 8px;
        margin-top: 20px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="header">📚 منصة إيداع مذكرات التخرج</h1>', unsafe_allow_html=True)

# ---- حالة الجلسة ----
if "step" not in st.session_state:
    st.session_state.step = "login"
if "note_number" not in st.session_state:
    st.session_state.note_number = ""
if "uploaded" not in st.session_state:
    st.session_state.uploaded = False
if "file_id" not in st.session_state:
    st.session_state.file_id = ""

df = load_data()

# --- صفحة تسجيل الدخول ---
if st.session_state.step == "login":
    note_number = st.text_input("🔢 رقم المذكرة")
    password = st.text_input("🔐 كلمة السر", type="password")
    if st.button("✅ تحقق"):
        if note_number.strip() == "" or password.strip() == "":
            st.warning("⚠️ الرجاء إدخال رقم المذكرة وكلمة السر.")
        else:
            matched = df[(df["رقم المذكرة"].astype(str).str.strip() == note_number.strip()) & 
                         (df["كلمة السر"].astype(str).str.strip() == password.strip())]
            if matched.empty:
                st.error("❌ رقم المذكرة أو كلمة السر غير صحيحة.")
            else:
                st.session_state.note_number = note_number.strip()
                st.session_state.step = "upload"
                st.experimental_rerun()

# --- صفحة رفع الملف ---
elif st.session_state.step == "upload" and not st.session_state.uploaded:
    st.success(f"✅ مرحبًا! رقم المذكرة: {st.session_state.note_number}")
    uploaded_file = st.file_uploader("📤 رفع ملف المذكرة (PDF فقط)", type="pdf")

    if uploaded_file:
        with st.spinner("⏳ جاري رفع الملف..."):
            file_id = upload_to_drive(uploaded_file, f"Memoire_{st.session_state.note_number}.pdf")
            if file_id:
                # تحديث حالة الإيداع في الشيت (يمكنك تفعيل هذا الجزء)
                # update_status(st.session_state.note_number)
                st.session_state.uploaded = True
                st.session_state.file_id = file_id
                st.experimental_rerun()
            else:
                st.error("❌ فشل رفع الملف.")

# --- صفحة النجاح ---
elif st.session_state.uploaded:
    st.markdown(f'<div class="success-box">✅ تم إيداع المذكرة بنجاح!<br>📎 معرف الملف على Drive: <code>{st.session_state.file_id}</code></div>', unsafe_allow_html=True)
    if st.button("⬅️ إنهاء"):
        st.session_state.step = "login"
        st.session_state.note_number = ""
        st.session_state.uploaded = False
        st.session_state.file_id = ""
        st.experimental_rerun()
