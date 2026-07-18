import os
import time
import json
import gradio as gr
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.agent import build_agent_graph, AgentState

# Custom CSS for premium glassmorphic dark telecom theme
custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');

body, .gradio-container {
    font-family: 'Outfit', sans-serif !important;
    background: linear-gradient(135deg, #0f172a 0%, #020617 100%) !important;
    color: #e2e8f0 !important;
}

/* Glassmorphism containers */
.glass-panel {
    background: rgba(30, 41, 59, 0.45) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 16px !important;
    padding: 20px !important;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37) !important;
    transition: all 0.3s ease;
}
.glass-panel:hover {
    border-color: rgba(6, 182, 212, 0.3) !important;
    box-shadow: 0 8px 32px 0 rgba(6, 182, 212, 0.1) !important;
}

/* Header style */
.header-container {
    text-align: center;
    margin-bottom: 25px;
    padding: 30px;
    background: linear-gradient(90deg, rgba(6, 182, 212, 0.15), rgba(139, 92, 246, 0.15)) !important;
    border-radius: 20px !important;
    border: 1px solid rgba(6, 182, 212, 0.25) !important;
}
.header-title {
    font-size: 2.8rem;
    font-weight: 800;
    background: linear-gradient(to right, #22d3ee, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 5px;
    letter-spacing: -0.025em;
}
.header-subtitle {
    font-size: 1.1rem;
    color: #94a3b8;
    font-weight: 400;
}

/* Terminal Console style */
.terminal-console {
    font-family: 'JetBrains Mono', monospace !important;
    background-color: #030712 !important;
    border: 1px solid #1f2937 !important;
    border-radius: 12px !important;
    padding: 15px !important;
    color: #38bdf8 !important;
    box-shadow: inset 0 2px 10px rgba(0,0,0,0.8) !important;
}

/* Premium Buttons */
.action-btn {
    background: linear-gradient(135deg, #06b6d4 0%, #0891b2 50%, #4f46e5 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    padding: 12px 24px !important;
    box-shadow: 0 4px 15px rgba(6, 182, 212, 0.4) !important;
    cursor: pointer;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
.action-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(6, 182, 212, 0.6) !important;
}
.action-btn:active {
    transform: translateY(1px);
}

/* Telemetry Dashboard Widgets */
.telemetry-card {
    background: rgba(15, 23, 42, 0.6) !important;
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
    border-radius: 10px !important;
    padding: 12px !important;
    text-align: center;
}
.telemetry-value {
    font-size: 1.8rem;
    font-weight: 800;
    margin-top: 5px;
}
.telemetry-label {
    font-size: 0.8rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* Hide Gradio footer logo */
footer {visibility: hidden !important;}
"""

# Compile the agent graph
agent_graph = build_agent_graph()

def generate_telemetry_html(metrics: dict) -> str:
    """Generate a responsive HTML dashboard displaying current router telemetry."""
    if not metrics:
        return "<div style='color: #64748b; text-align: center; padding: 20px;'>No telemetry data loaded. Run diagnosis.</div>"
    
    status = metrics.get("status", "unknown").upper()
    status_color = "#10b981" if status == "HEALTHY" else "#f43f5e"
    
    cpu = metrics.get("cpu_usage_pct", 0)
    cpu_color = "#ef4444" if cpu > 80 else ("#f59e0b" if cpu > 50 else "#10b981")
    
    loss = metrics.get("packet_loss_pct", 0)
    loss_color = "#ef4444" if loss > 5 else ("#f59e0b" if loss > 1 else "#10b981")
    
    latency = metrics.get("latency_ms", 0)
    latency_color = "#ef4444" if latency > 100 else ("#f59e0b" if latency > 30 else "#10b981")
    
    errors_list = metrics.get("system_errors", [])
    errors_html = ""
    if errors_list:
        for err in errors_list:
            errors_html += f"<span style='display:inline-block; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); color: #fc8181; border-radius: 4px; padding: 2px 8px; margin: 4px; font-size: 0.75rem; font-family: monospace;'>{err}</span>"
    else:
        errors_html = "<span style='color: #10b981; font-size: 0.85rem;'>✅ No active faults</span>"

    html = f"""
    <div style="font-family: 'Outfit', sans-serif; background: rgba(15, 23, 42, 0.4); border-radius: 12px; padding: 16px; border: 1px solid rgba(255,255,255,0.05);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 10px;">
            <div>
                <div style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase;">Router IP Address</div>
                <div style="font-size: 1.2rem; font-weight: 800; color: #38bdf8;">{metrics.get('ip', 'N/A')}</div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase;">Device Health</div>
                <div style="font-size: 1.1rem; font-weight: 800; color: {status_color};">{status}</div>
            </div>
        </div>
        
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px;">
            <div style="background: rgba(2, 6, 17, 0.4); border: 1px solid rgba(255,255,255,0.02); border-radius: 8px; padding: 10px; text-align: center;">
                <div style="font-size: 0.75rem; color: #94a3b8;">Latency</div>
                <div style="font-size: 1.3rem; font-weight: 800; color: {latency_color};">{latency} <span style="font-size: 0.8rem; font-weight: 400; color: #94a3b8;">ms</span></div>
            </div>
            <div style="background: rgba(2, 6, 17, 0.4); border: 1px solid rgba(255,255,255,0.02); border-radius: 8px; padding: 10px; text-align: center;">
                <div style="font-size: 0.75rem; color: #94a3b8;">Packet Loss</div>
                <div style="font-size: 1.3rem; font-weight: 800; color: {loss_color};">{loss} <span style="font-size: 0.8rem; font-weight: 400; color: #94a3b8;">%</span></div>
            </div>
            <div style="background: rgba(2, 6, 17, 0.4); border: 1px solid rgba(255,255,255,0.02); border-radius: 8px; padding: 10px; text-align: center;">
                <div style="font-size: 0.75rem; color: #94a3b8;">CPU Usage</div>
                <div style="font-size: 1.3rem; font-weight: 800; color: {cpu_color};">{cpu} <span style="font-size: 0.8rem; font-weight: 400; color: #94a3b8;">%</span></div>
            </div>
        </div>
        
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 16px;">
            <div style="background: rgba(2, 6, 17, 0.2); border-radius: 6px; padding: 8px 12px; font-size: 0.85rem;">
                <span style="color: #64748b;">DNS State:</span> <b style="color: {'#10b981' if metrics.get('dns_resolution') == 'success' else '#ef4444'}">{metrics.get('dns_resolution', 'unknown').upper()}</b>
            </div>
            <div style="background: rgba(2, 6, 17, 0.2); border-radius: 6px; padding: 8px 12px; font-size: 0.85rem;">
                <span style="color: #64748b;">Active NAT:</span> <b style="color: #cbd5e1;">{metrics.get('active_connections', 0)} sessions</b>
            </div>
        </div>
        
        <div style="margin-top: 10px;">
            <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 6px; text-transform: uppercase;">Active Alerts & Fault Logs</div>
            <div style="display: flex; flex-wrap: wrap;">
                {errors_html}
            </div>
        </div>
    </div>
    """
    return html

def run_agent_interactive(message: str, max_loops: int):
    """Gradio generator to run the agent step-by-step and yield updates."""
    # Validate input message
    if not message.strip():
        yield "❌ Error: Please enter a customer complaint message.", "", "No active telemetry"
        return
        
    initial_state = {
        "customer_message": message,
        "router_ip": "",
        "diagnostic_logs": {},
        "healing_actions_taken": [],
        "loop_count": 0,
        "max_loops": int(max_loops),
        "current_status": "unknown",
        "agent_reasoning": [],
        "final_response": ""
    }
    
    console_logs = []
    
    # Run the graph and stream node state updates
    try:
        console_logs.append("⚡ Starting TeleHeal Auto-Diagnosis engine...")
        yield "\n".join(console_logs), "", generate_telemetry_html({})
        
        # Step through the graph execution
        for event in agent_graph.stream(initial_state, stream_mode="updates"):
            # Inspect the node outputs
            for node_name, node_output in event.items():
                console_logs.append(f"\n▶ Running Graph Node: [{node_name.upper()}]")
                
                # Extract reasons or logs from state updates
                if "agent_reasoning" in node_output:
                    # Append new reasoning logs only
                    for r in node_output["agent_reasoning"]:
                        if r not in console_logs:
                            console_logs.append(f"  └─ {r}")
                            
                # Check for diagnostics output to show telemetry
                diagnostics = {}
                if "diagnostic_logs" in node_output:
                    diagnostics = node_output["diagnostic_logs"]
                
                # Yield intermediate logs
                yield (
                    "\n".join(console_logs), 
                    node_output.get("final_response", ""),
                    generate_telemetry_html(diagnostics) if diagnostics else gr.update()
                )
                
                time.sleep(0.4) # Add tiny pacing for aesthetic feel
                
    except Exception as e:
        console_logs.append(f"\n❌ Error during execution: {str(e)}")
        yield "\n".join(console_logs), "An internal error occurred during self-healing workflow execution.", "Error loading telemetry"

# Create Gradio interface
with gr.Blocks(theme=gr.themes.Default(), css=custom_css) as demo:
    with gr.Div(elem_classes="header-container"):
        gr.Markdown("# 📡 TeleHeal Node", elem_classes="header-title")
        gr.Markdown("Autonomous Network Troubleshooting & Self-Healing Agent powered by DeepSeek & LangGraph", elem_classes="header-subtitle")
        
    with gr.Row():
        with gr.Column(scale=4, elem_classes="glass-panel"):
            gr.Markdown("### 🛠️ Incident Triage")
            
            # Input Fields
            complaint_input = gr.Textbox(
                label="Customer Complaint / Ticket details",
                placeholder="Describe the networking issue. e.g., '192.168.1.1 is having severe slowdowns since this morning.'",
                value="My internet is extremely slow. We have packet drops at 192.168.1.1 and DNS queries are timing out.",
                lines=4
            )
            
            # Preset templates for convenience
            gr.Markdown("**Quick Diagnostic Presets** (Pre-configures mock errors)")
            with gr.Row():
                preset1 = gr.Button("🚨 192.168.1.1 - DNS Fault", size="sm")
                preset2 = gr.Button("⚠️ 10.0.0.1 - Routing Table Overflow", size="sm")
                preset3 = gr.Button("🔥 172.16.1.10 - NAT Session Exhaustion", size="sm")
                
            max_loops_slider = gr.Slider(
                minimum=1, 
                maximum=5, 
                value=3, 
                step=1, 
                label="Maximum Healing Iterations (Loop Limit)"
            )
            
            run_btn = gr.Button("⚡ Trigger Auto-Healing Agent", elem_classes="action-btn")
            
        with gr.Column(scale=6):
            with gr.Column(elem_classes="glass-panel"):
                gr.Markdown("### 📊 Live Telemetry Dashboard")
                telemetry_output = gr.HTML(value=generate_telemetry_html({}))
                
            with gr.Column(elem_classes="glass-panel", style="margin-top: 20px;"):
                gr.Markdown("### 💻 Agent Console & Resolution")
                
                with gr.Tab("Reasoning & Tool Execution Log"):
                    console_output = gr.Textbox(
                        label="LangGraph State Engine logs",
                        lines=12,
                        elem_classes="terminal-console",
                        interactive=False,
                        autoscroll=True
                    )
                
                with gr.Tab("Final Response & Resolution"):
                    final_msg_output = gr.Markdown(
                        value="*Awaiting execution...*",
                        label="Customer Output Notification"
                    )

    # Preset handlers
    def set_preset_dns():
        return "The customer router at 192.168.1.1 is experiencing severe outages. Web pages don't resolve and it returns DNS lookup errors."
    
    def set_preset_routing():
        return "Our secondary gateway at 10.0.0.1 has extremely high latency (around 200ms) and standard trace routes are timing out."
        
    def set_preset_nat():
        return "Internal customer complains that connections are failing to establish at 172.16.1.10. Router memory usage is high."

    preset1.click(fn=set_preset_dns, outputs=[complaint_input])
    preset2.click(fn=set_preset_routing, outputs=[complaint_input])
    preset3.click(fn=set_preset_nat, outputs=[complaint_input])

    # Run handler
    run_btn.click(
        fn=run_agent_interactive,
        inputs=[complaint_input, max_loops_slider],
        outputs=[console_output, final_msg_output, telemetry_output]
    )

if __name__ == "__main__":
    # Get port from environment (essential for Google Cloud Run deployment)
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting TeleHeal Web Service on port {port}...")
    demo.launch(server_name="0.0.0.0", server_port=port, share=False)
