from werkzeug.wrappers import Request, Response
from werkzeug.serving import run_simple
import os
import importlib.util

# Dynamically load the requested Python file under /api
@Request.application
def application(request):
    path = request.path.strip("/")

    if not path.startswith("api/"):
        # Serve frontend
        with open("public/index.html", "r") as f:
            return Response(f.read(), mimetype="text/html")

    file_path = os.path.join(os.getcwd(), path + ".py")
    if not os.path.isfile(file_path):
        return Response("Endpoint not found", status=404)

    # Dynamically execute the endpoint script
    spec = importlib.util.spec_from_file_location("endpoint", file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if hasattr(module, "handler"):  # Expect each API file to define a handler(request)
        return module.handler(request)
    else:
        return Response("Handler not found", status=500)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    run_simple("0.0.0.0", port, application)
