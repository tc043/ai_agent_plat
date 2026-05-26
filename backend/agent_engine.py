"""
Agent Engine for AI Agent Platform & Sandbox.
Implements a real ReAct reasoning loop using native OpenAI-compatible function calling.
Powered by Pollinations AI, OpenAI, Gemini, or Claude.
"""

import json
import time
import requests
from datetime import datetime
from typing import Optional
from backend.models import AgentStep, StepType, ToolCall, LLMConfig
from backend.tools import registry
from backend.context_manager import ContextManager
from backend.trace import TraceSystem

# Import tool modules to register them
import backend.tools.crypto
import backend.tools.calculator
import backend.tools.code_sandbox
import backend.tools.blockchain


class AgentEngine:
    """ReAct-style agent using native function calling and a real LLM."""

    def __init__(self, context_manager: ContextManager, trace_system: TraceSystem):
        self.context = context_manager
        self.traces = trace_system
        self.tool_registry = registry

    def _get_openai_tools(self) -> list[dict]:
        """Convert registered tools to OpenAI-compatible function schemas."""
        tools = []
        for name, tool_data in self.tool_registry._tools.items():
            schema = tool_data["schema"]
            properties = {}
            required = []
            
            for p in schema.parameters:
                p_type = p.type.lower().strip()
                if p_type in ("int", "integer", "float", "number"):
                    schema_type = "number"
                elif p_type in ("bool", "boolean"):
                    schema_type = "boolean"
                elif p_type in ("list", "array"):
                    schema_type = "array"
                elif p_type in ("dict", "object"):
                    schema_type = "object"
                else:
                    schema_type = "string"
                    
                properties[p.name] = {
                    "type": schema_type,
                    "description": p.description
                }
                required.append(p.name)
                
            tools.append({
                "type": "function",
                "function": {
                    "name": schema.name,
                    "description": schema.description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required
                    }
                }
            })
        return tools

    def _translate_to_claude(self, prompt_messages: list[dict], openai_tools: list[dict]) -> tuple[str, list[dict], list[dict]]:
        """Translate OpenAI message format & tools list into Anthropic Claude format."""
        system_msg = ""
        claude_messages = []
        
        for m in prompt_messages:
            role = m["role"]
            content = m.get("content", "") or ""
            
            if role == "system":
                system_msg = content
                continue
                
            if role == "user":
                claude_messages.append({"role": "user", "content": content})
            elif role == "assistant":
                content_blocks = []
                if content:
                    content_blocks.append({"type": "text", "text": content})
                if m.get("tool_calls"):
                    for tc in m["tool_calls"]:
                        func = tc["function"]
                        args_str = func["arguments"]
                        try:
                            args = json.loads(args_str) if isinstance(args_str, str) else args_str
                        except Exception:
                            args = {"args": args_str}
                        content_blocks.append({
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": func["name"],
                            "input": args
                        })
                claude_messages.append({"role": "assistant", "content": content_blocks})
            elif role == "tool":
                claude_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": m["tool_call_id"],
                        "content": content
                    }]
                })
                
        # Merge consecutive user/assistant messages to satisfy Anthropic Claude rules
        merged_messages = []
        for msg in claude_messages:
            if not merged_messages:
                merged_messages.append(msg)
                continue
            prev = merged_messages[-1]
            if prev["role"] == msg["role"]:
                if isinstance(prev["content"], str) and isinstance(msg["content"], str):
                    prev["content"] = prev["content"] + "\n" + msg["content"]
                elif isinstance(prev["content"], list) and isinstance(msg["content"], list):
                    prev["content"].extend(msg["content"])
                elif isinstance(prev["content"], str):
                    prev["content"] = [{"type": "text", "text": prev["content"]}] + (msg["content"] if isinstance(msg["content"], list) else [{"type": "text", "text": msg["content"]}])
                else:
                    prev["content"].append({"type": "text", "text": msg["content"]})
            else:
                merged_messages.append(msg)
                
        claude_tools = []
        if openai_tools:
            for t in openai_tools:
                f = t["function"]
                claude_tools.append({
                    "name": f["name"],
                    "description": f["description"],
                    "input_schema": f["parameters"]
                })
                
        return system_msg, merged_messages, claude_tools

    async def run(self, query: str, conversation_id: str, max_steps: int = 8, llm_config: Optional[LLMConfig] = None):
        """Execute the function-calling loop with selected LLM configuration."""
        step_num = 0
        openai_tools = self._get_openai_tools()
        
        # Get past conversation history (pre-formatted messages)
        past_context = self.context.get_context(conversation_id)
        
        # Messages for the current turn
        turn_messages = [{"role": "user", "content": query}]

        # 1. Parse LLM configuration routing parameters
        provider = "pollinations"
        api_key = None
        model = None
        
        if llm_config:
            provider = (llm_config.provider or "pollinations").lower().strip()
            api_key = llm_config.api_key
            model = llm_config.model

        while step_num < max_steps:
            # Throttle requests to avoid rate limits (HTTP 429) on free Pollinations
            if step_num > 0 and provider == "pollinations":
                time.sleep(1.5)
                
            # Combine history with current turn
            prompt_messages = past_context + turn_messages

            start_time = time.time()
            
            # Setup HTTP Request based on selected Provider
            url = ""
            headers = {"Content-Type": "application/json"}
            payload = {}

            if provider == "openai":
                url = "https://api.openai.com/v1/chat/completions"
                headers["Authorization"] = f"Bearer {api_key or ''}"
                payload = {
                    "model": model or "gpt-4o",
                    "messages": prompt_messages
                }
                if openai_tools:
                    payload["tools"] = openai_tools
                    
            elif provider == "gemini":
                # Google's official OpenAI-compatible endpoint
                url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
                headers["Authorization"] = f"Bearer {api_key or ''}"
                payload = {
                    "model": model or "gemini-3.1-flash-lite",
                    "messages": prompt_messages
                }
                if openai_tools:
                    payload["tools"] = openai_tools
                    
            elif provider == "claude":
                system_msg, claude_messages, claude_tools = self._translate_to_claude(prompt_messages, openai_tools)
                url = "https://api.anthropic.com/v1/messages"
                headers = {
                    "x-api-key": api_key or "",
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                payload = {
                    "model": model or "claude-3-5-sonnet-20241022",
                    "messages": claude_messages,
                    "max_tokens": 4096
                }
                if system_msg:
                    payload["system"] = system_msg
                if claude_tools:
                    payload["tools"] = claude_tools
                    
            else: # Free Pollinations (Default)
                url = "https://text.pollinations.ai/"
                payload = {
                    "messages": prompt_messages,
                    "model": "openai"
                }
                if openai_tools:
                    payload["tools"] = openai_tools

            # Call the LLM with retry logic
            attempts = 3
            success = False
            response_text = ""
            last_err = None

            for attempt in range(attempts):
                try:
                    r = requests.post(url, headers=headers, json=payload, timeout=30)
                    if r.status_code == 200:
                        response_text = r.text.strip()
                        success = True
                        break
                    else:
                        raise Exception(f"HTTP Status {r.status_code}: {r.text}")
                except Exception as e:
                    last_err = e
                    # Avoid retrying if authentication error (401/403)
                    if getattr(e, "args", None) and any(x in str(e) for x in ("401", "403")):
                        break
                    if attempt < attempts - 1:
                        time.sleep(1.5 * (attempt + 1))
                    continue

            if not success:
                step_num += 1
                error_step = AgentStep(
                    step_number=step_num,
                    step_type=StepType.ERROR,
                    content=f"LLM API Connection Error ({provider}): {str(last_err)}. Please verify model choice, network, and API keys.",
                    latency_ms=round((time.time() - start_time) * 1000, 2),
                )
                self.traces.record(conversation_id, error_step)
                yield error_step
                break

            latency_ms = (time.time() - start_time) * 1000

            # Parse responses according to Provider
            thought = ""
            tool_calls = []
            content = ""
            thought_signature = None

            try:
                if provider == "claude":
                    data = json.loads(response_text)
                    for item in data.get("content", []):
                        if item.get("type") == "text":
                            content += item.get("text", "")
                        elif item.get("type") == "tool_use":
                            tool_calls.append({
                                "id": item.get("id"),
                                "type": "function",
                                "function": {
                                    "name": item.get("name"),
                                    "arguments": json.dumps(item.get("input"))
                                }
                            })
                    thought = content
                else: # OpenAI / Gemini / Pollinations
                    data = json.loads(response_text)
                    if "choices" in data:
                        choice = data["choices"][0]["message"]
                        choice_role = choice.get("role", "assistant")
                        thought = choice.get("content", "") or ""
                        tool_calls = choice.get("tool_calls", [])
                        content = choice.get("content", "") or ""
                        
                        # Capture thought signatures (camelCase, snake_case, and extra_content)
                        thought_signature = choice.get("thoughtSignature") or choice.get("thought_signature")
                        if not thought_signature:
                            choice_extra = choice.get("extra_content") or {}
                            choice_google = choice_extra.get("google") or {}
                            thought_signature = choice_google.get("thought_signature") or choice_google.get("thoughtSignature")
                            
                        if not thought_signature and tool_calls:
                            first_tc = tool_calls[0]
                            # Try from extra_content -> google -> thought_signature
                            tc_extra = first_tc.get("extra_content") or {}
                            tc_google = tc_extra.get("google") or {}
                            thought_signature = tc_google.get("thought_signature") or tc_google.get("thoughtSignature")
                            
                            if not thought_signature:
                                thought_signature = first_tc.get("thoughtSignature") or first_tc.get("thought_signature")
                            if not thought_signature and "function" in first_tc:
                                func_obj = first_tc["function"]
                                thought_signature = func_obj.get("thoughtSignature") or func_obj.get("thought_signature")
                                if not thought_signature:
                                    func_extra = func_obj.get("extra_content") or {}
                                    func_google = func_extra.get("google") or {}
                                    thought_signature = func_google.get("thought_signature") or func_google.get("thoughtSignature")
                    else: # Pollinations custom format
                        thought = data.get("reasoning", "") or data.get("thought", "")
                        tool_calls = data.get("tool_calls", [])
                        content = data.get("content", "")
                        
                    if not thought_signature:
                        thought_signature = data.get("thoughtSignature") or data.get("thought_signature")
                        if not thought_signature:
                            data_extra = data.get("extra_content") or {}
                            data_google = data_extra.get("google") or {}
                            thought_signature = data_google.get("thought_signature") or data_google.get("thoughtSignature")
                    
                    # Safety fallback for Gemini API validation
                    if not thought_signature and provider == "gemini":
                        thought_signature = "skip_thought_signature_validator"
            except Exception:
                # Plain text fallback
                thought = ""
                tool_calls = []
                content = response_text

            if not tool_calls and not content and thought:
                content = thought

            # 1. Yield Thought step if LLM provided reasoning
            if thought:
                step_num += 1
                thought_step = AgentStep(
                    step_number=step_num,
                    step_type=StepType.THOUGHT,
                    content=thought,
                    latency_ms=round(latency_ms / 2 if tool_calls or content else latency_ms, 2),
                    tokens_used=len(thought.split()),
                )
                self.traces.record(conversation_id, thought_step)
                yield thought_step

            # 2. Handle Tool Call (Action) if requested
            if tool_calls and isinstance(tool_calls, list):
                first_call = tool_calls[0]
                tc_id = first_call.get("id", f"call_{int(time.time())}")
                
                if first_call.get("type") == "function" and "function" in first_call:
                    func = first_call["function"]
                    tool_name = func.get("name")
                    args_val = func.get("arguments", "{}")
                    try:
                        tool_args = json.loads(args_val) if isinstance(args_val, str) else args_val
                    except Exception:
                        tool_args = {"args": args_val}
                else:
                    tool_name = first_call.get("name") or first_call.get("tool_name")
                    tool_args = first_call.get("arguments") or first_call.get("args") or {}
                    if isinstance(tool_args, str):
                        try:
                            tool_args = json.loads(tool_args)
                        except Exception:
                            pass

                step_num += 1
                tool_call = ToolCall(tool_name=tool_name, arguments=tool_args)
                action_str = f"Using tool: {tool_name}({json.dumps(tool_args)})"
                
                action_step = AgentStep(
                    step_number=step_num,
                    step_type=StepType.ACTION,
                    content=action_str,
                    tool_call=tool_call,
                    latency_ms=round(latency_ms / 2, 2),
                    tokens_used=len(action_str.split()),
                )
                self.traces.record(conversation_id, action_step)
                yield action_step

                # Append assistant message with tool calls and thought signature to history
                tool_call_obj = {
                    "id": tc_id,
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(tool_args)
                    }
                }
                if thought_signature:
                    # In OpenAI compatibility mode, Gemini API expects the signature in:
                    # tool_calls[*].extra_content.google.thought_signature
                    tool_call_obj["extra_content"] = {
                        "google": {
                            "thought_signature": thought_signature,
                            "thoughtSignature": thought_signature
                        }
                    }
                    tool_call_obj["thoughtSignature"] = thought_signature
                    tool_call_obj["thought_signature"] = thought_signature
                    tool_call_obj["function"]["thoughtSignature"] = thought_signature
                    tool_call_obj["function"]["thought_signature"] = thought_signature

                assistant_msg = {
                    "role": locals().get("choice_role", "assistant"),
                    "content": content or "",
                    "tool_calls": [tool_call_obj]
                }
                if thought_signature:
                    assistant_msg["thoughtSignature"] = thought_signature
                    assistant_msg["thought_signature"] = thought_signature
                    assistant_msg["extra_content"] = {
                        "google": {
                            "thought_signature": thought_signature,
                            "thoughtSignature": thought_signature
                        }
                    }
                turn_messages.append(assistant_msg)



                # Execute tool
                start_tool = time.time()
                observation = self.tool_registry.execute(tool_name, tool_args)
                tool_latency = (time.time() - start_tool) * 1000

                # Yield Observation step
                step_num += 1
                obs_step = AgentStep(
                    step_number=step_num,
                    step_type=StepType.OBSERVATION,
                    content=observation,
                    tool_call=tool_call,
                    tool_result=observation,
                    latency_ms=round(tool_latency, 2),
                    tokens_used=len(observation.split()),
                )
                self.traces.record(conversation_id, obs_step)
                yield obs_step

                # Append tool response to history
                turn_messages.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "name": tool_name,
                    "content": observation
                })

            # 3. Final Answer step
            else:
                step_num += 1
                final_step = AgentStep(
                    step_number=step_num,
                    step_type=StepType.FINAL_ANSWER,
                    content=content,
                    latency_ms=round(latency_ms / 2 if thought else latency_ms, 2),
                    tokens_used=len(content.split()),
                )
                self.traces.record(conversation_id, final_step)
                yield final_step

                # Update Context Manager with the full user & agent exchange
                self.context.add_message(conversation_id, "user", query)
                self.context.add_message(conversation_id, "agent", content)
                break
