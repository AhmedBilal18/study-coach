import os
import json
import re
import urllib.request
from dotenv import load_dotenv
load_dotenv()
from groq import Groq
from agent.prompts import QUIZ_SYSTEM, ANALYZE_SYSTEM, STRESS_SYSTEM

import fitz  # pymupdf
import base64
from PIL import Image
import io


client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def pdf_to_base64_images(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_bytes = pix.tobytes("jpeg")
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        images.append(b64)
    doc.close()
    return images

def _parse(raw_text):
    try:
        clean_text = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(clean_text)
    except Exception:
        return None

def extract_text_from_pdf(pdf_bytes):
    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text.strip()

def generate_quiz(topic, image_b64=None, pdf_text=None, num_questions=5, age=15):
    messages = [{"role": "system", "content": QUIZ_SYSTEM}]
    
    if age <= 10:
        age_instruction = f"CRITICAL: The user is a young child (age {age}). Use extremely simple vocabulary, short sentences, and basic introductory concepts. Make the wrong options obvious and fun."
    elif age <= 14:
        age_instruction = f"CRITICAL: The user is a middle school student (age {age}). Use accessible language and foundational concepts. Avoid overly complex jargon."
    elif age <= 18:
        age_instruction = f"CRITICAL: The user is a high school student (age {age}). Use standard academic vocabulary and challenging but fair distractors."
    else:
        age_instruction = f"CRITICAL: The user is an adult/college student (age {age}). Use highly advanced terminology, complex conceptual questions, and nuanced distractors that require deep understanding."

    if pdf_text:
        messages.append({
            "role": "user",
            "content": f"Based on these notes extracted from a PDF, generate a {num_questions}-question quiz:\n\n{pdf_text[:4000]}\n\n{age_instruction}"
        })
    elif image_b64 is not None:
        messages.append({
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                {"type": "text", "text": f"Based on these notes, generate a {num_questions}-question quiz.\n\n{age_instruction}"}
            ]
        })
    else:
        messages.append({
            "role": "user",
            "content": f"Generate a {num_questions}-question quiz on: {topic}.\n\n{age_instruction}"
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