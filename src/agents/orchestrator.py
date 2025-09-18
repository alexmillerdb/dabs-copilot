"""Orchestrator agent - main routing and coordination"""
import re
import logging
from typing import Optional
from agents.base import BaseAgent
from tools.mcp_client import DatabricksMCPClient
from config.settings import get_settings

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """Main orchestrator agent following Chief of Staff pattern"""
    
    def __init__(self):
        super().__init__("orchestrator")
        self.settings = get_settings()
        self.mcp_client = DatabricksMCPClient(mode=self.settings.mcp_mode)
    
    def _create_client(self):
        """Create Claude SDK client"""
        if not self.settings.claude_api_key:
            return None
        
        try:
            from claude_code_sdk import ClaudeSDKClient
            return ClaudeSDKClient()
        except ImportError:
            logger.warning("Claude Code SDK not available")
            return None
    
    async def handle_request(self, request: str) -> str:
        """Route and handle user requests"""
        request_lower = request.lower().strip()
        
        try:
            # Simple routing based on keywords
            if "list jobs" in request_lower:
                return await self._handle_list_jobs()
            
            # Extract job ID from requests like "get job 123"
            job_match = re.search(r"get job (\d+)", request_lower)
            if job_match:
                job_id = int(job_match.group(1))
                return await self._handle_get_job(job_id)
            
            # Generate bundle requests
            if "generate bundle" in request_lower:
                return await self._handle_generate_bundle(request)
            
            # Default response
            return self._help_message()
            
        except Exception as e:
            logger.error(f"Error handling request '{request}': {e}")
            return f"Error processing request: {str(e)}"
    
    async def _handle_list_jobs(self) -> str:
        """Handle job listing requests"""
        result = await self.mcp_client.list_jobs(limit=10)
        
        if result.get("success"):
            jobs_data = result.get("data", {})
            if isinstance(jobs_data, dict) and "jobs" in jobs_data:
                job_count = len(jobs_data["jobs"])
                return f"Found {job_count} jobs in your workspace"
            return "Job list retrieved successfully"
        
        return f"Failed to list jobs: {result.get('error', 'Unknown error')}"
    
    async def _handle_get_job(self, job_id: int) -> str:
        """Handle specific job requests"""
        result = await self.mcp_client.get_job(job_id)
        
        if result.get("success"):
            return f"Retrieved details for job {job_id}"
        
        return f"Failed to get job {job_id}: {result.get('error', 'Unknown error')}"
    
    async def _handle_generate_bundle(self, request: str) -> str:
        """Handle bundle generation requests"""
        # Extract job ID if mentioned
        job_match = re.search(r"job (\d+)", request.lower())
        if job_match:
            job_id = int(job_match.group(1))
            result = await self.mcp_client.generate_bundle_from_job(
                job_id=job_id,
                bundle_name=f"job-{job_id}-bundle"
            )
            
            if result.get("success"):
                return f"Generated bundle for job {job_id}"
            return f"Failed to generate bundle: {result.get('error', 'Unknown error')}"
        
        return "Please specify a job ID for bundle generation (e.g., 'generate bundle from job 123')"
    
    def _help_message(self) -> str:
        """Return help message for available commands"""
        return """Available commands:
• list jobs - List all jobs in workspace
• get job <id> - Get details for specific job
• generate bundle from job <id> - Create DAB from existing job

Example: "generate bundle from job 123"
"""