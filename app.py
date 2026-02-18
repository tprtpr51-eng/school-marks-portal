import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- SETTINGS ---
EXAMS = ["Unit Test 1", "Midterm", "Unit Test 2", "Final", "Practical"]
SUBJECTS = ["Math", "Physics", "Chemistry", "Biology", "English", "Hindi", "History", "Geography", "CS"]

st.set_page_config(page_title="Marks Portal", layout="centered")

# --- DATA LOADING ---
def load_students():
    if not os.path.exists("students.csv"):
        st.error("Missing 'students.csv' on GitHub!")
        return None
    try:
        df = pd.read_csv("students.csv")
        # Clean white spaces from headers
        df.columns = df.columns.str.strip()
        
        # Mapping logic: Find column regardless of Case or Dots
        new_cols = {}
        for c in df.columns:
            low_c = c.lower()
            if 'class' in low_c: new_cols[c] = 'Class'
            elif 'adm' in low_c: new_cols[c] = 'AdmissionNo'
            elif 'name' in low_c: new_cols[c] = 'Name'
        
        df = df.rename(columns=new_cols)
        return df
    except Exception as e:
        st.error(f"CSV Error: {e}")
        return None

df_students = load_students()

# --- UI START ---
st.title("📝 Student Marks Entry")

if df_students is not None:
    try:
        # Check if we successfully mapped the columns
        if 'Class' not in df_students.columns:
            st.error("Could not find 'Class' column. Please check your CSV headers.")
            st.write("Found columns:", list(df_students.columns))
        else:
            # 1. Top Selectors
            classes = sorted(df_students['Class'].unique())
            c1, c2, c3 = st.columns(3)
            sel_class = c1.selectbox("Class", classes)
            sel_exam = c2.selectbox("Exam", EXAMS)
            sel_subject = c3.selectbox("Subject", SUBJECTS)

            # Filter students
            class_list = df_students[df_students['Class'] == sel_class]
            
            st.divider()
            st.subheader(f"{sel_subject} | {sel_class}")

            # 2. Entry Form
            with st.form("marks_form", clear_on_submit=True):
                entry_rows = []
                
                for i, row in class_list.iterrows():
                    col_name, col_input = st.columns([3, 1])
                    col_name.write(f"**{row.get('Name', 'Unknown')}**")
                    col_name.caption(f"Adm: {row.get('AdmissionNo', 'N/A')}")
                    
                    val = col_input.number_input("Mark", 0, 100, 0, 1, key=f"k_{i}", label_visibility="collapsed")
                    
                    record = {
                        "Time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Class": sel_class,
                        "AdmNo": row.get('AdmissionNo', 'N/A'),
                        "Name": row.get('Name', 'Unknown'),
                        "Subject": sel_subject,
                        "Exam": sel_exam,
                        "Mark": val
                    }
                    entry_rows.append(record)
                    st.write("---")

                submitted = st.form_submit_button("SUBMIT ALL", use_container_width=True)

            # 3. Save Data
            if submitted:
                final_df = pd.DataFrame(entry_rows)
                fname = "master_marks.csv"
                if os.path.exists(fname):
                    final_df.to_csv(fname, mode='a', header=False, index=False)
                else:
                    final_df.to_csv(fname, index=False)
                st.success("Marks Saved Successfully!")
                st.balloons()

    except Exception as err:
        st.error(f"Internal Error: {err}")

    # 4. Download for Admin
    if os.path.exists("master_marks.csv"):
        with st.expander("Admin: Download Data"):
            db = pd.read_csv("master_marks.csv")
            st.download_button("Download CSV", db.to_csv(index=False), "marks.csv")