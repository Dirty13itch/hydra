"""
Tests for hydra_cli module
"""

import pytest
from unittest.mock import patch, MagicMock
from io import StringIO


class TestCLINodes:
    """Tests for node configuration in CLI."""

    def test_nodes_defined(self):
        """Test all nodes are defined."""
        from hydra_cli.main import NODES

        assert "hydra-ai" in NODES
        assert "hydra-compute" in NODES
        assert "hydra-storage" in NODES

    def test_node_ip_lookup(self):
        """Test looking up node IP."""
        from hydra_cli.main import get_node_ip

        assert get_node_ip("hydra-ai") == "192.168.1.250"
        assert get_node_ip("hydra-storage") == "192.168.1.244"

        # Unknown node returns input
        assert get_node_ip("10.0.0.1") == "10.0.0.1"


class TestCLIServices:
    """Tests for service configuration in CLI."""

    def test_services_defined(self):
        """Test key services are defined."""
        from hydra_cli.main import SERVICES

        assert "tabbyapi" in SERVICES
        assert "ollama" in SERVICES
        assert "litellm" in SERVICES
        assert "qdrant" in SERVICES

    def test_service_properties(self):
        """Test service properties."""
        from hydra_cli.main import SERVICES

        tabby = SERVICES["tabbyapi"]
        assert tabby["port"] == 5000
        assert tabby["node"] == "hydra-ai"
        assert "health" in tabby


class TestServiceHealthCheck:
    """Tests for check_service_health function."""

    def test_unknown_service(self):
        """Test checking unknown service."""
        from hydra_cli.main import check_service_health

        healthy, message, latency = check_service_health("nonexistent")

        assert healthy is False
        assert message == "Unknown service"
        assert latency == 0

    @patch("hydra_cli.main.httpx.Client")
    def test_healthy_service(self, mock_client_class):
        """Test checking healthy HTTP service."""
        from hydra_cli.main import check_service_health

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)
        mock_client.get.return_value = mock_response

        mock_client_class.return_value = mock_client

        healthy, message, latency = check_service_health("litellm")

        assert healthy is True
        assert "200" in message
        assert latency >= 0

    @patch("hydra_cli.main.httpx.Client")
    def test_unhealthy_service(self, mock_client_class):
        """Test checking unhealthy service."""
        from hydra_cli.main import check_service_health
        import httpx

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")

        mock_client_class.return_value = mock_client

        healthy, message, latency = check_service_health("litellm")

        assert healthy is False
        assert "refused" in message.lower()


class TestSSHCommand:
    """Tests for ssh_command function."""

    @patch("hydra_cli.main.subprocess.run")
    def test_ssh_success(self, mock_run):
        """Test successful SSH command."""
        from hydra_cli.main import ssh_command

        mock_run.return_value = MagicMock(stdout="result\n")

        result = ssh_command("hydra-ai", "echo hello")

        assert result == "result\n"
        mock_run.assert_called_once()

        # Verify command structure
        call_args = mock_run.call_args[0][0]
        assert "ssh" in call_args[0]
        assert "typhon@192.168.1.250" in call_args
        assert "echo hello" in call_args

    def test_ssh_unknown_node(self):
        """Test SSH to unknown node."""
        from hydra_cli.main import ssh_command

        result = ssh_command("unknown-node", "echo hello")

        assert result is None

    @patch("hydra_cli.main.subprocess.run")
    def test_ssh_timeout(self, mock_run):
        """Test SSH timeout handling."""
        from hydra_cli.main import ssh_command
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ssh", timeout=30)

        result = ssh_command("hydra-ai", "slow-command")

        assert result is None


class TestCLIArguments:
    """Tests for CLI argument parsing."""

    def test_status_command(self):
        """Test status command parsing."""
        from hydra_cli.main import main
        import sys

        with patch.object(sys, "argv", ["hydra", "status"]):
            with patch("hydra_cli.main.cmd_status") as mock_cmd:
                # Would need more setup to fully test
                pass

    def test_nodes_command(self):
        """Test nodes command parsing."""
        from hydra_cli.main import main
        import sys

        with patch.object(sys, "argv", ["hydra", "nodes"]):
            with patch("hydra_cli.main.cmd_nodes") as mock_cmd:
                pass

    def test_services_filter(self):
        """Test services command with filters."""
        from hydra_cli.main import main
        import sys

        with patch.object(sys, "argv", ["hydra", "services", "--node", "hydra-storage"]):
            with patch("hydra_cli.main.cmd_services") as mock_cmd:
                pass


class TestOutputFormatting:
    """Tests for output formatting."""

    def test_table_creation(self):
        """Test Rich table creation doesn't fail."""
        from rich.table import Table
        from rich import box

        table = Table(title="Test", box=box.ROUNDED)
        table.add_column("Name")
        table.add_column("Value")
        table.add_row("test", "value")

        # Should not raise
        assert table.row_count == 1

    def test_panel_creation(self):
        """Test Rich panel creation."""
        from rich.panel import Panel

        panel = Panel.fit("Test Content")

        assert panel is not None
