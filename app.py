import streamlit as st
st.set_page_config(page_title="منصة إيداع المذكرات", page_icon="📚", layout="centered")

import pandas as pd
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

FOLDER_ID = '1TfhvUA9oqvSlj9TuLjkyHi5xsC5svY1D'
SCOPES = ['https://www.googleapis.com/auth/drive.file']

@st.cache_data
def load_data():
    df = pd.read_excel("حالة تسجيل المذكرات.xlsx")
    df.columns = df.columns.str.strip()  # إزالة الفراغات من أسماء الأعمدة
    df = df.astype(str)
    return df

@st.cache_resource
def get_drive_service():
    client_id = st.secrets["google_oauth"]["client_id"]
    client_secret = st.secrets["google_oauth"]["client_secret"]
    redirect_uri = st.secrets["google_oauth"]["redirect_uri"]

    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uris": [redirect_uri],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        SCOPES,
    )
    creds = flow.run_local_server(port=0)
    service = build('drive', 'v3', credentials=creds)
    return service

def upload_to_drive(file_path, file_name, service):
    file_metadata = {
        'name': file_name,
        'parents': [FOLDER_ID]
    }
    media = MediaFileUpload(file_path, mimetype='application/pdf')
    uploaded = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return uploaded.get('id')

# ========================== واجهة التطبيق ===========================

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
        font-family: 'Cairo', sans-serif !important;
        color: #ffffff;
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

st.markdown("يرجى إدخال **رقم المذكرة** و **كلمة السر** ثم الضغط على زر التحقق.")

note_number = st.text_input('رقم المذكرة', placeholder='أدخل رقم المذكرة هنا')
password = st.text_input('كلمة السر', type='password', placeholder='أدخل كلمة السر')

if 'upload_success' not in st.session_state:
    st.session_state.upload_success = False
if 'file_id' not in st.session_state:
    st.session_state.file_id = None

if st.button("✅ تأكيد"):
    if note_number and password:
        df = load_data()

        required_columns = ['رقم المذكرة', 'كلمة السر', 'عنوان المذكرة', 'الطالب الأول', 'الطالب الثاني']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            st.error("⚠️ بعض الأعمدة مفقودة في ملف Excel: " + ", ".join(missing_columns))
            st.stop()

        # تنظيف القيم
        df['رقم المذكرة'] = df['رقم المذكرة'].str.strip()
        df['كلمة السر'] = df['كلمة السر'].str.strip()

        input_note = note_number.strip()
        input_pass = password.strip()

        match = df[(df['رقم المذكرة'].str.lower() == input_note.lower()) & (df['كلمة السر'].str.lower() == input_pass.lower())]

        if not match.empty:
            memo_info = match.iloc[0]
            st.success("✅ تم التحقق من المعلومات بنجاح")
            st.markdown(f"""
                ### 📄 عنوان المذكرة:
                {memo_info.get('عنوان المذكرة', 'غير متوفر')}
                ### 🎓 الطلبة:
                - {memo_info.get('الطالب الأول', '---')}
                {f"- {memo_info.get('الطالب الثاني')}" if pd.notna(memo_info.get('الطالب الثاني')) else ""}
            """)

            st.markdown("---")
            st.subheader("📤 رفع ملف المذكرة")

            uploaded_file = st.file_uploader('اختر ملف PDF للمذكرة:', type=['pdf'])

            if uploaded_file is not None and not st.session_state.upload_success:
                temp_file_path = "temp.pdf"
                with open(temp_file_path, "wb") as f:
                    f.write(uploaded_file.read())

                try:
                    with st.spinner("🚀 جاري رفع الملف إلى Google Drive..."):
                        service = get_drive_service()
                        file_id = upload_to_drive(temp_file_path, f"Memoire_{input_note}.pdf", service)
                    st.session_state.upload_success = True
                    st.session_state.file_id = file_id
                except Exception as e:
                    st.error(f"❌ حدث خطأ أثناء رفع الملف: {e}")
                finally:
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)

            if st.session_state.upload_success:
                st.success("✅ تم إيداع المذكرة بنجاح!")
                st.info(f'📎 معرف الملف على Drive: `{st.session_state.file_id}`')
                if st.button("رفع مذكرة أخرى"):
                    st.session_state.upload_success = False
                    st.session_state.file_id = None
                    st.experimental_rerun()

        else:
            st.error("❌ رقم المذكرة أو كلمة السر غير صحيحة. يرجى التحقق والمحاولة مجددًا.")
    else:
        st.warning("⚠️ يرجى تعبئة رقم المذكرة وكلمة السر.")
