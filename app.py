import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import io

# --- CONFIGURATION ---
EXCEL_FILE = "students.xlsx"
SHEET_ID = "12m5GDAKoWeVd58UI-Ho4jM_HRUYkS9PDP3ekBsc1_ls"  # <-- Paste your ID right here!

def get_gsheet_client():
    try:
        service_account_info = json.loads(st.secrets["service_account"])
        creds = Credentials.from_service_account_info(
            service_account_info,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Secret Key Error: {e}")
        return None

# --- LOCKOUT CHECKER ---
def check_existing_submission(target_class, target_subject, target_exam):
    client = get_gsheet_client()
    if not client: return False
    try:
        # Using open_by_key to bypass Google Drive API search errors!
        sheet = client.open_by_key(SHEET_ID).sheet1
        records = sheet.get_all_records()
        if not records: return False
        
        for row in records:
            if str(row.get('Class')) == target_class and str(row.get('Subject')) == target_subject and str(row.get('Exam_Type')) == target_exam:
                return True
        return False
    except Exception as e:
        return False

@st.cache_data
def load_and_clean_excel(class_sheet):
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name=class_sheet)
        df.columns = df.columns.str.strip().str.lower()
        
        if 'date_of_birth' in df.columns:
            df['date_of_birth'] = pd.to_datetime(df['date_of_birth'], errors='coerce').dt.strftime('%d/%m/%Y')
        
        if 'first_name' in df.columns:
            df['display_name'] = df['first_name'].astype(str).str.strip()
        else:
            df['display_name'] = "Unknown Name"
            
        return df
    except Exception as e:
        st.error(f"Error loading {class_sheet}: {e}")
        return None

# --- EMAIL BACKUP ENGINE ---
def send_email_backup(data, class_name, subject, exam_type):
    try:
        sender = st.secrets["email_sender"]
        receiver = st.secrets["email_receiver"]
        password = st.secrets["email_password"]

        # 1. Load all data
        df_temp = pd.DataFrame(data, columns=['Date', 'Class', 'Subject', 'Exam_Type', 'admission_no', 'marks', 'status', 'note'])
        
        # 2. Filter to ONLY the 4 columns you want, in the exact order!
        df_email = df_temp[['admission_no', 'status', 'marks', 'note']].copy()
        
        # 3. Rename 'admission_no' to 'adm_no' to perfectly match your request
        df_email.rename(columns={'admission_no': 'adm_no'}, inplace=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            # We save the cleaned-up df_email here instead of df_temp
            df_email.to_excel(writer, index=False, sheet_name='Marks')
        
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = receiver
        msg['Subject'] = f"Database Backup: {class_name} - {subject} ({exam_type})"
        
        part = MIMEBase('application', "vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        part.set_payload(buffer.getvalue())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{class_name}_{subject}_backup.xlsx"')
        msg.attach(part)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Email Backup Failed: {e}")
        return False

# --- UI CONTROLS ---
st.set_page_config(page_title="Apex Marks Portal", layout="centered")
st.title("🏫 Student Marks Entry")

try:
    xls = pd.ExcelFile(EXCEL_FILE)
    available_classes = xls.sheet_names 
except Exception as e:
    st.error(f"Could not read the Excel file. Error: {e}")
    available_classes = []

if available_classes:
    sel_class = st.selectbox("Select Class", available_classes)
    sel_subject = st.selectbox("Subject", ["Hindi", "English", "Math", "Science", "Social Science","G. K.","Moral","Computer","Sanskrit","Art", "P.T.", "Craft", "Hindi Written", "English Written", "Math Written", "Hindi Oral", "English Oral", "Math Oral"])
    
   # All 6 exams added here (using selectbox so it doesn't clutter the screen)
    exam_list = [
        "1st Term Test (Max 20)", 
        "Quarterly Examination (Max 80)", 
        "2nd Term Test (Max 20)", 
        "Half Yearly Examination (Max 80)", 
        "3rd Term Test (Max 20)", 
        "Annual Examination (Max 80)"
    ]
    exam_mode = st.selectbox("Exam Type", exam_list)
    
    # Automatically sets limits based on the name of the exam!
    if "Max 80" in exam_mode:
        max_val, pass_val = 80, 27
    else:
        max_val, pass_val = 20, 7

    is_locked = check_existing_submission(sel_class, sel_subject, exam_mode)

    if is_locked:
        st.error(f"🚨 STOP! Marks for **{sel_class} - {sel_subject} ({exam_mode})** have already been submitted.")
        st.info("If you need to make corrections, please contact the Admin to delete the old record first.")
    else:
        df_students = load_and_clean_excel(sel_class)
        
        if df_students is not None:
            with st.form("entry_form"):
                batch_data = []
                for i, row in df_students.iterrows():
                    # 1. Safely extract the admission number
                    raw_adm = row.get('admission_no', f"Temp-{i}")
                    
                    # 2. Force it into a plain string to strip Numpy formatting
                    if isinstance(raw_adm, (float, int)):
                        adm_no = str(int(raw_adm))
                    else:
                        adm_no = str(raw_adm).strip()
                    
                    st.write(f"**{row['display_name']}** (Adm: {adm_no})")
                    mark = st.number_input(f"Marks", 0, max_val, 0, key=f"m_{i}")
                    
                    status = 1 if mark >= pass_val else 0
                    note = "Good" if status == 1 else "Fail"
                    
                    # 3. Force EVERY single item into a plain Python type (This prevents the JSON Error!)
                    batch_data.append([
                        str(datetime.now().strftime("%Y-%m-%d")),
                        str(sel_class),
                        str(sel_subject),
                        str(exam_mode),
                        str(adm_no), 
                        int(mark),   
                        int(status), 
                        str(note)    
                    ])
                    st.divider()

                if st.form_submit_button("SAVE ALL TO GOOGLE SHEETS"):
                    client = get_gsheet_client()
                    if client:
                        # Save using the specific Sheet ID
                        sheet = client.open_by_key(SHEET_ID).sheet1
                        sheet.append_rows(batch_data)
                        
                        with st.spinner("Saving to cloud and sending email backup..."):
                            email_success = send_email_backup(batch_data, sel_class, sel_subject, exam_mode)
                        
                        if email_success:
                            st.success(f"Uploaded successfully and Email Backup sent!")
                        else:
                            st.warning(f"Uploaded to Google Sheets, but Email Backup failed.")
                        
                        # Create Teacher's Instant Excel Receipt
                        df_receipt = pd.DataFrame(batch_data, columns=['Date', 'Class', 'Subject', 'Exam_Type', 'admission_no', 'marks', 'status', 'note'])
                        receipt_buffer = io.BytesIO()
                        with pd.ExcelWriter(receipt_buffer, engine='xlsxwriter') as writer:
                            df_receipt.to_excel(writer, index=False, sheet_name='Submitted_Marks')
                        
                        st.session_state['receipt_data'] = receipt_buffer.getvalue()
                        st.session_state['receipt_filename'] = f"{sel_class}_{sel_subject}_Receipt.xlsx"
                        
                        st.balloons()

        # Teacher's Download Button
        if 'receipt_data' in st.session_state:
            st.info("👇 Click below to save a copy of the marks you just entered.")
            st.download_button(
                label=f"📥 Download {sel_subject} Receipt",
                data=st.session_state['receipt_data'],
                file_name=st.session_state['receipt_filename'],
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# --- EMERGENCY BACKUP & ADMIN TOOLS ---
st.divider()
st.subheader("💾 Admin Backup")
st.write("Use this button to download the entire Google Sheet database directly to your device.")

if st.button("Fetch Entire Database"):
    client = get_gsheet_client()
    if client:
        with st.spinner("Fetching data from Google Sheets..."):
            try:
                sheet = client.open_by_key(SHEET_ID).sheet1
                all_data = sheet.get_all_records()
                if all_data:
                    df_backup = pd.DataFrame(all_data)
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        df_backup.to_excel(writer, index=False, sheet_name='All_Marks')
                    
                    st.download_button(
                        label="📥 Click to Download Full Database Excel File",
                        data=buffer.getvalue(),
                        file_name=f"Apex_Marks_Database_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.info("The database is currently empty.")
            except Exception as e:
                st.error(f"Could not fetch backup. Error: {e}")