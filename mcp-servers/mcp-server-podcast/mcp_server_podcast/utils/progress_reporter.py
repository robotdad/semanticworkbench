"""
Progress reporter for MCP long-running operations.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from mcp.server.fastmcp import Context


class ProgressReporter:
    """Reports progress for long-running operations."""
    
    def __init__(self, ctx: Optional[Context] = None):
        """Initialize the progress reporter.
        
        Args:
            ctx: MCP context for reporting progress
        """
        self.ctx = ctx
        self.logger = logging.getLogger("mcp-server-podcast.progress")
        self._last_percentage = 0
        self._last_report_time = 0
        self._min_report_interval = 0.5  # seconds
        
    async def report_progress(self, percentage: int, status: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Report progress to the MCP client.
        
        Args:
            percentage: Progress percentage (0-100)
            status: Status message
            details: Optional additional details
        """
        # Only report if there's a context
        if not self.ctx:
            self.logger.debug(f"Progress: {percentage}% - {status}")
            return
            
        # Avoid excessive progress reports
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self._last_report_time
        
        # Report if: 
        # 1. It's the first report (0%) or the last report (100%)
        # 2. The percentage has changed significantly (at least 5%)
        # 3. Enough time has passed since the last report
        if (percentage == 0 or percentage == 100 or 
                abs(percentage - self._last_percentage) >= 5 or
                time_since_last >= self._min_report_interval):
            
            progress_data = {
                "percentage": percentage,
                "status": status
            }
            
            if details:
                progress_data.update(details)
                
            await self.ctx.report_progress(progress_data)
            
            self._last_percentage = percentage
            self._last_report_time = current_time
    
    def create_progress_callback(self):
        """Create a callback function for progress reporting.
        
        Returns:
            A callback function that can be passed to services
        """
        async def progress_callback(percentage: int, status: str, details: Optional[Dict[str, Any]] = None):
            await self.report_progress(percentage, status, details)
        
        return progress_callback