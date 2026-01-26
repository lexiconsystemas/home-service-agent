"""Tests for client provisioning functionality."""

import pytest
from unittest.mock import AsyncMock, patch
import tempfile
import json

from scripts.provision_client import (
    generate_client_api_key,
    load_template,
    provision_client,
)


class TestClientProvisioning:
    """Test cases for client provisioning functionality."""
    
    @pytest.mark.asyncio
    async def test_generate_client_api_key_format(self):
        """Test that generated client API keys have correct format."""
        api_key = await generate_client_api_key()
        
        # Verify format
        assert api_key.startswith("lexicon_client_")
        assert len(api_key) > 20  # Should be sufficiently long
        assert "_" in api_key  # Should have separators
        
        # Verify it's different each time
        api_key2 = await generate_client_api_key()
        assert api_key != api_key2
    
    @pytest.mark.asyncio
    async def test_load_template_success(self):
        """Test successful template loading."""
        # Create a temporary template file
        template_data = {
            "name": "Test Template",
            "description": "Test description",
            "rules_json": {"test": "rules"},
            "routing_json": {"test": "routing"},
            "delivery_defaults": {
                "delivery_channels": ["WEBHOOK"],
                "webhook_url": "https://test.com"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(template_data, f)
            template_path = f.name
        
        try:
            # Mock the template directory path
            with patch('scripts.provision_client.Path') as mock_path:
                mock_path.return_value.parent.parent / "templates" / "test.json" = template_path
                
                # Load template
                template = await load_template("test")
                
                # Verify template content
                assert template["name"] == "Test Template"
                assert template["description"] == "Test description"
                assert template["rules_json"]["test"] == "rules"
                assert template["routing_json"]["test"] == "routing"
                assert template["delivery_defaults"]["delivery_channels"] == ["WEBHOOK"]
        
        finally:
            import os
            os.unlink(template_path)
    
    @pytest.mark.asyncio
    async def test_load_template_not_found(self):
        """Test template loading when file doesn't exist."""
        # Mock the template directory path
        with patch('scripts.provision_client.Path') as mock_path:
            mock_path.return_value.parent.parent / "templates" / "nonexistent.json" = "/nonexistent/path"
            
            with patch('scripts.provision_client.sys.exit') as mock_exit:
                # Try to load non-existent template
                await load_template("nonexistent")
                
                # Verify sys.exit was called
                mock_exit.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_provision_client_success(self):
        """Test successful client provisioning."""
        # Mock template data
        template_data = {
            "name": "HVAC Template",
            "description": "HVAC services template",
            "rules_json": {"qualification": {"budget_threshold": 100}},
            "routing_json": {"timezone": "America/New_York"},
            "delivery_defaults": {
                "delivery_channels": ["WEBHOOK"],
                "webhook_url": "https://hvac.example.com/webhook"
            },
            "message_templates": {"confirmation": {"sms": "Thank you!"}},
            "followup_flags": {"send_confirmation_to_caller": True}
        }
        
        # Mock database connection and operations
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = None
        
        # Mock template loading
        with patch('scripts.provision_client.load_template', return_value=template_data):
            with patch('scripts.provision_client.generate_client_api_key', return_value="test_api_key_123"):
                with patch('scripts.provision_client.asyncpg.connect', return_value=mock_conn):
                    # Provision client
                    result = await provision_client(
                        database_url="postgresql://test",
                        client_id="test-client",
                        to_number="+15550000000",
                        template_name="hvac"
                    )
                    
                    # Verify result
                    assert result["client_id"] == "test-client"
                    assert result["to_number"] == "+15550000000"
                    assert result["template"] == "hvac"
                    assert result["template_description"] == "HVAC services template"
                    assert result["client_api_key"] == "test_api_key_123"
                    assert result["version"] == 1
                    assert result["status"] == "provisioned"
                    
                    # Verify database insert was called
                    assert mock_conn.execute.call_count == 2  # Client config + audit log
                    
                    # Verify client config insert
                    client_insert_call = mock_conn.execute.call_args_list[0]
                    insert_sql = client_insert_call[0][0]
                    assert "INSERT INTO lexicon_intake.client_configs" in insert_sql
                    assert "test-client" in str(client_insert_call[1])
                    assert "+15550000000" in str(client_insert_call[1])
                    assert "test_api_key_123" in str(client_insert_call[1])
                    
                    # Verify audit log insert
                    audit_insert_call = mock_conn.execute.call_args_list[1]
                    audit_sql = audit_insert_call[0][0]
                    assert "INSERT INTO lexicon_intake.audit_logs" in audit_sql
                    assert "CREATE_CLIENT" in str(audit_insert_call[1])
    
    @pytest.mark.asyncio
    async def test_provision_client_database_error(self):
        """Test client provisioning with database error."""
        # Mock template data
        template_data = {"name": "Test", "rules_json": {}, "delivery_defaults": {}}
        
        # Mock database connection that raises error
        mock_conn = AsyncMock()
        mock_conn.execute.side_effect = Exception("Database connection failed")
        
        with patch('scripts.provision_client.load_template', return_value=template_data):
            with patch('scripts.provision_client.generate_client_api_key', return_value="test_key"):
                with patch('scripts.provision_client.asyncpg.connect', return_value=mock_conn):
                    # Provision client should raise exception
                    with pytest.raises(Exception) as exc_info:
                        await provision_client(
                            database_url="postgresql://test",
                            client_id="test-client",
                            to_number="+15550000000",
                            template_name="test"
                        )
                    
                    assert "Database connection failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_provision_client_all_templates(self):
        """Test provisioning with all available templates."""
        templates = ["hvac", "plumbing", "pressure_wash", "restoration"]
        
        for template_name in templates:
            # Mock template data
            template_data = {
                "name": f"{template_name.title()} Template",
                "description": f"{template_name.title()} services template",
                "rules_json": {"qualification": {"budget_threshold": 50}},
                "routing_json": {"timezone": "America/New_York"},
                "delivery_defaults": {
                    "delivery_channels": ["WEBHOOK"],
                    "webhook_url": f"https://{template_name}.example.com/webhook"
                }
            }
            
            # Mock database connection
            mock_conn = AsyncMock()
            mock_conn.execute.return_value = None
            
            with patch('scripts.provision_client.load_template', return_value=template_data):
                with patch('scripts.provision_client.generate_client_api_key', return_value=f"api_key_{template_name}"):
                    with patch('scripts.provision_client.asyncpg.connect', return_value=mock_conn):
                        # Provision client
                        result = await provision_client(
                            database_url="postgresql://test",
                            client_id=f"{template_name}-client",
                            to_number=f"+1555000000{templates.index(template_name)}",
                            template_name=template_name
                        )
                        
                        # Verify template-specific results
                        assert result["template"] == template_name
                        assert result["template_description"] == f"{template_name.title()} services template"
                        assert result["client_api_key"] == f"api_key_{template_name}"
    
    @pytest.mark.asyncio
    async def test_provision_client_version_tracking(self):
        """Test that version is properly tracked during provisioning."""
        # Mock template data
        template_data = {
            "name": "Test Template",
            "rules_json": {},
            "delivery_defaults": {"delivery_channels": []}
        }
        
        # Mock database connection
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = None
        
        with patch('scripts.provision_client.load_template', return_value=template_data):
            with patch('scripts.provision_client.generate_client_api_key', return_value="test_key"):
                with patch('scripts.provision_client.asyncpg.connect', return_value=mock_conn):
                    # Provision client
                    result = await provision_client(
                        database_url="postgresql://test",
                        client_id="test-client",
                        to_number="+15550000000",
                        template_name="test"
                    )
                    
                    # Verify version starts at 1
                    assert result["version"] == 1
                    
                    # Verify version is included in database insert
                    client_insert_call = mock_conn.execute.call_args_list[0]
                    insert_args = client_insert_call[1]
                    assert insert_args[12] == 1  # version parameter
    
    @pytest.mark.asyncio
    async def test_provision_client_audit_log_content(self):
        """Test that audit log contains correct provisioning information."""
        # Mock template data
        template_data = {
            "name": "Test Template",
            "description": "Test description",
            "rules_json": {},
            "delivery_defaults": {"delivery_channels": []}
        }
        
        # Mock database connection
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = None
        
        with patch('scripts.provision_client.load_template', return_value=template_data):
            with patch('scripts.provision_client.generate_client_api_key', return_value="test_api_key"):
                with patch('scripts.provision_client.asyncpg.connect', return_value=mock_conn):
                    # Provision client
                    await provision_client(
                        database_url="postgresql://test",
                        client_id="test-client",
                        to_number="+15550000000",
                        template_name="test"
                    )
                    
                    # Verify audit log content
                    audit_insert_call = mock_conn.execute.call_args_list[1]
                    audit_args = audit_insert_call[1]
                    
                    # Verify audit log fields
                    assert audit_args[1] == "ADMIN"  # actor_type
                    assert audit_args[2] == "provision_script"  # actor_id
                    assert audit_args[3] == "CREATE_CLIENT"  # action
                    assert audit_args[4] == "client_config"  # target_type
                    assert audit_args[5] == "test-client"  # target_id
                    
                    # Verify after_state contains provisioning details
                    after_state = json.loads(audit_args[7])
                    assert after_state["client_id"] == "test-client"
                    assert after_state["to_number"] == "+15550000000"
                    assert after_state["template"] == "test"
                    assert after_state["client_api_key"] == "test_api_key"
                    assert after_state["version"] == 1
