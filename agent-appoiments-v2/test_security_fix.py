#!/usr/bin/env python3
"""
Quick test to verify security fix (v1.3.1).

This script verifies that get_user_appointments_tool is NOT available
in the agent's tool list, preventing unauthorized email-based lookup.
"""

from src.agent import tools, llm_with_tools

def test_security_fix():
    """Verify get_user_appointments_tool is removed from tools."""
    print("=" * 70)
    print("🔒 SECURITY FIX VERIFICATION (v1.3.1)")
    print("=" * 70)
    print()

    # Get all tool names
    tool_names = [tool.name for tool in tools]

    print("📋 Available tools:")
    for i, name in enumerate(tool_names, 1):
        print(f"   {i}. {name}")
    print()

    # Check for the removed tool
    if "get_user_appointments_tool" in tool_names:
        print("❌ SECURITY ISSUE: get_user_appointments_tool is still available!")
        print("   This allows unauthorized email-based lookup.")
        return False
    else:
        print("✅ SECURITY FIX VERIFIED: get_user_appointments_tool is removed")
        print("   Email-based lookup is no longer available.")
        print()

    # Verify expected tools are present
    print("🔍 Verifying expected tools:")
    expected_tools = {
        "get_appointment_tool": "✅ Required for rescheduling",
        "reschedule_appointment_tool": "✅ Required for rescheduling",
        "cancel_appointment_tool": "✅ Required for cancellation",
        "get_services_tool": "✅ Required for booking",
    }

    all_present = True
    for tool_name, description in expected_tools.items():
        if tool_name in tool_names:
            print(f"   ✅ {tool_name}: Present")
        else:
            print(f"   ❌ {tool_name}: MISSING!")
            all_present = False
    print()

    if all_present:
        print("=" * 70)
        print("✅ ALL SECURITY CHECKS PASSED")
        print("=" * 70)
        print()
        print("Summary:")
        print("- ❌ get_user_appointments_tool removed (email lookup blocked)")
        print("- ✅ Confirmation number-based tools present")
        print("- 🔒 Unauthorized access via email is now prevented")
        print()
        return True
    else:
        print("=" * 70)
        print("❌ SOME CHECKS FAILED")
        print("=" * 70)
        return False


if __name__ == "__main__":
    success = test_security_fix()
    exit(0 if success else 1)
