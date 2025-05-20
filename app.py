import streamlit as st
import pandas as pd
from datetime import datetime
import os

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- إعداد الاتصال بـ Google Sheets و Google Drive ---
SCOPES = ['https://www.googleapis.com/auth/spreadsheets ',
          'https://www.googleapis.com/auth/drive ']

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

# --- واجهة المستخدم ---
st.set_page_config(page_title="إيداع مذكرات التخرج", page_icon="📥", layout="centered")
st.markdown("<h1 style='text-align:center; color:#4B8BBE;'>📥 منصة إيداع التخرج</h1>", unsafe_allow_html=True)
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
            already_submitted, submission_date = is_already_submitted(note_number)
            if already_submitted:
                st.error(f"❌ المذكرة رقم {note_number} تم إيداعها سابقًا بتاريخ: {submission_date}. الرجاء الاتصال بالإدارة لأي استفسار.")
            else:
                memo_info = df[df["رقم المذكرة"].astype(str).str.strip() == str(note_number).strip()]
                if memo_info.empty:
                    st.error("❌ رقم المذكرة غير موجود.")
                elif memo_info.iloc[0]["كلمة السر"] != password:
                    st.error("❌ كلمة السر غير صحيحة.")
                else:
                    st.session_state.authenticated = True
                    st.session_state.note_number = note_number
                    st.success("✅ تم التحقق بنجاح. يمكنك الآن رفع المذكرة.")

else:
    st.success(f"✅ مرحبًا! رقم المذكرة: {st.session_state.note_number}")

    # --- رسالة للمستخدم باسم الملف الصحيح ---
    note_number = st.session_state.note_number
    expected_name = f"{note_number}.pdf"

    st.markdown(f"""
    ### ⚠️ اسم الملف المطلوب:
    ```
    {expected_name}
    ```
    📌 الرجاء رفع الملف بهذا الاسم فقط.
    """)

    uploaded_file = st.file_uploader("📤 رفع ملف المذكرة (PDF فقط)", type="pdf", key="file_uploader")

    if uploaded_file and not st.session_state.file_uploaded:
        filename = uploaded_file.name

        # --- التحقق من اسم الملف ---
        if filename != expected_name:
            st.error(f"""
            ❌ اسم الملف غير صحيح.  
            يجب أن تكون المذكرة باسم: `{expected_name}`
            """)
            st.stop()

        # --- حفظ الملف مؤقتًا ---
        temp_filename = f"temp_memo_{note_number}.pdf"
        with open(temp_filename, "wb") as f:
            f.write(uploaded_file.getbuffer())

        with st.spinner("⏳ جاري رفع الملف..."):
            file_id = upload_to_drive(temp_filename, note_number)

        # --- تنظيف الملف المؤقت ---
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

        if file_id:
            updated = update_submission_status(note_number)
            if updated:
                st.success("✅ تم إيداع المذكرة وتحديث الحالة بنجاح!")
                st.markdown(f"📎 معرف الملف على Drive: `{file_id}`")
                st.session_state.file_uploaded = True
            else:
                st.error("❌ فشل تحديث حالة الإيداع.")
        else:
            st.error("❌ فشل رفع الملف إلى Drive.")

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

# --- إعادة التشغيل ---
if st.session_state.get("reset_app"):
    for key in ["authenticated", "note_number", "file_uploaded", "reset_app"]:
        if key in st.session_state:
            del st.session_state[key]
    st.experimental_rerun()