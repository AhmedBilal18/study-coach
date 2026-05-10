import streamlit as st
import base64
import json
import time

from agent.coach import generate_quiz, analyze_results, stress_mode_plan
from agent.profile import new_profile, update_profile
from agent.quiz_engine import check_answer, build_results, get_wrong_answers, calculate_score

st.set_page_config(page_title="Study Coach", page_icon="🎓", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
.stApp { background-color: #f8f9fb; }
.profile-card { background: white; border-radius: 12px; padding: 1.5rem; border: 1px solid #e0e0e0; }
.concept-strong { background: #e8f5e9; color: #2e7d32; padding: 4px 10px; border-radius: 20px; font-size: 13px; display: inline-block; margin: 3px; }
.concept-weak { background: #ffebee; color: #c62828; padding: 4px 10px; border-radius: 20px; font-size: 13px; display: inline-block; margin: 3px; }
.stress-item { background: white; border-left: 4px solid #f44336; border-radius: 8px; padding: 12px 16px; margin: 8px 0; }
.question-box { background: white; border-radius: 12px; padding: 2rem; border: 1px solid #e0e0e0; margin-bottom: 1rem; }
.score-bar-fill { background: linear-gradient(90deg, #43a047, #66bb6a); height: 8px; border-radius: 4px; transition: width 0.4s ease; }
.score-bar-bg { background: #e0e0e0; height: 8px; border-radius: 4px; margin: 8px 0 16px; }
div[data-testid="stRadio"] label { font-size: 15px; padding: 6px 0; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "profile" not in st.session_state:
    st.session_state.profile = new_profile()
if "quiz" not in st.session_state:
    st.session_state.quiz = None
if "current_q" not in st.session_state:
    st.session_state.current_q = 0
if "answers" not in st.session_state:
    st.session_state.answers = []
if "selected_options" not in st.session_state:
    st.session_state.selected_options = []
if "stage" not in st.session_state:
    st.session_state.stage = "input"
if "analysis" not in st.session_state:
    st.session_state.analysis = None
if "stress_plan" not in st.session_state:
    st.session_state.stress_plan = None
if "stress_mode" not in st.session_state:
    st.session_state.stress_mode = False

col1, col2 = st.columns([1.1, 0.9], gap="large")

with col1:
    if st.session_state.stage == "input":
        st.markdown("## 📚 Adaptive Study Coach")
        st.markdown("*Your AI teacher that adapts to you*")
        st.divider()
        
        topic = st.text_input("What topic do you want to study?", placeholder="e.g. Photosynthesis, World War 2, Newton's Laws")
        uploaded_file = st.file_uploader("Or upload a photo of your handwritten notes", type=["jpg","jpeg","png"])
        
        if uploaded_file is not None:
            st.image(uploaded_file, caption="Notes uploaded", use_column_width=True)
            
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            st.session_state.stress_mode = st.toggle("⚡ Exam Stress Mode", help="Compresses your study plan when deadline is near", value=st.session_state.stress_mode)
        with sub_col2:
            start_btn = st.button("Start Quiz →", type="primary", use_container_width=True)
            
        if start_btn:
            if not topic:
                st.error("Please enter a topic first")
                st.stop()
                
            with st.spinner("Generating your quiz..."):
                image_b64 = None
                if uploaded_file is not None:
                    image_b64 = base64.b64encode(uploaded_file.read()).decode()
                    
                quiz_result = generate_quiz(topic, image_b64)
                st.session_state.quiz = quiz_result.get("questions", [])
                st.session_state.profile["topic"] = topic
                st.session_state.current_q = 0
                st.session_state.answers = []
                st.session_state.selected_options = []
                st.session_state.analysis = None
                st.session_state.stress_plan = None
                st.session_state.stage = "quiz"
                st.rerun()

    elif st.session_state.stage == "quiz":
        total = len(st.session_state.quiz)
        current = st.session_state.current_q
        
        st.progress((current) / total)
        st.caption(f"Question {current+1} of {total}")
        
        question = st.session_state.quiz[current]
        
        with st.container():
            st.markdown(f"### {question['q']}")
            selected = st.radio("Choose your answer:", question["options"], key=f"q_{current}", label_visibility="collapsed")
            
        if st.button("Submit Answer →", type="primary"):
            is_correct = check_answer(question, selected)
            
            if is_correct:
                st.success("Correct!")
                st.balloons()
            else:
                st.error(f"Wrong — correct answer was {question['answer']}")
                
            st.session_state.selected_options.append(selected)
            
            time.sleep(0.8)
            
            if current + 1 < total:
                st.session_state.current_q += 1
                st.rerun()
            else:
                with st.spinner("Analyzing your results..."):
                    final_results = build_results(st.session_state.quiz, st.session_state.selected_options)
                    st.session_state.answers = final_results
                    
                    st.session_state.profile = update_profile(st.session_state.profile, final_results)
                    wrong_answers = get_wrong_answers(final_results)
                    
                    st.session_state.analysis = analyze_results(wrong_answers)
                    
                    if "weak" in st.session_state.analysis:
                        for weak_concept in st.session_state.analysis["weak"]:
                            if weak_concept not in st.session_state.profile["weak"]:
                                st.session_state.profile["weak"].append(weak_concept)
                                
                    if st.session_state.stress_mode:
                        st.session_state.stress_plan = stress_mode_plan(st.session_state.profile["weak"])
                        
                    st.session_state.stage = "results"
                st.rerun()

    elif st.session_state.stage == "results":
        quiz_stats = calculate_score(st.session_state.answers)
        score = quiz_stats["score"]
        total_q = quiz_stats["total"]
        pct = quiz_stats["percentage"]
        
        st.markdown("## Results")
        
        if pct == 100:
            st.success("Perfect score! Outstanding work.")
            st.balloons()
        elif pct >= 60:
            st.info(f"Good effort — {score}/{total_q} correct.")
        else:
            st.warning(f"Keep going — {score}/{total_q} correct. Focus on the weak areas.")
            
        if st.session_state.analysis:
            st.info(f"📌 Next: {st.session_state.analysis.get('next_task')}")
            st.success(st.session_state.analysis.get("encouragement"))
            
        if st.button("Take Another Quiz", use_container_width=True):
            st.session_state.stage = "input"
            st.rerun()

with col2:
    profile = st.session_state.profile
    
    st.markdown("### 👤 Learner Profile")
    st.divider()
    
    st.markdown(f"**Topic:** {profile.get('topic') or 'Not started yet'}")
    
    st.metric("Score", f"{profile['score']}/{profile['total']}", delta=None)
    
    prof_total = profile['total']
    prof_score = profile['score']
    prof_pct = int((prof_score/prof_total)*100) if prof_total > 0 else 0
    st.markdown(f'<div class="score-bar-bg"><div class="score-bar-fill" style="width: {prof_pct}%;"></div></div>', unsafe_allow_html=True)
    
    st.markdown("**✅ Strong concepts**")
    if not profile["strong"]:
        st.caption("None yet")
    else:
        badges = " ".join([f'<span class="concept-strong">{c}</span>' for c in profile["strong"]])
        st.markdown(badges, unsafe_allow_html=True)
        
    st.markdown("**❌ Weak concepts**")
    if not profile["weak"]:
        st.caption("None yet")
    else:
        badges = " ".join([f'<span class="concept-weak">{c}</span>' for c in profile["weak"]])
        st.markdown(badges, unsafe_allow_html=True)
        
    if st.session_state.stress_plan is not None:
        st.markdown("### ⚡ Stress Mode Plan")
        for item in st.session_state.stress_plan.get("plan", []):
            priority = item.get('priority')
            topic = item.get('topic')
            action = item.get('action')
            time_mins = item.get('time_mins')
            html = f"""<div class="stress-item">
            <b>Priority {priority}: {topic}</b><br>
            {action}<br>
            <small style="color: gray;">⏱ {time_mins} min</small>
            </div>"""
            st.markdown(html, unsafe_allow_html=True)
            
    if st.session_state.analysis is not None and st.session_state.stress_plan is None:
        st.markdown("### 📋 Study Recommendation")
        st.info(st.session_state.analysis.get("next_task"))
        st.success(st.session_state.analysis.get("encouragement"))
        
    st.divider()
    st.caption("Powered by GPT-4o · Built for hackathon")
