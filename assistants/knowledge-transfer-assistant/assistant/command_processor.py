"""
Command processor for the project assistant.

This module provides a unified framework for processing commands in the project assistant.
It defines a command registry, command handlers for both Coordinator and Team modes, and authorization
controls based on user roles.
"""

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from semantic_workbench_api_model.workbench_model import (
    ConversationMessage,
    MessageType,
    NewConversationMessage,
)
from semantic_workbench_assistant.assistant_app import ConversationContext

from .conversation_share_link import ConversationKnowledgePackageManager
from .data import (
    RequestPriority,
    RequestStatus,
)
from .manager import KnowledgeTransferManager
from .notifications import ProjectNotifier
from .storage import ShareStorage
from .storage_models import ConversationRole

logger = logging.getLogger(__name__)

# Command handler function type
CommandHandlerType = Callable[[ConversationContext, ConversationMessage, List[str]], Awaitable[None]]


class CommandRegistry:
    """Registry for command handlers with authorization controls."""

    def __init__(self):
        """Initialize the command registry."""
        self.commands: Dict[str, Dict[str, Any]] = {}

    def register_command(
        self,
        command_name: str,
        handler: CommandHandlerType,
        description: str,
        usage: str,
        example: str,
        authorized_roles: Optional[List[str]] = None,
    ) -> None:
        """
        Register a command handler.

        Args:
            command_name: The command name (without the '/')
            handler: The function that handles the command
            description: A brief description of what the command does
            usage: The command usage format
            example: An example of how to use the command
            authorized_roles: List of roles that can use this command (None for all)
        """
        self.commands[command_name] = {
            "handler": handler,
            "description": description,
            "usage": usage,
            "example": example,
            "authorized_roles": authorized_roles,
        }

    def is_authorized(self, command_name: str, role: str) -> bool:
        """
        Check if a role is authorized to use a command.

        Args:
            command_name: The command name
            role: The user role

        Returns:
            True if authorized, False otherwise
        """
        if command_name not in self.commands:
            return False

        authorized_roles = self.commands[command_name]["authorized_roles"]
        if authorized_roles is None:
            return True  # Command available to all roles

        return role in authorized_roles

    def get_command_help(self, command_name: str) -> Optional[Dict[str, str]]:
        """
        Get help information for a command.

        Args:
            command_name: The command name

        Returns:
            Dictionary with help information or None if command not found
        """
        if command_name not in self.commands:
            return None

        return {
            "description": self.commands[command_name]["description"],
            "usage": self.commands[command_name]["usage"],
            "example": self.commands[command_name]["example"],
        }

    def get_commands_for_role(self, role: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all commands available for a specific role.

        Args:
            role: The user role

        Returns:
            Dictionary of commands available to the role
        """
        return {name: cmd for name, cmd in self.commands.items() if self.is_authorized(name, role)}

    async def process_command(self, context: ConversationContext, message: ConversationMessage, role: str) -> bool:
        """
        Process a command message.

        Args:
            context: The conversation context
            message: The command message
            role: The user's role (coordinator or team)

        Returns:
            True if command was processed, False otherwise
        """
        # Split the command and extract the command name
        content = message.content.strip()
        if not content.startswith("/"):
            return False

        # Extract command name and arguments
        parts = content.split()
        command_name = parts[0][1:]  # Remove the '/' prefix
        args = parts[1:] if len(parts) > 1 else []

        # Check if command exists
        if command_name not in self.commands:
            await context.send_messages(
                NewConversationMessage(
                    content=f"Unknown command: /{command_name}. Type /help to see available commands.",
                    message_type=MessageType.notice,
                )
            )
            return True

        # Check if user is authorized to use this command
        if not self.is_authorized(command_name, role):
            await context.send_messages(
                NewConversationMessage(
                    content=f"The /{command_name} command is only available to {' or '.join(self.commands[command_name]['authorized_roles'])} roles. You are in {role.upper()} mode.",
                    message_type=MessageType.notice,
                )
            )
            return True

        try:
            # Execute the command handler
            await self.commands[command_name]["handler"](context, message, args)
            return True
        except Exception as e:
            logger.exception(f"Error processing command /{command_name}: {e}")
            await context.send_messages(
                NewConversationMessage(
                    content=f"Error processing command /{command_name}: {str(e)}",
                    message_type=MessageType.notice,
                )
            )
            return True


# Initialize the command registry
command_registry = CommandRegistry()


# Command handler implementations


async def handle_help_command(context: ConversationContext, message: ConversationMessage, args: List[str]) -> None:
    """Handle the help command."""
    # Get the conversation's role
    from .conversation_share_link import ConversationKnowledgePackageManager

    # First check conversation metadata
    conversation = await context.get_conversation()
    metadata = conversation.metadata or {}
    setup_complete = metadata.get("setup_complete", False)
    assistant_mode = metadata.get("assistant_mode", "setup")
    metadata_role = metadata.get("share_role")

    # First check if project ID exists - if it does, setup should be considered complete
    share_id = await KnowledgeTransferManager.get_share_id(context)
    if share_id:
        # If we have a project ID, we should never show the setup instructions
        setup_complete = True

        # If metadata doesn't reflect this, try to get actual role
        if not metadata.get("setup_complete", False):
            role = await ConversationKnowledgePackageManager.get_conversation_role(context)
            if role:
                metadata_role = role.value
            else:
                # Default to team mode if we can't determine role
                metadata_role = "team"

    # Special handling for setup mode - only if we truly have no project
    if not setup_complete and assistant_mode == "setup" and not share_id:
        # If a specific command is specified, show detailed help for that command
        if args:
            command_name = args[0]
            if command_name.startswith("/"):
                command_name = command_name[1:]  # Remove the '/' prefix

            # For setup mode, only show help for setup commands
            setup_commands = ["start-coordinator", "join", "help"]

            if command_name in setup_commands:
                help_info = command_registry.get_command_help(command_name)
                if help_info:
                    await context.send_messages(
                        NewConversationMessage(
                            content=f"""## Help: /{command_name}

{help_info["description"]}

**Usage:** {help_info["usage"]}

**Example:** {help_info["example"]}
""",
                            message_type=MessageType.chat,
                        )
                    )
                    return

            # If not a setup command, show generic message
            await context.send_messages(
                NewConversationMessage(
                    content=f"The /{command_name} command is not available in setup mode. Please first use `/start-coordinator` or `/join` to establish your role.",
                    message_type=MessageType.notice,
                )
            )
            return

        # Show setup-specific help
        help_text = """## Knowledge Share Assistant

This assistant is automatically set up to help you with your knowledge share:

- As a Coordinator: This conversation is your personal conversation for managing the knowledge share
- As a Team Member: This conversation is for collaborating on the knowledge share with others

No setup commands needed! You're already good to go.

Type `/help` to see all available commands for your role.
"""

        await context.send_messages(
            NewConversationMessage(
                content=help_text,
                message_type=MessageType.chat,
            )
        )
        return

    # Normal (non-setup) help processing
    # Use the role from metadata, which is always the authoritative source
    # Log the role for debugging
    logger.debug(f"Role detection in help command - Metadata role: {metadata_role}")

    # Use the role from metadata or default to coordinator
    role = metadata_role or "coordinator"  # Default to coordinator if not set

    # If a specific command is specified, show detailed help for that command
    if args:
        command_name = args[0]
        if command_name.startswith("/"):
            command_name = command_name[1:]  # Remove the '/' prefix

        help_info = command_registry.get_command_help(command_name)

        if help_info and command_registry.is_authorized(command_name, role):
            await context.send_messages(
                NewConversationMessage(
                    content=f"""## Help: /{command_name}

{help_info["description"]}

**Usage:** {help_info["usage"]}

**Example:** {help_info["example"]}
""",
                    message_type=MessageType.chat,
                )
            )
        else:
            await context.send_messages(
                NewConversationMessage(
                    content=f"No help available for command /{command_name} or you're not authorized to use it.",
                    message_type=MessageType.notice,
                )
            )
        return

    # Otherwise show all available commands for the current role
    available_commands = command_registry.get_commands_for_role(role)

    # Format help text based on role
    if role == ConversationRole.COORDINATOR.value:
        help_text = "## Assistant Commands (Coordinator Mode)\n\n"
    else:
        help_text = "## Assistant Commands (Team Mode)\n\n"

    # Group commands by category
    project_commands = []
    request_commands = []
    team_commands = []
    status_commands = []
    info_commands = []

    for name, cmd in available_commands.items():
        command_entry = f"- `/{name}`: {cmd['description']}"

        if "create-brief" in name or "add-learning-objective" in name:
            project_commands.append(command_entry)
        elif "request" in name:
            request_commands.append(command_entry)
        elif "invite" in name or "join" in name or "list-participants" in name:
            team_commands.append(command_entry)
        elif "status" in name or "update" in name:
            status_commands.append(command_entry)
        else:
            info_commands.append(command_entry)

    # Add sections to help text if they have commands
    if project_commands:
        help_text += "### Project Configuration\n" + "\n".join(project_commands) + "\n\n"

    if team_commands:
        help_text += "### Team Management\n" + "\n".join(team_commands) + "\n\n"

    if request_commands:
        help_text += "### Information Request Management\n" + "\n".join(request_commands) + "\n\n"

    if status_commands:
        help_text += "### Status Management\n" + "\n".join(status_commands) + "\n\n"

    if info_commands:
        help_text += "### Information\n" + "\n".join(info_commands) + "\n\n"

    # Add role-specific guidance
    if role == ConversationRole.COORDINATOR.value:
        help_text += (
            "As a Coordinator, you are responsible for defining the project and responding to team member requests."
        )
    else:
        help_text += "As a Team member, you can access knowledge package information, request information, and report progress on learning outcomes."

    await context.send_messages(
        NewConversationMessage(
            content=help_text,
            message_type=MessageType.chat,
        )
    )


async def handle_create_brief_command(
    context: ConversationContext, message: ConversationMessage, args: List[str]
) -> None:
    """Handle the create-knowledge-brief command."""
    # Parse the command
    content = message.content.strip()[len("/create-knowledge-brief") :].strip()

    if not content or "|" not in content:
        await context.send_messages(
            NewConversationMessage(
                content="Please provide a knowledge brief title and description in the format: `/create-knowledge-brief Title|Description here`",
                message_type=MessageType.notice,
            )
        )
        return

    # Extract title and description
    try:
        title, description = content.split("|", 1)
        title = title.strip()
        description = description.strip()

        if not title or not description:
            raise ValueError("Both name and description are required")

        # Create the brief without sending a notification (we'll send our own)
        briefing = await KnowledgeTransferManager.update_knowledge_brief(
            context, title, description, send_notification=False
        )

        if briefing:
            await context.send_messages(
                NewConversationMessage(
                    content=f"Brief '{title}' updated successfully.",
                    message_type=MessageType.chat,
                )
            )
        else:
            await context.send_messages(
                NewConversationMessage(
                    content="Failed to update brief. Please try again.",
                    message_type=MessageType.notice,
                )
            )
    except Exception as e:
        logger.exception(f"Error updating brief: {e}")
        await context.send_messages(
            NewConversationMessage(
                content=f"Error updating brief: {str(e)}",
                message_type=MessageType.notice,
            )
        )


async def handle_add_learning_objective_command(
    context: ConversationContext, message: ConversationMessage, args: List[str]
) -> None:
    """Handle the add-learning-objective command."""
    # Parse the command
    content = message.content.strip()[len("/add-learning-objective") :].strip()

    if not content or "|" not in content:
        await context.send_messages(
            NewConversationMessage(
                content="Please provide an objective name, description, and learning outcomes in the format: `/add-learning-objective Objective Name|Objective description|Learning outcome 1;Learning outcome 2`",
                message_type=MessageType.notice,
            )
        )
        return

    # Extract learning objective details
    try:
        parts = content.split("|")

        if len(parts) < 2:
            raise ValueError("Objective name and description are required")

        objective_name = parts[0].strip()
        objective_description = parts[1].strip()

        # Parse learning outcomes if provided
        learning_outcomes = []
        if len(parts) > 2 and parts[2].strip():
            outcomes_list = parts[2].strip().split(";")
            learning_outcomes = [o.strip() for o in outcomes_list if o.strip()]

        if not objective_name or not objective_description:
            raise ValueError("Both objective name and description are required")

        # Get project ID
        share_id = await ConversationKnowledgePackageManager.get_associated_share_id(context)
        if not share_id:
            await context.send_messages(
                NewConversationMessage(
                    content="You are not associated with a project. Please create one first with `/create-brief`.",
                    message_type=MessageType.notice,
                )
            )
            return

        # Use the dedicated method to add a learning objective to the knowledge package
        objective = await KnowledgeTransferManager.add_learning_objective(
            context=context,
            objective_name=objective_name,
            description=objective_description,
            outcomes=learning_outcomes,
        )

        if objective:
            # Notify all linked conversations about the update
            await ProjectNotifier.notify_project_update(
                context=context,
                share_id=share_id,
                update_type="briefing",
                message=f"Learning objective added to knowledge package: {objective_name}",
            )

            # Build learning outcomes message
            outcomes_msg = ""
            if learning_outcomes:
                outcomes_list = "\n".join([f"- {o}" for o in learning_outcomes])
                outcomes_msg = f"\n\nLearning Outcomes:\n{outcomes_list}"

            await context.send_messages(
                NewConversationMessage(
                    content=f"Learning objective '{objective_name}' added successfully.{outcomes_msg}",
                    message_type=MessageType.chat,
                )
            )
        else:
            await context.send_messages(
                NewConversationMessage(
                    content="Failed to add new learning objective. Please try again.",
                    message_type=MessageType.notice,
                )
            )
    except Exception as e:
        logger.exception(f"Error adding learning objective: {e}")
        await context.send_messages(
            NewConversationMessage(
                content=f"Error adding learning objective: {str(e)}",
                message_type=MessageType.notice,
            )
        )


async def handle_request_info_command(
    context: ConversationContext, message: ConversationMessage, args: List[str]
) -> None:
    """Handle the request-info command."""
    # Parse the command
    content = message.content.strip()[len("/request-info") :].strip()

    if not content or "|" not in content:
        await context.send_messages(
            NewConversationMessage(
                content="Please provide a request title and description in the format: `/request-info Request Title|Description of what you need|priority` (priority is optional: low, medium, high, critical)",
                message_type=MessageType.notice,
            )
        )
        return

    # Extract request details
    try:
        parts = content.split("|")

        title = parts[0].strip()
        description = parts[1].strip() if len(parts) > 1 else ""
        priority_str = parts[2].strip().lower() if len(parts) > 2 else "medium"

        if not title or not description:
            raise ValueError("Both request title and description are required")

        # Map priority string to enum
        priority_map = {
            "low": RequestPriority.LOW,
            "medium": RequestPriority.MEDIUM,
            "high": RequestPriority.HIGH,
            "critical": RequestPriority.CRITICAL,
        }
        priority = priority_map.get(priority_str, RequestPriority.MEDIUM)

        # Create the information request
        success, request = await KnowledgeTransferManager.create_information_request(
            context=context, title=title, description=description, priority=priority
        )

        if success and request:
            await context.send_messages(
                NewConversationMessage(
                    content=f"Information request '{title}' created successfully with {priority_str} priority. The Coordinator has been notified and will respond to your request.",
                    message_type=MessageType.chat,
                )
            )
        else:
            await context.send_messages(
                NewConversationMessage(
                    content="Failed to create information request. Please try again.",
                    message_type=MessageType.notice,
                )
            )
    except Exception as e:
        logger.exception(f"Error creating information request: {e}")
        await context.send_messages(
            NewConversationMessage(
                content=f"Error creating information request: {str(e)}",
                message_type=MessageType.notice,
            )
        )


async def handle_update_status_command(
    context: ConversationContext, message: ConversationMessage, args: List[str]
) -> None:
    """Handle the update-status command."""
    # Parse the command
    content = message.content.strip()[len("/update-status") :].strip()

    if not content:
        await context.send_messages(
            NewConversationMessage(
                content="Please provide status information in the format: `/update-status status|progress|message` (e.g., `/update-status in_progress|75|Making good progress on objectives`)",
                message_type=MessageType.notice,
            )
        )
        return

    # Extract status details
    try:
        parts = content.split("|")

        status = parts[0].strip() if parts else None
        progress_str = parts[1].strip() if len(parts) > 1 else None
        status_message = parts[2].strip() if len(parts) > 2 else None

        # Convert progress to int if provided
        progress = None
        if progress_str:
            try:
                progress = int(progress_str)
                # Ensure progress is between 0-100
                progress = max(0, min(100, progress))
            except ValueError:
                progress = None

        # Update the project status
        success, status_obj = await KnowledgeTransferManager.update_share_state(
            context=context, status_message=status_message
        )

        if success and status_obj:
            # Format progress as percentage if available
            progress_text = f" ({progress}% complete)" if progress is not None else ""

            await context.send_messages(
                NewConversationMessage(
                    content=f"Project status updated to '{status}'{progress_text}. All project participants will see this update.",
                    message_type=MessageType.chat,
                )
            )
        else:
            await context.send_messages(
                NewConversationMessage(
                    content="Failed to update project status. Please try again.",
                    message_type=MessageType.notice,
                )
            )
    except Exception as e:
        logger.exception(f"Error updating project status: {e}")
        await context.send_messages(
            NewConversationMessage(
                content=f"Error updating project status: {str(e)}",
                message_type=MessageType.notice,
            )
        )


async def handle_resolve_request_command(
    context: ConversationContext, message: ConversationMessage, args: List[str]
) -> None:
    """Handle the resolve-request command."""
    # Parse the command
    content = message.content.strip()[len("/resolve-request") :].strip()

    if not content or "|" not in content:
        await context.send_messages(
            NewConversationMessage(
                content="Please provide a request ID and resolution in the format: `/resolve-request request_id|Resolution information here`",
                message_type=MessageType.notice,
            )
        )
        return

    try:
        # Extract request ID and resolution
        request_id, resolution = content.split("|", 1)
        request_id = request_id.strip()
        resolution = resolution.strip()

        if not request_id or not resolution:
            raise ValueError("Both request ID and resolution are required")

        # Show all information requests if the user doesn't know the ID
        if request_id.lower() == "list":
            await context.send_messages(
                NewConversationMessage(
                    content="Here are the active information requests:",
                    message_type=MessageType.notice,
                )
            )

            # Get information requests
            requests = await KnowledgeTransferManager.get_information_requests(context)

            # Filter for active requests
            active_requests = [r for r in requests if r.status != RequestStatus.RESOLVED]

            if active_requests:
                request_list = ["## Active Information Requests\n"]

                for request in active_requests:
                    request_list.append(f"**ID**: `{request.request_id}`")
                    request_list.append(f"**Title**: {request.title}")
                    request_list.append(f"**Priority**: {request.priority.value}")
                    request_list.append(f"**Description**: {request.description}")
                    request_list.append("")

                await context.send_messages(
                    NewConversationMessage(
                        content="\n".join(request_list),
                        message_type=MessageType.chat,
                    )
                )
            else:
                await context.send_messages(
                    NewConversationMessage(
                        content="No active information requests found.",
                        message_type=MessageType.notice,
                    )
                )
            return

        # Resolve the information request
        success, info_request = await KnowledgeTransferManager.resolve_information_request(
            context=context, request_id=request_id, resolution=resolution
        )

        if success and info_request:
            await context.send_messages(
                NewConversationMessage(
                    content=f"Information request '{info_request.title}' has been resolved. The Team has been notified.",
                    message_type=MessageType.chat,
                )
            )
        else:
            await context.send_messages(
                NewConversationMessage(
                    content="Failed to resolve the information request. Make sure the request ID is correct and the request is not already resolved.",
                    message_type=MessageType.notice,
                )
            )

            # Suggest listing all requests to help the user
            await context.send_messages(
                NewConversationMessage(
                    content="Use `/resolve-request list|` to view all information requests and their IDs.",
                    message_type=MessageType.notice,
                )
            )
    except Exception as e:
        logger.exception(f"Error resolving information request: {e}")
        await context.send_messages(
            NewConversationMessage(
                content=f"Error resolving information request: {str(e)}",
                message_type=MessageType.notice,
            )
        )


async def handle_project_info_command(
    context: ConversationContext, message: ConversationMessage, args: List[str]
) -> None:
    """Handle the knowledge-info command."""
    # Parse the command
    content = " ".join(args).strip().lower()

    try:
        # Determine which information to show
        info_type = content if content else "all"

        if info_type not in ["all", "brief", "digest", "status", "requests"]:
            await context.send_messages(
                NewConversationMessage(
                    content="Please specify what information you want to see: `/knowledge-info [brief|digest|status|requests]`",
                    message_type=MessageType.notice,
                )
            )
            return

        # Get the requested information
        output = []

        # Always show project ID at the top for easy access
        share_id = await KnowledgeTransferManager.get_share_id(context)
        if share_id:
            # Check if Coordinator or Team
            role = await KnowledgeTransferManager.get_share_role(context)
            if role == ConversationRole.COORDINATOR:
                # For Coordinator, make it prominent with instructions
                output.append(f"## Project ID: `{share_id}`")
                output.append(f"_Share this ID with team members so they can join using_ `/join {share_id}`\n")
            else:
                # For Team, just show the ID
                output.append(f"## Project ID: `{share_id}`\n")

        # Get brief if requested
        if info_type in ["all", "brief"]:
            briefing = await KnowledgeTransferManager.get_knowledge_brief(context)

            if briefing:
                # Format briefing information
                output.append(f"## Brief: {briefing.title}")
                output.append(f"\n{briefing.description}\n")

                # Get learning objectives
                if share_id:
                    share = ShareStorage.read_share(share_id)
                    if share and share.learning_objectives:
                        output.append("\n### Learning Objectives:\n")

                        for i, objective in enumerate(share.learning_objectives):
                            # Count achieved outcomes
                            achieved = sum(1 for c in objective.learning_outcomes if c.achieved)
                            total = len(objective.learning_outcomes)

                            output.append(f"{i + 1}. **{objective.name}** - {objective.description}")

                            if objective.learning_outcomes:
                                output.append(f"   Progress: {achieved}/{total} outcomes achieved")
                                output.append("   Learning Outcomes:")

                                for j, criterion in enumerate(objective.learning_outcomes):
                                    status = "✅" if criterion.achieved else "⬜"
                                    output.append(f"   {status} {criterion.description}")

                            output.append("")

        # Get knowledge digest if requested
        if info_type in ["all", "digest"]:
            digest = await KnowledgeTransferManager.get_knowledge_digest(context)

            if digest and digest.content:
                output.append("\n## Knowledge Digest\n")
                output.append(digest.content)
                output.append("")

                if digest.is_auto_generated:
                    output.append("*This knowledge digest is automatically updated by the assistant.*")
                else:
                    output.append("*This knowledge digest has been manually edited.*")

                output.append("")
            elif info_type == "digest":
                output.append("\n## Knowledge Digest\n")
                output.append(
                    "*No digest content available yet. Content will be automatically generated as the knowledge transfer progresses.*"
                )

        # Get project status if requested
        if info_type in ["all", "status"]:
            project_info = await KnowledgeTransferManager.get_share_info(context)

            if project_info:
                output.append("\n## Project Status\n")
                stage_label = project_info.get_stage_label(for_coordinator=True)
                output.append(f"**Current Stage**: {stage_label}")

                if project_info.transfer_notes:
                    output.append(f"**Transfer Notes**: {project_info.transfer_notes}")

                # Success criteria status can be calculated from the brief if needed later
            elif info_type == "status":
                output.append("\n## Project Status\n")
                output.append("*No project status defined yet. Update status with `/update-status`.*")

        # Get information requests if requested
        if info_type in ["all", "requests"]:
            requests = await KnowledgeTransferManager.get_information_requests(context)

            if requests:
                output.append("\n## Information Requests\n")

                # Group requests by status
                active_requests = [r for r in requests if r.status != RequestStatus.RESOLVED]
                resolved_requests = [r for r in requests if r.status == RequestStatus.RESOLVED]

                if active_requests:
                    output.append("### Active Requests\n")

                    for request in active_requests:
                        priority_marker = {
                            RequestPriority.LOW.value: "🔹",
                            RequestPriority.MEDIUM.value: "🔶",
                            RequestPriority.HIGH.value: "🔴",
                            RequestPriority.CRITICAL.value: "⚠️",
                        }.get(request.priority.value, "🔹")

                        # Include request ID for easy reference when resolving
                        output.append(f"{priority_marker} **{request.title}** ({request.status.value})")
                        output.append(f"  ID: `{request.request_id}`")
                        output.append(f"  {request.description}")

                        if request.updates:
                            last_update = request.updates[-1]
                            output.append(f"  *Last update: {last_update.get('message', '')}*")

                        output.append("")

                if resolved_requests and info_type == "requests":
                    output.append("### Resolved Requests\n")

                    for request in resolved_requests[:5]:  # Show only the 5 most recent
                        output.append(f"✅ **{request.title}** ({request.status.value})")
                        output.append(f"  ID: `{request.request_id}`")

                        if request.resolution:
                            output.append(f"  Resolution: {request.resolution}")

                        output.append("")
            elif info_type == "requests":
                output.append("\n## Information Requests\n")
                output.append("*No information requests created yet. Request information with `/request-info`.*")

        # If no data was found for any category
        if not output:
            output.append("No project information found. Start by creating a brief with `/create-brief`.")

        # Send the formatted information
        await context.send_messages(
            NewConversationMessage(
                content="\n".join(output),
                message_type=MessageType.chat,
            )
        )

    except Exception as e:
        logger.exception(f"Error displaying project info: {e}")
        await context.send_messages(
            NewConversationMessage(
                content=f"Error displaying project information: {str(e)}",
                message_type=MessageType.notice,
            )
        )


async def handle_list_participants_command(
    context: ConversationContext, message: ConversationMessage, args: List[str]
) -> None:
    """Handle the list-participants command."""
    try:
        # Get project ID
        share_id = await ConversationKnowledgePackageManager.get_associated_share_id(context)
        if not share_id:
            await context.send_messages(
                NewConversationMessage(
                    content="You are not associated with a project.",
                    message_type=MessageType.notice,
                )
            )
            return

        # Get all linked conversations
        linked_conversation_ids = await ConversationKnowledgePackageManager.get_linked_conversations(context)

        if not linked_conversation_ids:
            await context.send_messages(
                NewConversationMessage(
                    content="No linked conversations found. Invite participants with the `/invite` command.",
                    message_type=MessageType.notice,
                )
            )
            return

        # Get participant information for all linked conversations
        output = ["## Project Participants\n"]

        # First add information about this conversation
        participants = await context.get_participants()

        output.append("### Coordinator Team\n")
        for participant in participants.participants:
            if participant.id != context.assistant.id:
                output.append(f"- {participant.name}")

        # In the simplified implementation, we don't have detail about the linked conversations
        # For a more complete implementation, we would need to get information
        # about each linked conversation

        # For now, just report that we have no other team members
        output.append("\n*No team members yet. Invite team members with the `/invite` command.*")

        # Send the information
        await context.send_messages(
            NewConversationMessage(
                content="\n".join(output),
                message_type=MessageType.chat,
            )
        )

    except Exception as e:
        logger.exception(f"Error listing participants: {e}")
        await context.send_messages(
            NewConversationMessage(
                content=f"Error listing participants: {str(e)}",
                message_type=MessageType.notice,
            )
        )


# File synchronization command handler
async def handle_sync_files_command(
    context: ConversationContext, message: ConversationMessage, args: List[str]
) -> None:
    """
    Handle the sync-files command which synchronizes shared files from Coordinator to Team.

    This is primarily for Team members to explicitly request a file sync
    if they suspect files are out of sync or missing.
    """
    try:
        # Get project ID
        share_id = await KnowledgeTransferManager.get_share_id(context)
        if not share_id:
            await context.send_messages(
                NewConversationMessage(
                    content="You are not associated with a project. Please join a project first.",
                    message_type=MessageType.notice,
                )
            )
            return

        # Import the file manager
        from .files import ShareManager

        # Start sync with a simple message
        await context.send_messages(
            NewConversationMessage(
                content="Synchronizing files from project...",
                message_type=MessageType.notice,
            )
        )

        # Perform synchronization directly - this handles all error messaging
        await ShareManager.synchronize_files_to_team_conversation(context=context, share_id=share_id)

    except Exception as e:
        logger.exception(f"Error synchronizing files: {e}")
        await context.send_messages(
            NewConversationMessage(
                content=f"Error synchronizing files: {str(e)}",
                message_type=MessageType.notice,
            )
        )


# General commands (available to all)
command_registry.register_command(
    "help",
    handle_help_command,
    "Get help with available commands",
    "/help [command]",
    "/help project-info",
    None,  # Available to all roles
)

command_registry.register_command(
    "knowledge-info",
    handle_project_info_command,
    "View knowledge package information",
    "/knowledge-info [brief|digest|status|requests]",
    "/knowledge-info brief",
    None,  # Available to all roles
)

# Team management commands
# Note: Manual project joining with /join is no longer needed - users just click the share URL

command_registry.register_command(
    "list-participants",
    handle_list_participants_command,
    "List all project participants",
    "/list-participants",
    "/list-participants",
    ["coordinator"],  # Only Coordinator can list participants
)


# Coordinator commands
command_registry.register_command(
    "create-knowledge-brief",
    handle_create_brief_command,
    "Create a knowledge brief",
    "/create-knowledge-brief Title|Description",
    "/create-knowledge-brief React Patterns|Key React patterns and best practices for our development team.",
    ["coordinator"],  # Only Coordinator can create knowledge briefs
)

command_registry.register_command(
    "add-learning-objective",
    handle_add_learning_objective_command,
    "Add a learning objective",
    "/add-learning-objective Objective Name|Objective description|Learning outcome 1;Learning outcome 2",
    "/add-learning-objective React Hooks|Understand React hooks and their usage|Can explain useState and useEffect;Can implement custom hooks",
    ["coordinator"],  # Only Coordinator can add learning objectives
)


command_registry.register_command(
    "resolve-request",
    handle_resolve_request_command,
    "Resolve an information request",
    "/resolve-request request_id|Resolution information",
    "/resolve-request abc123|The API documentation can be found at docs.example.com/api",
    ["coordinator"],  # Only Coordinator can resolve requests
)

# Team commands
command_registry.register_command(
    "request-info",
    handle_request_info_command,
    "Request information or assistance from the Coordinator",
    "/request-info Request Title|Request description|priority",
    "/request-info Need API Documentation|I need access to the API documentation for integration|high",
    ["team"],  # Only team can create requests
)

command_registry.register_command(
    "update-status",
    handle_update_status_command,
    "Update project status and progress",
    "/update-status status|progress|message",
    "/update-status in_progress|50|Completed homepage wireframes, working on mobile design",
    ["team"],  # Only team can update status
)

# File synchronization command (primarily for team members)
command_registry.register_command(
    "sync-files",
    handle_sync_files_command,
    "Synchronize shared files from the project to this conversation",
    "/sync-files",
    "/sync-files",
    ["team"],  # Primarily for team members
)
