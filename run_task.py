from flask import Flask, request, jsonify
import os

# Attempt to import the executor function
try:
    from task_executor import execute_task
except ImportError:
    # Define a placeholder if import fails, useful for initial deployment testing
    def execute_task(task_data):
        print("WARNING: task_executor.py not found or execute_task not defined. Using placeholder.")
        return {"status": "executor_not_found", "task_data_received": task_data}

app = Flask(__name__)

@app.route("/run_task", methods=["POST"])
def run_task_endpoint(): # Renamed function to avoid conflict with module name
    try:
        task_data = request.get_json()
        if not task_data:
            print("ERROR: No JSON data received in POST request to /run_task")
            return jsonify({"error": "No JSON data provided"}), 400

        print(f"INFO: Received task: {task_data.get("task_type", "unknown")}")
        result = execute_task(task_data)

        print(f"INFO: Task {task_data.get("task_type", "unknown")} execution result: {result}")
        return jsonify({
            "status": "success",
            "task_type": task_data.get("task_type", "unknown"),
            "result": result
        }), 200

    except Exception as e:
        # Log the exception for debugging
        print(f"ERROR in /run_task endpoint: {e}") # Basic logging to console
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Listen on all interfaces and Railway's assigned port, disable debug for production
    port = int(os.environ.get("PORT", 8080))
    print(f"INFO: Starting Flask server on 0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False) # Set debug=False for Railway deployment

