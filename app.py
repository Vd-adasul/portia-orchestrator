import os
import json
from flask import Flask, jsonify, render_template, request
from portia_sdk.main import Portia
from portia_sdk.llms.google import GoogleGenAI

# Import all your tool functions
from tools.communication import communication_tools
from tools.github import github_tools
from tools.scheduling import scheduling_tools
from tools.productivity import productivity_tools

# Initialize the Flask App
app = Flask(__name__, static_folder='static', template_folder='templates')

# --- Portia AI Setup ---
try:
    portia = Portia(llm=GoogleGenAI(model="gemini-1.5-flash"))
    all_tools = communication_tools + github_tools + scheduling_tools + productivity_tools
    # Create a dictionary for easy tool lookup
    tool_map = {tool.id: tool for tool in all_tools}
    print("Portia initialized successfully.")
except Exception as e:
    print(f"FATAL ERROR: Could not initialize Portia. Check GOOGLE_API_KEY. Error: {e}")
    portia = None
    tool_map = {}

# --- API Routes ---

@app.route('/')
def index():
    """Serves the main HTML frontend."""
    return render_template('index.html')

@app.route('/api/daily-plan', methods=['GET'])
def get_daily_plan():
    """The main 'brain' endpoint that generates the action plan."""
    if not portia:
        return jsonify({"error": "Portia AI not initialized."}), 500

    prompt = (
        "You are Portia, an AI Chief of Staff. Create a prioritized daily action plan (max 5 items). "
        "1. Fetch all tasks from emails, Slack, and GitHub. "
        "2. For each high-priority item, generate a proactive next step (e.g., draft a reply, add a task to Notion). "
        "3. Present the final output as a JSON list of tasks, each with a 'proposed_action' object."
    )
    try:
        plan = portia.plan(prompt, tools=all_tools)
        plan_run = portia.run_plan(plan=plan, tools=all_tools)
        final_tasks = format_plan_outputs_to_tasks(plan_run.outputs)
        return jsonify(final_tasks)
    except Exception as e:
        print(f"Error in /api/daily-plan: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/approve', methods=['POST'])
def approve_task():
    """Executes an approved task."""
    if not tool_map:
        return jsonify({"error": "Tools not initialized."}), 500
    
    data = request.json
    tool_id = data.get("tool_id")
    params = data.get("params")

    if not tool_id or params is None:
        return jsonify({"error": "Missing 'tool_id' or 'params'"}), 400

    tool_to_execute = tool_map.get(tool_id)
    if not tool_to_execute:
        return jsonify({"error": f"Tool '{tool_id}' not found"}), 404

    try:
        result = tool_to_execute.func(**params)
        return jsonify({"status": "success", "result": result})
    except Exception as e:
        print(f"Error executing tool {tool_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/reject', methods=['POST'])
def reject_task():
    """Logs a rejected task."""
    data = request.json
    task_id = data.get("id", "Unknown task")
    print(f"Task {task_id} was rejected by the user.")
    return jsonify({"status": "success", "message": f"Task {task_id} rejected."})


# --- Helper Function ---
def format_plan_outputs_to_tasks(outputs):
    tasks, task_id_counter = [], 1
    if 'fetch_unread_emails' in outputs and isinstance(outputs['fetch_unread_emails'], list):
        for email in outputs['fetch_unread_emails']:
            action = {"tool_id": "add_task_to_notion_db", "params": {"task_title": f"Follow up on email: {email['subject']}"}} if "urgent" in email['subject'].lower() else {"tool_id": "send_gmail_reply", "params": {"thread_id": email['id'], "body": f"AI DRAFT: Thanks for your email about '{email['subject']}'. I'm on it."}}
            tasks.append({"id": f"task_{task_id_counter}", "type": "notion" if "urgent" in email['subject'].lower() else "gmail", "summary": f"Email from {email['from']}: {email['subject']}", "source": "Gmail", "priority": "high", "proposed_action": action})
            task_id_counter += 1
    if 'fetch_github_items' in outputs and isinstance(outputs['fetch_github_items'], list):
        for item in outputs['fetch_github_items']:
            action = {"tool_id": "merge_pull_request", "params": {"repo_name": item['repo'], "pr_number": item['number'], "merge_method": "squash"}} if item['type'] == 'PR' else {"tool_id": "post_github_comment", "params": {"repo_name": item['repo'], "issue_number": item['number'], "comment": "AI DRAFT: Thanks for flagging this. I'll investigate."}}
            tasks.append({"id": f"task_{task_id_counter}", "type": "github", "summary": f"GitHub {item['type']} in {item['repo']}: {item['title']}", "source": "GitHub", "priority": "high", "proposed_action": action})
            task_id_counter += 1
    return tasks[:5]


if __name__ == '__main__':
    # This allows the app to run on Railway and other platforms
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
