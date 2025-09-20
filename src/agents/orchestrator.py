"""Orchestrator agent - main routing and coordination with natural language understanding"""
import re
import logging
from typing import Optional, Dict, Any, List, Tuple
from agents.base import BaseAgent
from tools.mcp_client import DatabricksMCPClient
from config.settings import get_settings

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """Main orchestrator agent with natural language understanding"""
    
    def __init__(self):
        super().__init__("orchestrator")
        self.settings = get_settings()
        self.mcp_client = DatabricksMCPClient(mode=self.settings.mcp_mode)
        self._init_patterns()
    
    def _init_patterns(self):
        """Initialize natural language patterns for command matching"""
        self.patterns = {
            'list_jobs': [
                r'list\s+(?:all\s+)?(?:the\s+)?jobs?',
                r'show\s+(?:me\s+)?(?:all\s+)?(?:the\s+)?jobs?',
                r'what\s+jobs?\s+(?:are\s+)?(?:there|available|exist)',
                r'get\s+(?:all\s+)?jobs?\s+list',
                r'display\s+jobs?',
                r'jobs?\s+in\s+(?:my\s+)?workspace',
            ],
            'get_job': [
                r'(?:get|show|display|fetch|retrieve)\s+job\s+(?:id\s+)?(\d+)',
                r'job\s+(\d+)\s+(?:details|info|information)',
                r'(?:what\s+is|describe|tell\s+me\s+about)\s+job\s+(\d+)',
                r'(?:details|info|information)\s+(?:for|about|on)\s+job\s+(\d+)',
            ],
            'list_notebooks': [
                r'list\s+(?:all\s+)?(?:the\s+)?notebooks?',
                r'show\s+(?:me\s+)?(?:all\s+)?(?:the\s+)?notebooks?',
                r'what\s+notebooks?\s+(?:are\s+)?(?:there|available|exist)',
                r'get\s+(?:all\s+)?notebooks?\s+list',
                r'notebooks?\s+in\s+(?:my\s+)?workspace',
            ],
            'generate_bundle': [
                r'(?:generate|create|build|make)\s+(?:a\s+)?(?:dab|bundle|asset\s+bundle).*?(?:from|for)\s+job\s+(\d+)',
                r'(?:convert|transform)\s+job\s+(\d+)\s+(?:to|into)\s+(?:a\s+)?(?:dab|bundle)',
                r'job\s+(\d+)\s+to\s+(?:dab|bundle)',
                r'(?:dab|bundle)\s+(?:from|for)\s+job\s+(\d+)',
            ],
            'analyze': [
                r'analyze\s+(?:the\s+)?(?:job|notebook|pipeline)\s+(?:id\s+)?(\d+|\S+)',
                r'(?:what\s+does|explain)\s+(?:job|notebook)\s+(?:id\s+)?(\d+|\S+)\s+do',
                r'(?:review|inspect|examine)\s+(?:job|notebook)\s+(?:id\s+)?(\d+|\S+)',
            ],
            'help': [
                r'help',
                r'what\s+can\s+you\s+do',
                r'(?:show|list)\s+(?:available\s+)?commands?',
                r'how\s+(?:do\s+i|to)\s+use',
                r'(?:get\s+)?started',
            ]
        }
    
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
    
    def _match_pattern(self, text: str, pattern_group: str) -> Optional[Tuple[bool, Optional[str]]]:
        """Match text against a group of patterns"""
        text_lower = text.lower().strip()
        
        for pattern in self.patterns.get(pattern_group, []):
            match = re.search(pattern, text_lower)
            if match:
                # Return match and any captured group (like ID)
                if match.groups():
                    return True, match.group(1)
                return True, None
        
        return False, None
    
    async def handle_request(self, request: str) -> str:
        """Route and handle user requests with natural language understanding"""
        request_clean = request.strip()
        
        try:
            # Check for help request
            if self._match_pattern(request_clean, 'help')[0]:
                return self._enhanced_help_message()
            
            # Check for list jobs
            if self._match_pattern(request_clean, 'list_jobs')[0]:
                return await self._handle_list_jobs()
            
            # Check for get specific job
            matched, job_id = self._match_pattern(request_clean, 'get_job')
            if matched and job_id:
                return await self._handle_get_job(int(job_id))
            
            # Check for list notebooks
            if self._match_pattern(request_clean, 'list_notebooks')[0]:
                return await self._handle_list_notebooks()
            
            # Check for generate bundle
            matched, job_id = self._match_pattern(request_clean, 'generate_bundle')
            if matched and job_id:
                return await self._handle_generate_bundle_from_job(int(job_id))
            
            # Check for analyze request
            matched, identifier = self._match_pattern(request_clean, 'analyze')
            if matched and identifier:
                return await self._handle_analyze(identifier)
            
            # If no patterns match, try to understand intent
            return await self._handle_natural_language(request_clean)
            
        except Exception as e:
            logger.error(f"Error handling request '{request}': {e}")
            return f"I encountered an error processing your request: {str(e)}\n\nPlease try rephrasing or type 'help' for available commands."
    
    async def _handle_list_jobs(self) -> str:
        """Handle job listing requests"""
        result = await self.mcp_client.list_jobs(limit=20)
        
        if result.get("success"):
            jobs_data = result.get("data", {})
            if isinstance(jobs_data, dict) and "jobs" in jobs_data:
                jobs = jobs_data["jobs"]
                job_count = len(jobs)
                
                if job_count == 0:
                    return "📂 No jobs found in your workspace."
                
                response = f"📋 Found {job_count} job{'s' if job_count != 1 else ''} in your workspace:\n\n"
                for i, job in enumerate(jobs[:10], 1):
                    job_name = job.get('settings', {}).get('name', 'Unnamed')
                    job_id = job.get('job_id', 'Unknown')
                    response += f"  {i}. {job_name} (ID: {job_id})\n"
                
                if job_count > 10:
                    response += f"\n  ... and {job_count - 10} more"
                
                response += "\n\n💡 Tip: Use 'get job <id>' for details or 'create bundle from job <id>' to generate a DAB"
                return response
            
            return "✅ Job list retrieved successfully"
        
        return f"❌ Failed to list jobs: {result.get('error', 'Unknown error')}"
    
    async def _handle_get_job(self, job_id: int) -> str:
        """Handle specific job requests"""
        result = await self.mcp_client.get_job(job_id)
        
        if result.get("success"):
            job_data = result.get("data", {})
            if isinstance(job_data, dict):
                settings = job_data.get('settings', {})
                name = settings.get('name', 'Unnamed')
                
                response = f"📊 Job Details: {name}\n"
                response += f"{'=' * 40}\n"
                response += f"ID: {job_id}\n"
                
                # Extract key information
                if 'tasks' in settings:
                    response += f"Tasks: {len(settings['tasks'])} task(s)\n"
                
                if 'schedule' in settings:
                    response += f"Schedule: {settings['schedule'].get('quartz_cron_expression', 'Not scheduled')}\n"
                
                if 'max_concurrent_runs' in settings:
                    response += f"Max concurrent runs: {settings['max_concurrent_runs']}\n"
                
                response += "\n💡 Next steps:\n"
                response += f"  • Generate DAB: 'create bundle from job {job_id}'\n"
                response += f"  • Analyze job: 'analyze job {job_id}'"
                
                return response
            
            return f"✅ Retrieved details for job {job_id}"
        
        return f"❌ Failed to get job {job_id}: {result.get('error', 'Unknown error')}"
    
    async def _handle_list_notebooks(self) -> str:
        """Handle notebook listing requests"""
        result = await self.mcp_client.list_notebooks(path="/", recursive=False)
        
        if result.get("success"):
            return "📓 Notebook list retrieved successfully"
        
        return f"❌ Failed to list notebooks: {result.get('error', 'Unknown error')}"
    
    async def _handle_generate_bundle_from_job(self, job_id: int) -> str:
        """Handle bundle generation from job"""
        result = await self.mcp_client.generate_bundle_from_job(
            job_id=job_id,
            bundle_name=f"job-{job_id}-bundle"
        )
        
        if result.get("success"):
            return f"""🎉 Successfully generated bundle for job {job_id}!

Bundle Details:
• Name: job-{job_id}-bundle
• Target: dev environment
• Status: Ready for deployment

Next steps:
1. Validate bundle: 'validate bundle job-{job_id}-bundle'
2. Deploy to dev: 'deploy bundle job-{job_id}-bundle'
3. View bundle: 'show bundle job-{job_id}-bundle'
"""
        
        return f"❌ Failed to generate bundle: {result.get('error', 'Unknown error')}"
    
    async def _handle_analyze(self, identifier: str) -> str:
        """Handle analysis requests"""
        # Check if it's a job ID
        if identifier.isdigit():
            result = await self.mcp_client.get_job(int(identifier))
            if result.get("success"):
                return f"🔍 Analyzing job {identifier}...\n\nThis job appears to be a data processing workflow. Use 'generate bundle from job {identifier}' to convert it to a DAB."
        
        # Otherwise treat as notebook path
        result = await self.mcp_client.analyze_notebook(notebook_path=identifier)
        if result.get("success"):
            return f"🔍 Analysis of {identifier} complete. Ready for bundle generation."
        
        return f"❌ Could not analyze {identifier}"
    
    async def _handle_natural_language(self, request: str) -> str:
        """Handle requests that don't match specific patterns"""
        request_lower = request.lower()
        
        # Try to understand intent from keywords
        if any(word in request_lower for word in ['job', 'jobs', 'workflow', 'task']):
            return """I understand you're asking about jobs. Here are some things I can help with:

• 'show me all jobs' - List all jobs in your workspace
• 'what is job 123?' - Get details about a specific job
• 'create a bundle from job 123' - Generate a DAB from an existing job

What would you like to do?"""
        
        if any(word in request_lower for word in ['bundle', 'dab', 'asset']):
            return """I can help you with Databricks Asset Bundles (DABs):

• 'generate bundle from job 123' - Create a DAB from an existing job
• 'list my jobs' - See available jobs to convert
• 'analyze job 123' - Review a job before conversion

Which job would you like to work with?"""
        
        if any(word in request_lower for word in ['notebook', 'code', 'script']):
            return """I can help with notebooks and code:

• 'list notebooks' - Show notebooks in your workspace
• 'analyze notebook /path/to/notebook' - Analyze a notebook
• 'create bundle from notebook' - Generate a DAB from notebook

What would you like to explore?"""
        
        # Default fallback
        return self._enhanced_help_message()
    
    def _enhanced_help_message(self) -> str:
        """Return enhanced help message with natural language examples"""
        return """🤖 Databricks Asset Bundle Assistant

I understand natural language! Try asking me:

📋 **Job Management**
• "Show me all my jobs"
• "What jobs are available?"
• "Tell me about job 123"
• "Get details for job 456"

📦 **Bundle Generation**
• "Create a bundle from job 123"
• "Convert job 456 to a DAB"
• "Generate an asset bundle for job 789"

📓 **Notebooks & Code**
• "List all notebooks"
• "Show my notebooks"
• "Analyze notebook /Users/me/analysis"

🔍 **Analysis**
• "Analyze job 123"
• "Review my ETL job"
• "Examine notebook structure"

💡 **Examples:**
• "I want to create a DAB from job 188317192422679"
• "Show me what job 123 does"
• "List all the jobs in my workspace"

Just describe what you need in your own words!"""