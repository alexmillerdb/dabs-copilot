"""Authentication resolution for DABs Copilot CLI.

Handles both Databricks workspace authentication and LLM backend configuration.
"""

import os
from typing import Optional

from databricks.sdk import WorkspaceClient


class AuthenticationError(Exception):
    """Raised when authentication fails or is not configured."""

    pass


def resolve_workspace_client(
    profile: Optional[str] = None,
    host: Optional[str] = None,
    token: Optional[str] = None,
) -> WorkspaceClient:
    """
    Resolve Databricks authentication in priority order.

    Priority:
    1. Explicit profile argument
    2. Explicit host + token arguments
    3. Environment variables (DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_CONFIG_PROFILE)
    4. Auto-detect in Databricks workspace runtime
    5. Default profile in ~/.databrickscfg

    Args:
        profile: Databricks CLI profile name
        host: Databricks workspace URL
        token: Databricks access token

    Returns:
        Configured WorkspaceClient

    Raises:
        AuthenticationError: If no valid authentication method is found
    """
    try:
        if profile:
            return WorkspaceClient(profile=profile)
        if host and token:
            return WorkspaceClient(host=host, token=token)
        if host:
            return WorkspaceClient(host=host)
        # Auto-resolve from env vars, workspace runtime, or config file
        return WorkspaceClient()
    except Exception as e:
        raise AuthenticationError(
            f"Failed to authenticate with Databricks: {e}\n\n"
            "Configure authentication using one of:\n"
            "  - CLI flag: --profile <profile-name>\n"
            "  - Environment: DATABRICKS_HOST + DATABRICKS_TOKEN\n"
            "  - Config file: ~/.databrickscfg with [DEFAULT] profile\n"
            "  - OAuth: Run 'databricks auth login' first"
        ) from e


def resolve_llm_config() -> dict:
    """
    Resolve LLM backend configuration.

    Priority:
    1. Databricks FMAPI (ANTHROPIC_BASE_URL + ANTHROPIC_AUTH_TOKEN)
    2. LiteLLM proxy (LITELLM_API_BASE)
    3. Anthropic direct (ANTHROPIC_API_KEY)

    Returns:
        dict with keys:
            - backend: "databricks_fmapi", "litellm", or "anthropic"
            - api_key: API key for the backend
            - api_base: (optional) Base URL for proxy/FMAPI
            - model: (optional) Model name for Databricks FMAPI

    Raises:
        AuthenticationError: If no LLM backend is configured
    """
    # Check for Databricks FMAPI (ANTHROPIC_BASE_URL + ANTHROPIC_AUTH_TOKEN)
    anthropic_base = os.environ.get("ANTHROPIC_BASE_URL")
    anthropic_auth = os.environ.get("ANTHROPIC_AUTH_TOKEN")

    if anthropic_base and anthropic_auth:
        # DABS_MODEL takes precedence, then ANTHROPIC_MODEL, then default
        model = os.environ.get("DABS_MODEL") or os.environ.get(
            "ANTHROPIC_MODEL", "databricks-claude-sonnet-4-5"
        )
        return {
            "backend": "databricks_fmapi",
            "api_base": anthropic_base,
            "api_key": anthropic_auth,
            "model": model,
        }

    # Check for LiteLLM proxy
    litellm_base = os.environ.get("LITELLM_API_BASE")
    litellm_key = os.environ.get("LITELLM_API_KEY")

    if litellm_base:
        return {
            "backend": "litellm",
            "api_base": litellm_base,
            "api_key": litellm_key or "",
        }

    # Fall back to Anthropic direct
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_key:
        raise AuthenticationError(
            "No LLM backend configured.\n\n"
            "Set one of the following:\n"
            "  - ANTHROPIC_BASE_URL + ANTHROPIC_AUTH_TOKEN for Databricks FMAPI\n"
            "  - ANTHROPIC_API_KEY for Anthropic direct access\n"
            "  - LITELLM_API_BASE for LiteLLM proxy"
        )

    return {
        "backend": "anthropic",
        "api_key": anthropic_key,
    }


def validate_databricks_auth(
    profile: Optional[str] = None,
    host: Optional[str] = None,
) -> tuple[bool, str]:
    """
    Validate Databricks authentication without raising exceptions.

    Args:
        profile: Databricks CLI profile name
        host: Databricks workspace URL

    Returns:
        Tuple of (success, message)
    """
    try:
        client = resolve_workspace_client(profile=profile, host=host)
        # Try a simple API call to verify authentication
        user = client.current_user.me()
        return True, f"Authenticated as {user.user_name} on {client.config.host}"
    except AuthenticationError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Authentication failed: {e}"


def validate_llm_auth() -> tuple[bool, str]:
    """
    Validate LLM backend configuration without raising exceptions.

    Returns:
        Tuple of (success, message)
    """
    try:
        config = resolve_llm_config()
        if config["backend"] == "databricks_fmapi":
            return True, f"Databricks FMAPI configured: {config['api_base']} (model: {config['model']})"
        if config["backend"] == "litellm":
            return True, f"LiteLLM proxy configured: {config['api_base']}"
        return True, "Anthropic API key configured"
    except AuthenticationError as e:
        return False, str(e)


def is_running_in_databricks() -> bool:
    """Check if running inside a Databricks workspace (notebook/job)."""
    return os.environ.get("DATABRICKS_RUNTIME_VERSION") is not None


def get_workspace_url_from_env() -> Optional[str]:
    """Get workspace URL from environment if available."""
    # Check standard env var
    host = os.environ.get("DATABRICKS_HOST")
    if host:
        return host

    # Check if running in Databricks
    if is_running_in_databricks():
        # In Databricks runtime, workspace URL is available via spark conf or env
        notebook_path = os.environ.get("DATABRICKS_NOTEBOOK_PATH")
        if notebook_path:
            # Try to extract from notebook context
            try:
                from dbruntime.databricks_repl_context import get_context

                ctx = get_context()
                return f"https://{ctx.browserHostName}"
            except ImportError:
                pass

    return None
