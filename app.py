# --- إعداد التصميم العام ---
st.set_page_config(page_title="إيداع مذكرات التخرج", layout="centered")

# --- CSS للتصميم ---
st.markdown("""
<style>
/* الخلفية العامة للصفحة بيضاء */
body {
    background-color: white;
}

/* الحاوية الداخلية (المربع الأزرق الداكن) */
section.main > div.block-container {
    max-width: 480px;
    margin: 3rem auto 4rem auto !important;
    background-color: #0b1a35; /* أزرق داكن */
    padding: 2rem 3rem 3rem 3rem;
    border-radius: 16px;
    color: white;
    box-shadow: 0 0 15px rgba(0,0,0,0.3);
    direction: rtl;
    font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
}

/* حقول الإدخال ورفع الملفات */
div.stTextInput > div > input,
div.stTextArea > div > textarea,
div.stFileUploader > div > label,
div.stFileUploader > div > input,
div.stButton > button,
div.stTextInput > div > input:focus {
    background-color: #1f2f4a !important; /* أزرق متوسط */
    color: white !important;
    border-radius: 8px !important;
    border: none !important;
    padding: 0.5rem 1rem !important;
    text-align: center !important;
}

/* زر الرفع hover */
div.stButton > button:hover {
    background-color: #29446c !important; /* أزرق فاتح عند hover */
    color: yellow !important;
}

/* مسافة بين الحقول */
div.stTextInput, div.stFileUploader, div.stButton {
    margin-bottom: 1.5rem !important;
}

/* العناوين */
h1, h2, h3, p {
    color: gold !important;
    text-align: center;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

# --- المحتوى الثابت (يظهر دائمًا) ---
st.title("📥 منصة إيداع مذكرات التخرج")
st.write("جامعة محمد البشير الإبراهيمي - برج بوعريريج")

df = load_data()

# --- حالة المستخدم ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "file_uploaded" not in st.session_state:
    st.session_state.file_uploaded = False

# --- المحتوى داخل الحاوية الزرقاء (يظهر دائمًا داخل الحاوية) ---
with st.container():
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
        st.markdown(f"### ⚠️ اسم الملف المطلوب:\n```\n{expected_name}\n```")
        st.markdown("📌 الرجاء رفع الملف بهذا الاسم فقط.")

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

# --- تذييل الصفحة ---
st.markdown("""<p style='text-align:center; color:gray; margin-top: 3rem;'>
للاتصال: domaine.dsp@univ-bba.dz<br>توقيع مسؤول الميدان
</p>""", unsafe_allow_html=True)
