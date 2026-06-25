"""Shared GraphQL operation strings used across the GraphQL and integration tests.

Selection sets are deliberate supersets (e.g. agent ops also fetch ``connected``);
selecting an extra field is harmless and lets one constant serve every call site that
previously inlined a near-identical operation.
"""

ENSURE_AGENT = """
    mutation EnsureAgent($input: AgentInput!) {
        ensureAgent(input: $input) {
            id
            name
            connected
        }
    }
"""

GET_AGENT = """
    query GetAgent($id: ID!) {
        agent(id: $id) {
            id
            name
            connected
        }
    }
"""

GET_AGENTS = """
    query GetAgents {
        agents {
            id
            name
            connected
        }
    }
"""

DELETE_AGENT = """
    mutation DeleteAgent($input: DeleteAgentInput!) {
        deleteAgent(input: $input)
    }
"""

CREATE_BLOK = """
    mutation CreateBlok($input: CreateBlokInput!) {
        createBlok(input: $input) {
            id
            name
            description
            creator {
                sub
            }
        }
    }
"""

CREATE_DASHBOARD = """
    mutation CreateDashboard($input: CreateDashboardInput!) {
        createDashboard(input: $input) {
            id
            name
        }
    }
"""
