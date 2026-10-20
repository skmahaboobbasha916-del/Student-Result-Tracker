
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import mysql.connector
import html
import math
import webbrowser
from datetime import datetime
from pathlib import Path


# ==================== DATABASE CONNECTION ====================

root = tk.Tk()
root.withdraw()
root.update_idletasks()

password = simpledialog.askstring(
    "Database Login",
    "Enter your MySQL root password:",
    show="*",
    parent=root
)

if password is None:
    root.destroy()
    raise SystemExit

try:
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password=password,
        database="student_result_tracker",
        connection_timeout=5
    )
except mysql.connector.Error as error:
    messagebox.showerror("Database Error", str(error), parent=root)
    root.destroy()
    raise SystemExit

root.deiconify()


# ==================== RESULT CALCULATION ====================

def calculate_result(python_marks, mysql_marks, java_marks):
    total = python_marks + mysql_marks + java_marks
    percentage = total / 300 * 100

    if percentage >= 90:
        grade = "A+"
    elif percentage >= 80:
        grade = "A"
    elif percentage >= 70:
        grade = "B"
    elif percentage >= 60:
        grade = "C"
    elif percentage >= 35:
        grade = "D"
    else:
        grade = "F"

    result = (
        "Pass"
        if min(python_marks, mysql_marks, java_marks) >= 35
        else "Fail"
    )

    return total, percentage, grade, result


# ==================== HELPER FUNCTIONS ====================

def get_student_values():
    student_id = id_entry.get().strip()
    name = name_entry.get().strip()
    branch = branch_entry.get().strip().upper()

    # Validate required fields individually so the user knows exactly
    # which field needs to be completed.
    if not student_id:
        messagebox.showwarning(
            "Missing Student ID",
            "Please enter Student ID."
        )
        id_entry.focus_set()
        return None

    if not name:
        messagebox.showwarning(
            "Missing Student Name",
            "Please enter Student Name."
        )
        name_entry.focus_set()
        return None

    if not branch:
        messagebox.showwarning(
            "Missing Branch",
            "Please enter Branch."
        )
        branch_entry.focus_set()
        return None

    if len(student_id) > 20:
        messagebox.showwarning(
            "Invalid Student ID",
            "Student ID must not exceed 20 characters."
        )
        return None

    if len(name) > 100:
        messagebox.showwarning(
            "Invalid Name",
            "Student name must not exceed 100 characters."
        )
        return None

    if not any(character.isalpha() for character in name):
        messagebox.showwarning(
            "Invalid Name",
            "Student name must contain at least one letter."
        )
        return None

    if len(branch) > 20:
        messagebox.showwarning(
            "Invalid Branch",
            "Branch must not exceed 20 characters."
        )
        return None

    # Store the normalized branch name in uppercase.
    branch_entry.delete(0, tk.END)
    branch_entry.insert(0, branch)

    try:
        raw_marks = [
            python_entry.get().strip(),
            mysql_entry.get().strip(),
            java_entry.get().strip()
        ]
        if any(value == "" for value in raw_marks):
            raise ValueError

        marks = [float(value) for value in raw_marks]

        if any(not math.isfinite(mark) for mark in marks):
            messagebox.showwarning(
                "Invalid Marks",
                "Marks must be finite numbers between 0 and 100."
            )
            return None

        if any(mark < 0 or mark > 100 for mark in marks):
            messagebox.showwarning(
                "Invalid Marks",
                "Marks must be between 0 and 100."
            )
            return None

    except ValueError:
        messagebox.showwarning(
            "Invalid Marks",
            "Enter valid numeric marks for all three subjects."
        )
        return None

    return (
        student_id, name, branch,
        marks[0], marks[1], marks[2]
    )


def clear_fields():
    for entry in entries:
        entry.delete(0, tk.END)

    student_table.selection_remove(student_table.selection())


def update_dashboard():
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM students")
        total = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(DISTINCT branch) FROM students"
        )
        branches = cursor.fetchone()[0]

        student_count_label.config(text=f"Total Students: {total}")
        branch_count_label.config(text=f"Total Branches: {branches}")

    finally:
        cursor.close()


def load_branches():
    cursor = connection.cursor()

    try:
        cursor.execute(
            "SELECT DISTINCT branch FROM students ORDER BY branch"
        )
        branches = [row[0] for row in cursor.fetchall()]

        branch_filter["values"] = ["All Branches"] + branches

        if branch_filter.get() not in branch_filter["values"]:
            branch_filter.set("All Branches")

    finally:
        cursor.close()


# ==================== SEARCH AND DISPLAY ====================

def load_students():
    search_text = search_entry.get().strip()
    selected_branch = branch_filter.get()

    query = """
        SELECT student_id, student_name, branch,
               python_marks, mysql_marks, java_marks
        FROM students
        WHERE 1=1
    """
    parameters = []

    if search_text:
        query += """
            AND (student_id LIKE %s OR student_name LIKE %s)
        """
        pattern = f"%{search_text}%"
        parameters.extend([pattern, pattern])

    if selected_branch and selected_branch != "All Branches":
        query += " AND branch = %s"
        parameters.append(selected_branch)

    query += " ORDER BY student_id"

    cursor = None

    try:
        cursor = connection.cursor()
        cursor.execute(query, parameters)
        records = cursor.fetchall()

        student_table.delete(*student_table.get_children())

        for record in records:
            student_id, name, branch, py, my, java = record

            total, percentage, grade, result = calculate_result(
                float(py), float(my), float(java)
            )

            student_table.insert(
                "",
                tk.END,
                values=(
                    student_id, name, branch,
                    py, my, java, total,
                    f"{percentage:.2f}%",
                    grade, result
                )
            )

    except mysql.connector.Error as error:
        messagebox.showerror("Database Error", str(error))

    finally:
        if cursor is not None:
            cursor.close()

    try:
        load_branches()
        update_dashboard()
    except mysql.connector.Error as error:
        messagebox.showerror("Database Error", str(error))


def show_all_students():
    search_entry.delete(0, tk.END)
    branch_filter.set("All Branches")
    load_students()


# ==================== PERFORMANCE ANALYTICS ====================

def show_analytics():
    """Calculate analytics from every student in the database."""

    cursor = None

    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT student_id, student_name, branch,
                   python_marks, mysql_marks, java_marks
            FROM students
            ORDER BY student_id
        """)
        records = cursor.fetchall()

    except mysql.connector.Error as error:
        messagebox.showerror("Analytics Error", str(error))
        return

    finally:
        if cursor is not None:
            cursor.close()

    if not records:
        messagebox.showinfo(
            "No Data",
            "Add student records before viewing performance analytics."
        )
        return

    students = []

    for record in records:
        student_id, name, branch, py, my, java = record

        py, my, java = float(py), float(my), float(java)
        total, percentage, grade, result = calculate_result(py, my, java)

        students.append({
            "id": student_id,
            "name": name,
            "branch": branch,
            "python": py,
            "mysql": my,
            "java": java,
            "total": total,
            "percentage": percentage,
            "grade": grade,
            "result": result
        })

    count = len(students)
    class_average = sum(s["percentage"] for s in students) / count
    passed = sum(1 for s in students if s["result"] == "Pass")
    failed = count - passed
    pass_percentage = passed / count * 100

    # Highest and lowest are based on overall percentage.
    highest = max(students, key=lambda s: s["percentage"])
    lowest = min(students, key=lambda s: s["percentage"])

    subject_averages = {
        "Python": sum(s["python"] for s in students) / count,
        "MySQL": sum(s["mysql"] for s in students) / count,
        "Java": sum(s["java"] for s in students) / count
    }

    # Collect branch-wise student counts and averages.
    branch_data = {}

    for student in students:
        branch = student["branch"]

        if branch not in branch_data:
            branch_data[branch] = {
                "count": 0,
                "total_percentage": 0.0,
                "passed": 0
            }

        branch_data[branch]["count"] += 1
        branch_data[branch]["total_percentage"] += student["percentage"]

        if student["result"] == "Pass":
            branch_data[branch]["passed"] += 1

    for branch, data in branch_data.items():
        data["average"] = (
            data["total_percentage"] / data["count"]
        )
        data["pass_percentage"] = (
            data["passed"] / data["count"] * 100
        )

    # Create the analytics window.
    window = tk.Toplevel(root)
    window.title("Student Performance Analytics")
    window.geometry("1120x820")
    window.minsize(850, 650)
    window.configure(bg="#F1F5F9")

    tk.Label(
        window,
        text="STUDENT PERFORMANCE ANALYTICS",
        font=("Arial", 19, "bold"),
        bg="#142D4E",
        fg="white",
        pady=16
    ).pack(fill="x")

    tk.Label(
        window,
        text=(
            "Overview of all student records in MySQL. "
            "Analytics are independent of the current table search."
        ),
        bg="#F1F5F9",
        fg="#475569",
        font=("Arial", 10)
    ).pack(pady=10)

    # Scrollable content allows the dashboard to fit smaller screens.
    outer = tk.Frame(window, bg="#F1F5F9")
    outer.pack(fill="both", expand=True, padx=15, pady=5)

    canvas = tk.Canvas(
        outer, bg="#F1F5F9", highlightthickness=0
    )
    scrollbar = ttk.Scrollbar(
        outer, orient="vertical", command=canvas.yview
    )
    content = tk.Frame(canvas, bg="#F1F5F9")

    content_window = canvas.create_window(
        (0, 0), window=content, anchor="nw"
    )

    content.bind(
        "<Configure>",
        lambda event: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )

    canvas.bind(
        "<Configure>",
        lambda event: canvas.itemconfigure(
            content_window, width=event.width
        )
    )

    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def create_card(parent, title, value, color, column):
        card = tk.Frame(
            parent,
            bg="white",
            padx=12,
            pady=12,
            highlightbackground="#D7DFEA",
            highlightthickness=1
        )
        card.grid(
            row=0, column=column, padx=5, pady=5, sticky="nsew"
        )

        tk.Label(
            card,
            text=title,
            font=("Arial", 10),
            bg="white",
            fg="#64748B"
        ).pack(anchor="w")

        tk.Label(
            card,
            text=value,
            font=("Arial", 17, "bold"),
            bg="white",
            fg=color
        ).pack(anchor="w", pady=(6, 0))

    # Four summary cards.
    cards = tk.Frame(content, bg="#F1F5F9")
    cards.pack(fill="x", pady=5)

    for column in range(4):
        cards.columnconfigure(column, weight=1)

    create_card(
        cards, "Total Students", str(count), "#142D4E", 0
    )
    create_card(
        cards, "Class Average", f"{class_average:.2f}%",
        "#2878B5", 1
    )
    create_card(
        cards, "Pass Percentage", f"{pass_percentage:.2f}%",
        "#16856B", 2
    )
    create_card(
        cards, "Failed Students", str(failed),
        "#C74440", 3
    )

    # Highest and lowest scoring students.
    scorer_frame = tk.LabelFrame(
        content,
        text="Student Performance Highlights",
        font=("Arial", 11, "bold"),
        bg="white",
        padx=12,
        pady=10
    )
    scorer_frame.pack(fill="x", padx=5, pady=10)

    tk.Label(
        scorer_frame,
        text=(
            f"Highest Scorer: {highest['name']} "
            f"({highest['id']}) — {highest['percentage']:.2f}%"
        ),
        bg="white",
        fg="#16856B",
        font=("Arial", 11, "bold"),
        anchor="w"
    ).pack(fill="x", pady=4)

    tk.Label(
        scorer_frame,
        text=(
            f"Lowest Scorer: {lowest['name']} "
            f"({lowest['id']}) — {lowest['percentage']:.2f}%"
        ),
        bg="white",
        fg="#C74440",
        font=("Arial", 11, "bold"),
        anchor="w"
    ).pack(fill="x", pady=4)

    tk.Label(
        scorer_frame,
        text=f"Passed: {passed}     Failed: {failed}",
        bg="white",
        fg="#334155",
        font=("Arial", 10)
    ).pack(anchor="w", pady=4)

    # Draw a bar chart on a Tkinter Canvas.
    def draw_bar_chart(chart_canvas, data, maximum, suffix="%"):
        chart_canvas.delete("all")

        width = max(chart_canvas.winfo_width(), 400)
        height = max(chart_canvas.winfo_height(), 200)

        left = 100
        right = width - 35
        top = 28
        bottom = height - 35
        chart_width = right - left
        chart_height = bottom - top

        if not data:
            chart_canvas.create_text(
                width / 2, height / 2,
                text="No data available"
            )
            return

        # Horizontal guide lines and scale labels.
        for step in range(5):
            value = maximum * step / 4
            y = bottom - chart_height * step / 4

            chart_canvas.create_line(
                left, y, right, y,
                fill="#E2E8F0"
            )
            chart_canvas.create_text(
                left - 8, y,
                text=f"{value:.0f}{suffix}",
                anchor="e",
                font=("Arial", 8),
                fill="#64748B"
            )

        row_height = chart_height / len(data)
        bar_height = min(24, row_height * 0.58)

        for index, (label, value) in enumerate(data):
            center_y = top + row_height * (index + 0.5)
            bar_length = chart_width * max(0, value) / maximum

            chart_canvas.create_text(
                left - 12, center_y,
                text=str(label)[:14],
                anchor="e",
                font=("Arial", 9),
                fill="#334155"
            )

            chart_canvas.create_rectangle(
                left,
                center_y - bar_height / 2,
                left + bar_length,
                center_y + bar_height / 2,
                fill="#2878B5",
                outline=""
            )

            value_x = min(left + bar_length + 5, right - 2)

            chart_canvas.create_text(
                value_x,
                center_y,
                text=f"{value:.1f}{suffix}",
                anchor="w" if value_x < right - 35 else "e",
                font=("Arial", 9, "bold"),
                fill="#142D4E"
            )

    # Subject averages.
    subject_frame = tk.LabelFrame(
        content,
        text="Subject-wise Average Marks (out of 100)",
        font=("Arial", 11, "bold"),
        bg="white",
        padx=10,
        pady=10
    )
    subject_frame.pack(fill="x", padx=5, pady=5)

    subject_chart = tk.Canvas(
        subject_frame,
        height=180,
        bg="white",
        highlightthickness=0
    )
    subject_chart.pack(fill="x", expand=True)

    subject_data = list(subject_averages.items())

    def redraw_subject_chart(event=None):
        draw_bar_chart(subject_chart, subject_data, 100, "")

    subject_chart.bind("<Configure>", redraw_subject_chart)

    # Branch average comparison.
    branch_frame = tk.LabelFrame(
        content,
        text="Branch-wise Average Percentage",
        font=("Arial", 11, "bold"),
        bg="white",
        padx=10,
        pady=10
    )
    branch_frame.pack(fill="x", padx=5, pady=10)

    branch_chart = tk.Canvas(
        branch_frame,
        height=max(180, min(420, 55 * len(branch_data) + 60)),
        bg="white",
        highlightthickness=0
    )
    branch_chart.pack(fill="x", expand=True)

    branch_chart_data = [
        (branch, data["average"])
        for branch, data in sorted(branch_data.items())
    ]

    def redraw_branch_chart(event=None):
        draw_bar_chart(branch_chart, branch_chart_data, 100, "%")

    branch_chart.bind("<Configure>", redraw_branch_chart)

    # Branch summary table.
    branch_table_frame = tk.LabelFrame(
        content,
        text="Branch Summary",
        font=("Arial", 11, "bold"),
        bg="white",
        padx=10,
        pady=10
    )
    branch_table_frame.pack(fill="x", padx=5, pady=5)

    branch_columns = (
        "branch", "count", "average", "passed", "pass_percentage"
    )

    branch_table = ttk.Treeview(
        branch_table_frame,
        columns=branch_columns,
        show="headings",
        height=min(8, len(branch_data))
    )

    branch_headings = {
        "branch": "Branch",
        "count": "Students",
        "average": "Average %",
        "passed": "Passed",
        "pass_percentage": "Pass %"
    }

    for column in branch_columns:
        branch_table.heading(column, text=branch_headings[column])
        branch_table.column(
            column, width=140, anchor="center"
        )

    for branch, data in sorted(branch_data.items()):
        branch_table.insert(
            "",
            tk.END,
            values=(
                branch,
                data["count"],
                f"{data['average']:.2f}%",
                data["passed"],
                f"{data['pass_percentage']:.2f}%"
            )
        )

    branch_table.pack(fill="x")

    tk.Label(
        content,
        text=(
            "Note: A student passes only when all three subject marks "
            "are at least 35. Highest and lowest scorers are determined "
            "by overall percentage."
        ),
        bg="#F1F5F9",
        fg="#64748B",
        wraplength=900,
        justify="left"
    ).pack(fill="x", padx=5, pady=12)

    tk.Button(
        window,
        text="Close Analytics",
        command=window.destroy,
        bg="#142D4E",
        fg="white",
        font=("Arial", 10, "bold"),
        width=18
    ).pack(pady=10)


# ==================== STUDENT REPORT CARD ====================

def generate_report_card():
    selected = student_table.selection()

    if not selected:
        messagebox.showwarning(
            "Select Student",
            "Select a student from the table before generating a report."
        )
        return

    student_id = student_table.item(selected[0], "values")[0]
    cursor = None

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT student_id, student_name, branch,
                   python_marks, mysql_marks, java_marks
            FROM students
            WHERE student_id = %s
            """,
            (student_id,)
        )
        student = cursor.fetchone()

        if student is None:
            messagebox.showwarning(
                "Student Not Found",
                "This student no longer exists in the database."
            )
            load_students()
            return

    except mysql.connector.Error as error:
        messagebox.showerror("Database Error", str(error))
        return

    finally:
        if cursor is not None:
            cursor.close()

    student_id, name, branch, py, my, java = student
    py, my, java = float(py), float(my), float(java)

    total, percentage, grade, result = calculate_result(py, my, java)
    generated_on = datetime.now().strftime("%d %B %Y, %I:%M %p")

    safe_id = html.escape(str(student_id))
    safe_name = html.escape(str(name))
    safe_branch = html.escape(str(branch))
    safe_result = html.escape(result)
    safe_grade = html.escape(grade)

    report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Student Report Card - {safe_id}</title>
<style>
body {{
    font-family: Arial, sans-serif;
    background: #f1f5f9;
    color: #1e293b;
    margin: 0;
    padding: 30px;
}}
.report {{
    max-width: 750px;
    margin: auto;
    background: white;
    padding: 35px;
    border: 2px solid #142d4e;
    border-radius: 10px;
}}
h1 {{ text-align: center; color: #142d4e; }}
.subtitle {{ text-align: center; color: #64748b; margin-bottom: 30px; }}
.student-details {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    padding: 18px;
    background: #f1f5f9;
}}
.label {{ color: #64748b; font-size: 13px; }}
.value {{ font-size: 16px; font-weight: bold; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 25px; }}
th, td {{ border: 1px solid #cbd5e1; padding: 13px; text-align: center; }}
th {{ background: #142d4e; color: white; }}
.summary {{ margin-top: 25px; padding: 20px; background: #eaf2ff; line-height: 1.9; }}
.result {{ font-size: 20px; font-weight: bold;
    color: {"#16856b" if result == "Pass" else "#c74440"}; }}
.footer {{ margin-top: 35px; text-align: center; font-size: 12px; color: #64748b; }}
@media print {{
    body {{ background: white; padding: 0; }}
    .report {{ border: 1px solid #142d4e; border-radius: 0; padding: 20px; }}
}}
</style>
</head>
<body>
<div class="report">
<h1>STUDENT REPORT CARD</h1>
<div class="subtitle">Student Result Tracker</div>
<div class="student-details">
<div><div class="label">Student ID</div><div class="value">{safe_id}</div></div>
<div><div class="label">Student Name</div><div class="value">{safe_name}</div></div>
<div><div class="label">Branch</div><div class="value">{safe_branch}</div></div>
<div><div class="label">Report Generated</div><div class="value">{generated_on}</div></div>
</div>
<table>
<thead><tr><th>Subject</th><th>Marks Obtained</th><th>Maximum Marks</th></tr></thead>
<tbody>
<tr><td>Python</td><td>{py:g}</td><td>100</td></tr>
<tr><td>MySQL</td><td>{my:g}</td><td>100</td></tr>
<tr><td>Java</td><td>{java:g}</td><td>100</td></tr>
<tr><th>Total</th><th>{total:g}</th><th>300</th></tr>
</tbody>
</table>
<div class="summary">
<div><strong>Percentage:</strong> {percentage:.2f}%</div>
<div><strong>Grade:</strong> {safe_grade}</div>
<div><strong>Result:</strong> <span class="result">{safe_result}</span></div>
</div>
<div class="footer">Generated by Student Result Tracker</div>
</div>
</body>
</html>
"""

    report_window = tk.Toplevel(root)
    report_window.title(f"Report Card - {student_id}")
    report_window.geometry("700x650")
    report_window.minsize(500, 450)
    report_window.configure(bg="#F1F5F9")

    tk.Label(
        report_window,
        text="STUDENT REPORT CARD",
        font=("Arial", 18, "bold"),
        bg="#142D4E",
        fg="white",
        pady=15
    ).pack(fill="x")

    details_frame = tk.Frame(
        report_window, bg="white", padx=20, pady=15
    )
    details_frame.pack(fill="x", padx=15, pady=15)

    detail_lines = [
        ("Student ID", student_id),
        ("Student Name", name),
        ("Branch", branch),
        ("Python Marks", f"{py:g} / 100"),
        ("MySQL Marks", f"{my:g} / 100"),
        ("Java Marks", f"{java:g} / 100"),
        ("Total Marks", f"{total:g} / 300"),
        ("Percentage", f"{percentage:.2f}%"),
        ("Grade", grade),
        ("Final Result", result),
        ("Generated On", generated_on)
    ]

    for row_index, (label, value) in enumerate(detail_lines):
        tk.Label(
            details_frame, text=f"{label}:",
            font=("Arial", 10, "bold"), bg="white", anchor="w"
        ).grid(row=row_index, column=0, sticky="w", padx=8, pady=5)

        value_color = (
            "#16856B" if value == "Pass"
            else "#C74440" if value == "Fail"
            else "#142D4E"
        )

        tk.Label(
            details_frame, text=str(value),
            font=("Arial", 10), bg="white",
            fg=value_color, anchor="w"
        ).grid(row=row_index, column=1, sticky="w", padx=12, pady=5)

    details_frame.columnconfigure(1, weight=1)

    tk.Label(
        report_window,
        text="Save the report as an HTML file to open it in your browser and print it.",
        bg="#F1F5F9", fg="#475569", wraplength=620
    ).pack(pady=5)

    report_buttons = tk.Frame(report_window, bg="#F1F5F9")
    report_buttons.pack(fill="x", padx=15, pady=12)

    def save_report():
        file_path = filedialog.asksaveasfilename(
            parent=report_window,
            title="Save Student Report Card",
            defaultextension=".html",
            initialfile=f"Report_Card_{student_id}.html",
            filetypes=[("HTML Report", "*.html"), ("All Files", "*.*")]
        )

        if not file_path:
            return

        try:
            Path(file_path).write_text(report_html, encoding="utf-8")
            webbrowser.open_new_tab(Path(file_path).resolve().as_uri())

            messagebox.showinfo(
                "Report Saved",
                f"Report card saved successfully:\n\n{file_path}\n\n"
                "Press Ctrl+P in your browser to print it.",
                parent=report_window
            )
        except (OSError, webbrowser.Error) as error:
            messagebox.showerror(
                "Save/Open Error", str(error), parent=report_window
            )

    tk.Button(
        report_buttons,
        text="Save Report & Open",
        command=save_report,
        bg="#16856B",
        fg="white",
        font=("Arial", 10, "bold"),
        width=22
    ).pack(side="left", padx=5)

    tk.Button(
        report_buttons, text="Close",
        command=report_window.destroy, width=12
    ).pack(side="right", padx=5)


# ==================== ADD STUDENT ====================

def add_student():
    values = get_student_values()

    if values is None:
        return

    cursor = None

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO students
            (student_id, student_name, branch,
             python_marks, mysql_marks, java_marks)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            values
        )
        connection.commit()

        messagebox.showinfo("Success", "Student added successfully!")
        clear_fields()
        load_students()

    except mysql.connector.Error as error:
        connection.rollback()

        # MySQL error 1062 means a duplicate value for a UNIQUE/PRIMARY KEY.
        if error.errno == 1062:
            messagebox.showwarning(
                "Duplicate Student ID",
                f"Student ID '{values[0]}' already exists!\n"
                "Please enter a different Student ID."
            )
        else:
            messagebox.showerror(
                "Database Error",
                f"An unexpected database error occurred:\n{error}"
            )

    finally:
        if cursor is not None:
            cursor.close()


# ==================== SELECT STUDENT ====================

def select_student(event=None):
    selected = student_table.selection()

    if not selected:
        return

    values = student_table.item(selected[0], "values")

    for entry, value in zip(entries, values[:6]):
        entry.delete(0, tk.END)
        entry.insert(0, value)


# ==================== UPDATE STUDENT ====================

def update_student():
    values = get_student_values()

    if values is None:
        return

    cursor = None

    try:
        cursor = connection.cursor()

        # Check existence separately because MySQL may report rowcount 0
        # when the student exists but the submitted values are unchanged.
        cursor.execute(
            "SELECT 1 FROM students WHERE student_id = %s",
            (values[0],)
        )
        if cursor.fetchone() is None:
            messagebox.showwarning(
                "Not Found",
                f"Student ID {values[0]} does not exist. Select an existing "
                "student or use Add Student to create a new record."
            )
            return

        cursor.execute(
            """
            UPDATE students
            SET student_name=%s, branch=%s,
                python_marks=%s, mysql_marks=%s, java_marks=%s
            WHERE student_id=%s
            """,
            (
                values[1], values[2], values[3],
                values[4], values[5], values[0]
            )
        )
        connection.commit()

        messagebox.showinfo("Success", "Student updated successfully!")
        clear_fields()
        load_students()

    except mysql.connector.Error as error:
        connection.rollback()
        messagebox.showerror("Database Error", str(error))

    finally:
        if cursor is not None:
            cursor.close()


# ==================== DELETE STUDENT ====================

def delete_student():
    student_id = id_entry.get().strip()

    if not student_id:
        messagebox.showwarning("Missing ID", "Select a student first.")
        return

    if not messagebox.askyesno(
        "Confirm Delete", f"Delete student {student_id}?"
    ):
        return

    cursor = None

    try:
        cursor = connection.cursor()
        cursor.execute(
            "DELETE FROM students WHERE student_id=%s",
            (student_id,)
        )
        connection.commit()
        affected = cursor.rowcount

        if affected:
            messagebox.showinfo("Success", "Student deleted successfully!")
        else:
            messagebox.showwarning("Not Found", "Student ID not found.")

        clear_fields()
        load_students()

    except mysql.connector.Error as error:
        connection.rollback()
        messagebox.showerror("Database Error", str(error))

    finally:
        if cursor is not None:
            cursor.close()


# ==================== BULK ENTRY WINDOW ====================

def open_bulk_entry():
    bulk_window = tk.Toplevel(root)
    bulk_window.title("Bulk Student Entry")
    bulk_window.geometry("1050x550")
    bulk_window.minsize(850, 400)
    bulk_window.configure(bg="#F1F5F9")

    tk.Label(
        bulk_window, text="BULK STUDENT ENTRY",
        font=("Arial", 19, "bold"),
        bg="#142D4E", fg="white", pady=15
    ).pack(fill="x")

    tk.Label(
        bulk_window,
        text="Double-click a cell to edit it. Fill in student details and select Save All.",
        font=("Arial", 10), bg="#F1F5F9"
    ).pack(pady=10)

    table_container = tk.Frame(bulk_window, bg="white")
    table_container.pack(fill="both", expand=True, padx=15, pady=5)

    bulk_columns = (
        "student_id", "student_name", "branch",
        "python_marks", "mysql_marks", "java_marks"
    )

    bulk_headings = (
        "Student ID", "Student Name", "Branch",
        "Python Marks", "MySQL Marks", "Java Marks"
    )

    bulk_table = ttk.Treeview(
        table_container, columns=bulk_columns,
        show="headings", height=12
    )

    for column, heading in zip(bulk_columns, bulk_headings):
        bulk_table.heading(column, text=heading)
        bulk_table.column(
            column, width=155, minwidth=100, anchor="center"
        )

    scrollbar_y = ttk.Scrollbar(
        table_container, orient="vertical", command=bulk_table.yview
    )
    scrollbar_x = ttk.Scrollbar(
        table_container, orient="horizontal", command=bulk_table.xview
    )

    bulk_table.configure(
        yscrollcommand=scrollbar_y.set,
        xscrollcommand=scrollbar_x.set
    )

    bulk_table.grid(row=0, column=0, sticky="nsew")
    scrollbar_y.grid(row=0, column=1, sticky="ns")
    scrollbar_x.grid(row=1, column=0, sticky="ew")

    table_container.rowconfigure(0, weight=1)
    table_container.columnconfigure(0, weight=1)

    def add_row():
        bulk_table.insert("", tk.END, values=("", "", "", "", "", ""))

    for _ in range(5):
        add_row()

    active_editor = {"widget": None}

    def finish_edit(save=True):
        editor = active_editor["widget"]

        if editor is None:
            return

        if save:
            try:
                editor._save_value()
            except (tk.TclError, AttributeError):
                pass

        active_editor["widget"] = None

        try:
            editor.destroy()
        except tk.TclError:
            pass

    def edit_cell(event):
        finish_edit()

        row_id = bulk_table.identify_row(event.y)
        column_id = bulk_table.identify_column(event.x)

        if not row_id or not column_id:
            return

        column_index = int(column_id[1:]) - 1

        if not 0 <= column_index < len(bulk_columns):
            return

        cell_box = bulk_table.bbox(row_id, column_id)

        if not cell_box:
            return

        x, y, width, height = cell_box
        current_values = list(bulk_table.item(row_id, "values"))

        editor = tk.Entry(bulk_table, font=("Arial", 10))
        editor.place(x=x, y=y, width=width, height=height)
        editor.insert(0, current_values[column_index])
        editor.select_range(0, tk.END)
        editor.focus_set()

        def save_value():
            new_values = list(bulk_table.item(row_id, "values"))
            new_values[column_index] = editor.get().strip()
            bulk_table.item(row_id, values=tuple(new_values))

        editor._save_value = save_value
        active_editor["widget"] = editor

        editor.bind("<Return>", lambda event: finish_edit())
        editor.bind("<Escape>", lambda event: finish_edit(save=False))
        editor.bind("<FocusOut>", lambda event: finish_edit())

    bulk_table.bind("<Double-1>", edit_cell)

    bulk_buttons = tk.Frame(bulk_window, bg="#F1F5F9")
    bulk_buttons.pack(fill="x", padx=15, pady=12)

    tk.Button(
        bulk_buttons, text="+ Add Row", command=add_row,
        bg="#2878B5", fg="white", width=14
    ).pack(side="left", padx=5)

    def remove_selected_rows():
        selected_rows = bulk_table.selection()

        if not selected_rows:
            messagebox.showwarning(
                "Select Row", "Select one or more rows to remove.",
                parent=bulk_window
            )
            return

        for row_id in selected_rows:
            bulk_table.delete(row_id)

    tk.Button(
        bulk_buttons, text="Remove Selected Rows",
        command=remove_selected_rows,
        bg="#C74440", fg="white", width=20
    ).pack(side="left", padx=5)

    def save_all():
        finish_edit()

        records = []
        seen_ids = set()

        for row_id in bulk_table.get_children():
            values = [
                str(value).strip()
                for value in bulk_table.item(row_id, "values")
            ]

            if not any(values):
                continue

            if not all(values):
                messagebox.showwarning(
                    "Incomplete Row",
                    "Complete every field in each non-empty row.",
                    parent=bulk_window
                )
                return

            student_id, name, branch = values[:3]
            branch = branch.upper()

            if len(student_id) > 20:
                messagebox.showwarning(
                    "Invalid Student ID",
                    f"Student ID in a row must not exceed 20 characters: {student_id}",
                    parent=bulk_window
                )
                return

            if len(name) > 100 or not any(character.isalpha() for character in name):
                messagebox.showwarning(
                    "Invalid Name",
                    f"Student name for ID {student_id} must be at most 100 "
                    "characters and contain at least one letter.",
                    parent=bulk_window
                )
                return

            if len(branch) > 20:
                messagebox.showwarning(
                    "Invalid Branch",
                    f"Branch for ID {student_id} must not exceed 20 characters.",
                    parent=bulk_window
                )
                return

            if student_id in seen_ids:
                messagebox.showwarning(
                    "Duplicate ID",
                    f"Student ID {student_id} appears more than once.",
                    parent=bulk_window
                )
                return

            seen_ids.add(student_id)

            try:
                if any(value == "" for value in values[3:6]):
                    raise ValueError
                marks = [float(values[3]), float(values[4]), float(values[5])]
            except ValueError:
                messagebox.showwarning(
                    "Invalid Marks",
                    f"Enter valid numeric marks for {student_id}.",
                    parent=bulk_window
                )
                return

            if any(not math.isfinite(mark) for mark in marks):
                messagebox.showwarning(
                    "Invalid Marks",
                    f"Marks for {student_id} must be finite numbers from 0 to 100.",
                    parent=bulk_window
                )
                return

            if any(mark < 0 or mark > 100 for mark in marks):
                messagebox.showwarning(
                    "Invalid Marks",
                    f"Marks for {student_id} must be between 0 and 100.",
                    parent=bulk_window
                )
                return

            records.append((
                student_id, name, branch,
                marks[0], marks[1], marks[2]
            ))

        if not records:
            messagebox.showwarning(
                "No Records", "Enter at least one student before saving.",
                parent=bulk_window
            )
            return

        cursor = None

        try:
            cursor = connection.cursor()
            ids = [record[0] for record in records]
            placeholders = ", ".join(["%s"] * len(ids))

            cursor.execute(
                f"SELECT student_id FROM students WHERE student_id IN ({placeholders})",
                tuple(ids)
            )
            existing_ids = [row[0] for row in cursor.fetchall()]

            if existing_ids:
                messagebox.showerror(
                    "Duplicate Student ID",
                    "These IDs already exist:\n"
                    + ", ".join(existing_ids)
                    + "\n\nNo records were saved.",
                    parent=bulk_window
                )
                return

            cursor.executemany(
                """
                INSERT INTO students
                (student_id, student_name, branch,
                 python_marks, mysql_marks, java_marks)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                records
            )
            connection.commit()

            messagebox.showinfo(
                "Success",
                f"{len(records)} student record(s) saved successfully!",
                parent=bulk_window
            )

            load_students()
            bulk_window.destroy()

        except mysql.connector.Error as error:
            connection.rollback()
            messagebox.showerror(
                "Database Error",
                f"No records were saved.\n\n{error}",
                parent=bulk_window
            )

        finally:
            if cursor is not None:
                cursor.close()

    tk.Button(
        bulk_buttons, text="Save All", command=save_all,
        bg="#16856B", fg="white",
        font=("Arial", 10, "bold"), width=14
    ).pack(side="right", padx=5)

    tk.Button(
        bulk_buttons, text="Close", command=bulk_window.destroy,
        width=12
    ).pack(side="right", padx=5)


# ==================== MAIN WINDOW DESIGN ====================

root.title("Student Result Tracker")
root.geometry("1350x750")
root.minsize(1050, 650)
root.configure(bg="#F1F5F9")

tk.Label(
    root, text="STUDENT RESULT TRACKER",
    font=("Arial", 22, "bold"),
    bg="#142D4E", fg="white", pady=18
).pack(fill="x")


# ---------------- DASHBOARD ----------------

dashboard = tk.Frame(root, bg="#F1F5F9")
dashboard.pack(fill="x", padx=20, pady=10)

student_count_label = tk.Label(
    dashboard, text="Total Students: 0",
    font=("Arial", 12, "bold"),
    bg="#DCEAFE", fg="#142D4E", padx=20, pady=12
)
student_count_label.pack(side="left", padx=5)

branch_count_label = tk.Label(
    dashboard, text="Total Branches: 0",
    font=("Arial", 12, "bold"),
    bg="#D9F5EC", fg="#126B59", padx=20, pady=12
)
branch_count_label.pack(side="left", padx=5)


# ---------------- STUDENT FORM ----------------

form = tk.LabelFrame(
    root, text="Student Details",
    font=("Arial", 12, "bold"),
    bg="white", padx=12, pady=10
)
form.pack(fill="x", padx=20, pady=5)

entries = []

labels = [
    "Student ID", "Student Name", "Branch",
    "Python Marks", "MySQL Marks", "Java Marks"
]

for index, label_text in enumerate(labels):
    row = index // 3
    column = (index % 3) * 2

    tk.Label(form, text=label_text, bg="white").grid(
        row=row, column=column, padx=5, pady=7, sticky="w"
    )

    entry = tk.Entry(form, width=22)
    entry.grid(
        row=row, column=column + 1, padx=5, pady=7
    )
    entries.append(entry)

(
    id_entry, name_entry, branch_entry,
    python_entry, mysql_entry, java_entry
) = entries


# ---------------- ACTION BUTTONS ----------------

buttons = tk.Frame(root, bg="#F1F5F9")
buttons.pack(fill="x", padx=20, pady=8)

tk.Button(
    buttons, text="Add Student", command=add_student,
    bg="#16856B", fg="white", width=15
).pack(side="left", padx=5)

tk.Button(
    buttons, text="Update Student", command=update_student,
    bg="#2878B5", fg="white", width=15
).pack(side="left", padx=5)

tk.Button(
    buttons, text="Delete Student", command=delete_student,
    bg="#C74440", fg="white", width=15
).pack(side="left", padx=5)

tk.Button(
    buttons, text="Clear Fields", command=clear_fields,
    width=13
).pack(side="left", padx=5)

tk.Button(
    buttons, text="Bulk Student Entry", command=open_bulk_entry,
    bg="#7048A8", fg="white", width=19
).pack(side="left", padx=5)

tk.Button(
    buttons, text="Generate Report Card",
    command=generate_report_card,
    bg="#D97706", fg="white",
    font=("Arial", 9, "bold"), width=21
).pack(side="left", padx=5)

# NEW: PERFORMANCE ANALYTICS BUTTON
tk.Button(
    buttons, text="Performance Analytics",
    command=show_analytics,
    bg="#0F766E", fg="white",
    font=("Arial", 9, "bold"), width=21
).pack(side="left", padx=5)


# ---------------- SEARCH AND FILTER ----------------

search_frame = tk.LabelFrame(
    root, text="Search and Filter",
    bg="white", padx=10, pady=8
)
search_frame.pack(fill="x", padx=20, pady=5)

tk.Label(
    search_frame, text="Search ID or Name:", bg="white"
).pack(side="left", padx=5)

search_entry = tk.Entry(search_frame, width=22)
search_entry.pack(side="left", padx=5)

tk.Button(
    search_frame, text="Search", command=load_students
).pack(side="left", padx=5)

tk.Label(search_frame, text="Branch:", bg="white").pack(
    side="left", padx=5
)

branch_filter = ttk.Combobox(
    search_frame, width=18, state="readonly",
    values=["All Branches"]
)
branch_filter.set("All Branches")
branch_filter.pack(side="left", padx=5)

tk.Button(
    search_frame, text="Apply Filter", command=load_students
).pack(side="left", padx=5)

tk.Button(
    search_frame, text="Show All", command=show_all_students
).pack(side="left", padx=5)

search_entry.bind("<Return>", lambda event: load_students())


# ---------------- STUDENT TABLE ----------------

table_frame = tk.Frame(root, bg="white")
table_frame.pack(fill="both", expand=True, padx=20, pady=10)

columns = (
    "id", "name", "branch", "python", "mysql",
    "java", "total", "percentage", "grade", "result"
)

student_table = ttk.Treeview(
    table_frame, columns=columns,
    show="headings", height=10
)

headings = [
    "Student ID", "Student Name", "Branch",
    "Python", "MySQL", "Java",
    "Total / 300", "Percentage", "Grade", "Result"
]

for column, heading in zip(columns, headings):
    student_table.heading(column, text=heading)
    student_table.column(column, width=110, anchor="center")

student_table.column("name", width=150)
student_table.column("result", width=90)

scrollbar = ttk.Scrollbar(
    table_frame, orient="vertical", command=student_table.yview
)

student_table.configure(yscrollcommand=scrollbar.set)
student_table.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

student_table.bind("<<TreeviewSelect>>", select_student)


# ==================== CLOSE APPLICATION ====================

def close_application():
    try:
        if connection.is_connected():
            connection.close()
    except mysql.connector.Error:
        pass
    finally:
        root.destroy()


root.protocol("WM_DELETE_WINDOW", close_application)


# ==================== START APPLICATION ====================

try:
    load_students()
    root.mainloop()

except Exception as error:
    messagebox.showerror(
        "Application Error",
        f"An unexpected error occurred:\n\n{error}"
    )
    root.destroy()
