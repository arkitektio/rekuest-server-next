"""Service for handling communication with hook agents via HTTP POST requests."""

import asyncio
import json
import logging
from typing import Any, Dict

import aiohttp
from django.conf import settings
from facade import messages, models

logger = logging.getLogger(__name__)


class HookAgentService:
    """Service for sending task assignments to hook agents via HTTP POST."""
    
    def __init__(self):
        self.session = None
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session for making HTTP requests."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def send_assignment_to_hook_agent(
        self,
        agent: models.Agent,
        assignment_message: messages.Assign,
    ) -> bool:
        """
        Send an assignment message to a hook agent via HTTP POST.
        
        Args:
            agent: The hook agent to send the assignment to
            assignment_message: The assignment message to send
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not agent.is_hook_agent:
            raise ValueError("Agent is not a hook agent")
            
        if not agent.hook_endpoint:
            raise ValueError("Hook agent has no endpoint configured")
            
        if not agent.hook_secret_token:
            raise ValueError("Hook agent has no secret token configured")
        
        try:
            session = await self._get_session()
            
            # Prepare the payload
            payload = {
                "type": "ASSIGN",
                "message": assignment_message.model_dump(),
                "agent_id": str(agent.id),
            }
            
            # Prepare headers with authentication
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {agent.hook_secret_token}",
                "User-Agent": "Rekuest-Server/1.0",
            }
            
            logger.info(f"Sending assignment to hook agent {agent.id} at {agent.hook_endpoint}")
            
            async with session.post(
                agent.hook_endpoint,
                json=payload,
                headers=headers,
            ) as response:
                if response.status == 200:
                    logger.info(f"Successfully sent assignment to hook agent {agent.id}")
                    return True
                else:
                    logger.error(
                        f"Failed to send assignment to hook agent {agent.id}. "
                        f"Status: {response.status}, Response: {await response.text()}"
                    )
                    return False
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout sending assignment to hook agent {agent.id}")
            return False
        except Exception as e:
            logger.error(f"Error sending assignment to hook agent {agent.id}: {e}")
            return False
    
    async def send_cancellation_to_hook_agent(
        self,
        agent: models.Agent,
        cancellation_message: messages.Cancel,
    ) -> bool:
        """
        Send a cancellation message to a hook agent via HTTP POST.
        
        Args:
            agent: The hook agent to send the cancellation to
            cancellation_message: The cancellation message to send
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not agent.is_hook_agent:
            raise ValueError("Agent is not a hook agent")
            
        if not agent.hook_endpoint:
            raise ValueError("Hook agent has no endpoint configured")
            
        if not agent.hook_secret_token:
            raise ValueError("Hook agent has no secret token configured")
        
        try:
            session = await self._get_session()
            
            # Prepare the payload
            payload = {
                "type": "CANCEL",
                "message": cancellation_message.model_dump(),
                "agent_id": str(agent.id),
            }
            
            # Prepare headers with authentication
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {agent.hook_secret_token}",
                "User-Agent": "Rekuest-Server/1.0",
            }
            
            logger.info(f"Sending cancellation to hook agent {agent.id} at {agent.hook_endpoint}")
            
            async with session.post(
                agent.hook_endpoint,
                json=payload,
                headers=headers,
            ) as response:
                if response.status == 200:
                    logger.info(f"Successfully sent cancellation to hook agent {agent.id}")
                    return True
                else:
                    logger.error(
                        f"Failed to send cancellation to hook agent {agent.id}. "
                        f"Status: {response.status}, Response: {await response.text()}"
                    )
                    return False
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout sending cancellation to hook agent {agent.id}")
            return False
        except Exception as e:
            logger.error(f"Error sending cancellation to hook agent {agent.id}: {e}")
            return False


    async def send_interrupt_to_hook_agent(
        self,
        agent: models.Agent,
        interrupt_message: messages.Interrupt,
    ) -> bool:
        """
        Send an interrupt message to a hook agent via HTTP POST.
        
        Args:
            agent: The hook agent to send the interrupt to
            interrupt_message: The interrupt message to send
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not agent.is_hook_agent:
            raise ValueError("Agent is not a hook agent")
            
        if not agent.hook_endpoint:
            raise ValueError("Hook agent has no endpoint configured")
            
        if not agent.hook_secret_token:
            raise ValueError("Hook agent has no secret token configured")
        
        try:
            session = await self._get_session()
            
            # Prepare the payload
            payload = {
                "type": "INTERRUPT",
                "message": interrupt_message.model_dump(),
                "agent_id": str(agent.id),
            }
            
            # Prepare headers with authentication
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {agent.hook_secret_token}",
                "User-Agent": "Rekuest-Server/1.0",
            }
            
            logger.info(f"Sending interrupt to hook agent {agent.id} at {agent.hook_endpoint}")
            
            async with session.post(
                agent.hook_endpoint,
                json=payload,
                headers=headers,
            ) as response:
                if response.status == 200:
                    logger.info(f"Successfully sent interrupt to hook agent {agent.id}")
                    return True
                else:
                    logger.error(
                        f"Failed to send interrupt to hook agent {agent.id}. "
                        f"Status: {response.status}, Response: {await response.text()}"
                    )
                    return False
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout sending interrupt to hook agent {agent.id}")
            return False
        except Exception as e:
            logger.error(f"Error sending interrupt to hook agent {agent.id}: {e}")
            return False


    async def send_collect_to_hook_agent(
        self,
        agent: models.Agent,
        collect_message: messages.Collect,
    ) -> bool:
        """
        Send a collect message to a hook agent via HTTP POST.
        
        Args:
            agent: The hook agent to send the collect to
            collect_message: The collect message to send
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not agent.is_hook_agent:
            raise ValueError("Agent is not a hook agent")
            
        if not agent.hook_endpoint:
            raise ValueError("Hook agent has no endpoint configured")
            
        if not agent.hook_secret_token:
            raise ValueError("Hook agent has no secret token configured")
        
        try:
            session = await self._get_session()
            
            # Prepare the payload
            payload = {
                "type": "COLLECT",
                "message": collect_message.model_dump(),
                "agent_id": str(agent.id),
            }
            
            # Prepare headers with authentication
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {agent.hook_secret_token}",
                "User-Agent": "Rekuest-Server/1.0",
            }
            
            logger.info(f"Sending collect to hook agent {agent.id} at {agent.hook_endpoint}")
            
            async with session.post(
                agent.hook_endpoint,
                json=payload,
                headers=headers,
            ) as response:
                if response.status == 200:
                    logger.info(f"Successfully sent collect to hook agent {agent.id}")
                    return True
                else:
                    logger.error(
                        f"Failed to send collect to hook agent {agent.id}. "
                        f"Status: {response.status}, Response: {await response.text()}"
                    )
                    return False
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout sending collect to hook agent {agent.id}")
            return False
        except Exception as e:
            logger.error(f"Error sending collect to hook agent {agent.id}: {e}")
            return False


# Global instance
hook_agent_service = HookAgentService()