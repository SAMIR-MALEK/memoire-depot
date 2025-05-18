import streamlit as st
st.set_page_config(page_title="منصة إيداع المذكرات", page_icon="📚", layout="centered")

import pandas as pd
import os
import tempfile
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ==================== الإعدادات الثابتة ====================
FOLDER_ID = '1TfhvUA9oqvSlj9TuLjkyHi5xsC5svY1D'
SCOPES = ['https://www.googleapis.com/auth/drive.file ']

# ==================== تحميل البيانات ====================
@st.cache_data(ttl=3600)  # تحديث كل ساعة
def load_data():
    try:
        df = pd.read_excel("حالة تسجيل المذكرات.xlsx")
        df.columns = df.columns.str.strip()
        return df.astype(str)
    except Exception as e:
        st.error(f"❌ لم يتم العثور على ملف البيانات أو حدث خطأ: {e}")
        st.stop()

# ==================== الاتصال بـ Google Drive API ====================
@st.cache_resource
def get_drive_service():
    info = {
        "type": st.secrets["service_account"]["type"],
        "project_id": st.secrets["service_account"]["project_id"],
        "private_key_id": st.secrets["service_account"]["private_key_id"],
        "private_key": st.secrets["service_account"]["private_key"].replace("\\n", "\n"),
        "client_email": st.secrets["service_account"]["client_email"],
        "client_id": st.secrets["service_account"]["client_id"],
        "auth_uri": st.secrets["service_account"]["auth_uri"],
        "token_uri": st.secrets["service_account"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["service_account"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["service_account"]["client_x509_cert_url"],
    }
    credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build('drive', 'v3', credentials=credentials)

def upload_to_drive(file_path, file_name, service):
    file_metadata = {'name': file_name, 'parents': [FOLDER_ID]}
    media = MediaFileUpload(file_path, mimetype='application/pdf')
    uploaded = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return uploaded.get('id')

# ==================== إعادة تهيئة الجلسة ====================
def reset_session():
    for key in ["step", "upload_success", "file_id", "memo_info"]:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.step = "login"

# ==================== تهيئة الحالة الأولية ====================
if "step" not in st.session_state:
    reset_session()

# ==================== واجهة المستخدم - CSS ====================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo :wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Cairo', sans-serif !important; }
.main { background-color: #1E2A38; color: #ffffff; }
.block-container { padding: 2rem; background-color: #243447; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); max-width: 700px; margin: auto; }
label, h1, h2, h3, h4, h5, h6, p, span, .stTextInput label { color: #ffffff !important; }
input, button { font-size: 16px !important; }
button { background-color: #256D85 !important; color: white !important; border: none !important; padding: 10px 20px !important; border-radius: 6px !important; transition: background-color 0.3s ease; }
button:hover { background-color: #2C89A0 !important; }
.header-container { text-align: center; margin-bottom: 30px; }
.header-logo { width: 70px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-container">
<img src="https://drive.google.com/uc?id=1sBEUeqEF6tKTglXP3ePMtV4BN_929R9Y " class="header-logo">
<h2>📚 منصة إيداع مذكرات التخرج</h2>
<h4>كلية الحقوق والعلوم السياسية</h4>
<h5>جامعة برج بوعريريج</h5>
</div>
""", unsafe_allow_html=True)

# ==================== الخطوة الأولى: تسجيل الدخول ====================
if st.session_state.step == "login":
    with st.form("login_form"):
        note_number = st.text_input('رقم المذكرة')
        password = st.text_input('كلمة السر', type='password')
        submitted = st.form_submit_button("✅ تأكيد")

    if submitted:
        df = load_data()
        df['رقم المذكرة'] = df['رقم المذكرة'].str.strip()
        df['كلمة السر'] = df['كلمة السر'].str.strip()

        match = df[
            (df['رقم المذكرة'].str.lower() == note_number.strip().lower()) &
            (df['كلمة السر'].str.lower() == password.strip().lower())
        ]

        if not match.empty:
            st.session_state.memo_info = match.iloc[0].to_dict()
            st.session_state.step = "upload"
            st.experimental_rerun()
        else:
            st.error("❌ رقم المذكرة أو كلمة السر غير صحيحة.")

# ==================== الخطوة الثانية: رفع الملف ====================
elif st.session_state.step == "upload":
    memo_info = st.session_state.memo_info
    st.success("✅ تم التحقق من المعلومات بنجاح")
    st.markdown(f"""
### 📄 عنوان المذكرة: {memo_info.get('عنوان المذكرة', 'غير متوفر')}
### 🎓 الطلبة:
- {memo_info.get('الطالب الأول', '---')}
{f"- {memo_info.get('الطالب الثاني')}" if memo_info.get('الطالب الثاني') and memo_info.get('الطالب الثاني') != 'nan' else ""}
""")
    st.markdown("---")
    st.subheader("📤 رفع ملف المذكرة (PDF فقط)")
    uploaded_file = st.file_uploader("اختر الملف:", type="pdf")

    if uploaded_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.getvalue())
            temp_path = tmp.name

        try:
            with st.spinner("🚀 جاري رفع الملف إلى Google Drive..."):
                service = get_drive_service()
                file_id = upload_to_drive(temp_path, f"Memoire_{memo_info['رقم المذكرة']}.pdf", service)
                st.session_state.file_id = file_id
                st.session_state.upload_success = True
        except Exception as e:
            st.error(f"❌ حدث خطأ أثناء رفع الملف: {e}")
        finally:
            os.unlink(temp_path)

        st.experimental_rerun()  # إعادة التحميل بعد اكتمال الرفع

# ==================== رسالة النجاح ====================
if hasattr(st.session_state, "upload_success") and st.session_state.upload_success:
    st.success("✅ تم إيداع المذكرة بنجاح!")
    file_url = f"https://drive.google.com/file/d/ {st.session_state.file_id}/view"
    st.markdown(f"[📎 عرض الملف على Google Drive]({file_url})")
    
    if st.button("⬅️ إنهاء"):
        reset_session()
        st.experimental_rerun()