from typing import Dict, Any, Optional
from utils.genai_utils import generate_teaching_suggestion
from utils.tts_engine import TTSEngine
from storage.database import log_ai_suggestion

class TeachingAssistant:
    def __init__(self):
        self.tts = TTSEngine()
        self.latest_suggestion: Optional[Dict[str, Any]] = None

    def process_trigger(self, session_id: str, trigger_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Receives an engagement trigger, invokes GenAI / offline heuristics,
        generates speech audio, logs into DB, and returns structured advice.
        """
        advice = generate_teaching_suggestion(trigger_context)
        
        suggestion_text = advice.get("suggestion", "Introduce an interactive question.")
        category = advice.get("category", "PACING")
        action_type = advice.get("action_type", "PAUSE_QUESTION")
        prompt_say = advice.get("suggested_prompt", "")
        
        # Synthesize audio for the instructor
        audio_file = self.tts.synthesize(f"{suggestion_text} You might ask: {prompt_say}")

        # Store in database
        suggestion_id = log_ai_suggestion(
            session_id=session_id,
            trigger=trigger_context.get("trigger_reason", "Periodic"),
            suggestion=suggestion_text,
            category=category,
            action_type=action_type
        )

        result = {
            "id": suggestion_id,
            "suggestion": suggestion_text,
            "category": category,
            "action_type": action_type,
            "suggested_prompt": prompt_say,
            "priority": advice.get("priority", "MEDIUM"),
            "audio_file": audio_file,
            "trigger_reason": trigger_context.get("trigger_reason")
        }
        self.latest_suggestion = result
        return result

    def generate_quiz_on_demand(self, topic: str = "Machine Learning Fundamentals") -> Dict[str, Any]:
        """Generates an instant 3-option interactive poll for the instructor"""
        return {
            "topic": topic,
            "question": f"Which factor most directly affects engagement retention during an ML lecture?",
            "options": [
                "A) Frequent active recall checkpoints and interactive quizzes",
                "B) Increasing the slide count and speed",
                "C) Extending the duration of uninterrupted monologue"
            ],
            "correct_option": "A",
            "explanation": "Active recall promotes retrieval practice, mitigating cognitive fatigue and attention decay."
        }
