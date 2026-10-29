import os
import json
import time
from typing import Dict, Any, Optional
from config import GEMINI_MODEL, GEMINI_API_KEY

# Try importing google-genai or google.generativeai
GEMINI_CLIENT = None
try:
    from google import genai
    from google.genai import types
    if GEMINI_API_KEY:
        GEMINI_CLIENT = genai.Client(api_key=GEMINI_API_KEY)
except Exception:
    try:
        import google.generativeai as legacy_genai
        if GEMINI_API_KEY:
            legacy_genai.configure(api_key=GEMINI_API_KEY)
            GEMINI_CLIENT = legacy_genai.GenerativeModel(GEMINI_MODEL)
    except Exception:
        GEMINI_CLIENT = None

def generate_teaching_suggestion(session_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates AI-driven teaching suggestions using Google Gemini 2.0 Flash.
    Gracefully falls back to offline educational rule-based heuristics if no API key is provided.
    """
    api_key = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY)
    
    if api_key and GEMINI_CLIENT:
        try:
            return _call_gemini_api(api_key, session_context)
        except Exception as e:
            print(f"[GenAI Utils] Gemini API error, falling back to offline reasoning agent: {e}")
            return _generate_offline_heuristic_suggestion(session_context)
    else:
        return _generate_offline_heuristic_suggestion(session_context)

def _call_gemini_api(api_key: str, context: Dict[str, Any]) -> Dict[str, Any]:
    prompt = f"""
You are an expert AI Pedagogical Assistant embedded in a smart classroom analytics system.
Current Classroom Telemetry:
- Session Duration: {context.get('duration_sec', 60)} seconds
- Current Fused Engagement: {context.get('fused_score', 70)}%
- Visual Attention Score: {context.get('visual_attention', 70)}%
- Visual Movement/Motion: {context.get('visual_motion', 70)}%
- Acoustic State: {context.get('acoustic_state', 'INSTRUCTIONAL_MONOLOGUE')}
- Present Students: {context.get('present_students', 1)}
- Trigger Reason: {context.get('trigger_reason', 'Periodic Check')}

Analyze these signals and provide an actionable, concise recommendation for the instructor.
Respond strictly in JSON format with these exact keys:
{{
  "suggestion": "Brief, actionable recommendation (1-2 sentences)",
  "category": "PACING" | "INTERACTIVE_POLL" | "ENERGIZER" | "DEEP_DIVE",
  "action_type": "PAUSE_QUESTION" | "THINK_PAIR_SHARE" | "SPEED_UP" | "STRETCH_BREAK",
  "suggested_prompt": "An exact question or prompt the teacher can say aloud to the class",
  "priority": "HIGH" | "MEDIUM" | "LOW"
}}
"""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        text = response.text.strip()
        # Clean potential markdown fences
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
    except Exception as e:
        # Fallback to legacy library if available
        import google.generativeai as genai_legacy
        genai_legacy.configure(api_key=api_key)
        model = genai_legacy.GenerativeModel(GEMINI_MODEL)
        resp = model.generate_content(prompt)
        text = resp.text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)

def _generate_offline_heuristic_suggestion(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Offline privacy-preserving expert decision-support heuristic engine.
    Ensures 100% functionality without internet connection or cloud API dependency.
    """
    score = context.get("fused_score", 70.0)
    acoustic = context.get("acoustic_state", "INSTRUCTIONAL_MONOLOGUE")
    attn = context.get("visual_attention", 70.0)
    dur = context.get("duration_sec", 60)

    if score < 40.0 or attn < 45.0:
        return {
            "suggestion": "Attention has significantly dropped below 45%. Shift away from passive lecture slides and ask an open-ended concept checking question.",
            "category": "INTERACTIVE_POLL",
            "action_type": "PAUSE_QUESTION",
            "suggested_prompt": "Can someone summarize the core trade-off we just covered before we proceed?",
            "priority": "HIGH"
        }
    elif acoustic == "SILENT_LISTENING" and dur > 120:
        return {
            "suggestion": "Classroom has experienced extended passive silence. Launch a 60-second peer discussion to rekindle participation.",
            "category": "PACING",
            "action_type": "THINK_PAIR_SHARE",
            "suggested_prompt": "Turn to your neighbor and take 60 seconds to explain how you would implement this in practice.",
            "priority": "MEDIUM"
        }
    elif acoustic == "HIGH_CLASS_COMMOTION":
        return {
            "suggestion": "Acoustic commotion detected. Reset classroom focus with a deliberate vocal pause and a targeted question.",
            "category": "PACING",
            "action_type": "FOCUS_RESET",
            "suggested_prompt": "Let's bring our attention back together. Let's look at line 14 together.",
            "priority": "HIGH"
        }
    elif score >= 75.0:
        return {
            "suggestion": "Engagement is optimal! High receptive attention. Ideal window to introduce challenging concepts or core exam takeaways.",
            "category": "DEEP_DIVE",
            "action_type": "ADVANCED_CONCEPT",
            "suggested_prompt": "Notice how this edge case connects with our fundamental architecture rule.",
            "priority": "LOW"
        }
    else:
        return {
            "suggestion": "Pacing is steady. Keep an eye on student eye-contact and vary your vocal pitch or gesture toward the diagram.",
            "category": "PACING",
            "action_type": "PACING_ADJUSTMENT",
            "suggested_prompt": "Who would like to take a guess at what happens next in this flow?",
            "priority": "MEDIUM"
        }
