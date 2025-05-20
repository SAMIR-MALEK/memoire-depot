import streamlit as st import pandas as pd import json import re import requests from datetime import datetime from google.oauth2 import service_account import google.auth.transport.requests

--- إعداد الاتصال بـ Google Sheets ---

from googleapiclient.discovery import build

SCOPES = [ 'https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive' ]

info = st.secrets["service_account"] credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES) sheets_service = build('sheets', 'v4', credentials=credentials)

SPREADSHEET_ID = "1Ycx-bUscF7rEpse4B5lC4xCszYLZ8uJyPJLp6bFK8zo" DRIVE_FOLDER_ID = "1TfhvUA9oqvSlj9TuLjkyHi5xsC5svY1D"

@st.cache_data(ttl=300) def load_data(): try: result = sheets_service.spreadsheets().values().get( spreadsheetId=SPREADSHEET_ID, range="Feuille 1!A1:Z1000" ).execute() values = result.get('values', []) if not values: st.error("❌ لا توجد بيانات في الشيت.") st.stop() df = pd.DataFrame(values[1:], columns=values[0]) return df except Exception as e: st.error(f"❌ خطأ في تحميل البيانات من Google Sheets: {e}") st.stop()

def is_already_submitted(note_number): try: df = load_data() memo = df[df["رقم المذكرة"].astype(str).str.strip() == str(note_number).strip()] if memo.empty: return False, None deposit_status = memo.iloc[0]["تم الإيداع"] submission_date = memo.iloc[0]["تاريخ الإيداع"] if (isinstance(deposit_status, str) and deposit_status.strip() == "نعم") or 
(isinstance(submission_date, str) and submission_date.strip() != ""): return True, submission_date return False, None except Exception as e: st.error(f"❌ خطأ في التحقق من حالة الإيداع: {e}") return False, None

def update_submission_status(note_number): try: df = load_data() row_idx = df[df["رقم المذكرة"].astype(str).str.strip() == str(note_number).strip()].index if row_idx.empty: st.error("❌ رقم المذكرة غير موجود في الشيت أثناء التحديث.") return False idx = row_idx[0] + 2 col_names = df.columns.tolist() deposit_col = col_names.index("تم الإيداع") + 1 date_col = col_names.index("تاريخ الإيداع") + 1

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

def sanitize_text(text): return re.sub(r'[^A-Za-z0-9]+', '_', text)

def get_access_token(): credentials = service_account.Credentials.from_service_account_info( st.secrets["service_account"], scopes=["https://www.googleapis.com/auth/drive"] ) auth_req = google.auth.transport.requests.Request() credentials.refresh(auth_req) return credentials.token

import tempfile
import os

def upload_to_drive(file, note_number):
    try:
        # إنشاء اسم آمن للملف
        safe_name = f"MEMOIRE_N{sanitize_text(str(note_number))}.pdf"

        # إنشاء ملف مؤقت بامتداد .pdf
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file.read())
            tmp_path = tmp.name

        # إعادة فتح الملف المؤقت لرفعه
        with open(tmp_path, "rb") as f:
            media = MediaIoBaseUpload(f, mimetype='application/pdf', resumable=True)
            file_metadata = {
                'name': safe_name,
                'parents': [DRIVE_FOLDER_ID]
            }
            uploaded = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

        # حذف الملف المؤقت
        os.remove(tmp_path)
        return uploaded.get('id')

    except Exception as e:
        st.error(f"❌ خطأ في رفع الملف إلى Google Drive: {e}")
        return None

--- واجهة Streamlit ---

st.set_page_config(page_title="إيداع مذكرات التخرج", page_icon="📥", layout="centered")

st.markdown("<h1 style='text-align:center; color:#4B8BBE;'>📥 منصة إيداع مذكرات التخرج</h1>", unsafe_allow_html=True) st.markdown("<p style='text-align:center; font-size:18px;'>جامعة برج بوعريريج</p>", unsafe_allow_html=True) st.markdown("---")

df = load_data()

if "authenticated" not in st.session_state: st.session_state.authenticated = False if "file_uploaded" not in st.session_state: st.session_state.file_uploaded = False

if not st.session_state.authenticated: note_number = st.text_input("🔢 أدخل رقم المذكرة:", key="note_input") password = st.text_input("🔐 أدخل كلمة السر:", type="password", key="pass_input")

if st.button("✅ تحقق", key="btn_check"):
    if not note_number or not password:
        st.warning("⚠️ الرجاء إدخال رقم المذكرة وكلمة السر.")
    else:
        already_submitted, submission_date = is_already_submitted(note_number)
        if already_submitted:
            st.error(f"❌ المذكرة رقم {note_number} تم إيداعها سابقًا بتاريخ: {submission_date}.")
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

else: st.success(f"✅ مرحبًا! رقم المذكرة: {st.session_state.note_number}") uploaded_file = st.file_uploader("📤 رفع ملف المذكرة (PDF فقط)", type="pdf", key="file_uploader")

if uploaded_file and not st.session_state.file_uploaded:
    with st.spinner("⏳ جاري رفع الملف..."):
        file_id = upload_to_drive(uploaded_file, st.session_state.note_number)
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

