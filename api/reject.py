# api/reject.py
import json
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Read the incoming request from the frontend
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        body = json.loads(post_data)
        
        task_id = body.get("id", "Unknown task")

        # In a real app, you might log this rejection to a database
        # to help the AI learn what not to suggest in the future.
        print(f"Task {task_id} was rejected by the user.")

        # Send a success response back to the frontend
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "success", "message": f"Task {task_id} rejected."}).encode('utf-8'))
