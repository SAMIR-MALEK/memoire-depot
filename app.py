import streamlit as st
st.set_page_config(page_title="منصة إيداع المذكرات", page_icon="📚", layout="centered")

import pandas as pd
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

FOLDER_ID = '1TfhvUA9oqvSlj9TuLjkyHi5xsC5svY1D'
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# تضمين Font Awesome
st.markdown("""
    <head>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    </head>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    df = pd.read_excel("حالة تسجيل المذكرات.xlsx")
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
    .main {
        background-color: #f8f9fa;
    }
    .block-container {
        padding: 2rem;
        background-color: white;
        border-radius: 12px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        max-width: 700px;
        margin: auto;
    }
    h2, h4 {
        color: #2c3e50;
    }
    ul {
        font-size: 16px;
        padding-left: 20px;
    }
    button {
        background-color: #4CAF50 !important;
        color: white !important;
        border: none !important;
        padding: 10px 20px !important;
        border-radius: 6px !important;
        font-size: 16px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h2><i class="fas fa-book"></i> منصة إيداع مذكرات التخرج</h2>', unsafe_allow_html=True)
st.markdown("""
    <p style='font-size:18px;'>يرجى إدخال <strong>رقم المذكرة</strong> و <strong>كلمة السر</strong> ثم الضغط على زر التحقق.</p>
""", unsafe_allow_html=True)

note_number = st.text_input('رقم المذكرة', placeholder='أدخل رقم المذكرة هنا')
password = st.text_input('كلمة السر', type='password', placeholder='أدخل كلمة السر')

if st.button('<i class="fas fa-check-circle"></i> تأكيد', key='confirm'):
    if note_number and password:
        df = load_data()
        match = df[(df['رقم المذكرة'] == note_number) & (df['كلمة السر'] == password)]

        if not match.empty:
            memo_info = match.iloc[0]
            st.success('<i class="fas fa-check-circle"></i> تم التحقق من المعلومات بنجاح', icon="✅")
            st.markdown(f"""
                <h4><i class="fas fa-file-alt"></i> عنوان المذكرة:</h4>
                <p>{memo_info['عنوان المذكرة']}</p>
                <h4><i class="fas fa-user-graduate"></i> الطلبة:</h4>
                <ul>
                    <li>{memo_info['الطالب 1']}</li>
                    {f"<li>{memo_info['الطالب 2']}</li>" if 'الطالب 2' in memo_info and pd.notna(memo_info['الطالب 2']) else ""}
                </ul>
            """, unsafe_allow_html=True)

            st.markdown("---")
            st.subheader('<i class="fas fa-upload"></i> رفع ملف المذكرة')
            uploaded_file = st.file_uploader('اختر ملف PDF للمذكرة:', type=['pdf'])

            if uploaded_file:
                with open("temp.pdf", "wb") as f:
                    f.write(uploaded_file.read())

                with st.spinner("🚀 جاري رفع الملف إلى Google Drive..."):
                    service = get_drive_service()
                    file_id = upload_to_drive("temp.pdf", f"Memoire_{note_number}.pdf", service)
                    os.remove("temp.pdf")

                st.success('<i class="fas fa-check-circle"></i> تم رفع الملف بنجاح!')
                st.info(f'📎 معرف الملف على Drive: `{file_id}`')

        else:
            st.error('<i class="fas fa-exclamation-triangle"></i> رقم المذكرة أو كلمة السر غير صحيحة. يرجى التحقق والمحاولة مجددًا.')
    else:
        st.warning('<i class="fas fa-exclamation-circle"></i> يرجى تعبئة رقم المذكرة وكلمة السر.')
