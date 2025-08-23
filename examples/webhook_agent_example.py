"""Example webhook agent implementation."""

import asyncio
import json
import logging
from typing import Dict, Any
from aiohttp import web, ClientSession
import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebhookAgent:
    """Example webhook agent that receives tasks via HTTP and reports back via GraphQL."""
    
    def __init__(self, agent_id: str, webhook_secret: str, rekuest_url: str):
        self.agent_id = agent_id
        self.webhook_secret = webhook_secret
        self.rekuest_url = rekuest_url
        self.app = web.Application()
        self.setup_routes()
        
    def setup_routes(self):
        """Setup HTTP routes for receiving webhook tasks."""
        self.app.router.add_post('/tasks', self.handle_task)
        self.app.router.add_get('/health', self.health_check)
    
    async def health_check(self, request):
        """Health check endpoint."""
        return web.json_response({"status": "healthy", "agent_id": self.agent_id})
    
    async def handle_task(self, request):
        """Handle incoming task assignment from Rekuest server."""
        try:
            # Verify authentication
            auth_header = request.headers.get('Authorization', '')
            secret_header = request.headers.get('X-Agent-Secret', '')
            
            provided_secret = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else secret_header
            if provided_secret != self.webhook_secret:
                return web.json_response({"error": "Invalid authentication"}, status=401)
            
            # Parse the task payload
            data = await request.json()
            message = data.get('message', {})
            assignation_id = message.get('assignation')
            task_type = message.get('type')
            
            logger.info(f"Received task {task_type} for assignation {assignation_id}")
            
            if task_type == 'ASSIGN':
                # Process the task asynchronously 
                asyncio.create_task(self.process_assignment(message))
                return web.json_response({"status": "accepted"})
            else:
                logger.warning(f"Unhandled task type: {task_type}")
                return web.json_response({"error": f"Unhandled task type: {task_type}"}, status=400)
                
        except Exception as e:
            logger.error(f"Error handling task: {e}")
            return web.json_response({"error": "Internal server error"}, status=500)
    
    async def process_assignment(self, message: Dict[str, Any]):
        """Process an assignment task."""
        assignation_id = message['assignation']
        args = message.get('args', {})
        action = message.get('action', 'unknown')
        
        try:
            # Report progress at start
            await self.report_progress(assignation_id, 0, "Starting task processing")
            
            # Simulate task processing
            logger.info(f"Processing assignment {assignation_id} for action {action}")
            
            # Simulate some work with progress updates
            for progress in [25, 50, 75, 100]:
                await asyncio.sleep(1)  # Simulate work
                await self.report_progress(assignation_id, progress, f"Processing... {progress}% complete")
            
            # Yield results
            results = {
                "processed": True,
                "action": action,
                "input_args": args,
                "timestamp": str(asyncio.get_event_loop().time())
            }
            
            await self.report_yield(assignation_id, results)
            
            # Mark as done
            await self.report_done(assignation_id)
            
            logger.info(f"Completed assignment {assignation_id}")
            
        except Exception as e:
            logger.error(f"Error processing assignment {assignation_id}: {e}")
            await self.report_error(assignation_id, str(e))
    
    async def report_progress(self, assignation_id: str, progress: int, message: str = None):
        """Report progress via GraphQL mutation."""
        mutation = """
        mutation WebhookProgress($input: WebhookProgressInput!) {
            webhookAssignationProgress(input: $input)
        }
        """
        
        variables = {
            "input": {
                "assignation": assignation_id,
                "agentSecret": self.webhook_secret,
                "progress": progress,
                "message": message
            }
        }
        
        await self.send_graphql_request(mutation, variables)
    
    async def report_yield(self, assignation_id: str, results: Dict[str, Any]):
        """Report yielded results via GraphQL mutation."""
        mutation = """
        mutation WebhookYield($input: WebhookYieldInput!) {
            webhookAssignationYield(input: $input)
        }
        """
        
        variables = {
            "input": {
                "assignation": assignation_id,
                "agentSecret": self.webhook_secret,
                "returns": json.dumps(results)
            }
        }
        
        await self.send_graphql_request(mutation, variables)
    
    async def report_done(self, assignation_id: str):
        """Report task completion via GraphQL mutation."""
        mutation = """
        mutation WebhookDone($input: WebhookAssignationEventInput!) {
            webhookAssignationDone(input: $input)
        }
        """
        
        variables = {
            "input": {
                "assignation": assignation_id,
                "agentSecret": self.webhook_secret
            }
        }
        
        await self.send_graphql_request(mutation, variables)
    
    async def report_error(self, assignation_id: str, error_message: str):
        """Report task error via GraphQL mutation."""
        mutation = """
        mutation WebhookError($input: WebhookErrorInput!) {
            webhookAssignationError(input: $input)
        }
        """
        
        variables = {
            "input": {
                "assignation": assignation_id,
                "agentSecret": self.webhook_secret,
                "error": error_message
            }
        }
        
        await self.send_graphql_request(mutation, variables)
    
    async def send_graphql_request(self, query: str, variables: Dict[str, Any]):
        """Send GraphQL request to Rekuest server."""
        payload = {
            "query": query,
            "variables": variables
        }
        
        headers = {
            "Content-Type": "application/json",
            # Add authentication headers as needed for your setup
        }
        
        try:
            async with ClientSession() as session:
                async with session.post(f"{self.rekuest_url}/graphql", json=payload, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        if 'errors' in result:
                            logger.error(f"GraphQL errors: {result['errors']}")
                        else:
                            logger.debug("GraphQL request successful")
                    else:
                        logger.error(f"GraphQL request failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error sending GraphQL request: {e}")
    
    async def register_with_rekuest(self):
        """Register this webhook agent with Rekuest server."""
        mutation = """
        mutation RegisterWebhookAgent($input: AgentInput!) {
            ensureAgent(input: $input) {
                id
                instanceId
                kind
                hookUrl
            }
        }
        """
        
        variables = {
            "input": {
                "instanceId": self.agent_id,
                "name": f"Webhook Agent {self.agent_id}",
                "kind": "WEBHOOK",
                "hookUrl": "http://localhost:8080/tasks",  # Adjust as needed
                "hookUrlSecret": self.webhook_secret,
                "extensions": ["webhook-example"]
            }
        }
        
        await self.send_graphql_request(mutation, variables)
        logger.info(f"Registered webhook agent {self.agent_id}")
    
    async def start_server(self, host='localhost', port=8080):
        """Start the webhook server."""
        logger.info(f"Starting webhook agent server on {host}:{port}")
        
        # Register with Rekuest
        await self.register_with_rekuest()
        
        # Start web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        logger.info(f"Webhook agent {self.agent_id} is ready to receive tasks")
        
        # Keep server running
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Shutting down webhook agent")
            await runner.cleanup()


async def main():
    """Example usage of webhook agent."""
    agent = WebhookAgent(
        agent_id="example-webhook-agent-1",
        webhook_secret="secure-webhook-secret-123", 
        rekuest_url="http://localhost:8000"  # Adjust to your Rekuest server URL
    )
    
    await agent.start_server(host='localhost', port=8080)


if __name__ == "__main__":
    asyncio.run(main())