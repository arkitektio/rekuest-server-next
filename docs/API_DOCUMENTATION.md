# Rekuest Server API Documentation

## Overview

Rekuest is a central repository service for managing computational tasks and agents in the Arkitekt ecosystem. It provides a GraphQL API for registering agents, defining actions, managing task execution, and handling state management.

## Architecture

Rekuest follows a microservices architecture designed for horizontal scalability:

- **Stateless Service**: The core Rekuest service is stateless and can be scaled horizontally
- **Message Brokers**: Uses Redis and optionally RabbitMQ for task routing and real-time communication
- **Database**: PostgreSQL for persistent storage (SQLite for development/testing)
- **GraphQL API**: Single endpoint for all operations with real-time subscriptions

## Core Concepts

### Agents
Agents are computational entities that can execute tasks. They register with Rekuest and provide information about their capabilities.

- **Registry**: Each agent belongs to a registry tied to a specific user/client/organization
- **Instance ID**: Unique identifier for the agent instance
- **Extensions**: List of capabilities/plugins the agent supports
- **States**: Current status and configuration of the agent
- **Agent Types**:
  - **WebSocket Agents**: Connect via WebSocket for real-time communication
  - **Webhook Agents**: Receive tasks via HTTP POST requests to their webhook URL

#### Webhook Agent Integration

Webhook agents enable server-to-server task assignment without maintaining persistent connections:

1. **Registration**: Register with `kind: "WEBHOOK"`, providing `hookUrl` and `hookUrlSecret`
2. **Task Assignment**: Server sends HTTP POST to webhook URL with task details and agent secret
3. **Status Updates**: Agent uses GraphQL mutations or REST endpoints to report progress
4. **Authentication**: All requests authenticated using the webhook secret token

**Webhook Payload Format:**
```json
{
  "message": {
    "type": "ASSIGN", 
    "assignation": "uuid",
    "args": {...},
    "user": "user_id",
    "app": "app_id", 
    "interface": "interface_name",
    "action": "action_hash"
  },
  "agent_id": "agent_uuid"
}
```

**Headers:**
- `Content-Type: application/json`
- `Authorization: Bearer {webhook_secret}`
- `X-Agent-Secret: {webhook_secret}`

### Actions
Actions are abstract representations of computational tasks that agents can perform.

- **Hash**: Unique identifier based on the action's signature
- **Protocols**: Groups of related actions
- **Implementations**: Concrete realizations of actions by specific agents
- **Ports**: Input/output specifications using typed data structures

### Reservations and Assignations
- **Reservations**: Claims on agent resources for future task execution
- **Assignations**: Active task executions with lifecycle management

### State Management
- **State Schemas**: Define the structure of agent states
- **States**: Current values of agent configurations
- **Persistence**: States can be stored and retrieved across sessions

## GraphQL API Reference

### Queries

#### Agent Queries
```graphql
# Get all agents
query GetAgents {
  agents {
    id
    instanceId
    name
    connected
    extensions
    lastSeen
  }
}

# Get specific agent
query GetAgent($id: ID!) {
  agent(id: $id) {
    id
    instanceId
    name
    connected
    registry {
      client {
        clientId
      }
      user {
        username
      }
    }
  }
}
```

#### Action Queries
```graphql
# Get all actions
query GetActions {
  actions {
    id
    name
    description
    hash
    protocols {
      name
    }
  }
}

# Get specific action
query GetAction($id: ID!) {
  action: action(interface: $interface) {
    id
    name
    description
    args
    returns
  }
}
```

#### State Queries
```graphql
# Get state schemas
query GetStateSchemas {
  stateSchemas {
    id
    name
    description
    hash
    ports
  }
}

# Get states for an agent
query GetStatesForAgent($instanceId: String!) {
  stateFor(instanceId: $instanceId) {
    id
    value
    schema {
      name
    }
  }
}
```

### Mutations

#### Agent Management
```graphql
# Register or update an agent (supports webhook agents)
mutation EnsureAgent($input: AgentInput!) {
  ensureAgent(input: $input) {
    id
    instanceId
    name
    extensions
    kind
    hookUrl
    hookUrlSecret
  }
}

# Agent input supports webhook fields
input AgentInput {
  instanceId: String!
  name: String
  extensions: [String!]
  kind: String # "WEBSOCKET" or "WEBHOOK" 
  hookUrl: String # Required for WEBHOOK agents
  hookUrlSecret: String # Required for WEBHOOK agents  
}

# Delete an agent
mutation DeleteAgent($input: DeleteAgentInput!) {
  deleteAgent(input: $input)
}
```

#### Task Management
```graphql
# Reserve an implementation
mutation Reserve($input: ReserveInput!) {
  reserve(input: $input) {
    id
    node
    hash
  }
}

# Assign a task
mutation Assign($input: AssignInput!) {
  assign(input: $input) {
    id
    args
    status
  }
}

# Cancel a task
mutation Cancel($input: CancelInput!) {
  cancel(input: $input) {
    id
    status
  }
}
```

#### Webhook Agent Events
Webhook agents can use these mutations to update assignment status:

```graphql
# Report progress on an assignation
mutation WebhookAssignationProgress($input: WebhookProgressInput!) {
  webhookAssignationProgress(input: $input)
}

# Log messages from assignation
mutation WebhookAssignationLog($input: WebhookLogInput!) {
  webhookAssignationLog(input: $input)  
}

# Yield results from assignation
mutation WebhookAssignationYield($input: WebhookYieldInput!) {
  webhookAssignationYield(input: $input)
}

# Mark assignation as completed
mutation WebhookAssignationDone($input: WebhookAssignationEventInput!) {
  webhookAssignationDone(input: $input)
}

# Report error in assignation  
mutation WebhookAssignationError($input: WebhookErrorInput!) {
  webhookAssignationError(input: $input)
}

# Mark assignation as cancelled
mutation WebhookAssignationCancelled($input: WebhookAssignationEventInput!) {
  webhookAssignationCancelled(input: $input)
}
```

#### State Management
```graphql
# Create a state schema
mutation CreateStateSchema($input: CreateStateSchemaInput!) {
  createStateSchema(input: $input) {
    id
    name
    hash
    ports
  }
}

# Set state value
mutation SetState($input: SetStateInput!) {
  setState(input: $input) {
    id
    value
    schema {
      name
    }
  }
}

# Update state
mutation UpdateState($input: UpdateStateInput!) {
  updateState(input: $input) {
    id
    value
  }
}
```

### Subscriptions

#### Real-time Updates
```graphql
# Subscribe to agent events
subscription AgentEvents($instanceId: String!) {
  agentEvent(instanceId: $instanceId) {
    type
    agent {
      id
      connected
    }
  }
}

# Subscribe to assignation updates
subscription AssignationUpdates($assignation: ID!) {
  assignationEvent(assignation: $assignation) {
    type
    assignation {
      id
      status
      progress
    }
  }
}
```

## Input Types

### AgentInput
```graphql
input AgentInput {
  instanceId: String!
  name: String
  extensions: [String!]
}
```

### ReserveInput
```graphql
input ReserveInput {
  node: ID!
  hash: String!
  params: GenericScalar
}
```

### AssignInput
```graphql
input AssignInput {
  node: ID!
  args: [GenericScalar!]!
  hooks: [AssignHookInput!]
}
```

## Authentication

All API operations require authentication via the Authentikate system:

1. **Token-based**: Use Bearer tokens in the Authorization header
2. **Client Registration**: Clients must be registered in the system
3. **User Context**: Operations are performed in the context of the authenticated user
4. **Organization Scope**: Resources are scoped to the user's organization

### Example Authentication
```http
POST /graphql
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json

{
  "query": "query { agents { id name } }"
}
```

## Error Handling

The API uses GraphQL error conventions:

```json
{
  "data": null,
  "errors": [
    {
      "message": "Agent not found",
      "locations": [{"line": 2, "column": 3}],
      "path": ["agent"]
    }
  ]
}
```

### Common Error Types
- **ValidationError**: Invalid input data
- **NotFound**: Requested resource doesn't exist
- **PermissionDenied**: Insufficient permissions
- **AuthenticationRequired**: Missing or invalid authentication

## Development Setup

### Prerequisites
- Python 3.12+
- PostgreSQL (or SQLite for development)
- Redis
- Node.js (for frontend development)

### Installation
```bash
# Clone the repository
git clone https://github.com/arkitektio/rekuest-server-next.git
cd rekuest-server-next

# Install dependencies
pip install -e .

# Set up environment variables
cp .env.example .env

# Run migrations
python manage.py migrate

# Start the development server
python manage.py runserver
```

### Testing
```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_graphql_queries.py

# Run with coverage
python -m pytest --cov=facade
```

### GraphQL Playground
Visit `http://localhost:8000/graphql` to access the interactive GraphQL playground for testing queries and exploring the schema.

## Production Deployment

### Docker
```bash
# Build the container
docker build -t rekuest-server .

# Run with docker-compose
docker-compose up -d
```

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: Django secret key
- `DEBUG`: Set to `false` in production
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts

### Scaling Considerations
- **Horizontal Scaling**: Multiple Rekuest instances can run behind a load balancer
- **Database**: Use PostgreSQL with connection pooling
- **Redis**: Consider Redis Cluster for high availability
- **Message Queue**: RabbitMQ for reliable task distribution

## Performance Optimization

### Database Optimization
- Use database indexes on frequently queried fields
- Implement query optimization with select_related/prefetch_related
- Consider read replicas for read-heavy workloads

### Caching
- Redis caching for frequently accessed data
- GraphQL query result caching
- Agent state caching for quick lookups

### Monitoring
- Use Django's built-in logging
- Implement health checks via `/health/` endpoint
- Monitor GraphQL query performance
- Track agent connectivity and task completion rates

## Webhook Integration

### Webhook Event Endpoint

**URL:** `POST /webhook/agent/events/`

Webhook agents can post events to this endpoint as an alternative to GraphQL mutations.

**Request Format:**
```json
{
  "agent_id": "uuid",
  "message": {
    "type": "PROGRESS|LOG|YIELD|DONE|ERROR|CANCELLED",
    "assignation": "assignation_uuid",
    // ... message-specific fields
  }
}
```

**Authentication:**
- `Authorization: Bearer {webhook_secret}` OR
- `X-Agent-Secret: {webhook_secret}`

**Response:**
- `200 OK`: Event processed successfully
- `400 Bad Request`: Invalid request format
- `401 Unauthorized`: Invalid or missing authentication
- `404 Not Found`: Agent not found
- `500 Internal Server Error`: Processing error

## Security

### Best Practices
- Always use HTTPS in production
- Validate all input data
- Implement rate limiting
- Regular security updates
- Database query timeout limits
- Proper error message sanitization

### Access Control
- Role-based permissions
- Organization-level isolation
- Agent ownership validation
- Resource access logging
