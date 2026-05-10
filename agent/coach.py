import os
import json
from dotenv import load_dotenv
load_dotenv()
from groq import Groq
from agent.prompts import QUIZ_SYSTEM, ANALYZE_SYSTEM, STRESS_SYSTEM

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def _parse(raw_text):
    try:
        clean_text = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(clean_text)
    except Exception:
        return None

def generate_quiz(topic, image_b64=None):
    messages = [{"role": "system", "content": QUIZ_SYSTEM}]
    if image_b64 is not None:
        messages.append({
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                {"type": "text", "text": "Based on these notes, generate a 5-question quiz."}
            ]
        })
    else:
        messages.append({
            "role": "user",
            "content": f"Generate a 5-question quiz on: {topic}"
        })
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=1000
        )
        parsed = _parse(response.choices[0].message.content)
        if parsed is None:
            raise ValueError("Quiz generation failed — unexpected format")
        return parsed
    except Exception as e:
        raise ValueError(f"OpenAI API Error: {str(e)}")

def analyze_results(wrong_answers):
    if not wrong_answers:
        return {
            "weak": [],
            "next_task": "Excellent — no weak areas detected!",
            "encouragement": "Perfect score, keep it up!"
        }
    messages = [
        {"role": "system", "content": ANALYZE_SYSTEM},
        {"role": "user", "content": json.dumps(wrong_answers)}
    ]
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=500
        )
        parsed = _parse(response.choices[0].message.content)
        if parsed is None:
            return {"weak": [], "next_task": "Could not analyze results.", "encouragement": "Keep studying!"}
        return parsed
    except Exception:
        return {"weak": [], "next_task": "Could not analyze results.", "encouragement": "Keep studying!"}

def stress_mode_plan(weak_concepts):
    if not weak_concepts:
        return {"plan": [{"priority": 1, "topic": "All clear", "action": "Light review of all notes", "time_mins": 10}]}
    messages = [
        {"role": "system", "content": STRESS_SYSTEM},
        {"role": "user", "content": json.dumps(weak_concepts)}
    ]
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=500
        )
        parsed = _parse(response.choices[0].message.content)
        if parsed is None:
            return {"plan": [{"priority": 1, "topic": "Review weak areas", "action": "Re-read your notes carefully", "time_mins": 20}]}
        return parsed
    except Exception:
        return {"plan": [{"priority": 1, "topic": "Review weak areas", "action": "Re-read your notes carefully", "time_mins": 20}]}