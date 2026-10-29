import os
import sys
import time
import uuid
import base64
import cv2
import numpy as np
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

import config
from modules.vision_tracker import VisionTracker
from modules.audio_analyzer import AudioAnalyzer
from modules.fusion_engine import MultimodalFusionEngine
from engine.reasoning_engine import SessionReasoningEngine
from engine.teaching_assistant import TeachingAssistant
from utils.code_executor import CodeExecutor
from storage import database as db

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# Global State & Singletons
vision_tracker = VisionTracker()
audio_analyzer = AudioAnalyzer()
fusion_engine = MultimodalFusionEngine()
reasoning_engine = SessionReasoningEngine()
teaching_assistant = TeachingAssistant()

current_session_id = f"SES-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
current_session_title = "Data Science & AI Interactive Lecture"
current_instructor = "Prof. Sarah Jenkins"
session_active = True

# Initialize initial session in DB
db.create_session(current_session_id, current_session_title, current_instructor)

@app.route("/")
def index():
    return render_template(
        "index.html",
        session_id=current_session_id,
        session_title=current_session_title,
        instructor=current_instructor,
        session_active=session_active
    )

@app.route("/history")
def history_page():
    conn = db.get_connection()
    sessions = conn.execute("SELECT * FROM sessions ORDER BY start_time DESC").fetchall()
    conn.close()
    return render_template("session_history.html", sessions=[dict(s) for s in sessions])

@app.route("/settings")
def settings_page():
    return render_template(
        "settings.html",
        config=config,
        gemini_key=os.getenv("GEMINI_API_KEY", config.GEMINI_API_KEY)
    )

# ----------------- SESSION CONTROL APIs ----------------- #

@app.route("/api/session/start", methods=["POST"])
def start_session():
    global current_session_id, current_session_title, current_instructor, session_active
    data = request.get_json() or {}
    current_session_title = data.get("title", "Classroom Lecture")
    current_instructor = data.get("instructor", "Prof. Sarah Jenkins")
    current_session_id = f"SES-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    session_active = True

    # Reset state engines
    fusion_engine.reset_session()
    audio_analyzer.start_live_mic()
    db.create_session(current_session_id, current_session_title, current_instructor)

    return jsonify({
        "status": "success",
        "session_id": current_session_id,
        "title": current_session_title,
        "instructor": current_instructor
    })

@app.route("/api/session/stop", methods=["POST"])
def stop_session():
    global session_active
    session_active = False
    audio_analyzer.stop_live_mic()

    # Finalize session metrics
    history = db.get_session_timeline(current_session_id)
    avg_eng = 0.0
    if history:
        avg_eng = round(sum(h["fused_score"] for h in history) / len(history), 1)

    summary = f"Session concluded with {len(db.get_session_attendance(current_session_id))} tracked attendees and average engagement of {avg_eng}%."
    db.close_session(current_session_id, avg_eng, summary)

    return jsonify({
        "status": "success",
        "session_id": current_session_id,
        "avg_engagement": avg_eng,
        "summary": summary
    })

# ----------------- REAL-TIME MULTIMODAL PROCESSING ----------------- #

@app.route("/api/process_frame", methods=["POST"])
def process_frame():
    """
    Accepts client video frame (Base64 JPEG/PNG), executes Vision Module,
    extracts Audio telemetry, computes Multimodal Fusion, updates DB,
    and runs the AI Reasoning Engine.
    """
    global current_session_id, session_active
    if not session_active:
        return jsonify({"status": "inactive", "message": "Session is inactive"})

    data = request.get_json() or {}
    image_b64 = data.get("image")
    
    if not image_b64:
        return jsonify({"error": "No image payload provided"}), 400

    try:
        # Decode base64 image
        if "base64," in image_b64:
            image_b64 = image_b64.split("base64,")[1]
        img_bytes = base64.b64decode(image_b64)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({"error": "Failed to decode image frame"}), 400

        # 1. Vision Module Processing
        vision_result = vision_tracker.process_frame(frame)

        # 2. Audio Module Telemetry
        client_audio_rms = data.get("client_audio_rms")
        if client_audio_rms is not None:
            audio_telemetry = audio_analyzer.process_raw_samples(
                np.full(100, float(client_audio_rms), dtype=np.float32)
            )
        else:
            audio_telemetry = audio_analyzer.get_telemetry()

        # 3. Multimodal Fusion Engine
        fused_snapshot = fusion_engine.fuse(vision_result, audio_telemetry)

        # 4. Log Attendance in Database
        for st in vision_result["students"]:
            db.log_attendance(
                session_id=current_session_id,
                student_id=st["student_id"],
                student_name=st["name"],
                sustained_sec=st["sustained_duration"],
                status=st["status"],
                avg_attention=st["attention_score"]
            )

        # 5. Log Engagement Snapshot in DB
        db.log_engagement_snapshot(
            session_id=current_session_id,
            sec_from_start=fused_snapshot["seconds_from_start"],
            visual_attn=fused_snapshot["visual_attention"],
            visual_mot=fused_snapshot["visual_motion"],
            audio_int=fused_snapshot["audio_interaction"],
            fused=fused_snapshot["fused_score"],
            category=fused_snapshot["category"],
            face_count=fused_snapshot["active_faces"]
        )

        # 6. Session Dynamics & AI Pedagogical Reasoning Engine
        reasoning_engine.add_metric(fused_snapshot)
        trigger_event = reasoning_engine.evaluate_dynamics()
        ai_suggestion = None
        if trigger_event:
            ai_suggestion = teaching_assistant.process_trigger(current_session_id, trigger_event)

        # Encode annotated frame back to base64
        _, buffer = cv2.imencode('.jpg', vision_result["annotated_frame"], [cv2.IMWRITE_JPEG_QUALITY, 80])
        annotated_b64 = base64.b64encode(buffer).decode('utf-8')

        return jsonify({
            "status": "success",
            "annotated_frame": f"data:image/jpeg;base64,{annotated_b64}",
            "fused_telemetry": fused_snapshot,
            "students": vision_result["students"],
            "ai_suggestion": ai_suggestion
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/process_audio", methods=["POST"])
def process_audio():
    """Receives direct audio binary stream or RMS telemetry from browser"""
    data = request.get_json() or {}
    rms = data.get("rms", 0.03)
    samples = np.full(100, float(rms), dtype=np.float32)
    telemetry = audio_analyzer.process_raw_samples(samples)
    return jsonify({"status": "success", "audio_telemetry": telemetry})

# ----------------- ANALYTICS & QUERY ENDPOINTS ----------------- #

@app.route("/api/attendance", methods=["GET"])
def get_attendance():
    records = db.get_session_attendance(current_session_id)
    return jsonify({"session_id": current_session_id, "attendance": records})

@app.route("/api/attendance/export", methods=["GET"])
def export_attendance():
    csv_data = db.export_attendance_csv(current_session_id)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=attendance_{current_session_id}.csv"}
    )

@app.route("/api/timeline", methods=["GET"])
def get_timeline():
    timeline = db.get_session_timeline(current_session_id, limit=50)
    return jsonify({"session_id": current_session_id, "timeline": timeline})

@app.route("/api/suggestions", methods=["GET"])
def get_suggestions():
    suggestions = db.get_session_suggestions(current_session_id, limit=10)
    return jsonify({"suggestions": suggestions})

@app.route("/api/trigger_suggestion", methods=["POST"])
def manual_trigger_suggestion():
    """Allows manual trigger or testing of the GenAI Teaching Assistant"""
    data = request.get_json() or {}
    reason = data.get("reason", "Instructor Manual Check")
    
    context = {
        "trigger_reason": reason,
        "fused_score": data.get("fused_score", fusion_engine.smoothed_engagement),
        "visual_attention": 65.0,
        "visual_motion": 70.0,
        "acoustic_state": audio_analyzer.current_state,
        "duration_sec": int(time.time() - fusion_engine.start_time),
        "present_students": len(vision_tracker.students)
    }
    advice = teaching_assistant.process_trigger(current_session_id, context)
    return jsonify({"status": "success", "suggestion": advice})

@app.route("/api/generate_quiz", methods=["POST"])
def generate_quiz():
    data = request.get_json() or {}
    topic = data.get("topic", "AI & Multimodal Systems")
    quiz = teaching_assistant.generate_quiz_on_demand(topic)
    return jsonify({"status": "success", "quiz": quiz})

@app.route("/api/execute_code", methods=["POST"])
def execute_code():
    data = request.get_json() or {}
    code = data.get("code", "result = 42")
    res = CodeExecutor.execute_analytics_code(code)
    return jsonify(res)

@app.route("/audio/<filename>")
def serve_audio(filename):
    return send_from_directory(config.AUDIO_DIR, filename)

@app.route("/api/upload_video", methods=["POST"])
def upload_video():
    """Handles recorded classroom video upload for offline analysis"""
    if 'video' not in request.files:
        return jsonify({"error": "No video file uploaded"}), 400
    file = request.files['video']
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400
        
    filename = secure_filename(file.filename)
    save_path = config.UPLOADS_DIR / filename
    file.save(str(save_path))

    return jsonify({
        "status": "success",
        "message": f"Video '{filename}' uploaded successfully.",
        "filepath": str(save_path)
    })

if __name__ == "__main__":
    print(f"[*] Starting Multimodal Attendance & Engagement Agent on http://{config.FLASK_HOST}:{config.FLASK_PORT}")
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=config.DEBUG, use_reloader=False)
