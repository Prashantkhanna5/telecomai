import os
import re
import json
from typing import TypedDict, List, Dict, Any, Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from app.tools import run_router_diagnostics, apply_router_fix

# Define the State for LangGraph
class AgentState(TypedDict):
    customer_message: str
    router_ip: str
    diagnostic_logs: Dict[str, Any]
    healing_actions_taken: List[str]
    loop_count: int
    max_loops: int
    current_status: Literal["healthy", "unhealthy", "escalated", "unknown"]
    agent_reasoning: List[str]
    final_response: str

# Helper function to get the LLM client
def get_llm():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        # Fallback to simulation/mock model if no key is provided
        return None
    
    # DeepSeek API is compatible with OpenAI SDK
    # Base URL is https://api.deepseek.com/v1 or https://api.deepseek.com
    base_url = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
    model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    
    return ChatOpenAI(
        model=model_name,
        openai_api_key=api_key,
        openai_api_base=base_url,
        temperature=0.1
    )

# --- Graph Nodes ---

def triage_node(state: AgentState) -> Dict[str, Any]:
    """Analyze customer query, extract router IP, and determine target."""
    message = state["customer_message"]
    reasoning = list(state.get("agent_reasoning", []))
    reasoning.append("Node [Triage]: Analyzing customer message...")
    
    # Try regex extraction first for reliability
    ip_pattern = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
    ips = re.findall(ip_pattern, message)
    
    extracted_ip = "192.168.1.1" # Default fallback
    if ips:
        extracted_ip = ips[0]
        reasoning.append(f"Node [Triage]: Extracted IP {extracted_ip} via pattern matching.")
    else:
        # Ask LLM if key is available
        llm = get_llm()
        if llm:
            try:
                system_prompt = (
                    "You are a telecom support assistant. Extract the router or gateway IP address mentioned in the message. "
                    "Respond with ONLY the IP address. If no IP is found, respond with '192.168.1.1'."
                )
                response = llm.invoke([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=message)
                ])
                ip_str = response.content.strip()
                if re.match(ip_pattern, ip_str):
                    extracted_ip = ip_str
                    reasoning.append(f"Node [Triage]: Extracted IP {extracted_ip} using DeepSeek LLM.")
                else:
                    reasoning.append(f"Node [Triage]: LLM returned invalid IP '{ip_str}', using fallback {extracted_ip}.")
            except Exception as e:
                reasoning.append(f"Node [Triage]: LLM failed ({str(e)}), using default {extracted_ip}.")
        else:
            reasoning.append(f"Node [Triage]: DeepSeek API Key not found. Simulated/regex extracted IP: {extracted_ip}.")

    return {
        "router_ip": extracted_ip,
        "agent_reasoning": reasoning
    }

def diagnostic_node(state: AgentState) -> Dict[str, Any]:
    """Run diagnostics tool and update router status."""
    ip = state["router_ip"]
    reasoning = list(state.get("agent_reasoning", []))
    reasoning.append(f"Node [Diagnostics]: Fetching telemetry for {ip}...")
    
    logs = run_router_diagnostics(ip)
    
    errors = logs.get("system_errors", [])
    status = logs.get("status", "unknown")
    
    reasoning.append(
        f"Node [Diagnostics]: Current telemetry: Status={status}, Latency={logs.get('latency_ms')}ms, "
        f"Loss={logs.get('packet_loss_pct')}%, CPU={logs.get('cpu_usage_pct')}%, Errors={errors}"
    )
    
    return {
        "diagnostic_logs": logs,
        "current_status": status,
        "agent_reasoning": reasoning
    }

def heal_node(state: AgentState) -> Dict[str, Any]:
    """Select repair action, apply the fix, and update history."""
    ip = state["router_ip"]
    logs = state["diagnostic_logs"]
    errors = logs.get("system_errors", [])
    reasoning = list(state.get("agent_reasoning", []))
    actions_taken = list(state.get("healing_actions_taken", []))
    loop_count = state.get("loop_count", 0)
    
    reasoning.append(f"Node [Heal] (Attempt {loop_count + 1}): Finding appropriate remedy for {errors}...")
    
    action = None
    llm = get_llm()
    
    if llm:
        try:
            system_prompt = (
                "You are an automated Telecom Network Auto-Healer. Decide which action to perform to fix the router. "
                "You must choose exactly ONE action from: ['flush_dns_cache', 'clear_routing_table', 'terminate_nat_sessions', 'reboot_router']. "
                "Base your decision on system errors:\n"
                "- DNS_CACHE_CORRUPTED -> 'flush_dns_cache'\n"
                "- ROUTING_TABLE_OVERFLOW -> 'clear_routing_table'\n"
                "- EXCESSIVE_NAT_SESSIONS -> 'terminate_nat_sessions'\n"
                "- If multiple errors or persistent issues exist -> 'reboot_router'\n"
                "Respond with a JSON object format: {\"action\": \"<action_name>\", \"reasoning\": \"<explanation>\"}"
            )
            prompt = f"Router Diagnostics:\n{json.dumps(logs, indent=2)}\nAlready tried actions: {actions_taken}"
            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=prompt)
            ])
            
            # Clean response if markdown blocks are wrapped
            res_content = response.content.strip()
            if "```json" in res_content:
                res_content = res_content.split("```json")[1].split("```")[0].strip()
            elif "```" in res_content:
                res_content = res_content.split("```")[1].split("```")[0].strip()
                
            parsed = json.loads(res_content)
            action = parsed.get("action")
            reason = parsed.get("reasoning", "LLM Selected")
            reasoning.append(f"Node [Heal]: DeepSeek selected '{action}' because: {reason}")
        except Exception as e:
            reasoning.append(f"Node [Heal]: DeepSeek selection failed ({str(e)}), falling back to rule engine.")
            
    if not action:
        # Rule-based fallback/simulation selection
        if "DNS_CACHE_CORRUPTED" in errors:
            action = "flush_dns_cache"
            reasoning.append("Node [Heal]: Rule engine selected 'flush_dns_cache'.")
        elif "ROUTING_TABLE_OVERFLOW" in errors:
            action = "clear_routing_table"
            reasoning.append("Node [Heal]: Rule engine selected 'clear_routing_table'.")
        elif "EXCESSIVE_NAT_SESSIONS" in errors:
            action = "terminate_nat_sessions"
            reasoning.append("Node [Heal]: Rule engine selected 'terminate_nat_sessions'.")
        else:
            action = "reboot_router"
            reasoning.append("Node [Heal]: Rule engine selected 'reboot_router' as fallback.")
            
    # Apply fix tool
    fix_result = apply_router_fix(ip, action)
    actions_taken.append(action)
    
    reasoning.append(f"Node [Heal]: Applied action '{action}'. Result: {fix_result.get('details')}")
    
    return {
        "healing_actions_taken": actions_taken,
        "loop_count": loop_count + 1,
        "agent_reasoning": reasoning
    }

def finalize_node(state: AgentState) -> Dict[str, Any]:
    """Create final report for the customer certifying router health."""
    ip = state["router_ip"]
    logs = state["diagnostic_logs"]
    actions = state["healing_actions_taken"]
    reasoning = list(state.get("agent_reasoning", []))
    reasoning.append("Node [Finalize]: Generating customer resolution message...")
    
    llm = get_llm()
    final_msg = ""
    
    if llm:
        try:
            system_prompt = (
                "You are an empathetic, professional Telecom Customer Support Agent. Write a friendly message "
                "to the customer summarizing the network diagnosis and the actions taken to repair their router. "
                "Confirm that the device is now fully operational and running at peak performance. Keep the tone helpful "
                "and explain technical items simply. Include metrics if appropriate."
            )
            prompt = (
                f"Customer Query: {state['customer_message']}\n"
                f"Router IP: {ip}\n"
                f"Actions Applied: {actions}\n"
                f"Final Telemetry: {json.dumps(logs, indent=2)}"
            )
            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=prompt)
            ])
            final_msg = response.content.strip()
        except Exception as e:
            reasoning.append(f"Node [Finalize]: LLM response generation failed ({str(e)}). Using template fallback.")
            
    if not final_msg:
        # Standard fallback template
        final_msg = (
            f"Dear Customer,\n\n"
            f"Thank you for reaching out to us. We have completed our remote diagnostic checks on your router "
            f"({ip}) and resolved the issue.\n\n"
            f"**Diagnostic Findings:**\n"
            f"- We detected telemetry discrepancies including packet loss and slow dns response times.\n\n"
            f"**Resolution Steps Applied:**\n"
            + "\n".join([f"- Successfully ran configuration patch: `{act.replace('_', ' ').title()}`" for act in actions]) +
            f"\n\n**Current Router Telemetry:**\n"
            f"- Connection status: **Active & Healthy**\n"
            f"- Latency: {logs.get('latency_ms')} ms\n"
            f"- Packet Loss: {logs.get('packet_loss_pct')}%\n\n"
            f"Your system is now operating within normal parameters. If you experience further issues, please let us know!"
        )
        
    reasoning.append("Node [Finalize]: Completed workflow.")
    return {
        "final_response": final_msg,
        "agent_reasoning": reasoning
    }

def escalate_node(state: AgentState) -> Dict[str, Any]:
    """Escalate to tier-2 support when automated repair fails."""
    ip = state["router_ip"]
    logs = state["diagnostic_logs"]
    actions = state["healing_actions_taken"]
    reasoning = list(state.get("agent_reasoning", []))
    reasoning.append("Node [Escalate]: Automated repair threshold exceeded. Initiating engineer dispatch...")
    
    escalation_ticket = (
        f"⚠️ **Tier-2 Escalation Alert** ⚠️\n\n"
        f"**Target System:** Router IP `{ip}`\n"
        f"**Diagnostics Summary:**\n"
        f"- Connection State: `{logs.get('connection_state')}`\n"
        f"- Persistent Errors: {logs.get('system_errors')}\n"
        f"- Latency: {logs.get('latency_ms')}ms | Packet Loss: {logs.get('packet_loss_pct')}%\n\n"
        f"**Automated Repairs Attempted:**\n"
        + "\n".join([f"- `{act}`" for act in actions]) +
        f"\n\n**Result:** Target remains degraded after {state.get('loop_count')} healing iterations. "
        f"Device requires physical engineering inspection or manual provisioning override."
    )
    
    customer_msg = (
        f"Hello. We ran standard automated troubleshooting steps on your device ({ip}) "
        f"but were unable to fully resolve the degradation remotely.\n\n"
        f"We have escalated this issue to our Tier-2 Technical Engineering team. A network technician "
        f"has been assigned to inspect the routing node. We apologize for the inconvenience and will update you "
        f"as soon as we have a resolution."
    )
    
    reasoning.append("Node [Escalate]: Escalation ticket created.")
    return {
        "final_response": f"{customer_msg}\n\n---\n\n{escalation_ticket}",
        "agent_reasoning": reasoning
    }

# --- Conditional Router / Loop Logic ---

def should_continue(state: AgentState) -> Literal["heal", "finalize", "escalate"]:
    """Conditional router that determines if we loop, resolve, or escalate."""
    status = state["current_status"]
    loop_count = state["loop_count"]
    max_loops = state["max_loops"]
    
    if status == "healthy":
        return "finalize"
    
    if loop_count >= max_loops:
        return "escalate"
    
    return "heal"

# --- Graph Definition ---

def build_agent_graph() -> StateGraph:
    """Build and compile the LangGraph workflow."""
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("triage", triage_node)
    workflow.add_node("diagnose", diagnostic_node)
    workflow.add_node("heal", heal_node)
    workflow.add_node("finalize", finalize_node)
    workflow.add_node("escalate", escalate_node)
    
    # Set Entry Point
    workflow.set_entry_point("triage")
    
    # Define normal edges
    workflow.add_edge("triage", "diagnose")
    
    # Define conditional edges from diagnose
    workflow.add_conditional_edges(
        "diagnose",
        should_continue,
        {
            "heal": "heal",
            "finalize": "finalize",
            "escalate": "escalate"
        }
    )
    
    # Heal node loops back to diagnose
    workflow.add_edge("heal", "diagnose")
    
    # Leaf nodes go to END
    workflow.add_edge("finalize", END)
    workflow.add_edge("escalate", END)
    
    return workflow.compile()

def run_telecom_agent(customer_message: str, max_loops: int = 3) -> Dict[str, Any]:
    """Execute the compiled LangGraph workflow with input customer query."""
    graph = build_agent_graph()
    initial_state = {
        "customer_message": customer_message,
        "router_ip": "",
        "diagnostic_logs": {},
        "healing_actions_taken": [],
        "loop_count": 0,
        "max_loops": max_loops,
        "current_status": "unknown",
        "agent_reasoning": [],
        "final_response": ""
    }
    
    # Run the graph synchronously
    final_output = graph.invoke(initial_state)
    return final_output
