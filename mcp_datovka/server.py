"""MCP server for Czech ISDS (datove schranky)."""

import logging
from mcp.server.fastmcp import FastMCP

from .tools.datovka import register_tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP(name="mcp-datovka")

register_tools(mcp)

logger.info("mcp-datovka server initialized")
