import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- SETTINGS ---
# You can add more exams or subjects here later
EXAMS = ["Unit Test 1", "Midterm", "Unit Test 2", "Final", "Practical"]
SUBJECTS = ["Math", "Physics", "Chemistry", "Biology", "English", "Hindi", "History", "Geography", "CS"]

st.set_page_config(page_title="School Marks Portal", layout="centered")

# --- LOAD STUDENT LIST ---
def load_students():
    if os.path.exists("students.csv"):
        return pd.read_csv("students.csv")
    else:
        st.error("Error: 'students.csv' not found. Please upload it to GitHub.")
        return None

df_students = load_students()

# --- APP UI ---
st.title("📝 Student Marks Entry")
st.markdown("Enter marks below. The data will be saved to the master database.")

if df_students is not None:
    # 1. Filters (Top of screen)
    classes = df_students['Class'].unique()
    
    col1, col2, col3 = st.columns(3)
    sel_class = col1.selectbox("Class", classes)
    sel_exam = col2.selectbox("Exam", EXAMS)
    sel_subject = col3.selectbox("Subject", SUBJECTS)

    # Filter students for the selected class
    class_list = df_students[df_students['Class'] == sel_class]

    st.divider()
    st.subheader(f"Entering: {sel_subject} ({sel_exam})")

    # 2. Entry Form
    with st.form("marks_entry_form", clear_on_submit=True):
        entry_rows = []
        
        for index, row in class_list.iterrows():
            # Mobile-friendly layout: Name on left, Box on right
            c1, c2 = st.columns([3, 1])
            c1.write(f"**{row['Name']}**")
            c1.caption(f"Adm: {row['AdmissionNo']}")
            
            # Use 'step=1' to trigger numeric keypad on Android
            mark = c2.number_input("Marks", min_value=0, max_value=100, step=1, key=f"id_{row['AdmissionNo']}", label_visibility="collapsed")
            
            entry_rows.append({
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Class": sel_class,
                "AdmissionNo": row['AdmissionNo'],
                "Name": row['Name'],
                "Subject": sel_subject,
                "Exam": sel_exam,
                "Marks": mark
            })
            st.write("---")

        # Big submit button for thumbs on mobile
        submitted = st.form_submit_button("SUBMIT MARKS", use_container_width=True)

    # 3. Saving Logic
    if submitted:
        new_data = pd.DataFrame(entry_rows)
        master_file = "master_marks.csv"
        
        # Check if file exists to append or create new
        if os.path.exists(master_file):
            new_data.to_csv(master_file, mode='a', header=False, index=False)
        else:
            new_data.to_csv(master_file, index=False)
            
        st.success(f"Done! {len(entry_rows)} records saved.")
        st.balloons()

    # 4. Data Download (For your use)
    if os.path.exists("master_marks.csv"):
        with st.expander("Admin: Download Recorded Data"):
            all_data = pd.read_csv("master_marks.csv")
            st.dataframe(all_data.tail(10)) # Show last 10 entries
            st.download_button("Download Full CSV for Excel", data=all_data.to_csv(index=False), file_name="final_marks.csv")