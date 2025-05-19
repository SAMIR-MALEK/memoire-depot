import streamlit as st
import pandas as pd
import io
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

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
                {"range": f"Feuille 1!{chr(64+date_col)}{idx}", "values": [[datetime.now().strftime("%Y-%m-%d %H:%M")]]},
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

# --- واجهة Streamlit ---
st.set_page_config(page_title="إيداع مذكرات التخرج", page_icon="📥", layout="centered")

st.markdown("<h1 style='text-align:center; color:#4B8BBE;'>📥 منصة إيداع مذكرات التخرج</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; font-size:18px;'>جامعة برج بوعريريج</p>", unsafe_allow_html=True)
st.markdown("---")

# --- تحميل بيانات الطلبة ---
df = load_data()

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
                updated = update_submission_status(st.session_state.note_number)
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

    if st.session_state.file_uploaded:
        st.success("✅ تم رفع الملف وتحديث حالة الإيداع بنجاح.")
        st.info("📌 لا حاجة لأي خطوة إضافية. يمكنك الآن إغلاق الصفحة أو تحميل وصل الإيداع.")
        st.download_button(
            label="📄 تحميل وصل الإيداع",
            data=f"وصل تأكيد إيداع\nرقم المذكرة: {st.session_state.note_number}\nتاريخ الإيداع: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            file_name="وصل_الإيداع.txt",
            mime="text/plain"
        )


# --- تنفيذ إعادة التهيئة بعد rerun ---
if st.session_state.get("reset_app"):
    for key in ["authenticated", "note_number", "file_uploaded", "reset_app"]:
        if key in st.session_state:
            del st.session_state[key]
    st.experimental_rerun()
