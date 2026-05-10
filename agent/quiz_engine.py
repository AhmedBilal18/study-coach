def check_answer(question, selected_option):
    correct_letter = question.get("answer", "")
    if selected_option and correct_letter:
        return selected_option.startswith(correct_letter)
    return False

def build_results(questions, selected_answers):
    results = []
    for q, selected in zip(questions, selected_answers):
        correct = check_answer(q, selected)
        correct_letter = q.get("answer", "")
        correct_answer_str = ""
        for opt in q.get("options", []):
            if opt.startswith(correct_letter):
                correct_answer_str = opt
                break
        results.append({
            "concept": q.get("concept", ""),
            "correct": correct,
            "question": q.get("q", ""),
            "selected": selected,
            "correct_answer": correct_answer_str
        })
    return results

def get_wrong_answers(results):
    return [res for res in results if not res.get("correct")]

def calculate_score(results):
    total = len(results)
    score = sum(1 for res in results if res.get("correct"))
    percentage = round((score / total) * 100) if total > 0 else 0
    return {
        "score": score,
        "total": total,
        "percentage": percentage
    }
