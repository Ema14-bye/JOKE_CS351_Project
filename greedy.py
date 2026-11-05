import csv
import ast

def read_csv(name: str):
    """reads the csv"""
    with open(name, mode='r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        return list(csv_reader)

def safe_parse_list(val: str) -> list:
    """evaluates lists as strings and flatten any accidental nesting."""
    if not val or not val.strip():
        return []

    parsed = ast.literal_eval(val.strip())
    if isinstance(parsed, list):
        # To account for nesting like [['CS151']]
        flat_list = []
        for item in parsed:
            if isinstance(item, list):
                flat_list.extend([str(sub_item).strip() for sub_item in item])
            else:
                flat_list.append(str(item).strip())
        return flat_list
    return [str(parsed).strip()]

def load_catalog(datalist: list) -> dict:
    """creates catalog using ast"""
    catalog = {}
    
    # Initialize the nodes
    for row in datalist:
        cid = row["id"].strip()
        catalog[cid] = {
            "id": cid,
            "credits": int(row["credits"]),
            "prerequisites": safe_parse_list(row["prerequisites"]),
            "corequisites": safe_parse_list(row["corequisites"]),
            "terms": safe_parse_list(row["terms"]),
            "offered": row["offered"].strip(),
            "meeting_times": safe_parse_list(row["meeting_times"]),
            "course_requirements": safe_parse_list(row["course_requirements"]),
            "priority": int(row["priority"]),
            "dependents": []  # Outgoing edges: courses that require this one
        }
        
    # Go back and make the DAG chains
    for cid, data in catalog.items():
        for prereq in data["prerequisites"]:
            if prereq in catalog:
                catalog[prereq]["dependents"].append(cid)
                
    return catalog

def parse_time_slot(time_str):
    """Helper to parse a time string like 'MWF 12:00-13:00' into days and minutes"""
    if not time_str or time_str.strip() == "":
        return None, 0, 0
    
    parts = time_str.strip().split()
    days = set(parts[0]) # e.g. {'M', 'W', 'F'}
    start_str, end_str = parts[1].split('-')
    
    def to_minutes(t_str):
        h, m = map(int, t_str.split(':'))
        return h * 60 + m
        
    return days, to_minutes(start_str), to_minutes(end_str)
    

def has_time_conflict(course_meeting_times, scheduled_courses, catalog):
    """Check if a candidate course conflicts with any already scheduled course this semester"""
    for cand_time in course_meeting_times:
        c_days, c_start, c_end = parse_time_slot(cand_time)
        if not c_days:
            continue
        for sc_id in scheduled_courses:
            for sc_time in catalog[sc_id]["meeting_times"]:
                s_days, s_start, s_end = parse_time_slot(sc_time)
                if not s_days:
                    continue
                # If they share at least one day and their time intervals overlap
                if c_days.intersection(s_days):
                    if max(c_start, s_start) < min(c_end, s_end):
                        return True 
    return False

def greedy_schedule(catalog, max_semesters=8, max_credits_per_sem=16):
    completed = set()
    semester_plans = []
    
    def get_term_name(sem_num):
        return "Fall" if sem_num % 2 != 0 else "Spring"

    for sem in range(1, max_semesters + 1):
        current_term = get_term_name(sem)
        semester_credits = 0
        semester_courses = []
        
        # Find all candidate courses available in this term whose prereqs are met
        candidates = []
        for cid, data in catalog.items():
            if cid in completed:
                continue
            # Check if offered this term
            if current_term not in data["terms"]:
                continue
            # Check if prerequisites are met
            if not all(prereq in completed for prereq in data["prerequisites"]):
                continue
            candidates.append(data)
            
        candidates.sort(key=lambda x: (x["priority"], -len(x["dependents"]), -x["credits"]))
        
        # For 1 semester
        for course in candidates:
            cid = course["id"]
            # Checking credit cap
            if semester_credits + course["credits"] > max_credits_per_sem:
                continue
            # Checking the time conflicts with courses already chosen
            if has_time_conflict(course["meeting_times"], semester_courses, catalog):
                continue
                
            # Add course to semester plan
            semester_courses.append(cid)
            semester_credits += course["credits"]
            
        # Mark selected courses as completed for future semesters
        for cid in semester_courses:
            completed.add(cid)
            
        semester_plans.append({
            "semester": sem,
            "term": current_term,
            "courses": semester_courses,
            "total_credits": semester_credits
        })
        
    return semester_plans, completed

if __name__ == "__main__":
    catalog = load_catalog(read_csv('cs_courses.csv'))
    plan, completed = greedy_schedule(catalog)
    
    # 8 semesters
    for sem_info in plan:
        print(f"--- Semester {sem_info['semester']} ({sem_info['term']}) | Credits: {sem_info['total_credits']} ---")
        for cid in sem_info['courses']:
            c = catalog[cid]
            print(f"  [{cid}] {c['meeting_times']} (Prereqs: {c['prerequisites']})")
        print()
        
    all_courses = set(catalog.keys())
    unmet = all_courses - completed
    if unmet:
        print(f"{len(unmet)} Leftover: {unmet}")
    