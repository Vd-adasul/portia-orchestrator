# api/approve.py
import json
from http.server import BaseHTTPRequestHandler
from .tools.communication import communication_tools
from .tools.github import github_tools
from .tools.scheduling import scheduling_tools
from .tools.productivity import productivity_tools

# This line gathers all the tools from the different files into one master dictionary.
# This makes it easy to find and run any tool by its ID.
all_tools = {tool.id: tool for tool in communication_tools + github_tools + scheduling_tools + productivity_tools}

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Read the incoming request from the frontend
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data)

            tool_id = body.get("tool_id")
            params = body.get("params")

            # Basic validation to ensure the request is valid
            if not tool_id or params is None:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Missing 'tool_id' or 'params' in request body"}).encode('utf-8'))
                return

            # Find the correct tool function from the 'all_tools' dictionary
            tool_to_execute = all_tools.get(tool_id)
            if not tool_to_execute:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Tool '{tool_id}' not found"}).encode('utf-8'))
                return

            # This is the core execution step: run the tool's function with the approved parameters.
            # For example, tool_to_execute.func might be 'send_gmail_reply_func'
            # and params would be {'thread_id': '...', 'body': '...'}
            result = tool_to_execute.func(**params)

            # Send a success response back to the frontend
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "result": result}).encode('utf-8'))

        except Exception as e:
            # Send an error response if anything goes wrong
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
