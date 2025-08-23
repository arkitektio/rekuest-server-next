"""Service for handling webhook agent communications."""

import json
import logging
from typing import Any, Dict
import httpx
from facade import messages, models

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for sending messages to webhook agents via HTTP POST."""

    def __init__(self) -> None:
        self.client = httpx.AsyncClient()

    async def send_message_to_webhook_agent(
        self, 
        agent: models.Agent, 
        message: messages.ToAgentMessage
    ) -> bool:
        """Send a message to a webhook agent via HTTP POST.
        
        Args:
            agent: The webhook agent to send to
            message: The message to send
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        if not agent.hook_url or not agent.hook_url_secret:
            logger.error(f"Agent {agent.id} is missing webhook URL or secret")
            return False

        try:
            payload = {
                "message": message.model_dump(),
                "agent_id": str(agent.id),
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {agent.hook_url_secret}",
                "X-Agent-Secret": agent.hook_url_secret,
            }

            response = await self.client.post(
                agent.hook_url,
                json=payload,
                headers=headers,
                timeout=30.0,
            )
            
            response.raise_for_status()
            logger.info(f"Successfully sent message to webhook agent {agent.id}")
            return True
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to send message to webhook agent {agent.id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending message to webhook agent {agent.id}: {e}")
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()


# Global webhook service instance
webhook_service = WebhookService()