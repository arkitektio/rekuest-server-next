#!/usr/bin/env python3
"""
Example Hook Agent Implementation

This is a simple example of how to implement a hook agent server that can
receive task assignments from Rekuest and report back progress and results.
"""

import json
import time
import logging
import requests
from flask import Flask, request, jsonify
from threading import Thread

# Configuration
REKUEST_BASE_URL = "http://localhost:8000"  # Update with your Rekuest server URL
SECRET_TOKEN = "my-secret-hook-token-123"   # Your hook agent secret token
AGENT_NAME = "Example Hook Agent"
INSTANCE_ID = "example-hook-agent"

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class HookAgentClient:
    """Client for communicating with Rekuest server."""
    
    def __init__(self, base_url, secret_token):
        self.base_url = base_url
        self.secret_token = secret_token
        
    def report_event(self, assignation_id, event_type, **kwargs):
        """Report an event back to the Rekuest server."""
        payload = {
            "assignation_id": assignation_id,
            "event_type": event_type,
            **kwargs
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/hook-agent/events/",
                json=payload,
                headers={"Authorization": f"Bearer {self.secret_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully reported {event_type} event for {assignation_id}")
            else:
                logger.error(f"Failed to report event: {response.status_code} {response.text}")
                
        except Exception as e:
            logger.error(f"Error reporting event: {e}")
    
    def send_heartbeat(self):
        """Send heartbeat to indicate agent is alive."""
        try:
            response = requests.post(
                f"{self.base_url}/api/hook-agent/heartbeat/",
                headers={"Authorization": f"Bearer {self.secret_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.debug("Heartbeat sent successfully")
            else:
                logger.warning(f"Heartbeat failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")

# Create client instance
client = HookAgentClient(REKUEST_BASE_URL, SECRET_TOKEN)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "agent": AGENT_NAME})

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """Main webhook endpoint for receiving assignments from Rekuest."""
    
    # Verify authentication
    auth_header = request.headers.get('Authorization')
    if not auth_header or auth_header != f'Bearer {SECRET_TOKEN}':
        logger.warning(f"Unauthorized request from {request.remote_addr}")
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        data = request.json
        message_type = data.get('type')
        message = data.get('message', {})
        agent_id = data.get('agent_id')
        
        logger.info(f"Received {message_type} message for agent {agent_id}")
        
        if message_type == 'ASSIGN':
            # Handle assignment in background thread
            thread = Thread(target=handle_assignment, args=(message,))
            thread.start()
            return jsonify({"status": "accepted"})
            
        elif message_type == 'CANCEL':
            handle_cancellation(message)
            return jsonify({"status": "cancelled"})
            
        elif message_type == 'INTERRUPT':
            handle_interrupt(message)
            return jsonify({"status": "interrupted"})
            
        elif message_type == 'COLLECT':
            handle_collect(message)
            return jsonify({"status": "collected"})
            
        else:
            logger.warning(f"Unknown message type: {message_type}")
            return jsonify({"error": "Unknown message type"}), 400
            
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        return jsonify({"error": "Internal server error"}), 500

def handle_assignment(message):
    """Handle a task assignment."""
    assignation_id = message.get('assignation')
    args = message.get('args', {})
    action_id = message.get('action')
    
    logger.info(f"Processing assignment {assignation_id} for action {action_id}")
    
    try:
        # Report that we're starting
        client.report_event(assignation_id, "LOG", 
                          message=f"Starting assignment {assignation_id}",
                          level="INFO")
        
        # Simulate some work with progress updates
        for progress in [25, 50, 75]:
            time.sleep(2)  # Simulate work
            client.report_event(assignation_id, "PROGRESS",
                              progress=progress,
                              message=f"Progress: {progress}%")
        
        # Simulate task execution based on action type
        result = execute_task(action_id, args)
        
        # Report completion
        client.report_event(assignation_id, "DONE", returns=result)
        logger.info(f"Completed assignment {assignation_id}")
        
    except Exception as e:
        logger.error(f"Error in assignment {assignation_id}: {e}")
        client.report_event(assignation_id, "ERROR", 
                          message=str(e))

def handle_cancellation(message):
    """Handle a cancellation request."""
    assignation_id = message.get('assignation')
    logger.info(f"Cancelling assignment {assignation_id}")
    
    # In a real implementation, you'd stop the running task
    client.report_event(assignation_id, "CANCELLED",
                      message="Task cancelled by request")

def handle_interrupt(message):
    """Handle an interrupt request.""" 
    assignation_id = message.get('assignation')
    logger.info(f"Interrupting assignment {assignation_id}")
    
    # In a real implementation, you'd pause/interrupt the running task
    client.report_event(assignation_id, "LOG",
                      message="Task interrupted",
                      level="WARN")

def handle_collect(message):
    """Handle a collect request."""
    drawers = message.get('drawers', [])
    logger.info(f"Collecting drawers: {drawers}")
    
    # In a real implementation, you'd collect and return the requested data

def execute_task(action_id, args):
    """
    Execute the actual task based on action type and arguments.
    
    This is where you'd implement your actual business logic.
    """
    logger.info(f"Executing action {action_id} with args: {args}")
    
    # Example task implementations
    if "process_file" in str(action_id):
        # File processing task
        filename = args.get('filename', 'unknown.txt')
        return {
            "processed_file": filename,
            "lines_processed": 1000,
            "status": "success"
        }
    
    elif "calculate" in str(action_id):
        # Mathematical calculation
        x = args.get('x', 0)
        y = args.get('y', 0)
        operation = args.get('operation', 'add')
        
        if operation == 'add':
            result = x + y
        elif operation == 'multiply':
            result = x * y
        else:
            result = 0
            
        return {
            "result": result,
            "operation": operation,
            "inputs": {"x": x, "y": y}
        }
    
    else:
        # Default task
        return {
            "status": "completed",
            "message": f"Processed action {action_id}",
            "args": args
        }

def start_heartbeat():
    """Start heartbeat thread."""
    def heartbeat_loop():
        while True:
            time.sleep(30)  # Send heartbeat every 30 seconds
            client.send_heartbeat()
    
    thread = Thread(target=heartbeat_loop, daemon=True)
    thread.start()
    logger.info("Heartbeat thread started")

if __name__ == '__main__':
    logger.info(f"Starting {AGENT_NAME} on port 5000")
    
    # Start heartbeat
    start_heartbeat()
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)