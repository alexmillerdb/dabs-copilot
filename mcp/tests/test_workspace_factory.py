"""
Test workspace client factory
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from databricks.sdk import WorkspaceClient


class TestWorkspaceFactory:
    """Test cases for workspace client factory"""
    
    @patch('server.workspace_factory.WorkspaceClient')
    def test_create_client_with_profile(self, mock_workspace_client):
        """Test creating client with profile configuration"""
        from server.workspace_factory import create_workspace_client
        
        # Set up environment
        with patch.dict(os.environ, {'DATABRICKS_CONFIG_PROFILE': 'test-profile'}):
            # Create client
            client = create_workspace_client()
            
            # Verify WorkspaceClient was called with profile
            mock_workspace_client.assert_called_once_with(profile='test-profile')
            assert client == mock_workspace_client.return_value
    
    @patch('server.workspace_factory.WorkspaceClient')
    def test_create_client_with_host_token(self, mock_workspace_client):
        """Test creating client with host and token"""
        from server.workspace_factory import create_workspace_client
        
        # Set up environment
        env_vars = {
            'DATABRICKS_HOST': 'https://test.databricks.com',
            'DATABRICKS_TOKEN': 'test-token'
        }
        with patch.dict(os.environ, env_vars, clear=True):
            # Create client
            client = create_workspace_client()
            
            # Verify WorkspaceClient was called with host and token
            mock_workspace_client.assert_called_once_with(
                host='https://test.databricks.com',
                token='test-token'
            )
            assert client == mock_workspace_client.return_value
    
    @patch('server.workspace_factory.WorkspaceClient')
    def test_create_client_default(self, mock_workspace_client):
        """Test creating client with default configuration"""
        from server.workspace_factory import create_workspace_client
        
        # Clear environment variables
        with patch.dict(os.environ, {}, clear=True):
            # Create client
            client = create_workspace_client()
            
            # Verify WorkspaceClient was called with no args (default)
            mock_workspace_client.assert_called_once_with()
            assert client == mock_workspace_client.return_value
    
    @patch('server.workspace_factory.WorkspaceClient')
    def test_create_client_profile_takes_precedence(self, mock_workspace_client):
        """Test that profile takes precedence over host/token"""
        from server.workspace_factory import create_workspace_client
        
        # Set up environment with both profile and host/token
        env_vars = {
            'DATABRICKS_CONFIG_PROFILE': 'test-profile',
            'DATABRICKS_HOST': 'https://test.databricks.com',
            'DATABRICKS_TOKEN': 'test-token'
        }
        with patch.dict(os.environ, env_vars):
            # Create client
            client = create_workspace_client()
            
            # Verify profile was used, not host/token
            mock_workspace_client.assert_called_once_with(profile='test-profile')
            assert client == mock_workspace_client.return_value
    
    @patch('server.workspace_factory.WorkspaceClient')
    def test_create_client_handles_exception(self, mock_workspace_client):
        """Test error handling when client creation fails"""
        from server.workspace_factory import create_workspace_client
        
        # Make WorkspaceClient raise an exception
        mock_workspace_client.side_effect = Exception("Connection failed")
        
        # Create client should handle the error gracefully
        client = create_workspace_client()
        
        # Should return None on failure
        assert client is None
    
    @patch('server.workspace_factory.WorkspaceClient')
    def test_get_or_create_client_singleton(self, mock_workspace_client):
        """Test that get_or_create_client returns singleton"""
        from server.workspace_factory import get_or_create_client, reset_client
        
        # Reset any existing client
        reset_client()
        
        # First call creates client
        client1 = get_or_create_client()
        assert mock_workspace_client.call_count == 1
        
        # Second call returns same client
        client2 = get_or_create_client()
        assert mock_workspace_client.call_count == 1  # Not called again
        assert client1 == client2
    
    @patch('server.workspace_factory.WorkspaceClient')
    def test_reset_client(self, mock_workspace_client):
        """Test resetting the cached client"""
        from server.workspace_factory import get_or_create_client, reset_client
        
        # Reset any existing client first
        reset_client()
        
        # Create initial client
        client1 = get_or_create_client()
        assert mock_workspace_client.call_count == 1
        
        # Reset client
        reset_client()
        
        # Next call creates new client
        client2 = get_or_create_client()
        assert mock_workspace_client.call_count == 2
        assert client2 == mock_workspace_client.return_value
    
    def test_create_client_with_custom_config(self):
        """Test creating client with custom configuration"""
        from server.workspace_factory import create_workspace_client
        
        config = {
            'profile': 'custom-profile',
            'host': 'https://custom.databricks.com',
            'token': 'custom-token'
        }
        
        with patch('server.workspace_factory.WorkspaceClient') as mock_client:
            # Test with profile in config
            client = create_workspace_client({'profile': 'custom-profile'})
            mock_client.assert_called_once_with(profile='custom-profile')
            
            # Reset mock
            mock_client.reset_mock()
            
            # Test with host/token in config
            client = create_workspace_client({'host': 'https://custom.databricks.com', 'token': 'custom-token'})
            mock_client.assert_called_once_with(host='https://custom.databricks.com', token='custom-token')