"""GraphQL mutations for webhook agents to update assignment status."""

import strawberry
import logging
from typing import Optional
from kante.types import Info
from facade import models, enums, messages
from facade.persist_backend import persist_backend

logger = logging.getLogger(__name__)


@strawberry.input
class WebhookAssignationEventInput:
    """Input for webhook agents to report assignation events."""
    assignation: strawberry.ID = strawberry.field(description="The assignation ID")
    agent_secret: str = strawberry.field(description="The webhook agent secret for authentication")


@strawberry.input
class WebhookProgressInput(WebhookAssignationEventInput):
    """Input for webhook agents to report progress."""
    progress: Optional[int] = strawberry.field(default=None, description="Progress percentage (0-100)")
    message: Optional[str] = strawberry.field(default=None, description="Progress message")


@strawberry.input
class WebhookLogInput(WebhookAssignationEventInput):
    """Input for webhook agents to report logs."""
    message: str = strawberry.field(description="Log message")
    level: str = strawberry.field(default="INFO", description="Log level (DEBUG, INFO, ERROR, WARN, CRITICAL)")


@strawberry.input
class WebhookYieldInput(WebhookAssignationEventInput):
    """Input for webhook agents to yield results."""
    returns: Optional[str] = strawberry.field(default=None, description="JSON-encoded return values")


@strawberry.input
class WebhookErrorInput(WebhookAssignationEventInput):
    """Input for webhook agents to report errors."""
    error: str = strawberry.field(description="Error message")


async def webhook_assignation_progress(info: Info, input: WebhookProgressInput) -> strawberry.ID:
    """Mutation for webhook agents to report assignation progress."""
    try:
        assignation = await models.Assignation.objects.aget(id=input.assignation)
        
        # Verify the agent secret
        if assignation.agent.hook_url_secret != input.agent_secret:
            raise ValueError("Invalid agent secret")
        
        # Create progress event
        progress_event = messages.ProgressEvent(
            assignation=str(assignation.id),
            progress=input.progress,
            message=input.message
        )
        
        # Process the event
        await persist_backend.on_agent_progress(assignation.agent.id, progress_event)
        
        return input.assignation
        
    except models.Assignation.DoesNotExist:
        raise ValueError("Assignation not found")
    except Exception as e:
        logger.error(f"Error processing webhook progress event: {e}")
        raise ValueError(f"Failed to process progress event: {str(e)}")


async def webhook_assignation_log(info: Info, input: WebhookLogInput) -> strawberry.ID:
    """Mutation for webhook agents to report assignation logs."""
    try:
        assignation = await models.Assignation.objects.aget(id=input.assignation)
        
        # Verify the agent secret
        if assignation.agent.hook_url_secret != input.agent_secret:
            raise ValueError("Invalid agent secret")
        
        # Create log event
        log_event = messages.LogEvent(
            assignation=str(assignation.id),
            message=input.message,
            level=input.level
        )
        
        # Process the event
        await persist_backend.on_agent_log(assignation.agent.id, log_event)
        
        return input.assignation
        
    except models.Assignation.DoesNotExist:
        raise ValueError("Assignation not found")
    except Exception as e:
        logger.error(f"Error processing webhook log event: {e}")
        raise ValueError(f"Failed to process log event: {str(e)}")


async def webhook_assignation_yield(info: Info, input: WebhookYieldInput) -> strawberry.ID:
    """Mutation for webhook agents to yield assignation results."""
    try:
        assignation = await models.Assignation.objects.aget(id=input.assignation)
        
        # Verify the agent secret
        if assignation.agent.hook_url_secret != input.agent_secret:
            raise ValueError("Invalid agent secret")
        
        # Parse returns if provided
        returns_dict = None
        if input.returns:
            import json
            try:
                returns_dict = json.loads(input.returns)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON in returns field")
        
        # Create yield event
        yield_event = messages.YieldEvent(
            assignation=str(assignation.id),
            returns=returns_dict
        )
        
        # Process the event
        await persist_backend.on_agent_yield(assignation.agent.id, yield_event)
        
        return input.assignation
        
    except models.Assignation.DoesNotExist:
        raise ValueError("Assignation not found")
    except Exception as e:
        logger.error(f"Error processing webhook yield event: {e}")
        raise ValueError(f"Failed to process yield event: {str(e)}")


async def webhook_assignation_done(info: Info, input: WebhookAssignationEventInput) -> strawberry.ID:
    """Mutation for webhook agents to mark assignation as done."""
    try:
        assignation = await models.Assignation.objects.aget(id=input.assignation)
        
        # Verify the agent secret
        if assignation.agent.hook_url_secret != input.agent_secret:
            raise ValueError("Invalid agent secret")
        
        # Create done event
        done_event = messages.DoneEvent(
            assignation=str(assignation.id)
        )
        
        # Process the event
        await persist_backend.on_agent_done(assignation.agent.id, done_event)
        
        return input.assignation
        
    except models.Assignation.DoesNotExist:
        raise ValueError("Assignation not found")
    except Exception as e:
        logger.error(f"Error processing webhook done event: {e}")
        raise ValueError(f"Failed to process done event: {str(e)}")


async def webhook_assignation_error(info: Info, input: WebhookErrorInput) -> strawberry.ID:
    """Mutation for webhook agents to report assignation errors."""
    try:
        assignation = await models.Assignation.objects.aget(id=input.assignation)
        
        # Verify the agent secret
        if assignation.agent.hook_url_secret != input.agent_secret:
            raise ValueError("Invalid agent secret")
        
        # Create error event
        error_event = messages.ErrorEvent(
            assignation=str(assignation.id),
            error=input.error
        )
        
        # Process the event
        await persist_backend.on_agent_error(assignation.agent.id, error_event)
        
        return input.assignation
        
    except models.Assignation.DoesNotExist:
        raise ValueError("Assignation not found")
    except Exception as e:
        logger.error(f"Error processing webhook error event: {e}")
        raise ValueError(f"Failed to process error event: {str(e)}")


async def webhook_assignation_cancelled(info: Info, input: WebhookAssignationEventInput) -> strawberry.ID:
    """Mutation for webhook agents to mark assignation as cancelled."""
    try:
        assignation = await models.Assignation.objects.aget(id=input.assignation)
        
        # Verify the agent secret
        if assignation.agent.hook_url_secret != input.agent_secret:
            raise ValueError("Invalid agent secret")
        
        # Create cancelled event
        cancelled_event = messages.CancelledEvent(
            assignation=str(assignation.id)
        )
        
        # Process the event
        await persist_backend.on_agent_cancelled(assignation.agent.id, cancelled_event)
        
        return input.assignation
        
    except models.Assignation.DoesNotExist:
        raise ValueError("Assignation not found")
    except Exception as e:
        logger.error(f"Error processing webhook cancelled event: {e}")
        raise ValueError(f"Failed to process cancelled event: {str(e)}")