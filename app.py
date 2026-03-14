import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

# --- CONFIGURATION ---
EXCEL_FILE = "students.xlsx"
SHEET_NAME_GS = "School_Marks_Database"

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

st.set_page_config(page_title="Apex Marks Portal", layout="centered")
st.title("🏫 Student Marks Entry")

# --- DATA CLEANING ENGINE ---
@st.cache_data
def load_and_clean_excel(class_sheet):
    try:
        # Load specific sheet (e.g., 'CLASS 8th')
        df = pd.read_excel(EXCEL_FILE, sheet_name=class_sheet)
        
        # 1. Standardize DOB (Fixes both 07-01 and 07/01)
        df['date_of_birth'] = pd.to_datetime(df['date_of_birth'], errors='coerce').dt.strftime('%d/%m/%Y')
        
        # 2. Use first_name as the Full Name (per your instruction)
        df['display_name'] = df['first_name'].astype(str).str.strip()
        
        return df
    except Exception as e:
        st.error(f"Error loading {class_sheet}: {e}")
        return None

# --- UI CONTROLS ---
# Automatically read exact sheet names from the Excel file
try:
    xls = pd.ExcelFile(EXCEL_FILE)
    available_classes = xls.sheet_names 
except Exception as e:
    st.error(f"Could not read the Excel file. Make sure 'students.xlsx' is uploaded. Error: {e}")
    available_classes = []

# ✅ THIS IS CORRECT (Separated by a line break)
if available_classes:
    sel_class = st.selectbox("Select Class Sheet", available_classes)
    
    sel_subject = st.selectbox("Subject", ["Hindi", "English", "Math", "Science", "Social Science","G. K.","Moral","Computer","Sanskrit","Art", "P.T.", "Craft", "Hindi Written", "English Written", "Math Written", "Hindi Oral", "English Oral", "Math Oral"])

exam_mode = st.radio("Entry Type", ["1st Term Test (Max 20)", "Quarterly Examination (Max 80)", "2nd Term Test (Max 20)", "Half Yearly Examination (Max 80)", "3rd Term Test (Max 20)", "Annual Examination (Max 80)"], horizontal=True)
max_val, pass_val = (80, 27) if "Quarterly" in exam_mode else (20, 7)

df_students = load_and_clean_excel(sel_class)

if df_students is not None:
    with st.form("entry_form"):
        batch_data = []
        for i, row in df_students.iterrows():
            st.write(f"**{row['display_name']}** (Adm: {row['admission_no']})")
            
            # Entering only the marks; Status and Note are automated
            mark = st.number_input(f"Marks", 0, max_val, 0, key=f"m_{i}")
            
            # --- THE 4 COLUMNS YOU REQUESTED ---
            status = 1 if mark >= pass_val else 0
            note = "Good" if status == 1 else "Fail"
            
            batch_data.append([
                datetime.now().strftime("%Y-%m-%d"),
                sel_class,
                sel_subject,
                exam_mode,
                row['admission_no'], # Column 1
                mark,                # Column 2
                status,              # Column 3
                note                 # Column 4
            ])
            st.divider()

        if st.form_submit_button("SAVE ALL TO GOOGLE SHEETS"):
            client = get_gsheet_client()
            if client:
                sheet = client.open(SHEET_NAME_GS).sheet1
                sheet.append_rows(batch_data)
                st.success(f"Uploaded {len(batch_data)} records to the cloud!")
                st.balloons()

# --- EMERGENCY BACKUP SECTION ---
st.divider()
st.subheader("💾 Admin Tools")

if st.button("Fetch Database Backup"):
    client = get_gsheet_client()
    if client:
        try:
            sheet = client.open(SHEET_NAME_GS).sheet1
            # Get all data from the sheet
            all_data = sheet.get_all_records()
            if all_data:
                # Convert to pandas dataframe
                df_backup = pd.DataFrame(all_data)
                
                # Create the download button
                st.download_button(
                    label="📥 Download Full Database as CSV",
                    data=df_backup.to_csv(index=False).encode('utf-8'),
                    file_name=f"Apex_Marks_Backup_{datetime.now().strftime('%Y-%m-%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("The database is currently empty.")
        except Exception as e:
            st.error(f"Could not fetch backup. Error: {e}")