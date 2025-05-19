import streamlit as st
st.set_page_config(page_title="منصة إيداع المذكرات", page_icon="📚", layout="centered")

import pandas as pd
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

FOLDER_ID = '1TfhvUA9oqvSlj9TuLjkyHi5xsC5svY1D'
SCOPES = ['https://www.googleapis.com/auth/drive.file']

@st.cache_data
def load_data():
    df = pd.read_excel("حالة تسجيل المذكرات.xlsx")
    df.columns = df.columns.str.strip()  # إزالة الفراغات من أسماء الأعمدة
    # التأكد من وجود الأعمدة المطلوبة
    required_columns = ["الطالب الأول", "الطالب الثاني", "رقم المذكرة", "عنوان المذكرة",
                        "التخصص", "الأستاذ", "كلمة السر", "تم الإيداع", "تاريخ الإيداع"]
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        raise ValueError(f"الأعمدة التالية مفقودة في ملف الإكسل: {missing_cols}")
    # تحويل كل القيم إلى نصوص (Strings) وتنظيف عمود "تم الإيداع"
    df = df.astype(str)
    df["تم الإيداع"] = df["تم الإيداع"].fillna("").str.strip().str.lower()
    df["تاريخ الإيداع"] = df["تاريخ الإيداع"].fillna("")
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

for key in ["step", "validated", "upload_success", "file_id", "memo_info"]:
    if key not in st.session_state:
        st.session_state[key] = None if key == "memo_info" else False if key in ["validated", "upload_success"] else "login"

# ========================== الواجهة ===========================
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

st.markdown("""
    <div class="header-container">
        <img src="https://drive.google.com/uc?id=1sBEUeqEF6tKTglXP3ePMtV4BN_929R9Y" class="header-logo">
        <h2>📚 منصة إيداع مذكرات التخرج</h2>
        <h4>كلية الحقوق والعلوم السياسية</h4>
        <h5>جامعة برج بوعريريج</h5>
    </div>
""", unsafe_allow_html=True)

# ======================== الخطوة الأولى =========================
if st.session_state.step == "login":
    note_number = st.text_input('رقم المذكرة', key="note_input")
    password = st.text_input('كلمة السر', type='password', key="pass_input")

    if st.button("✅ تأكيد"):
        df = load_data()
        df['رقم المذكرة'] = df['رقم المذكرة'].str.strip()
        df['كلمة السر'] = df['كلمة السر'].str.strip()
        df['تم الإيداع'] = df['تم الإيداع'].fillna("").str.strip().str.lower()
        df['تاريخ الإيداع'] = df['تاريخ الإيداع'].fillna("")

        note = note_number.strip().lower()
        pw = password.strip().lower()

        match = df[(df['رقم المذكرة'].str.lower() == note) & (df['كلمة السر'].str.lower() == pw)]

        if not match.empty:
            if match.iloc[0].get('تم الإيداع', '') == 'نعم':
                deposit_date = match.iloc[0].get('تاريخ الإيداع', 'غير محدد')
                st.warning(f"⚠️ لقد تم إيداع هذه المذكرة مسبقًا بتاريخ **{deposit_date}**.\n\nإذا كنت ترى أن هناك خطأ، يرجى التواصل مع الإدارة.")
            else:
                st.session_state.memo_info = match.iloc[0]
                st.session_state.step = "upload"
        else:
            st.error("❌ رقم المذكرة أو كلمة السر غير صحيحة. يرجى التحقق والمحاولة مجددًا.")

# ======================== الخطوة الثانية =========================
elif st.session_state.step == "upload" and not st.session_state.upload_success:
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
        temp_path = uploaded_file.name
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.read())
        try:
            with st.spinner("🚀 جاري رفع الملف إلى Google Drive..."):
                service = get_drive_service()
                file_id = upload_to_drive(temp_path, f"Memoire_{memo_info['رقم المذكرة']}.pdf", service)
            st.session_state.upload_success = True
            st.session_state.file_id = file_id
        except Exception as e:
            st.error(f"❌ حدث خطأ أثناء رفع الملف: {e}")
        finally:
            os.remove(temp_path)

# ======================== رسالة النجاح بعد الرفع =========================
if st.session_state.upload_success:
    st.success("✅ تم إيداع المذكرة بنجاح!")
    st.info(f"📎 معرف الملف على Drive: {st.session_state.file_id}")
    if st.button("⬅️ إنهاء"):
        for key in ["step", "validated", "upload_success", "file_id", "memo_info"]:
            st.session_state[key] = None if key == "memo_info" else False if key in ["validated", "upload_success"] else "login"
        st.experimental_rerun()
