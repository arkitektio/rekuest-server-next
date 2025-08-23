# Hook Agent Documentation

## Overview

Hook Agents are a server-to-server communication mechanism that allows external servers to register as agents and receive task assignments via HTTP POST requests instead of WebSocket connections.

## How It Works

1. **Registration**: An external server registers as a "hook agent" using the `ensure_agent` GraphQL mutation
2. **Task Assignment**: When tasks are assigned to hook agents, the Rekuest server sends HTTP POST requests to the hook agent's endpoint
3. **Event Reporting**: Hook agents report back assignment events (progress, completion, errors, etc.) via REST API endpoints

## Registration

To register a hook agent, use the `ensure_agent` GraphQL mutation with these additional parameters:

```graphql
mutation EnsureHookAgent {
  ensureAgent(input: {
    instanceId: "my-hook-agent"
    name: "My Hook Agent"
    isHookAgent: true
    hookEndpoint: "https://my-server.com/rekuest-webhook"
    hookSecretToken: "my-secret-token-123"
  }) {
    id
    name
    isHookAgent
    hookEndpoint
  }
}
```

### Required Parameters for Hook Agents

- `isHookAgent: true` - Marks this as a hook agent
- `hookEndpoint` - The URL where POST requests will be sent
- `hookSecretToken` - Secret token for authenticating requests

## Receiving Task Assignments

When a task is assigned to your hook agent, you'll receive a POST request to your `hookEndpoint`:

### Request Format

```http
POST /rekuest-webhook HTTP/1.1
Host: my-server.com
Content-Type: application/json
Authorization: Bearer my-secret-token-123
User-Agent: Rekuest-Server/1.0

{
  "type": "ASSIGN",
  "message": {
    "assignation": "assignment-id-123",
    "args": { ... },
    "user": "user-id",
    "app": "client-id",
    "reference": "ref-123",
    "interface": { ... },
    "extension": { ... },
    "action": "action-id"
  },
  "agent_id": "agent-id-456"
}
```

### Message Types

- `ASSIGN` - New task assignment
- `CANCEL` - Cancel a running task
- `INTERRUPT` - Interrupt a running task
- `COLLECT` - Collect results from memory drawers

## Reporting Assignment Events

Hook agents must report back assignment events using the REST API:

### Base URL

`POST /api/hook-agent/events/`

### Authentication

Include your hook secret token in the Authorization header:

```http
Authorization: Bearer my-secret-token-123
```

### Event Types and Payload Examples

#### Progress Event

```json
{
  "assignation_id": "assignment-id-123",
  "event_type": "PROGRESS", 
  "progress": 50,
  "message": "Processing data..."
}
```

#### Log Event

```json
{
  "assignation_id": "assignment-id-123",
  "event_type": "LOG",
  "message": "Started processing file.txt",
  "level": "INFO"
}
```

#### Done Event

```json
{
  "assignation_id": "assignment-id-123",
  "event_type": "DONE",
  "returns": {
    "result": "success",
    "output_file": "/path/to/output.txt"
  }
}
```

#### Yield Event

```json
{
  "assignation_id": "assignment-id-123", 
  "event_type": "YIELD",
  "returns": {
    "intermediate_result": "partial data"
  }
}
```

#### Error Event

```json
{
  "assignation_id": "assignment-id-123",
  "event_type": "ERROR",
  "message": "Failed to process input file"
}
```

#### Critical Event

```json
{
  "assignation_id": "assignment-id-123",
  "event_type": "CRITICAL", 
  "message": "System out of memory"
}
```

#### Cancelled Event

```json
{
  "assignation_id": "assignment-id-123",
  "event_type": "CANCELLED",
  "message": "Task was cancelled by user"
}
```

## Heartbeat

Hook agents should periodically send heartbeat requests to indicate they are still active:

```http
POST /api/hook-agent/heartbeat/ HTTP/1.1
Authorization: Bearer my-secret-token-123
```

## Implementation Example

Here's a simple Python example of a hook agent server:

```python
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

REKUEST_BASE_URL = "https://rekuest-server.com"
SECRET_TOKEN = "my-secret-token-123"

@app.route('/rekuest-webhook', methods=['POST'])
def handle_assignment():
    # Verify authentication
    auth_header = request.headers.get('Authorization')
    if not auth_header or auth_header != f'Bearer {SECRET_TOKEN}':
        return 'Unauthorized', 401
    
    data = request.json
    message_type = data['type']
    message = data['message']
    
    if message_type == 'ASSIGN':
        # Process the assignment
        assignation_id = message['assignation']
        args = message['args']
        
        # Report progress
        report_progress(assignation_id, 25, "Starting task...")
        
        # Do work here...
        result = process_task(args)
        
        # Report completion
        report_done(assignation_id, result)
        
    return jsonify({'status': 'ok'})

def report_progress(assignation_id, progress, message):
    requests.post(
        f"{REKUEST_BASE_URL}/api/hook-agent/events/",
        json={
            "assignation_id": assignation_id,
            "event_type": "PROGRESS",
            "progress": progress,
            "message": message
        },
        headers={"Authorization": f"Bearer {SECRET_TOKEN}"}
    )

def report_done(assignation_id, returns):
    requests.post(
        f"{REKUEST_BASE_URL}/api/hook-agent/events/",
        json={
            "assignation_id": assignation_id,
            "event_type": "DONE", 
            "returns": returns
        },
        headers={"Authorization": f"Bearer {SECRET_TOKEN}"}
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

## Security Considerations

- Keep your `hookSecretToken` secure and rotate it regularly
- Use HTTPS for your hook endpoint to protect data in transit
- Validate all incoming requests and sanitize input data
- Implement proper error handling and logging
- Consider rate limiting to prevent abuse

## Error Handling

The Rekuest server will retry failed requests with exponential backoff. Hook agents should:

- Return HTTP 200 for successful requests
- Return appropriate error codes for failures
- Include error details in the response body when possible
- Handle timeouts gracefully (requests timeout after 30 seconds)