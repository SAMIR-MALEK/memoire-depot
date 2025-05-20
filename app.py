import streamlit as st
import pandas as pd
from datetime import datetime
import os

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- إعداد الاتصال بـ Google Sheets و Google Drive ---
SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive']

info = st.secrets["service_account"]
credentials = Credentials.from_service_account_info(info, scopes=SCOPES)

drive_service = build('drive', 'v3', credentials=credentials)
sheets_service = build('sheets', 'v4', credentials=credentials)

# --- معرف الشيت ومجلد الدرايف ---
SPREADSHEET_ID = "1Ycx-bUscF7rEpse4B5lC4xCszYLZ8uJyPJLp6bFK8zo"
DRIVE_FOLDER_ID = "1TfhvUA9oqvSlj9TuLjkyHi5xsC5svY1D"

# --- تحميل البيانات من Google Sheets ---
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

# --- التحقق مما إذا تم الإيداع مسبقًا ---
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

# --- تحديث حالة الإيداع في Google Sheets ---
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

# --- رفع ملف PDF إلى Google Drive باسم memoire_رقم_المذكرة ---
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

# --- إعداد التصميم العام ---
st.set_page_config(page_title="إيداع مذكرات التخرج", layout="centered")

st.markdown("""
    <style>
    body {
        background-color: white !important;
    }
    .app-window {
        background-color: #0b1a35;
        color: white;
        max-width: 400px;
        margin: auto;
        padding: 2rem;
        border-radius: 16px;
        box-shadow: 0 0 12px rgba(0,0,0,0.2);
    }
    .app-window h1, .app-window h2, .app-window h3 {
        color: gold;
        text-align: center;
    }
    .stTextInput > div > div > input,
    .stTextInput > div > div > textarea,
    .stFileUploader > div,
    .stButton > button {
        background-color: #1f2f4a;
        color: white;
    }
    .stButton > button:hover {
        background-color: #29446c;
        color: yellow;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="app-window">', unsafe_allow_html=True)

# --- العنوان الرئيسي ---
st.markdown("<h1>📥  منصة إيداع مذكرات التخرج السنة ماستر2</h1>", unsafe_allow_html=True)

st.markdown("<p style='text-align:center;'>جامعة محمد البشير الإبراهيمي - برج بوعريريج</p>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;'>كلية الحقوق والعلوم السياسية</p>", unsafe_allow_html=True)
st.markdown("---")

df = load_data()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "file_uploaded" not in st.session_state:
    st.session_state.file_uploaded = False

if not st.session_state.authenticated:
    note_number = st.text_input("🔢 أدخل رقم المذكرة:")
    password = st.text_input("🔐 أدخل كلمة السر:", type="password")

    if st.button("✅ تحقق"):
        if not note_number or not password:
            st.warning("⚠️ الرجاء إدخال رقم المذكرة وكلمة السر.")
        else:
            already_submitted, submission_date = is_already_submitted(note_number)
            if already_submitted:
                st.error(f"❌ المذكرة رقم {note_number} تم إيداعها بتاريخ: {submission_date}.")
            else:
                memo_info = df[df["رقم المذكرة"].astype(str).str.strip() == str(note_number).strip()]
                if memo_info.empty:
                    st.error("❌ رقم المذكرة غير موجود.")
                elif memo_info.iloc[0]["كلمة السر"] != password:
                    st.error("❌ كلمة السر غير صحيحة.")
                else:
                    st.session_state.authenticated = True
                    st.session_state.note_number = note_number
                    st.success("✅ تم التحقق بنجاح.")
else:
    st.success(f"✅ مرحبًا! رقم المذكرة: {st.session_state.note_number}")

    expected_name = f"{st.session_state.note_number}.pdf"
    st.markdown(f"### ⚠️ اسم الملف المطلوب:\n```
{expected_name}
```\n📌 الرجاء رفع الملف بهذا الاسم فقط.")

    uploaded_file = st.file_uploader("📤 رفع ملف المذكرة (PDF فقط)", type="pdf")

    if uploaded_file and not st.session_state.file_uploaded:
        filename = uploaded_file.name

        if filename != expected_name:
            st.error(f"❌ اسم الملف غير صحيح. يجب أن يكون `{expected_name}`.")
            st.stop()

        temp_filename = f"temp_memo_{st.session_state.note_number}.pdf"
        with open(temp_filename, "wb") as f:
            f.write(uploaded_file.getbuffer())

        with st.spinner("⏳ جاري رفع الملف..."):
            file_id = upload_to_drive(temp_filename, st.session_state.note_number)

        if os.path.exists(temp_filename):
            os.remove(temp_filename)

        if file_id:
            updated = update_submission_status(st.session_state.note_number)
            if updated:
                st.success("✅ تم إيداع المذكرة وتحديث الحالة بنجاح!")
                st.session_state.file_uploaded = True
                st.markdown(f"📎 معرف الملف على Drive: `{file_id}`")
            else:
                st.error("❌ فشل تحديث حالة الإيداع.")
        else:
            st.error("❌ فشل رفع الملف إلى Drive.")

    elif st.session_state.file_uploaded:
        st.info("📌 تم رفع الملف مسبقًا.")

    if st.session_state.file_uploaded:
        st.download_button(
            label="📄 تحميل وصل الإيداع",
            data=f"وصل تأكيد إيداع\nرقم المذكرة: {st.session_state.note_number}\nتاريخ الإيداع: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\nللاتصال: domaine.dsp@univ-bba.dz\nتوقيع مسؤول الميدان",
            file_name="وصل_الإيداع.txt",
            mime="text/plain"
        )

# --- التذييل ---
st.markdown("</div>", unsafe_allow_html=True)
st.markdown("""<p style='text-align:center; color:gray;'>للاتصال: domaine.dsp@univ-bba.dz<br>توقيع مسؤول الميدان</p>""", unsafe_allow_html=True)
