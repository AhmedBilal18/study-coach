import os
import base64
import time
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from agent import generate_quiz, analyze_results, stress_mode_plan, new_profile, update_profile, build_results, get_wrong_answers, calculate_score

st.set_page_config(page_title="Study Coach", page_icon="🎓", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
.stApp { background-color: #f8f9fb; }
h1, h2, h3, h4, h5, h6, p, span, div, label, .stMarkdown { color: #000000 !important; }
.concept-strong { background: #e8f5e9 !important; color: #2e7d32 !important; padding: 4px 10px; border-radius: 20px; font-size: 13px; display: inline-block; margin: 3px; }
.concept-weak { background: #ffebee !important; color: #c62828 !important; padding: 4px 10px; border-radius: 20px; font-size: 13px; display: inline-block; margin: 3px; }
.stress-item { background: white; border-left: 4px solid #f44336; border-radius: 8px; padding: 12px 16px; margin: 8px 0; color: #000000; }
.question-box { background: white; border-radius: 12px; padding: 2rem; border: 1px solid #e0e0e0; margin-bottom: 1rem; }
.score-bar-fill { background: #43a047; height: 8px; border-radius: 4px; }
.score-bar-bg { background: #e0e0e0; height: 8px; border-radius: 4px; margin: 8px 0 16px; }
div[data-testid="stRadio"] label { font-size: 15px; padding: 6px 0; color: #000000 !important; }

/* Black background and white text for inputs */
[data-baseweb="input"], [data-baseweb="input"] input {
    background-color: #000000 !important;
    color: #ffffff !important;
}
[data-testid="stFileUploaderDropzone"] {
    background-color: #000000 !important;
}
[data-testid="stFileUploaderDropzone"] * {
    color: #ffffff !important;
}

/* Make Exam Stress Mode toggle visible when off */
[data-testid="stToggle"] {
    background-color: #000000 !important;
    padding: 8px 16px;
    border-radius: 8px;
}
[data-testid="stToggle"] p {
    color: #ffffff !important;
}
[data-testid="stToggle"] div[role="switch"] {
    background-color: #f44336 !important;
    border-color: #f44336 !important;
}
[data-testid="stToggle"] div[role="switch"][aria-checked="true"] {
    background-color: #b71c1c !important;
    border-color: #b71c1c !important;
}

/* Make secondary buttons (Take Another Quiz) black with white text */
button[kind="secondary"] {
    background-color: #000000 !important;
    color: #ffffff !important;
    border: 1px solid #000000 !important;
}
button[kind="secondary"] p, button[kind="secondary"] span {
    color: #ffffff !important;
}

/* Style the top Streamlit header (Deploy button area) */
header[data-testid="stHeader"] {
    background-color: #000000 !important;
}
header[data-testid="stHeader"] * {
    color: #ffffff !important;
}

/* Style popovers and modals (like the Deploy menu) to be black with white text */
[data-baseweb="popover"] > div, [data-baseweb="modal"] > div, div[role="dialog"] {
    background-color: #000000 !important;
}
[data-baseweb="popover"] *, [data-baseweb="modal"] *, div[role="dialog"] * {
    color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)

if "profile" not in st.session_state:
    st.session_state.profile = new_profile()
if "quiz" not in st.session_state:
    st.session_state.quiz = None
if "current_q" not in st.session_state:
    st.session_state.current_q = 0
if "answers" not in st.session_state:
    st.session_state.answers = []
if "stage" not in st.session_state:
    st.session_state.stage = "input"
if "analysis" not in st.session_state:
    st.session_state.analysis = None
if "stress_plan" not in st.session_state:
    st.session_state.stress_plan = None
if "stress_mode" not in st.session_state:
    st.session_state.stress_mode = False
if "selected_answers" not in st.session_state:
    st.session_state.selected_answers = []

col1, col2 = st.columns([1.1, 0.9], gap="large")

with col1:
    if st.session_state.stage == "input":
        st.markdown("## 📚 Adaptive Study Coach")
        st.markdown("*Your AI teacher that adapts to you*")
        st.divider()
        
        topic = st.text_input("What topic do you want to study?", placeholder="e.g. Photosynthesis, World War 2, Newton's Laws")
        
        colA, colB = st.columns(2)
        with colA:
            num_questions = st.number_input("Number of questions", min_value=1, max_value=30, value=5)
        with colB:
            age = st.number_input("Your Age", min_value=5, max_value=100, value=15)
            
        uploaded_file = st.file_uploader("Or upload a photo of your handwritten notes", type=["jpg", "jpeg", "png"])
        
        if uploaded_file is not None:
            uploaded_file.seek(0)
            st.image(uploaded_file, caption="Notes uploaded", use_container_width=True)
            uploaded_file.seek(0)
            
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            st.session_state.stress_mode = st.toggle("⚡ Exam Stress Mode")
        with sub_col2:
            start_btn = st.button("Start Quiz →", type="primary", use_container_width=True)
            
        if start_btn:
            if not topic:
                st.error("Please enter a topic first.")
                st.stop()
                
            with st.spinner("Generating your quiz..."):
                if uploaded_file is not None:
                    image_b64 = base64.b64encode(uploaded_file.read()).decode("utf-8")
                else:
                    image_b64 = None
                    
                try:
                    quiz_result = generate_quiz(topic, image_b64, num_questions, age)
                except ValueError as e:
                    st.error(f"Failed to generate quiz. {str(e)}")
                    st.info("If you are getting a 'insufficient_quota' error, it means your OpenAI account has run out of credits. Please visit platform.openai.com to top up your account.")
                    st.stop()
                    
                st.session_state.quiz = quiz_result.get("questions", [])
                st.session_state.current_q = 0
                st.session_state.answers = []
                st.session_state.selected_answers = []
                st.session_state.analysis = None
                st.session_state.stress_plan = None
                st.session_state.stage = "quiz"
                st.session_state.profile["topic"] = topic
                st.session_state.profile["age"] = age
                st.rerun()

    elif st.session_state.stage == "quiz":
        total = len(st.session_state.quiz)
        current = st.session_state.current_q
        question = st.session_state.quiz[current]
        
        st.progress(current / total)
        st.caption(f"Question {current + 1} of {total} — Topic: {st.session_state.profile['topic']}")
        
        with st.container():
            st.markdown(f"### {question['q']}")
            selected = st.radio("Choose your answer:", question["options"], key=f"radio_{current}", label_visibility="collapsed", index=None)
            
        if st.button("Submit Answer →", type="primary"):
            if selected is None:
                st.warning("Please select an answer.")
                st.stop()
                
            st.session_state.selected_answers.append(selected)
            
            if current + 1 < total:
                st.session_state.current_q += 1
                st.rerun()
            else:
                results = build_results(st.session_state.quiz, st.session_state.selected_answers)
                st.session_state.profile = update_profile(st.session_state.profile, results)
                wrong = get_wrong_answers(results)
                
                st.session_state.analysis = analyze_results(wrong)
                
                if "weak" in st.session_state.analysis:
                    for w in st.session_state.analysis["weak"]:
                        if w not in st.session_state.profile["weak"]:
                            st.session_state.profile["weak"].append(w)
                            
                if st.session_state.stress_mode:
                    st.session_state.stress_plan = stress_mode_plan(st.session_state.profile["weak"])
                    
                st.session_state.stage = "results"
                st.rerun()

    elif st.session_state.stage == "results":
        score = st.session_state.profile["score"]
        total = st.session_state.profile["total"]
        pct = int((score/total)*100) if total > 0 else 0
        
        st.markdown("## 📊 Quiz Complete")
        
        if pct == 100:
            st.success("Perfect score! Outstanding.")
            st.balloons()
        elif pct >= 60:
            st.info(f"Good effort — {score}/{total} correct ({pct}%)")
        else:
            st.warning(f"Keep going — {score}/{total} correct ({pct}%). Review weak areas below.")
            
        st.divider()
        
        analysis = st.session_state.analysis
        if analysis and analysis.get("next_task"):
            st.info(f"📌 Next: {analysis['next_task']}")
            
        if analysis and analysis.get("encouragement"):
            st.success(analysis['encouragement'])
            
        if analysis and analysis.get("resources"):
            st.markdown("### 📺 Recommended Resources")
            for res in analysis["resources"]:
                st.markdown(f"**[{res.get('title', 'Watch Video')}]({res.get('url', '#')})**")
                if "video_id" in res:
                    st.image(f"https://img.youtube.com/vi/{res['video_id']}/mqdefault.jpg", width=320)
            
        if st.button("🔄 Take Another Quiz", use_container_width=True):
            st.session_state.stage = "input"
            st.session_state.quiz = None
            st.session_state.current_q = 0
            st.session_state.answers = []
            st.session_state.selected_answers = []
            st.session_state.analysis = None
            st.session_state.stress_plan = None
            st.session_state.profile = new_profile()
            st.rerun()

with col2:
    profile = st.session_state.profile
    
    st.markdown("### 👤 Learner Profile")
    st.divider()
    
    st.markdown(f"**Topic:** {profile['topic'] or 'Not started yet'}")
    if profile.get('topic'):
        st.markdown(f"**Age Level:** {profile.get('age', 15)} years old")
    
    st.metric("Score", f"{profile['score']}/{profile['total']}")
    
    prof_score = profile["score"]
    prof_total = profile["total"]
    prof_pct = int((prof_score/prof_total)*100) if prof_total > 0 else 0
    st.markdown(f"<div class='score-bar-bg'><div class='score-bar-fill' style='width:{prof_pct}%'></div></div>", unsafe_allow_html=True)
    
    st.markdown("**✅ Strong Concepts**")
    if not profile["strong"]:
        st.caption("None yet")
    else:
        badges = " ".join([f'<span class="concept-strong">{c}</span>' for c in profile["strong"]])
        st.markdown(badges, unsafe_allow_html=True)
        
    st.markdown("**❌ Weak Concepts**")
    if not profile["weak"]:
        st.caption("None yet")
    else:
        badges = " ".join([f'<span class="concept-weak">{c}</span>' for c in profile["weak"]])
        st.markdown(badges, unsafe_allow_html=True)
        
    if st.session_state.stress_plan is not None:
        st.markdown("### ⚡ Exam Stress Plan")
        for item in st.session_state.stress_plan.get("plan", []):
            priority = item.get("priority")
            topic_str = item.get("topic")
            action = item.get("action")
            time_mins = item.get("time_mins")
            html = f"""<div class='stress-item'>
            <b>Priority {priority}: {topic_str}</b><br>
            {action}<br>
            <small style='color: gray;'>⏱ {time_mins} min</small>
            </div>"""
            st.markdown(html, unsafe_allow_html=True)
            
    if st.session_state.analysis is not None and st.session_state.stress_plan is None:
        st.markdown("### 📋 Recommendation")
        analysis = st.session_state.analysis
        if analysis.get("next_task"):
            st.info(analysis["next_task"])
        if analysis.get("encouragement"):
            st.success(analysis["encouragement"])
        if analysis.get("resources"):
            st.markdown("**📺 Resources to Review:**")
            for res in analysis["resources"]:
                st.markdown(f"**[{res.get('title', 'Watch Video')}]({res.get('url', '#')})**")
                if "video_id" in res:
                    st.image(f"https://img.youtube.com/vi/{res['video_id']}/mqdefault.jpg", use_container_width=True)
            
    st.divider()
    st.caption("Powered by GPT-4o · Adaptive Study Coach")
