"""
Tool Adapter Registry for AI Agent Platform & Sandbox.
Implements the registry pattern for pluggable tool adapters.
"""

from typing import Callable, Any
from backend.models import ToolSchema, ToolParameter


class ToolRegistry:
    """Central registry for all available tool adapters."""

    def __init__(self):
        self._tools: dict[str, dict] = {}

    def register(
        self,
        name: str,
        description: str,
        category: str,
        parameters: list[dict],
        examples: list[str],
        handler: Callable,
    ):
        """Register a tool adapter with the registry."""
        schema = ToolSchema(
            name=name,
            description=description,
            category=category,
            parameters=[ToolParameter(**p) for p in parameters],
            examples=examples,
        )
        self._tools[name] = {
            "schema": schema,
            "handler": handler,
        }

    def get_tool(self, name: str) -> dict | None:
        return self._tools.get(name)

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool by name with given arguments."""
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Tool '{name}' not found in registry."
        try:
            result = tool["handler"](**arguments)
            return str(result)
        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"

    def list_tools(self) -> list[ToolSchema]:
        return [t["schema"] for t in self._tools.values()]

    def get_tools_description(self) -> str:
        """Get a detailed formatted description of all available tools for the agent."""
        lines = []
        for tool in self._tools.values():
            schema = tool["schema"]
            lines.append(f"Tool Name: {schema.name}")
            lines.append(f"  Description: {schema.description}")
            if schema.parameters:
                lines.append("  Arguments:")
                for p in schema.parameters:
                    lines.append(f"    - {p.name} ({p.type}): {p.description}")
            if schema.examples:
                lines.append(f"  Examples: {', '.join(schema.examples)}")
            lines.append("")
        return "\n".join(lines)



# Global registry instance
registry = ToolRegistry()
