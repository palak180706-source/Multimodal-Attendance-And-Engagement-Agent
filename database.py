import sqlite3
import json
import csv
import io
from datetime import datetime
from pathlib import Path
from config import DB_PATH, LOGS_DIR

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Sessions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        instructor TEXT DEFAULT 'Instructor',
        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_time TIMESTAMP,
        status TEXT DEFAULT 'ACTIVE',
        total_students INTEGER DEFAULT 0,
        avg_engagement REAL DEFAULT 0.0,
        summary TEXT
    )
    """)

    # Students Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        roll_no TEXT UNIQUE,
        enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Attendance Records Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        student_id TEXT NOT NULL,
        student_name TEXT NOT NULL,
        first_detected TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_detected TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        sustained_duration REAL DEFAULT 0.0,
        status TEXT DEFAULT 'PROVISIONAL',
        avg_attention REAL DEFAULT 0.0,
        FOREIGN KEY (session_id) REFERENCES sessions (id)
    )
    """)

    # Engagement Snapshots Table (Time Series)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS engagement_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        seconds_from_start REAL NOT NULL,
        visual_attention REAL NOT NULL,
        visual_motion REAL NOT NULL,
        audio_interaction REAL NOT NULL,
        fused_score REAL NOT NULL,
        engagement_category TEXT NOT NULL,
        active_faces_count INTEGER NOT NULL,
        FOREIGN KEY (session_id) REFERENCES sessions (id)
    )
    """)

    # AI Teaching Suggestions Log Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ai_suggestions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        trigger_reason TEXT NOT NULL,
        suggestion TEXT NOT NULL,
        category TEXT NOT NULL,
        action_type TEXT,
        is_spoken INTEGER DEFAULT 0,
        FOREIGN KEY (session_id) REFERENCES sessions (id)
    )
    """)

    conn.commit()

    # Pre-populate sample students if table is empty
    cursor.execute("SELECT COUNT(*) as count FROM students")
    if cursor.fetchone()["count"] == 0:
        sample_students = [
            ("STD-101", "Aarav Sharma", "CS2026-01"),
            ("STD-102", "Diya Patel", "CS2026-02"),
            ("STD-103", "Rohan Mehta", "CS2026-03"),
            ("STD-104", "Ananya Iyer", "CS2026-04"),
            ("STD-105", "Kabir Sen", "CS2026-05"),
            ("STD-106", "Priya Nair", "CS2026-06")
        ]
        cursor.executemany("INSERT INTO students (id, name, roll_no) VALUES (?, ?, ?)", sample_students)
        conn.commit()

    conn.close()

def create_session(session_id, title="Classroom Lecture", instructor="Prof. Sarah Jenkins"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sessions (id, title, instructor, status) VALUES (?, ?, ?, 'ACTIVE')",
        (session_id, title, instructor)
    )
    conn.commit()
    conn.close()

def close_session(session_id, avg_engagement=0.0, summary=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE sessions
        SET end_time = CURRENT_TIMESTAMP, status = 'COMPLETED', avg_engagement = ?, summary = ?
        WHERE id = ?
    """, (avg_engagement, summary, session_id))
    conn.commit()
    conn.close()

def log_attendance(session_id, student_id, student_name, sustained_sec, status="PRESENT", avg_attention=80.0):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, sustained_duration FROM attendance_records WHERE session_id = ? AND student_id = ?",
        (session_id, student_id)
    )
    row = cursor.fetchone()
    if row:
        cursor.execute("""
            UPDATE attendance_records
            SET last_detected = CURRENT_TIMESTAMP,
                sustained_duration = ?,
                status = ?,
                avg_attention = ?
            WHERE id = ?
        """, (sustained_sec, status, avg_attention, row["id"]))
    else:
        cursor.execute("""
            INSERT INTO attendance_records (session_id, student_id, student_name, sustained_duration, status, avg_attention)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, student_id, student_name, sustained_sec, status, avg_attention))
    conn.commit()
    conn.close()

def log_engagement_snapshot(session_id, sec_from_start, visual_attn, visual_mot, audio_int, fused, category, face_count):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO engagement_snapshots 
        (session_id, seconds_from_start, visual_attention, visual_motion, audio_interaction, fused_score, engagement_category, active_faces_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (session_id, sec_from_start, visual_attn, visual_mot, audio_int, fused, category, face_count))
    conn.commit()
    conn.close()

def log_ai_suggestion(session_id, trigger, suggestion, category, action_type="INTERACTIVE_POLL"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ai_suggestions (session_id, trigger_reason, suggestion, category, action_type)
        VALUES (?, ?, ?, ?, ?)
    """, (session_id, trigger, suggestion, category, action_type))
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id

def get_session_attendance(session_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM attendance_records WHERE session_id = ? ORDER BY sustained_duration DESC", (session_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_session_timeline(session_id, limit=100):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM engagement_snapshots WHERE session_id = ? ORDER BY seconds_from_start ASC LIMIT ?",
        (session_id, limit)
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_session_suggestions(session_id, limit=20):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM ai_suggestions WHERE session_id = ? ORDER BY id DESC LIMIT ?",
        (session_id, limit)
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def export_attendance_csv(session_id):
    rows = get_session_attendance(session_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student ID", "Student Name", "Status", "Sustained Presence (s)", "Avg Attention (%)", "First Seen", "Last Seen"])
    for r in rows:
        writer.writerow([
            r["student_id"],
            r["student_name"],
            r["status"],
            round(r["sustained_duration"], 1),
            round(r["avg_attention"], 1),
            r["first_detected"],
            r["last_detected"]
        ])
    return output.getvalue()

# Initialize DB on load
init_db()
