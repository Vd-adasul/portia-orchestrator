# api/index.py
import os
import json
from http.server import BaseHTTPRequestHandler
from portia_sdk.main import Portia
from portia_sdk.llms.google import GoogleGenAI
from .tools.communication import communication_tools
from .tools.github import github_tools
from .tools.scheduling import scheduling_tools
from .tools.productivity import productivity_tools

# --- API KEY USAGE ---
# This file uses the following environment variable:
# - GOOGLE_API_KEY: For Portia to use the Gemini model for planning.

# This line initializes Portia with the Gemini model as its reasoning engine.
portia = Portia(llm=GoogleGenAI(model="gemini-1.5-flash"))
# This line collects all the available tools from the other files.
all_tools = communication_tools + github_tools + scheduling_tools + productivity_tools

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # This is the high-level instruction given to the AI.
        prompt = (
            "You are Portia, an AI Chief of Staff. Create a prioritized daily action plan (max 5 items). "
            "1. Fetch all tasks from emails, Slack, and GitHub. "
            "2. For each high-priority item, generate a proactive next step (e.g., draft a reply, add a task to Notion, schedule a meeting). "
            "3. Present the final output as a JSON list of tasks, each with a 'proposed_action' object."
        )
        try:
            # Step 1: The AI creates a plan of which tools to run.
            plan = portia.plan(prompt, tools=all_tools)
            
            # Step 2: The plan is executed, and the data-gathering tools are run.
            plan_run = portia.run_plan(plan=plan, tools=all_tools)
            
            # Step 3: The raw data from the tools is formatted into the final task list.
            final_tasks = self.format_plan_outputs_to_tasks(plan_run.outputs)
            
            # Send the final plan to the frontend.
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(final_tasks).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

    def format_plan_outputs_to_tasks(self, outputs):
        tasks, task_id_counter = [], 1
        
        # Process emails and decide whether to reply or create a Notion task.
        if 'fetch_unread_emails' in outputs and isinstance(outputs['fetch_unread_emails'], list):
            for email in outputs['fetch_unread_emails']:
                action = {"tool_id": "add_task_to_notion_db", "params": {"task_title": f"Follow up on email: {email['subject']}"}} if "urgent" in email['subject'].lower() else {"tool_id": "send_gmail_reply", "params": {"thread_id": email['id'], "body": f"AI DRAFT: Thanks for your email about '{email['subject']}'. I'm on it."}}
                tasks.append({"id": f"task_{task_id_counter}", "type": "notion" if "urgent" in email['subject'].lower() else "gmail", "summary": f"Email from {email['from']}: {email['subject']}", "source": "Gmail", "priority": "high", "proposed_action": action})
                task_id_counter += 1
        
        # Process GitHub items and decide whether to comment or merge.
        if 'fetch_github_items' in outputs and isinstance(outputs['fetch_github_items'], list):
            for item in outputs['fetch_github_items']:
                action = {"tool_id": "merge_pull_request", "params": {"repo_name": item['repo'], "pr_number": item['number'], "merge_method": "squash"}} if item['type'] == 'PR' else {"tool_id": "post_github_comment", "params": {"repo_name": item['repo'], "issue_number": item['number'], "comment": "AI DRAFT: Thanks for flagging this. I'll investigate."}}
                tasks.append({"id": f"task_{task_id_counter}", "type": "github", "summary": f"GitHub {item['type']} in {item['repo']}: {item['title']}", "source": "GitHub", "priority": "high", "proposed_action": action})
                task_id_counter += 1
        
        # Return the top 5 most important tasks.
        return tasks[:5]
