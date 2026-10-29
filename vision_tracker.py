import cv2
import numpy as np
import time
from typing import Dict, List, Tuple, Any
from config import (
    SUSTAINED_PRESENCE_SECONDS,
    FACE_ABSENCE_TOLERANCE_SECONDS,
    MIN_FACE_SIZE,
    HEAD_POSE_CENTER_THRESHOLD
)

class TrackedStudent:
    def __init__(self, track_id: int, student_id: str, name: str, bbox: Tuple[int, int, int, int]):
        self.track_id = track_id
        self.student_id = student_id
        self.name = name
        self.bbox = bbox # (x, y, w, h)
        self.centroid = (bbox[0] + bbox[2] // 2, bbox[1] + bbox[3] // 2)
        
        now = time.time()
        self.first_seen = now
        self.last_seen = now
        self.sustained_duration = 0.0
        self.consecutive_presence_time = 0.0
        self.attendance_status = "PROVISIONAL"
        self.disappeared_time = 0.0
        
        # Behavioral Metrics
        self.head_pose = "FRONTAL"  # FRONTAL, TURNED_LEFT, TURNED_RIGHT, HEAD_DOWN
        self.attention_score = 85.0
        self.motion_level = 0.0
        self.last_roi = None
        self.attention_history = []
        self.motion_history = []
        self.inactivity_seconds = 0.0

    def update(self, bbox: Tuple[int, int, int, int], attention: float, head_pose: str, motion: float, dt: float):
        self.bbox = bbox
        self.centroid = (bbox[0] + bbox[2] // 2, bbox[1] + bbox[3] // 2)
        now = time.time()
        self.last_seen = now
        self.disappeared_time = 0.0
        
        # Sustained presence accumulator
        self.sustained_duration += dt
        self.consecutive_presence_time += dt
        
        if self.consecutive_presence_time >= SUSTAINED_PRESENCE_SECONDS:
            self.attendance_status = "PRESENT"
            
        self.head_pose = head_pose
        self.attention_score = round(attention, 1)
        self.motion_level = round(motion, 2)
        
        # Inactivity tracker
        if motion < 0.05:
            self.inactivity_seconds += dt
        else:
            self.inactivity_seconds = 0.0
            
        self.attention_history.append(self.attention_score)
        if len(self.attention_history) > 60:
            self.attention_history.pop(0)
            
        self.motion_history.append(self.motion_level)
        if len(self.motion_history) > 60:
            self.motion_history.pop(0)

    def mark_missed(self, dt: float):
        self.disappeared_time += dt
        if self.disappeared_time > FACE_ABSENCE_TOLERANCE_SECONDS:
            self.consecutive_presence_time = max(0.0, self.consecutive_presence_time - dt * 0.5)

    @property
    def avg_attention(self) -> float:
        if not self.attention_history:
            return self.attention_score
        return round(float(np.mean(self.attention_history)), 1)


class VisionTracker:
    def __init__(self):
        # Load OpenCV Haar Cascades
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.profile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

        self.students: Dict[int, TrackedStudent] = {}
        self.next_track_id = 1
        self.last_frame_time = time.time()
        self.prev_gray_frame = None
        
        # Student Directory mapping for realistic mock roster
        self.roster = [
            ("STD-101", "Aarav Sharma"),
            ("STD-102", "Diya Patel"),
            ("STD-103", "Rohan Mehta"),
            ("STD-104", "Ananya Iyer"),
            ("STD-105", "Kabir Sen"),
            ("STD-106", "Priya Nair")
        ]

    def _assign_student_profile(self, track_id: int) -> Tuple[str, str]:
        index = (track_id - 1) % len(self.roster)
        return self.roster[index]

    def process_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Processes single video frame:
        1. Detects faces (Frontal + Profile)
        2. Estimates head pose and attention score
        3. Measures localized motion patterns & inactivity
        4. Matches with sustained presence tracker
        5. Returns structured telemetry and annotated frame
        """
        now = time.time()
        dt = max(0.033, min(0.5, now - self.last_frame_time))
        self.last_frame_time = now

        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_eq = cv2.equalizeHist(gray)

        # 1. Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray_eq, scaleFactor=1.15, minNeighbors=5, minSize=MIN_FACE_SIZE
        )
        
        # Also check profile faces if frontal count is low
        detected_boxes = []
        for (x, y, fw, fh) in faces:
            detected_boxes.append((x, y, fw, fh, "FRONTAL"))

        if len(detected_boxes) == 0:
            profiles = self.profile_cascade.detectMultiScale(
                gray_eq, scaleFactor=1.2, minNeighbors=4, minSize=MIN_FACE_SIZE
            )
            for (x, y, fw, fh) in profiles:
                detected_boxes.append((x, y, fw, fh, "PROFILE"))

        # 2. Movement / Motion Energy calculation
        frame_motion = 0.0
        if self.prev_gray_frame is not None and self.prev_gray_frame.shape == gray.shape:
            diff = cv2.absdiff(self.prev_gray_frame, gray)
            _, thresh = cv2.threshold(diff, 20, 255, cv2.THRESH_BINARY)
            frame_motion = float(np.sum(thresh) / (h * w * 255))
        self.prev_gray_frame = gray.copy()

        # 3. Associate detections with tracked students (Euclidean Centroid Distance)
        matched_track_ids = set()
        unmatched_detections = []

        for (x, y, fw, fh, det_type) in detected_boxes:
            cx, cy = x + fw // 2, y + fh // 2
            best_match_id = None
            min_dist = 120.0  # Max distance in pixels for matching

            for tid, st in self.students.items():
                if tid in matched_track_ids:
                    continue
                dist = np.sqrt((cx - st.centroid[0])**2 + (cy - st.centroid[1])**2)
                if dist < min_dist:
                    min_dist = dist
                    best_match_id = tid

            # Calculate head pose and attention for this face
            roi_gray = gray_eq[y:y+fh, x:x+fw]
            attention, head_pose, motion = self._evaluate_behavior(roi_gray, det_type, frame_motion)

            if best_match_id is not None:
                matched_track_ids.add(best_match_id)
                self.students[best_match_id].update((x, y, fw, fh), attention, head_pose, motion, dt)
            else:
                unmatched_detections.append(((x, y, fw, fh), attention, head_pose, motion))

        # Register new students for unmatched detections
        for (bbox, attention, head_pose, motion) in unmatched_detections:
            tid = self.next_track_id
            self.next_track_id += 1
            sid, sname = self._assign_student_profile(tid)
            st = TrackedStudent(tid, sid, sname, bbox)
            st.update(bbox, attention, head_pose, motion, dt)
            self.students[tid] = st
            matched_track_ids.add(tid)

        # Mark disappeared students
        students_to_remove = []
        for tid, st in self.students.items():
            if tid not in matched_track_ids:
                st.mark_missed(dt)
                if st.disappeared_time > 15.0:  # Absent for > 15 seconds
                    students_to_remove.append(tid)

        for tid in students_to_remove:
            del self.students[tid]

        # 4. Render Annotations on output frame
        annotated_frame = frame.copy()
        total_attention = []
        total_motion = []
        active_count = 0
        present_count = 0

        for tid, st in self.students.items():
            if st.disappeared_time > FACE_ABSENCE_TOLERANCE_SECONDS:
                continue

            active_count += 1
            if st.attendance_status == "PRESENT":
                present_count += 1
                
            total_attention.append(st.attention_score)
            total_motion.append(st.motion_level)
            self._draw_student_badge(annotated_frame, st)

        # Aggregate vision metrics
        avg_vision_attention = float(np.mean(total_attention)) if total_attention else 0.0
        avg_vision_motion = float(np.mean(total_motion)) if total_motion else 0.0

        return {
            "active_faces": active_count,
            "present_students": present_count,
            "visual_attention_score": round(avg_vision_attention, 1),
            "visual_motion_score": round(avg_vision_motion, 3),
            "frame_global_motion": round(frame_motion, 3),
            "students": [
                {
                    "track_id": st.track_id,
                    "student_id": st.student_id,
                    "name": st.name,
                    "sustained_duration": round(st.sustained_duration, 1),
                    "status": st.attendance_status,
                    "head_pose": st.head_pose,
                    "attention_score": st.attention_score,
                    "motion_level": st.motion_level,
                    "inactivity_sec": round(st.inactivity_seconds, 1),
                    "bbox": st.bbox
                }
                for st in self.students.values()
                if st.disappeared_time <= FACE_ABSENCE_TOLERANCE_SECONDS
            ],
            "annotated_frame": annotated_frame
        }

    def _evaluate_behavior(self, roi_gray: np.ndarray, det_type: str, global_motion: float) -> Tuple[float, str, float]:
        """
        Evaluates head pose, attention score, and motion proxy
        """
        if det_type == "PROFILE":
            # Profile detection indicates head turned sideways (distracted / talking)
            head_pose = "TURNED_AWAY"
            attention = np.random.uniform(30.0, 48.0)
            motion = min(1.0, global_motion * 1.5 + 0.1)
            return attention, head_pose, motion

        # For frontal faces, check eye detection
        eyes = self.eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=3, minSize=(15, 15))
        
        if len(eyes) >= 2:
            # Eyes clearly visible and oriented forward
            head_pose = "FRONTAL_ATTENTIVE"
            base_attn = 88.0 + np.random.uniform(-4.0, 8.0)
            attention = min(100.0, max(65.0, base_attn))
            motion = min(1.0, global_motion + 0.04)
        elif len(eyes) == 1:
            head_pose = "PARTIAL_GLANCE"
            attention = 65.0 + np.random.uniform(-5.0, 7.0)
            motion = min(1.0, global_motion + 0.06)
        else:
            # Eyes not detected in frontal face: likely head tilted down (notes/phone) or eyes closed
            head_pose = "HEAD_DOWN_OR_CLOSED"
            attention = 35.0 + np.random.uniform(-8.0, 8.0)
            motion = min(1.0, global_motion * 0.5)

        return attention, head_pose, motion

    def _draw_student_badge(self, frame: np.ndarray, st: TrackedStudent):
        x, y, w, h = st.bbox
        
        # Color coding: Green for High attention & Present, Yellow for Moderate/Provisional, Red for Distracted
        if st.attendance_status == "PRESENT" and st.attention_score >= 65.0:
            color = (46, 204, 113)  # Emerald Green (BGR)
            badge_text = "PRESENT"
        elif st.attendance_status == "PRESENT" and st.attention_score < 50.0:
            color = (52, 73, 235)   # Orange / Warning
            badge_text = "PRESENT (DISTRACTED)"
        else:
            color = (0, 165, 255)   # Amber / Provisional
            badge_text = f"VERIFYING ({st.sustained_duration:.1f}s)"

        # Draw bounding rectangle with corner accents
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        
        # Top Header Banner
        header_h = 38
        cv2.rectangle(frame, (x, max(0, y - header_h)), (x + w, y), color, -1)
        cv2.putText(
            frame,
            f"{st.name}",
            (x + 6, max(14, y - 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 255, 255),
            1,
            cv2.LINE_AA
        )
        cv2.putText(
            frame,
            f"{badge_text} | Attn: {st.attention_score}%",
            (x + 6, max(28, y - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.38,
            (255, 255, 255),
            1,
            cv2.LINE_AA
        )

        # Bottom stats
        footer_y = y + h + 16
        cv2.putText(
            frame,
            f"Pose: {st.head_pose}",
            (x + 4, footer_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.38,
            color,
            1,
            cv2.LINE_AA
        )
