import os
import json
import re
import urllib.request
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

def generate_quiz(topic, image_b64=None, num_questions=5, age=15):
    messages = [{"role": "system", "content": QUIZ_SYSTEM}]
    if image_b64 is not None:
        messages.append({
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                {"type": "text", "text": f"Based on these notes, generate a {num_questions}-question quiz. The user is {age} years old. Adjust the difficulty, complexity, and vocabulary to perfectly match a {age}-year-old."}
            ]
        })
    else:
        messages.append({
            "role": "user",
            "content": f"Generate a {num_questions}-question quiz on: {topic}. The user is {age} years old. Adjust the difficulty, complexity, and vocabulary to perfectly match a {age}-year-old."
        })
    try:
        model_name = "meta-llama/llama-4-scout-17b-16e-instruct" if image_b64 is not None else "llama-3.3-70b-versatile"
        response = client.chat.completions.create(
            model=model_name,
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
            "resources": [],
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
            return {"weak": [], "resources": [], "next_task": "Could not analyze results.", "encouragement": "Keep studying!"}
            
        for res in parsed.get("resources", []):
            url = res.get("url", "")
            if url:
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    html = urllib.request.urlopen(req, timeout=3).read().decode('utf-8')
                    video_ids = re.findall(r'"videoId":"(.{11})"', html)
                    if video_ids:
                        res["video_id"] = video_ids[0]
                        res["url"] = f"https://www.youtube.com/watch?v={video_ids[0]}"
                except Exception:
                    pass
                    
        return parsed
    except Exception:
        return {"weak": [], "resources": [], "next_task": "Could not analyze results.", "encouragement": "Keep studying!"}

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