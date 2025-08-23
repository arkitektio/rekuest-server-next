# Webhook Agent Example

This directory contains a complete example of how to implement a webhook agent for the Rekuest server.

## Overview

The webhook agent allows server-to-server task assignment without maintaining persistent WebSocket connections. Instead, the Rekuest server sends HTTP POST requests to the webhook agent's endpoint with task assignments.

## Files

- `webhook_agent_example.py` - Complete webhook agent implementation using aiohttp

## How It Works

1. **Registration**: Agent registers with Rekuest using `kind: "WEBHOOK"`
2. **Task Reception**: Rekuest sends HTTP POST to webhook URL with task details  
3. **Processing**: Agent processes the task asynchronously
4. **Status Updates**: Agent reports progress/results back via GraphQL mutations
5. **Completion**: Agent marks task as done/error/cancelled

## Usage

### Prerequisites

```bash
pip install aiohttp
```

### Running the Example

1. Start your Rekuest server
2. Update the `rekuest_url` in the example to match your server
3. Run the webhook agent:

```bash
python webhook_agent_example.py
```

The agent will:
- Register itself with the Rekuest server as a webhook agent
- Start an HTTP server on localhost:8080 to receive tasks
- Process any assigned tasks and report progress

### Testing the Integration

You can test the webhook agent by assigning tasks to it through the Rekuest GraphQL API:

```graphql
mutation {
  assign(input: {
    # ... your assignment parameters
  }) {
    id
    status
  }
}
```

## Key Components

### WebhookAgent Class

The main class that handles:
- HTTP server setup for receiving tasks
- Task processing simulation
- GraphQL communication for status updates
- Authentication validation

### Authentication

The agent validates incoming requests using:
- `Authorization: Bearer {webhook_secret}` header
- `X-Agent-Secret: {webhook_secret}` header

### Task Processing Flow

1. Receive ASSIGN message via HTTP POST
2. Validate authentication
3. Start asynchronous task processing
4. Send progress updates (0%, 25%, 50%, 75%, 100%)
5. Yield results when complete
6. Mark assignment as done

### Error Handling

- Invalid authentication returns 401
- Malformed requests return 400  
- Processing errors are reported back to Rekuest
- All errors are logged for debugging

## Production Considerations

For production deployments:

1. **Security**: Use HTTPS and secure webhook secrets
2. **Scalability**: Consider horizontal scaling with load balancers
3. **Reliability**: Implement retry logic and error recovery
4. **Monitoring**: Add metrics and health checks
5. **Configuration**: Use environment variables for settings

## GraphQL Mutations Used

The example demonstrates all webhook agent mutations:

- `webhookAssignationProgress` - Report task progress
- `webhookAssignationYield` - Send intermediate/final results  
- `webhookAssignationDone` - Mark task as completed
- `webhookAssignationError` - Report processing errors

## Customization

To adapt this example for your use case:

1. Replace the task processing logic in `process_assignment()`
2. Modify the result format in the yield step
3. Add your own authentication/authorization
4. Implement your specific business logic
5. Add monitoring and error handling as needed