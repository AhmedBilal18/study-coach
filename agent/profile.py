def new_profile():
    return {
        "topic": "",
        "strong": [],
        "weak": [],
        "quiz_history": [],
        "score": 0,
        "total": 0
    }

def update_profile(profile, results):
    for result in results:
        profile["total"] += 1
        concept = result["concept"]
        if result["correct"]:
            profile["score"] += 1
            if concept not in profile["strong"]:
                profile["strong"].append(concept)
        else:
            if concept not in profile["weak"]:
                profile["weak"].append(concept)
        profile["quiz_history"].append(result)
    return profile
