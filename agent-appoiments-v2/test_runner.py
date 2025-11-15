# test_runner.py
"""
Test runner for organization-specific agent configurations.

Usage:
    python test_runner.py <organization_id>

Example:
    python test_runner.py 550e8400-e29b-41d4-a716-446655440001
"""
import sys
import os
from typing import Optional
from dotenv import load_dotenv

from src.config_manager import ConfigManager
from src.org_config import OrganizationConfig
from src.agent import create_agent_for_org  # REAL org-aware agent

from langchain_core.messages import HumanMessage

# Load environment
load_dotenv()


def print_header(text: str) -> None:
    """Print section header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def validate_org_exists(org_id: str, manager: ConfigManager) -> None:
    """
    Validate that organization configuration exists.

    Args:
        org_id: Organization ID to validate
        manager: ConfigManager instance

    Raises:
        SystemExit: If organization not found
    """
    if not manager.config_exists(org_id):
        print(f"❌ ERROR: Organization '{org_id}' not found.")
        print(f"\nAvailable organizations:")

        orgs = manager.list_organizations()
        if orgs:
            for org in orgs:
                print(f"  - {org}")
        else:
            print("  (none)")

        print(f"\nTo create a new organization, run:")
        print(f"  python setup_wizard.py")

        sys.exit(1)


def load_and_display_config(
    org_id: str,
    manager: ConfigManager
) -> OrganizationConfig:
    """
    Load and display organization configuration.

    Args:
        org_id: Organization ID to load
        manager: ConfigManager instance

    Returns:
        Loaded OrganizationConfig
    """
    config = manager.load_config(org_id)

    org_display = config.org_name if config.org_name else f"Organization {config.org_id}"
    print_header(f"ORGANIZATION: {org_display}")

    print(f"📋 Organization ID: {config.org_id}")
    print(f"📛 Name: {config.org_name if config.org_name else '(not provided)'}")

    # System prompt
    if config.system_prompt:
        print(f"\n🤖 Custom System Prompt:")
        prompt_preview = config.system_prompt[:200]
        if len(config.system_prompt) > 200:
            prompt_preview += "..."
        print(f"   {prompt_preview}")
    else:
        print(f"\n🤖 System Prompt: Using default")

    # Services
    active_services = config.get_active_services()
    print(f"\n📦 Services: {len(config.services)} total ({len(active_services)} active)")
    for service in config.services:
        status = "✅" if service.active else "❌"
        print(f"   {status} {service.name} ({service.duration_minutes} min, ${service.price:.2f})")

    # Permissions
    perms = config.permissions
    print(f"\n🔐 Permissions:")
    print(f"   Book: {'✅ Enabled' if perms.can_book else '❌ Disabled'}")
    print(f"   Reschedule: {'✅ Enabled' if perms.can_reschedule else '❌ Disabled'}")
    print(f"   Cancel: {'✅ Enabled' if perms.can_cancel else '❌ Disabled'}")

    # Promotional offers
    if config.promotional_offers:
        active_offers = [o for o in config.promotional_offers if o.active]
        print(f"\n🎁 Promotional Offers: {len(config.promotional_offers)} total ({len(active_offers)} active)")
        for offer in config.promotional_offers:
            status = "✅" if offer.active else "❌"
            print(f"   {status} {offer.title}")

    # Location
    if config.location:
        print(f"\n📍 Location: {config.location.get('name', 'N/A')}")
        print(f"   {config.location.get('address', 'N/A')}")

    # Provider
    if config.assigned_person:
        print(f"\n👨‍⚕️ Provider: {config.assigned_person.get('name', 'N/A')}")
        print(f"   {config.assigned_person.get('type', 'N/A')}")

    return config


def run_agent_interactive(config: OrganizationConfig) -> None:
    """
    Run agent in interactive mode with organization-specific configuration.

    THIS USES THE REAL create_agent_for_org() - NOT create_graph()

    Args:
        config: Organization configuration
    """
    print_header("INTERACTIVE AGENT TEST")
    print("⚠️  Using REAL org-specific agent with custom prompt and permissions!")
    print("Type your messages below. Type 'exit' or 'quit' to stop.\n")

    # *** CRITICAL: Use create_agent_for_org() NOT create_graph() ***
    graph = create_agent_for_org(config)

    # Initialize config for LangGraph
    thread_id = f"test-{config.org_id}"
    config_dict = {"configurable": {"thread_id": thread_id}}

    print("🤖 Agent: Hello! How can I help you today?\n")

    try:
        while True:
            # Get user input
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("\n🤖 Agent: Goodbye! Have a great day!\n")
                break

            # Create user message
            message = HumanMessage(content=user_input)

            # Invoke org-specific graph
            result = graph.invoke(
                {"messages": [message]},
                config_dict
            )

            # Display agent response
            if result and "messages" in result:
                last_message = result["messages"][-1]
                if hasattr(last_message, 'content'):
                    print(f"\n🤖 Agent: {last_message.content}\n")

    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted. Goodbye!\n")
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python test_runner.py <organization_id>")
        print("\nExample:")
        print("  python test_runner.py 550e8400-e29b-41d4-a716-446655440001")
        print("\nTry the sample organizations:")
        print("  python test_runner.py 550e8400-e29b-41d4-a716-446655440001  # Medical center")
        print("  python test_runner.py 550e8400-e29b-41d4-a716-446655440002  # Therapy clinic")
        sys.exit(1)

    org_id = sys.argv[1]

    # Initialize manager
    manager = ConfigManager()

    # Validate organization exists
    validate_org_exists(org_id, manager)

    # Load and display config
    config = load_and_display_config(org_id, manager)

    print("\n⚠️  VERIFICATION:")
    print(f"   - Agent will use: {config.org_name if config.org_name else config.org_id}")
    print(f"   - System prompt: {'CUSTOM' if config.system_prompt else 'DEFAULT'}")
    print(f"   - Active services: {len(config.get_active_services())}")
    print(f"   - Can reschedule: {'YES' if config.permissions.can_reschedule else 'NO'}")
    print(f"   - Can cancel: {'YES' if config.permissions.can_cancel else 'NO'}")

    # Run interactive agent with REAL org config
    run_agent_interactive(config)


if __name__ == "__main__":
    main()
