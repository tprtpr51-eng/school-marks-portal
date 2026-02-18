import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- CONFIGURATION ---
EXAMS = ["Unit Test 1", "Midterm", "Unit Test 2", "Final", "Practical"]
# Updated subject list
SUBJECTS = ["Math", "Physics", "Chemistry", "Biology", "English", "Hindi", "History", "Geography", "CS"]

st.set_page_config(page_title="Marks Entry Portal", layout="centered")

# --- DATA LOADING WITH SAFETY CHECKS ---
def load_students():
    if os.path.exists("students.csv"):
        try:
            # Load the CSV
            df = pd.read_csv("students.csv")
            
            # SAFETY CLEANING: Remove hidden spaces from column names
            df.columns = df.columns.str.strip()
            
            # ENSURE COLUMNS EXIST (Check for spelling)
            # This looks for any column containing 'Class', 'Adm', or 'Name'
            col_map = {}
            for col in df.columns:
                if 'class' in col.lower(): col_map['Class'] = col
                if 'adm' in col.lower(): col_map['AdmissionNo'] = col
                if 'name' in col.lower(): col_map['Name'] = col
            
            # Rename them to our standard names
            df = df.rename(columns=col_map)
            return df
        except Exception as e:
            st.error(f"Error reading CSV: {e}")
            return None
    else:
        st.error("Missing 'students.csv' file on GitHub!")
        return None

df_students = load_students()

# --- APP UI ---
st.title("📝 Student Marks Entry")

if df_students is not None:
    # Get unique classes from the cleaned 'Class' column
    try:
        classes = sorted(df_students['Class'].unique())
        
        # 1. Selection Header
        col1, col2, col3 = st.columns(3)
        sel_class = col1.selectbox("Class", classes)
        sel_exam = col2.selectbox("Exam", EXAMS)
        sel_subject = col3.selectbox("Subject", SUBJECTS)

        # Filter students for the selected class
        class_list = df_students[df_students['Class'] == sel_class]

        st.divider()
        st.subheader(f"{sel_subject} Entry - {sel_class}")
        st.caption(f"Exam: {sel_exam}")

        # 2. Entry Form
        with st.form("marks_entry_form", clear_on_submit=True):
            entry_rows = []
            
            for index, row in class_list.iterrows():
                # Mobile Layout
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{row['Name']}**")
                c1.caption(f"Adm: {row['AdmissionNo']}")
                
                # 'step=1' forces the numeric keypad on Android
                mark = c2.number_input("Marks", min_value=0, max_value=100, step=1, key=f"id_{row['AdmissionNo']}", label_visibility="collapsed")
                
                entry_rows.append({
                    "Timestamp": datetime.now().strftime("%Y-%m-%d