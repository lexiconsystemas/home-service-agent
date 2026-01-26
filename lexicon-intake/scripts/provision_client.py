#!/usr/bin/env python3
"""Client provisioning script for one-command client setup."""

import argparse
import json
import secrets
import sys
from pathlib import Path

import asyncpg
import structlog

logger = structlog.get_logger()


async def generate_client_api_key() -> str:
    """Generate a secure client API key."""
    return f"lexicon_client_{secrets.token_urlsafe(32)}"


async def load_template(template_name: str) -> dict:
    """Load client template from JSON file."""
    template_path = Path(__file__).parent.parent / "templates" / f"{template_name}.json"
    
    if not template_path.exists():
        logger.error(f"Template not found: {template_name}")
        sys.exit(1)
    
    with open(template_path, 'r') as f:
        return json.load(f)


async def provision_client(
    database_url: str,
    client_id: str,
    to_number: str,
    template_name: str,
) -> dict:
    """Provision a new client with template configuration."""
    
    # Load template
    template = await load_template(template_name)
    
    # Generate client API key
    client_api_key = await generate_client_api_key()
    
    # Connect to database
    conn = await asyncpg.connect(database_url)
    
    try:
        # Insert client configuration
        await conn.execute("""
            INSERT INTO lexicon_intake.client_configs (
                client_id,
                to_number,
                greeting_message,
                rules_json,
                routing_json,
                delivery_channels,
                webhook_url,
                sms_to_numbers,
                email_to_addresses,
                message_templates,
                followup_flags,
                client_api_key,
                version
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, 1)
            ON CONFLICT (client_id) DO NOTHING
        """, 
            client_id,
            to_number,
            "Thank you for calling. How can we help you today?",
            json.dumps(template["rules_json"]),
            json.dumps(template["routing_json"]),
            template["delivery_defaults"]["delivery_channels"],
            template["delivery_defaults"].get("webhook_url"),
            template["delivery_defaults"].get("sms_to_numbers", []),
            template["delivery_defaults"].get("email_to_addresses", []),
            json.dumps(template.get("message_templates", {})),
            json.dumps(template.get("followup_flags", {})),
            client_api_key,
        )
        
        # Log audit entry
        await conn.execute("""
            INSERT INTO lexicon_intake.audit_logs (
                actor_type,
                actor_id,
                action,
                target_type,
                target_id,
                before_state,
                after_state,
                details
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """,
            "ADMIN",
            "provision_script",
            "CREATE_CLIENT",
            "client_config",
            client_id,
            None,
            json.dumps({
                "client_id": client_id,
                "to_number": to_number,
                "template": template_name,
                "client_api_key": client_api_key,
                "version": 1
            }),
            json.dumps({
                "template_name": template_name,
                "template_description": template.get("description", ""),
                "provisioned_at": "now()"
            })
        )
        
        logger.info(
            "Client provisioned successfully",
            client_id=client_id,
            to_number=to_number,
            template=template_name,
            api_key=client_api_key,
        )
        
        return {
            "client_id": client_id,
            "to_number": to_number,
            "template": template_name,
            "template_description": template.get("description", ""),
            "client_api_key": client_api_key,
            "version": 1,
            "status": "provisioned"
        }
        
    except Exception as e:
        logger.error(
            "Failed to provision client",
            client_id=client_id,
            error=str(e),
            exc_info=True,
        )
        raise
        
    finally:
        await conn.close()


def print_onboarding_summary(client_data: dict) -> None:
    """Print onboarding summary for the client."""
    print("\n" + "="*60)
    print("CLIENT ONBOARDING SUMMARY")
    print("="*60)
    print(f"Client ID: {client_data['client_id']}")
    print(f"To Number: {client_data['to_number']}")
    print(f"Template: {client_data['template']}")
    print(f"Description: {client_data['template_description']}")
    print(f"Version: {client_data['version']}")
    print(f"Status: {client_data['status']}")
    print("\n" + "-"*60)
    print("IMPORTANT - SAVE THIS INFORMATION:")
    print("-"*60)
    print(f"Client API Key: {client_data['client_api_key']}")
    print("\nNext Steps:")
    print("1. Update your .env file with the client API key")
    print("2. Configure your Twilio webhook to point to:")
    print("   https://your-domain.com/v1/calls/inbound")
    print("3. Test inbound calls to verify routing works")
    print("4. Monitor logs and delivery status")
    print("="*60)


async def main():
    """Main provisioning function."""
    parser = argparse.ArgumentParser(
        description="Provision a new client with template configuration"
    )
    parser.add_argument(
        "--client-id",
        required=True,
        help="Unique client identifier"
    )
    parser.add_argument(
        "--to-number",
        required=True,
        help="Twilio phone number for this client (E.164 format)"
    )
    parser.add_argument(
        "--template",
        required=True,
        choices=["hvac", "plumbing", "pressure_wash", "restoration"],
        help="Template to apply"
    )
    parser.add_argument(
        "--database-url",
        default="postgresql+asyncpg://lexicon:lexicon@localhost:5432/lexicon_intake",
        help="Database connection URL"
    )
    
    args = parser.parse_args()
    
    # Validate phone number format
    if not args.to_number.startswith("+"):
        print("Error: Phone number must be in E.164 format (e.g., +15550000000)")
        sys.exit(1)
    
    try:
        # Provision the client
        client_data = await provision_client(
            database_url=args.database_url,
            client_id=args.client_id,
            to_number=args.to_number,
            template_name=args.template,
        )
        
        # Print onboarding summary
        print_onboarding_summary(client_data)
        
    except Exception as e:
        logger.error("Provisioning failed", error=str(e))
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
