#!/usr/bin/env python3
"""CLI tool to generate API keys for organizations."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.auth import APIKeyManager
from dotenv import load_dotenv

load_dotenv()


def main():
    """Generate API key for organization."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/generate_api_key.py <org_id> [description]")
        print("\nExample:")
        print("  python scripts/generate_api_key.py org-clinic-downtown 'Production API key'")
        sys.exit(1)

    org_id = sys.argv[1]
    description = sys.argv[2] if len(sys.argv) > 2 else None

    db_url = os.getenv("DATABASE_URL", "sqlite:///sessions.db")
    manager = APIKeyManager(database_url=db_url)

    api_key = manager.generate_api_key(org_id, description)

    print(f"\n✅ API Key generated for organization: {org_id}")
    if description:
        print(f"   Description: {description}")
    print(f"\n🔑 API Key: {api_key}")
    print("\n⚠️  IMPORTANT: Save this key securely! It cannot be retrieved later.")
    print("\n📋 Usage Example:")
    print(f"  curl -X POST http://localhost:8000/api/v1/chat \\")
    print(f"    -H 'X-API-Key: {api_key}' \\")
    print(f"    -H 'Content-Type: application/json' \\")
    print(f"    -d '{{")
    print(f"      \"message\": \"Hello\",")
    print(f"      \"session_id\": \"550e8400-e29b-41d4-a716-446655440000\",")
    print(f"      \"org_id\": \"{org_id}\"")
    print(f"    }}'\n")


if __name__ == "__main__":
    main()
