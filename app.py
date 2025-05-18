import streamlit as st
import pandas as pd
import os
import tempfile
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# إعداد الصفحة
st.set_page_config(page_title="منصة إيداع المذكرات", page_icon="📚", layout="centered")

# إعدادات Google Drive
FOLDER_ID = '1TfhvUA9oqvSlj9TuLjkyHi5xsC5svY1D'
SCOPES = ['https://www.googleapis.com/auth/drive.file']

@st.cache_data
def load_data():
    df = pd.read_excel("حالة تسجيل المذكرات.xlsx")
    df.columns = df.columns.str.strip()
    df = df.astype(str)
    return df

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
    st.write("Service Account Info:")
    st.write(info)  # إضافة تسجيل معلومات حساب الخدمة
    credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    service = build('drive', 'v3', credentials=credentials)
    return service

def upload_to_drive(file_path, file_name, service):
    file_metadata = {
        'name': file_name,
        'parents': [FOLDER_ID]
    }
    media = MediaFileUpload(file_path, mimetype='application/pdf')
    uploaded = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return uploaded.get('id')

# حالة الجلسة
for key in ["step", "upload_success", "file_id", "memo_info"]:
    if key not in st.session_state:
        if key == "step":
            st.session_state[key] = "login"
        else:
            st.session_state[key] = None if key == "memo_info" else False

# واجهة CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"]  {
        font-family: 'Cairo', sans-serif !important;
    }
    .main {
        background-color: #1E2A38;
        color: #ffffff;
    }
    .block-container {
        padding: 2rem;
        background-color: #243447;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        max-width: 700px;
        margin: auto;
    }
    label, h1, h2, h3, h4, h5, h6, p, span, .stTextInput label {
        color: #ffffff !important;
    }
    input, button {
        font-size: 16px !important;
    }
    button {
        background-color: #256D85 !important;
        color: white !important;
        border: none !important;
        padding: 10px 20px !important;
        border-radius: 6px !important;
        transition: background-color 0.3s ease;
    }
    button:hover {
        background-color: #2C89A0 !important;
    }
    .header-container {
        text-align: center;
        margin-bottom: 30px;
    }
    .header-logo {
        width: 70px;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# عنوان المنصة
st.markdown("""
    <div class="header-container">
        <img src="https://drive.google.com/uc?id=1sBEUeqEF6tKTglXP3ePMtV4BN_929R9Y" class="header-logo">
        <h2>📚 منصة إيداع مذكرات التخرج</h2>
        <h4>كلية الحقوق والعلوم السياسية</h4>
        <h5>جامعة برج بوعريريج</h5>
    </div>
""", unsafe_allow_html=True)

# === الخطوة 1: التحقق من البيانات ===
st.write("Session State at Start:")
st.write(st.session_state)  # إضافة تسجيل حالة الجلسة

if st.session_state.step == "login":
    with st.form("login_form"):
        note_number = st.text_input('رقم المذكرة')
        password = st.text_input('كلمة السر', type='password')
        submitted = st.form_submit_button("✅ تأكيد")

    if submitted:
        df = load_data()
        df['رقم المذكرة'] = df['رقم المذكرة'].str.strip()
        df['كلمة السر'] = df['كلمة السر'].str.strip()

        note = note_number.strip().lower()
        pw = password.strip().lower()

        st.write(f"Note Number: {note}, Password: {pw}")  # إضافة تسجيل القيم المدخلة
        st.write("Dataframe:")
        st.write(df)  # إضافة تسجيل قيم DataFrame

        match = df[(df['رقم المذكرة'].str.lower() == note) & (df['كلمة السر'].str.lower() == pw)]
        if not match.empty:
            st.session_state.memo_info = match.iloc[0]
            st.session_state.step = "upload"
            st.experimental_rerun()
        else:
            st.error("❌ رقم المذكرة أو كلمة السر غير صحيحة. يرجى التحقق والمحاولة مجددًا.")

# === الخطوة 2: رفع الملف ===
elif st.session_state.step == "upload" and not st.session_state.upload_success:
    st.write("Session State Before Upload:")
    st.write(st.session_state)  # إضافة تسجيل حالة الجلسة

    memo_info = st.session_state.memo_info
    st.success("✅ تم التحقق من المعلومات بنجاح")

    st.markdown(f"""
        ### 📄 عنوان المذكرة:
        {memo_info.get('عنوان المذكرة', 'غير متوفر')}
        ### 🎓 الطلبة:
        - {memo_info.get('الطالب الأول', '---')}
        {f"- {memo_info.get('الطالب الثاني')}" if pd.notna(memo_info.get('الطالب الثاني')) else ""}
    """)

    st.markdown("---")
    st.subheader("📤 رفع ملف المذكرة (PDF فقط)")
    uploaded_file = st.file_uploader("اختر الملف:", type="pdf")

    if uploaded_file:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name

            st.write(f"File Name: Memoire_{memo_info['رقم المذكرة']}.pdf")  # إضافة تسجيل اسم الملف
            with st.spinner("🚀 جاري رفع الملف إلى Google Drive..."):
                service = get_drive_service()
                file_id = upload_to_drive(tmp_path, f"Memoire_{memo_info['رقم المذكرة']}.pdf", service)

            st.session_state.upload_success = True
            st.session_state.file_id = file_id

        except Exception as e:
            st.error(f"❌ حدث خطأ أثناء رفع الملف: {type(e).__name__}: {str(e)}")  # عرض رسالة الخطأ الكاملة

        finally:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)

# === الخطوة 3: تأكيد الرفع ===
if st.session_state.upload_success:
    st.write("Session State After Upload:")
    st.write(st.session_state)  # إضافة تسجيل حالة الجلسة

    st.success("✅ تم إيداع المذكرة بنجاح!")
    st.info(f"📎 معرف الملف على Drive: `{st.session_state.file_id}`")
    if st.button("⬅️ إنهاء"):
        for key in ["step", "upload_success", "file_id", "memo_info"]:
            st.session_state[key] = None if key == "memo_info" else False if key == "upload_success" else "login"
        st.experimental_rerun()
