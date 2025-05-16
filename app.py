import streamlit as st st.set_page_config(page_title="منصة إيداع المذكرات", page_icon="📚", layout="centered")

import pandas as pd import os from google.oauth2 import service_account from googleapiclient.discovery import build from googleapiclient.http import MediaFileUpload

FOLDER_ID = '1TfhvUA9oqvSlj9TuLjkyHi5xsC5svY1D' SCOPES = ['https://www.googleapis.com/auth/drive.file']

@st.cache_data def load_data(): df = pd.read_excel("حالة تسجيل المذكرات.xlsx") df.columns = df.columns.str.strip() df = df.astype(str) return df

@st.cache_resource def get_drive_service(): info = { "type": st.secrets["service_account"]["type"], "project_id": st.secrets["service_account"]["project_id"], "private_key_id": st.secrets["service_account"]["private_key_id"], "private_key": st.secrets["service_account"]["private_key"].replace("\n", "\n"), "client_email": st.secrets["service_account"]["client_email"], "client_id": st.secrets["service_account"]["client_id"], "auth_uri": st.secrets["service_account"]["auth_uri"], "token_uri": st.secrets["service_account"]["token_uri"], "auth_provider_x509_cert_url": st.secrets["service_account"]["auth_provider_x509_cert_url"], "client_x509_cert_url": st.secrets["service_account"]["client_x509_cert_url"], } credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES) service = build('drive', 'v3', credentials=credentials) return service

def upload_to_drive(file_path, file_name, service): file_metadata = { 'name': file_name, 'parents': [FOLDER_ID] } media = MediaFileUpload(file_path, mimetype='application/pdf') uploaded = service.files().create(body=file_metadata, media_body=media, fields='id').execute() return uploaded.get('id')

for key in ["step", "validated", "upload_success", "file_id", "memo_info"]: if key not in st.session_state: st.session_state[key] = None if key == "memo_info" else False if key in ["validated", "upload_success"] else "login"

========================== الواجهة ===========================

st.markdown(""" <style> @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap'); html, body, [class*="css"]  { font-family: 'Cairo', sans-serif !important; } .main { background-color: #1E2A38; color: #ffffff; } .block-container { padding: 2rem; background-color: #243447; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); max-width: 700px; margin: auto; } label, h1, h2, h3, h4, h5, h6, p, span, .stTextInput label { color: #ffffff !important; } input, button { font-size: 16px !important; } button { background-color: #256D85 !important; color: white !important; border: none !important; padding: 10px 20px !important; border-radius: 6px !important; transition: background-color 0.3s ease; } button:hover { background-color: #2C89A0 !important; } .header-container { text-align: center; margin-bottom: 30px; } .header-logo { width: 70px; margin-bottom: 10px; } </style> """, unsafe_allow_html=True)

st.markdown(""" <div class="header-container"> <img src="https://drive.google.com/uc?id=1sBEUeqEF6tKTglXP3ePMtV4BN_929R9Y" class="header-logo"> <h2>📚 منصة إيداع مذكرات التخرج</h2> <h4>كلية الحقوق والعلوم السياسية</h4> <h5>جامعة برج بوعريريج</h5> </div> """, unsafe_allow_html=True)

====== إظهار مثال من ملف إكسل ======

if st.checkbox("عرض مثال من ملف Excel"): df_test = load_data() df_test.columns = df_test.columns.str.strip() sample = df_test[['رقم المذكرة', 'كلمة السر', 'عنوان المذكرة']].head(1).to_dict(orient='records')[0] st.info(f""" ### بيانات اختبارية: - رقم المذكرة: {sample['رقم المذكرة']} - كلمة السر: {sample['كلمة السر']} - العنوان: {sample['عنوان المذكرة']} """)

