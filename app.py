import os
import json
import requests
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

# Import frontend client helpers and styles loader
from utils import (
    API_URL,
    load_custom_css,
    upload_file_to_backend,
    delete_file_from_backend,
    get_documents_from_backend,
    get_briefings_from_backend,
    get_briefing_content,
    get_indexing_status_from_backend
)

# Load environment configuration and retrieve key
load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY", "")

# Page configuration
st.set_page_config(
    page_title="Multi-Agent Research Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Glassmorphic Styles Injection
load_custom_css()

# Initialize Session State
if "selected_briefing_name" not in st.session_state:
    st.session_state.selected_briefing_name = ""
if "selected_briefing_content" not in st.session_state:
    st.session_state.selected_briefing_content = ""
if "selected_briefing_plan" not in st.session_state:
    st.session_state.selected_briefing_plan = []
if "indexing_logs" not in st.session_state:
    st.session_state.indexing_logs = []
if "show_logs" not in st.session_state:
    st.session_state.show_logs = False

# ----------------------------------------------------
# 1. Sidebar Interface (Document Library Control)
# ----------------------------------------------------
with st.sidebar:
    st.markdown('<div class="logo-area" style="display:flex;align-items:center;gap:10px;margin-bottom:15px;"><span style="font-size:28px;">🤖</span><h2 style="margin:0;font-size:20px;">Control Panel</h2></div>', unsafe_allow_html=True)
    
    # Document Library Management
    st.markdown("### Document Library")
    uploaded_files = st.file_uploader(
        "Index local files for RAG",
        type=["pdf", "txt", "md", "json", "csv"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )
    
    if uploaded_files:
        if st.button("⚡ Index Uploaded Files", use_container_width=True):
            ret = upload_file_to_backend(uploaded_files)
            if "error" in ret:
                st.error(f"Upload failed: {ret['error']}")
            else:
                st.session_state.show_logs = True
                st.session_state.indexing_logs = []
                st.rerun()

    if st.session_state.show_logs:
        st.info("Files uploaded! Tracking background indexing...")
        import time
        log_placeholder = st.empty()
        
        while True:
            status = get_indexing_status_from_backend()
            logs = status.get("logs", [])
            is_indexing = status.get("is_indexing", False)
            
            if logs:
                st.session_state.indexing_logs = logs
            
            terminal_logs = []
            for msg in st.session_state.indexing_logs:
                terminal_logs.append(f'<span style="color:#a9ff9f;">&gt;&gt;</span> {msg}')
            
            terminal_html = f'<div class="terminal-container" style="height: 180px; font-size:11px; font-family:monospace; background-color:#1e1e1e; padding:8px; border-radius:4px; overflow-y:auto; color:#d4d4d4; margin-bottom:10px;">{"<br>".join(terminal_logs)}</div>'
            log_placeholder.markdown(terminal_html, unsafe_allow_html=True)
            
            if not is_indexing and len(st.session_state.indexing_logs) > 0:
                st.success("Indexing completed successfully!")
                st.session_state.show_logs = False
                time.sleep(2.0)
                st.rerun()
                break
            
            time.sleep(0.5)
            
    # Display persisted logs after completion
    elif st.session_state.indexing_logs:
        terminal_logs = []
        for msg in st.session_state.indexing_logs:
            terminal_logs.append(f'<span style="color:#a9ff9f;">&gt;&gt;</span> {msg}')
        terminal_html = f'<div class="terminal-container" style="height: 180px; font-size:11px; font-family:monospace; background-color:#1e1e1e; padding:8px; border-radius:4px; overflow-y:auto; color:#d4d4d4; margin-bottom:10px;">{"<br>".join(terminal_logs)}</div>'
        st.markdown("<p style='font-size:12px;color:var(--text-secondary);font-weight:600;margin-bottom:6px;'>LAST INDEXING LOGS</p>", unsafe_allow_html=True)
        st.markdown(terminal_html, unsafe_allow_html=True)
                
    # Display List of indexed files
    docs = get_documents_from_backend()
    if docs:
        st.markdown("<p style='font-size:12px;color:var(--text-secondary);font-weight:600;margin-bottom:6px;'>INDEXED CORPUS</p>", unsafe_allow_html=True)
        for doc in docs:
            col_name, col_del = st.columns([4, 1])
            kb_size = round(doc['size'] / 1024, 1)
            col_name.markdown(f"<span style='font-size:12px;' title='{doc['name']}'>📄 {doc['name'][:20]}... ({kb_size} KB)</span>", unsafe_allow_html=True)
            if col_del.button("🗑️", key=f"del_{doc['name']}"):
                delete_file_from_backend(doc['name'])
                st.rerun()
    else:
        st.info("Document library is empty. Upload files above to enable RAG.")

# ----------------------------------------------------
# 2. Main Dashboard Interface (Research Trigger)
# ----------------------------------------------------
st.markdown('<h1 class="title-gradient">Multi-Agent Research Assistant</h1>', unsafe_allow_html=True)
st.markdown('<div class="status-badge"><span class="status-pulse"></span> Multi-Agent RAG Connected (Gemini Node)</div>', unsafe_allow_html=True)

# Run Research Query card
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
topic = st.text_input("What topics do you want to research?", placeholder="Enter topic (e.g. 'Project Antigravity latency guidelines and secure offline operation policies')")
btn_run = st.button("Synthesize Briefing")
st.markdown('</div>', unsafe_allow_html=True)

if btn_run:
    if not topic.strip():
        st.warning("Please enter a research topic first.")
    else:
        st.session_state.selected_briefing_plan = [] # Clear previous plan
        st.markdown("### Orchestration Progress")
        
        # 1. Pipeline steps indicators placeholders
        col1, col2, col3, col4 = st.columns(4)
        step_idx = col1.empty()
        step_plan = col2.empty()
        step_res = col3.empty()
        step_wri = col4.empty()
        
        # Draw initial pending states
        step_idx.markdown('<div class="step-badge">1. Ingesting & Indexing</div>', unsafe_allow_html=True)
        step_plan.markdown('<div class="step-badge">2. Planner Agent</div>', unsafe_allow_html=True)
        step_res.markdown('<div class="step-badge">3. Researcher (RAG)</div>', unsafe_allow_html=True)
        step_wri.markdown('<div class="step-badge">4. Writer Synthesis</div>', unsafe_allow_html=True)
        
        # Plan list and live logs placeholders
        plan_container = st.empty()
        st.markdown("#### Execution Terminal Output")
        log_terminal = st.empty()
        
        # Trigger Backend Research Job
        payload = {"topic": topic}
        if gemini_key.strip():
            payload["api_key"] = gemini_key
            
        try:
            res = requests.post(f"{API_URL}/api/research", json=payload)
            if res.status_code != 200:
                st.error(f"Backend failed to trigger task: {res.text}")
            else:
                task_id = res.json()["task_id"]
                
                # Connect to log stream using HTTP client iteration (SSE style)
                log_lines = []
                stream_res = requests.get(f"{API_URL}/api/research/stream/{task_id}", stream=True)
                
                for line in stream_res.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        if decoded_line.startswith("data: "):
                            data = json.loads(decoded_line[6:])
                            
                            # Check for finishing packet
                            if data.get("message") == "__FINISHED__":
                                payload = data.get("payload", {})
                                if payload.get("status") == "completed":
                                    step_idx.markdown('<div class="step-badge step-completed">1. Ingesting Done</div>', unsafe_allow_html=True)
                                    step_plan.markdown('<div class="step-badge step-completed">2. Planner Done</div>', unsafe_allow_html=True)
                                    step_res.markdown('<div class="step-badge step-completed">3. Researcher Done</div>', unsafe_allow_html=True)
                                    step_wri.markdown('<div class="step-badge step-completed">4. Writer Done</div>', unsafe_allow_html=True)
                                    
                                    st.session_state.selected_briefing_content = payload.get("report")
                                    st.session_state.selected_briefing_name = "latest_generation"
                                    st.session_state.selected_briefing_plan = payload.get("plan", [])
                                    st.success("Research synthesis complete!")
                                else:
                                    st.error("Workflow encountered errors.")
                                break
                            
                            # Add regular logs
                            agent_name = data.get("agent", "System")
                            msg = data.get("message", "")
                            
                            # Live-parse Planner questions
                            if agent_name == "Planner" and ". " in msg:
                                parts = msg.strip().split(". ", 1)
                                if parts[0].isdigit() and len(parts) > 1:
                                    clean_q = parts[1].strip()
                                    if clean_q not in st.session_state.selected_briefing_plan:
                                        st.session_state.selected_briefing_plan.append(clean_q)
                                        
                                        # Render the plan container live
                                        plan_markdown = '<div class="glass-card"><h4>📋 Planner Agent: Research Sub-Questions</h4><ul>'
                                        for q in st.session_state.selected_briefing_plan:
                                            plan_markdown += f'<li>{q}</li>'
                                        plan_markdown += '</ul></div>'
                                        plan_container.markdown(plan_markdown, unsafe_allow_html=True)
                            
                            # Parse dates
                            time_str = datetime.now().strftime("%H:%M:%S")
                            log_lines.append(f"[{time_str}] [{agent_name}] {msg}")
                            
                            # Render logs in scrolling window
                            terminal_html = f'<div class="terminal-container">{"<br>".join(log_lines)}</div>'
                            log_terminal.markdown(terminal_html, unsafe_allow_html=True)
                            
                            # Update workflow progress boxes
                            if agent_name == "System":
                                step_idx.markdown('<div class="step-badge step-active">1. Ingesting & Indexing</div>', unsafe_allow_html=True)
                            elif agent_name == "Planner":
                                step_idx.markdown('<div class="step-badge step-completed">1. Ingesting Done</div>', unsafe_allow_html=True)
                                step_plan.markdown('<div class="step-badge step-active">2. Planner Agent</div>', unsafe_allow_html=True)
                            elif agent_name == "Researcher":
                                step_idx.markdown('<div class="step-badge step-completed">1. Ingesting Done</div>', unsafe_allow_html=True)
                                step_plan.markdown('<div class="step-badge step-completed">2. Planner Done</div>', unsafe_allow_html=True)
                                step_res.markdown('<div class="step-badge step-active">3. Researcher (RAG)</div>', unsafe_allow_html=True)
                            elif agent_name == "Writer":
                                step_idx.markdown('<div class="step-badge step-completed">1. Ingesting Done</div>', unsafe_allow_html=True)
                                step_plan.markdown('<div class="step-badge step-completed">2. Planner Done</div>', unsafe_allow_html=True)
                                step_res.markdown('<div class="step-badge step-completed">3. Researcher Done</div>', unsafe_allow_html=True)
                                step_wri.markdown('<div class="step-badge step-active">4. Writer Synthesis</div>', unsafe_allow_html=True)
                                
        except Exception as e:
            st.error(f"Error during stream connection: {e}")

# ----------------------------------------------------
# 3. Briefing Output Section (Report Display)
# ----------------------------------------------------
if st.session_state.selected_briefing_content:
    if st.session_state.selected_briefing_plan:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 📋 Planner Agent: Research Sub-Questions")
        for idx, q in enumerate(st.session_state.selected_briefing_plan):
            st.markdown(f"**{idx+1}.** {q}")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### 📝 Synthesized Research Briefing")
    
    # Download actions
    col_dl, col_blank = st.columns([1, 4])
    col_dl.download_button(
        "💾 Download Briefing (.md)",
        st.session_state.selected_briefing_content,
        file_name="briefing.md",
        mime="text/markdown"
    )
    
    # Render final report markdown
    st.markdown(st.session_state.selected_briefing_content)
    st.markdown('</div>', unsafe_allow_html=True)

# ----------------------------------------------------
# 4. Briefings History Section (Saved reports)
# ----------------------------------------------------
st.markdown("### 📚 Briefings History")
briefs = get_briefings_from_backend()
if briefs:
    for idx, brief in enumerate(briefs[:5]): # Show last 5
        col_item, col_load = st.columns([5, 1])
        
        # Render human readable label
        clean_name = brief['name'].replace('briefing_', '').replace('.md', '').replace('_', ' ')
        clean_name = clean_name.capitalize()
        
        col_item.markdown(f"**Briefing:** {clean_name}")
        if col_load.button("Load", key=f"load_{idx}_{brief['name']}"):
            content = get_briefing_content(brief['name'])
            st.session_state.selected_briefing_content = content
            st.session_state.selected_briefing_name = brief['name']
            st.rerun()
else:
    st.info("No previously generated briefings found in outputs library.")
