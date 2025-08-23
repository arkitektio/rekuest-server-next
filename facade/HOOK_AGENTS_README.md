# Hook Agent Implementation

This directory contains the implementation of Hook Agents for server-to-server task assignment in the Rekuest system.

## Files Added/Modified

### Core Implementation

- **`models.py`** - Extended `Agent` model with hook agent fields:
  - `is_hook_agent` - Boolean flag to identify hook agents
  - `hook_endpoint` - URL endpoint for HTTP POST requests
  - `hook_secret_token` - Secret token for authentication

- **`mutations/agent.py`** - Extended `AgentInput` and `ensure_agent` mutation:
  - Added validation for hook agent parameters
  - Support for registering hook agents via GraphQL

- **`hook_agent_service.py`** - New service for HTTP communication:
  - Handles HTTP POST requests to hook agent endpoints
  - Implements retry logic and error handling
  - Supports all message types (assign, cancel, interrupt, collect)

- **`backend.py`** - Updated assignment logic:
  - Routes messages to WebSocket or HTTP based on agent type
  - Async task execution to prevent blocking

### REST API

- **`views.py`** - REST API endpoints for hook agents:
  - `/api/hook-agent/events/` - For reporting assignment events
  - `/api/hook-agent/heartbeat/` - For agent health checks
  - Token-based authentication using hook secret tokens

- **`urls.py`** - URL routing for REST endpoints

### Database

- **`migrations/0005_add_hook_agent_fields.py`** - Database migration for new fields

### Testing

- **`test_hook_agents.py`** - Unit tests for hook agent functionality
- **`test_hook_agent_integration.py`** - Integration tests for complete workflow

### Documentation

- **`docs/hook-agents.md`** - Comprehensive documentation for hook agent usage

## Architecture

```
┌─────────────────┐    GraphQL     ┌──────────────────┐
│   Client App    │──────────────▶ │  Rekuest Server  │
└─────────────────┘                └──────────────────┘
                                           │
                                           │ HTTP POST
                                           ▼
                                   ┌──────────────────┐
                                   │   Hook Agent     │
                                   │  (External       │
                                   │   Server)        │
                                   └──────────────────┘
                                           │
                                           │ REST API
                                           ▼
                                   ┌──────────────────┐
                                   │  Rekuest Server  │
                                   │  (Event Updates) │
                                   └──────────────────┘
```

## Key Features

1. **Dual Agent Types**: Supports both WebSocket agents (existing) and HTTP hook agents (new)
2. **Seamless Integration**: Hook agents work with existing assignment and reservation system
3. **Authentication**: Secure token-based authentication for hook agent communication
4. **Event Reporting**: Comprehensive event reporting system (progress, logs, completion, errors)
5. **Error Handling**: Robust error handling with timeout management
6. **Backward Compatibility**: Does not break existing WebSocket agent functionality

## Usage Example

### 1. Register Hook Agent

```graphql
mutation {
  ensureAgent(input: {
    instanceId: "my-server"
    name: "My Hook Agent"
    isHookAgent: true
    hookEndpoint: "https://my-server.com/rekuest-webhook"
    hookSecretToken: "secret-token-123"
  }) {
    id
    name
    isHookAgent
  }
}
```

### 2. Receive Assignment

Your webhook endpoint will receive:

```json
{
  "type": "ASSIGN",
  "message": {
    "assignation": "assignment-id",
    "args": {"param1": "value1"},
    "action": "action-id"
  },
  "agent_id": "agent-id"
}
```

### 3. Report Progress

```http
POST /api/hook-agent/events/
Authorization: Bearer secret-token-123

{
  "assignation_id": "assignment-id",
  "event_type": "PROGRESS",
  "progress": 50,
  "message": "Processing..."
}
```

## Benefits

1. **Server-to-Server Communication**: Enables direct server communication without WebSocket complexity
2. **Scalability**: External servers can handle their own load balancing and scaling
3. **Language Agnostic**: Hook agents can be implemented in any language that supports HTTP
4. **Firewall Friendly**: Uses standard HTTP/HTTPS protocols
5. **Stateless**: No persistent connection requirements

## Security Considerations

- Hook secret tokens provide authentication
- HTTPS recommended for production
- Token rotation supported through re-registration
- Request validation and sanitization implemented
- Rate limiting can be implemented at infrastructure level