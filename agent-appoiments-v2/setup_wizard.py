# setup_wizard.py
"""
Interactive setup wizard for organization configuration.

Guides user through:
1. Organization details
2. System prompt (optional)
3. Services (1-10)
4. Permissions
5. Promotional offers (optional)
6. Location and provider info
"""
import uuid
import sys
from typing import Optional, List
from src.org_config import (
    OrganizationConfig,
    ServiceConfig,
    PermissionsConfig,
    PromotionalOffer
)
from src.config_manager import ConfigManager


def generate_org_id() -> str:
    """Generate unique organization ID."""
    return str(uuid.uuid4())


def print_header(text: str) -> None:
    """Print section header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def prompt_text(
    prompt: str,
    required: bool = True,
    max_length: Optional[int] = None,
    default: Optional[str] = None
) -> str:
    """
    Prompt for text input with validation.

    Args:
        prompt: Prompt message
        required: Whether input is required
        max_length: Maximum length (optional)
        default: Default value if empty (optional)

    Returns:
        User input (validated)
    """
    while True:
        if default:
            value = input(f"{prompt} [{default}]: ").strip()
            if not value:
                value = default
        else:
            value = input(f"{prompt}: ").strip()

        # Check required
        if required and not value:
            print("❌ This field is required. Please try again.\n")
            continue

        # Check max length
        if max_length and len(value) > max_length:
            print(f"❌ Maximum length is {max_length} characters. Please try again.\n")
            continue

        return value


def prompt_yes_no(prompt: str, default: bool = True) -> bool:
    """
    Prompt for yes/no answer.

    Args:
        prompt: Question to ask
        default: Default value if user presses enter

    Returns:
        True for yes, False for no
    """
    default_str = "Y/n" if default else "y/N"

    while True:
        answer = input(f"{prompt} [{default_str}]: ").strip().lower()

        if not answer:
            return default

        if answer in ['y', 'yes']:
            return True
        elif answer in ['n', 'no']:
            return False
        else:
            print("❌ Please answer 'yes' or 'no'.\n")


def prompt_number(
    prompt: str,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
    is_int: bool = False
) -> float:
    """
    Prompt for numeric input with validation.

    Args:
        prompt: Prompt message
        min_val: Minimum value (optional)
        max_val: Maximum value (optional)
        is_int: Whether to return integer

    Returns:
        Validated number
    """
    while True:
        value_str = input(f"{prompt}: ").strip()

        try:
            if is_int:
                value = int(value_str)
            else:
                value = float(value_str)

            # Validate range
            if min_val is not None and value < min_val:
                print(f"❌ Minimum value is {min_val}. Please try again.\n")
                continue

            if max_val is not None and value > max_val:
                print(f"❌ Maximum value is {max_val}. Please try again.\n")
                continue

            return value

        except ValueError:
            print(f"❌ Invalid number. Please try again.\n")


def prompt_service(index: int) -> ServiceConfig:
    """
    Prompt for service configuration.

    Args:
        index: Service number (for display)

    Returns:
        ServiceConfig instance
    """
    print(f"\n--- Service #{index} ---")

    name = prompt_text("Service name", required=True, max_length=100)
    description = prompt_text("Description", required=True, max_length=500)
    duration = prompt_number(
        "Duration (minutes)",
        min_val=1,
        max_val=480,
        is_int=True
    )
    price = prompt_number("Price", min_val=0.0)
    active = prompt_yes_no("Active?", default=True)

    # Generate service ID
    service_id = f"srv-{index:03d}"

    return ServiceConfig(
        id=service_id,
        name=name,
        description=description,
        duration_minutes=int(duration),
        price=price,
        active=active
    )


def prompt_permissions() -> PermissionsConfig:
    """
    Prompt for permission configuration.

    Returns:
        PermissionsConfig instance
    """
    print_header("PERMISSIONS")
    print("Configure what actions the agent can perform.")
    print("⚠️  At least one permission must be enabled.\n")

    can_book = prompt_yes_no("Allow booking appointments?", default=True)
    can_reschedule = prompt_yes_no("Allow rescheduling appointments?", default=True)
    can_cancel = prompt_yes_no("Allow canceling appointments?", default=True)

    # Validate at least one active
    if not (can_book or can_reschedule or can_cancel):
        print("\n❌ At least one permission must be active. Enabling all permissions.\n")
        return PermissionsConfig(
            can_book=True,
            can_reschedule=True,
            can_cancel=True
        )

    return PermissionsConfig(
        can_book=can_book,
        can_reschedule=can_reschedule,
        can_cancel=can_cancel
    )


def run_setup_wizard() -> OrganizationConfig:
    """
    Run interactive setup wizard.

    Returns:
        Complete OrganizationConfig
    """
    print_header("ORGANIZATION SETUP WIZARD")
    print("This wizard will guide you through configuring your appointment agent.\n")

    # Step 1: Organization details
    print_header("ORGANIZATION DETAILS")
    org_id = generate_org_id()
    print(f"📋 Generated Organization ID: {org_id}\n")

    org_name = prompt_text("Organization name", required=True, max_length=200)

    # Step 2: System prompt (optional)
    print_header("AGENT PERSONALITY")
    print("You can customize how the agent communicates.")
    print("Leave empty to use the default professional prompt.\n")

    custom_prompt = None
    if prompt_yes_no("Customize agent personality?", default=False):
        print("\nEnter custom system prompt (press Enter on empty line to finish):")
        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)

        if lines:
            custom_prompt = "\n".join(lines)
            if len(custom_prompt) > 4000:
                print(f"⚠️  Prompt too long ({len(custom_prompt)} chars). Truncating to 4000 chars.")
                custom_prompt = custom_prompt[:4000]

    # Step 3: Services
    print_header("SERVICES")
    print("Add services (minimum 1, maximum 10).\n")

    services = []
    for i in range(1, 11):
        service = prompt_service(i)
        services.append(service)

        if i >= 1:  # Allow exit after first service
            if not prompt_yes_no(f"\nAdd another service? ({i}/10 configured)", default=True):
                break

    # Step 4: Permissions
    permissions = prompt_permissions()

    # Step 5: Promotional offers (optional)
    print_header("PROMOTIONAL OFFERS")
    print("Promotional offers are optional. You can add them later.\n")

    offers = []
    if prompt_yes_no("Add promotional offers?", default=False):
        for i in range(1, 6):  # Max 5 offers
            print(f"\n--- Offer #{i} ---")
            title = prompt_text("Offer title", required=True, max_length=200)
            description = prompt_text("Offer description", required=True)

            # Metadata
            print("\nMetadata (optional key-value pairs, empty key to finish):")
            metadata = {}
            while True:
                key = input("  Key: ").strip()
                if not key:
                    break
                value = input("  Value: ").strip()
                metadata[key] = value

            active = prompt_yes_no("Active?", default=True)

            offer = PromotionalOffer(
                id=f"offer-{i:03d}",
                title=title,
                description=description,
                metadata=metadata,
                active=active
            )
            offers.append(offer)

            if not prompt_yes_no(f"\nAdd another offer? ({i}/5 configured)", default=False):
                break

    # Step 6: Location (optional)
    print_header("LOCATION")
    location = None
    if prompt_yes_no("Add location information?", default=True):
        location = {
            "name": prompt_text("Location name", required=True),
            "address": prompt_text("Address", required=True),
            "city": prompt_text("City", required=True),
            "phone": prompt_text("Phone", required=True)
        }

    # Step 7: Provider (optional)
    print_header("PROVIDER")
    assigned_person = None
    if prompt_yes_no("Add provider information?", default=True):
        assigned_person = {
            "name": prompt_text("Provider name", required=True),
            "type": prompt_text("Type (e.g., doctor, therapist)", required=True),
            "specialization": prompt_text("Specialization", required=False)
        }

    # Step 8: Operating hours (optional)
    print_header("OPERATING HOURS")
    operating_hours = None
    if prompt_yes_no("Configure operating hours?", default=True):
        print("\nDays (comma-separated, e.g., monday,tuesday,wednesday):")
        days_str = input("Days: ").strip().lower()
        days = [d.strip() for d in days_str.split(",")]

        start_time = prompt_text("Start time (HH:MM)", default="09:00")
        end_time = prompt_text("End time (HH:MM)", default="18:00")
        slot_duration = prompt_number(
            "Slot duration (minutes)",
            min_val=5,
            max_val=120,
            is_int=True
        )

        operating_hours = {
            "days": days,
            "start_time": start_time,
            "end_time": end_time,
            "slot_duration_minutes": int(slot_duration)
        }

    # Create configuration
    config = OrganizationConfig(
        org_id=org_id,
        org_name=org_name,
        system_prompt=custom_prompt,
        services=services,
        permissions=permissions,
        promotional_offers=offers,
        location=location,
        assigned_person=assigned_person,
        operating_hours=operating_hours
    )

    return config


def main():
    """Main entry point."""
    try:
        config = run_setup_wizard()

        # Summary
        print_header("CONFIGURATION SUMMARY")
        print(f"Organization ID: {config.org_id}")
        print(f"Organization Name: {config.org_name}")
        print(f"Custom Prompt: {'Yes' if config.system_prompt else 'No (using default)'}")
        print(f"Services: {len(config.services)} ({len(config.get_active_services())} active)")
        print(f"Permissions: Book={config.permissions.can_book}, "
              f"Reschedule={config.permissions.can_reschedule}, "
              f"Cancel={config.permissions.can_cancel}")
        print(f"Promotional Offers: {len(config.promotional_offers)}")
        print(f"Location: {'Yes' if config.location else 'No'}")
        print(f"Provider: {'Yes' if config.assigned_person else 'No'}")
        print(f"Operating Hours: {'Yes' if config.operating_hours else 'No'}\n")

        # Save
        if prompt_yes_no("\nSave this configuration?", default=True):
            manager = ConfigManager()
            manager.save_config(config)

            print(f"\n✅ Configuration saved successfully!")
            print(f"📋 Organization ID: {config.org_id}")
            print(f"📁 Saved to: data/organizations/{config.org_id}.json")
            print(f"\nTo test this configuration, run:")
            print(f"  python test_runner.py {config.org_id}")
        else:
            print("\n❌ Configuration not saved.")

    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
