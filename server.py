import os
import uuid
import tempfile
import json
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

from vector_db import NutritionHealthVectorDB
from llm_processor import LLMProcessor
from medical_report_pipeline import MedicalReportPipeline

app = Flask(__name__)
CORS(app)

# Initialize singletons for our DBs and LLM
print("Initializing databases and models...")
diagnosis_db = NutritionHealthVectorDB(db_path="./diagnosis_vectordb")
nutrition_db = NutritionHealthVectorDB(db_path="./nutrition_vectordb")
llm = LLMProcessor()
pipeline = MedicalReportPipeline(diagnosis_db=diagnosis_db, nutrition_db=nutrition_db, llm=llm)

# In-memory session store
# Format: { "session_id": { "report_text": "...", "findings": [...], "patient_notes": "...", "loop_count": 0, "rag_queries": [] } }
sessions = {}

def parse_question(text: str):
    """
    Parses a multiple-choice question from Gemini's output.
    Expected format:
    1. [Question]
       A) [Option 1]
       B) [Option 2]
       C) [Option 3]
       D) [Option 4]
    """
    text = text.strip()
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    question_text = lines[0]
    options = []
    for line in lines[1:]:
        if re.match(r'^[A-D][\.\)]', line, re.IGNORECASE):
            options.append(line.split(' ', 1)[1].strip())
    
    # If parsing fails to find options, return raw text as a single question
    if not options:
        return {"text": text, "options": []}
    return {"text": question_text, "options": options}

def clean_json_output(text: str) -> dict:
    try:
        # Strip markdown code blocks if any
        text = re.sub(r'```json', '', text)
        text = re.sub(r'```', '', text)
        return json.loads(text.strip())
    except Exception as e:
        print("JSON Decode Error:", e)
        # Fallback dictionary if JSON parsing fails
        return {
            "summary": text[:500] + "...\n\n(Error parsing JSON)",
            "general_advice": "",
            "diet": "Error parsing JSON",
            "fitness": "Error parsing JSON",
            "important": ""
        }

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/api/start', methods=['POST'])
def start_session():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400
    
    ext = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
        file.save(temp_file.name)
        file_path = temp_file.name

    try:
        print("Extracting report text...")
        report_text = pipeline.extract_report_text(file_path)
        if not report_text or len(report_text.strip()) < 30:
            return jsonify({"error": "Could not extract sufficient text."}), 400
        
        max_report = int(os.getenv("REPORT_MAX_CHARS", "24000"))
        report_for_llm = report_text[:max_report]

        print("Extracting findings...")
        findings = llm.extract_report_findings(report_for_llm, "")

        print("Fetching initial diagnosis context...")
        diag_queries = llm.plan_rag_queries(findings, "")
        diag_hits = pipeline._search_knowledge(diagnosis_db, "server_session", diag_queries, findings)

        print("Generating initial summary...")
        initial_summary = llm.generate_summary(report_for_llm, findings, "")

        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "report_text": report_for_llm,
            "findings": findings,
            "diag_hits": diag_hits,
            "patient_notes": "",
            "loop_count": 0,
            "current_summary": initial_summary
        }

        print("Evaluating first step...")
        evaluation = llm.evaluate_and_ask(report_for_llm, findings, "", diag_hits)

        if evaluation.strip().startswith("[READY]"):
            return generate_final_report(session_id)
        else:
            q_data = parse_question(evaluation)
            return jsonify({
                "status": "question",
                "session_id": session_id,
                "question": q_data,
                "summary": initial_summary
            })

    except Exception as e:
        print(f"Error in start_session: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            os.unlink(file_path)
        except:
            pass

@app.route('/api/answer', methods=['POST'])
def answer_question():
    data = request.json
    if not data or 'session_id' not in data or 'answer' not in data:
        return jsonify({"error": "Missing session_id or answer"}), 400
    
    session_id = data['session_id']
    if session_id not in sessions:
        return jsonify({"error": "Invalid or expired session_id"}), 404
    
    session = sessions[session_id]
    question_text = data.get('question_text', 'Question')
    user_answer = data['answer']

    session['patient_notes'] += f"\nQ: {question_text}\nA: {user_answer}\n"
    session['loop_count'] += 1

    if session['loop_count'] >= 5:
        print("Max loop reached, generating report...")
        return generate_final_report(session_id)

    print(f"Evaluating step {session['loop_count']}...")
    evaluation = llm.evaluate_and_ask(session['report_text'], session['findings'], session['patient_notes'], session['diag_hits'])

    if evaluation.strip().startswith("[READY]"):
        return generate_final_report(session_id)
    else:
        q_data = parse_question(evaluation)
        return jsonify({
            "status": "question",
            "session_id": session_id,
            "question": q_data
        })

def generate_final_report(session_id: str):
    session = sessions[session_id]
    print("Generating final report...")
    rag_queries = llm.plan_rag_queries(session['findings'], session['patient_notes'])
    
    # Generic user_id for the server session queries
    user_id = "server_session"
    
    diag_hits = pipeline._search_knowledge(diagnosis_db, user_id, rag_queries, session['findings'])
    nutri_hits = pipeline._search_knowledge(nutrition_db, user_id, rag_queries, session['findings'])
    knowledge_hits = diag_hits + nutri_hits

    care_plan_json_str = llm.synthesize_care_plan(
        session['report_text'],
        session['findings'],
        knowledge_hits,
        session['patient_notes']
    )
    
    care_plan = clean_json_output(care_plan_json_str)

    sources = set()
    for hit in knowledge_hits:
        src = hit.get('source')
        if src:
            sources.add(os.path.basename(src))
            
    if sources:
        sources_md = "\n\n<details><summary>View Sources</summary>\n<ul>\n"
        for src in sorted(sources):
            sources_md += f"<li>{src}</li>\n"
        sources_md += "</ul>\n</details>"
        
        if care_plan.get('diet'):
            care_plan['diet'] += sources_md
        if care_plan.get('fitness'):
            care_plan['fitness'] += sources_md

    return jsonify({
        "status": "ready",
        "session_id": session_id,
        "report": care_plan,
        "patient_info": care_plan.get("patient_info")
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
