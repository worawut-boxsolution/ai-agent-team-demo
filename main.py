import os
import sys
from unittest.mock import MagicMock

# ป้องกันปัญหา Windows Application Control บล็อกไฟล์ DLL ของ lancedb
sys.modules["lancedb"] = MagicMock()
sys.modules["crewai.memory.storage.lancedb_storage"] = MagicMock()

import json
import time
import threading
import webbrowser
import subprocess
from http.server import SimpleHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv
from pydantic import BaseModel
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from crewai.flow.flow import Flow, listen, start, router
import crewai.memory.unified_memory as um
um.Memory.model_post_init = lambda self, __context: None

load_dotenv()
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"

SMART_LLM = 'gemini/gemini-3-flash-preview'
FAST_LLM = 'gemini/gemini-3-flash-preview'

# ==========================================
# 0. ระบบจัดการ Virtual Office State & Process Control
# ==========================================
OFFICE_Roles = [
    'System Analyst (SA)',
    'Solution Architect (.NET)',
    'Senior .NET Backend Developer',
    'Senior Blazor Frontend Developer',
    'QA Automation Engineer (.NET)',
    'Technical Writer & Product Specialist',
    'DevOps Engineer'
]

OFFICE_STATE = {
    "is_running": False,
    "app_running": False,
    "work_mode": "feature",
    "project_name": "OrderSystem",
    "workspace_path": os.path.abspath("./workspace"),
    "repo_url": "",
    "phase": "รอรับการตั้งค่าโปรเจกต์และ Requirement บนหน้าเว็บ...",
    "agents": {role: {"status": "Idle", "action": "นั่งจิบกาแฟรอรับงาน ☕"} for role in OFFICE_Roles},
    "logs": []
}

RUNNING_PROCESSES = []

def get_workspace_dir() -> str:
    """ดึง Path ของโฟลเดอร์โปรเจกต์ปัจจุบันที่ตั้งค่ามาจากหน้าเว็บ"""
    path = OFFICE_STATE.get("workspace_path", "./workspace")
    abs_path = os.path.abspath(path)
    os.makedirs(abs_path, exist_ok=True)
    return abs_path

def update_office(phase=None, active_role=None, action=None, status="Working", log=None, is_running=None, app_running=None):
    if is_running is not None:
        OFFICE_STATE["is_running"] = is_running
    if app_running is not None:
        OFFICE_STATE["app_running"] = app_running
    if phase:
        OFFICE_STATE["phase"] = phase
    if active_role:
        if status == "Working":
            for r in OFFICE_STATE["agents"]:
                if r != active_role and OFFICE_STATE["agents"][r]["status"] == "Working":
                    OFFICE_STATE["agents"][r]["status"] = "Idle"
                    OFFICE_STATE["agents"][r]["action"] = "รอดูผลงานเพื่อนร่วมทีม 👀"
        
        if active_role not in OFFICE_STATE["agents"]:
            OFFICE_STATE["agents"][active_role] = {"status": status, "action": action or ""}
        else:
            OFFICE_STATE["agents"][active_role]["status"] = status
            if action:
                OFFICE_STATE["agents"][active_role]["action"] = action

    if log:
        timestamp = time.strftime("%H:%M:%S")
        OFFICE_STATE["logs"].insert(0, f"<span class='text-emerald-400'>[{timestamp}]</span> {log}")
        OFFICE_STATE["logs"] = OFFICE_STATE["logs"][:80]

def stop_running_apps():
    global RUNNING_PROCESSES
    for proc in RUNNING_PROCESSES:
        try:
            subprocess.run(f"taskkill /F /T /PID {proc.pid}", shell=True, capture_output=True)
        except Exception:
            pass
    RUNNING_PROCESSES = []
    update_office(app_running=False, log="🛑 หยุดการทำงานของเซิร์ฟเวอร์ .NET (API & Web) เรียบร้อยแล้ว")

class OfficeHTTPHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path.startswith('/api/state'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
            self.end_headers()
            self.wfile.write(json.dumps(OFFICE_STATE, ensure_ascii=False).encode('utf-8'))
            return
        return super().do_GET()

    def do_POST(self):
        global RUNNING_PROCESSES
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b"{}"
        data = json.loads(post_data.decode('utf-8'))

        if self.path == '/api/start':
            work_mode = data.get("work_mode", "feature").strip()
            proj_name = data.get("project_name", "OrderSystem").strip()
            raw_path = data.get("workspace_path", "./workspace").strip()
            repo_url = data.get("repo_url", "").strip()
            req_text = data.get("requirement", "").strip()

            if not OFFICE_STATE["is_running"] and req_text:
                stop_running_apps()
                abs_workspace = os.path.abspath(raw_path)
                os.makedirs(abs_workspace, exist_ok=True)
                
                for role in OFFICE_Roles:
                    OFFICE_STATE["agents"][role] = {"status": "Idle", "action": "เตรียมพร้อมรับงานรอบใหม่ ☕"}

                OFFICE_STATE["work_mode"] = work_mode
                OFFICE_STATE["project_name"] = proj_name
                OFFICE_STATE["workspace_path"] = abs_workspace
                OFFICE_STATE["repo_url"] = repo_url

                mode_title = {
                    "new": "🆕 สร้างโปรเจกต์ใหม่ (New Project)",
                    "feature": "➕ ต่อยอดเพิ่มฟีเจอร์ใหม่ (Feature Addition)",
                    "scale": "🚀 ขยายขนาดและเพิ่มประสิทธิภาพ (Scalability Enhancement)"
                }.get(work_mode, work_mode)

                update_office(
                    is_running=True,
                    phase=f"[{mode_title}] กำลังเริ่มงานโปรเจกต์ {proj_name}...",
                    log=f"📥 <b>เริ่มงานโหมด: {mode_title}</b> | Project: <b>{proj_name}</b> | Path: <code>{abs_workspace}</code>"
                )
                threading.Thread(
                    target=run_ai_flow, 
                    args=(work_mode, proj_name, abs_workspace, repo_url, req_text), 
                    daemon=True
                ).start()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "started"}).encode('utf-8'))
            return

        elif self.path == '/api/open-folder':
            workspace_dir = get_workspace_dir()
            if os.path.exists(workspace_dir):
                os.startfile(workspace_dir)
                update_office(log=f"📂 เปิดโฟลเดอร์โปรเจกต์บน Windows Explorer: <code>{workspace_dir}</code>")
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "opened"}).encode('utf-8'))
            return

        elif self.path == '/api/run-app':
            stop_running_apps()
            workspace_dir = get_workspace_dir()
            p_name = OFFICE_STATE["project_name"]
            api_proj = os.path.join(workspace_dir, f"{p_name}.Api")
            web_proj = os.path.join(workspace_dir, f"{p_name}.Web")

            if os.path.exists(api_proj):
                p_api = subprocess.Popen(
                    "dotnet run --urls http://localhost:5050",
                    cwd=api_proj, shell=True
                )
                RUNNING_PROCESSES.append(p_api)
                update_office(app_running=True, log="🚀 สั่งรัน Backend API ที่ <a href='http://localhost:5050/swagger' target='_blank' class='underline text-cyan-400'>http://localhost:5050/swagger</a>")

            if os.path.exists(web_proj):
                p_web = subprocess.Popen(
                    "dotnet run --urls http://localhost:5055",
                    cwd=web_proj, shell=True
                )
                RUNNING_PROCESSES.append(p_web)
                update_office(app_running=True, log="🎨 สั่งรัน Blazor Web UI ที่ <a href='http://localhost:5055' target='_blank' class='underline text-emerald-400'>http://localhost:5055</a>")
                threading.Timer(4.0, lambda: webbrowser.open("http://localhost:5055")).start()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "running"}).encode('utf-8'))
            return

        elif self.path == '/api/stop-app':
            stop_running_apps()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "stopped"}).encode('utf-8'))
            return

# ==========================================
# 1. สร้าง Tools (พร้อม Replace In File Tool)
# ==========================================
@tool("Write File Tool")
def write_file_tool(filename: str, content: str) -> str:
    """เขียนโค้ดหรือเอกสารลงในไฟล์ภายในโฟลเดอร์โปรเจกต์ปัจจุบัน (รองรับ subfolder เช่น 'Docs/SRS.md')"""
    workspace_dir = get_workspace_dir()
    filepath = os.path.abspath(os.path.join(workspace_dir, filename))
    
    if not filepath.startswith(workspace_dir):
        return "Error: ไม่อนุญาตให้เขียนไฟล์นอกโฟลเดอร์โปรเจกต์ที่กำหนด"
        
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    
    update_office(log=f"📝 บันทึกไฟล์: <b>{filename}</b> ({len(content)} ตัวอักษร)")
    return f"บันทึกไฟล์ {filename} สำเร็จแล้ว"

@tool("Replace In File Tool")
def replace_in_file_tool(filename: str, old_code: str, new_code: str) -> str:
    """แก้ไขโค้ดเฉพาะจุดในไฟล์เดิม โดยระบุบล็อกโค้ดเดิม (old_code) และโค้ดใหม่ที่ต้องการแทนที่ (new_code) 
    ช่วยประหยัดเวลาและป้องกันโค้ดฟีเจอร์เก่าหาย"""
    workspace_dir = get_workspace_dir()
    filepath = os.path.abspath(os.path.join(workspace_dir, filename))
    if not filepath.startswith(workspace_dir) or not os.path.exists(filepath):
        return f"Error: ไม่พบไฟล์ {filename}"
        
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
    if old_code not in content:
        return f"Error: ไม่พบส่วนของ old_code ในไฟล์ {filename} กรุณาใช้ Read File Tool อ่านเนื้อหาไฟล์ล่าสุดก่อน"
        
    updated_content = content.replace(old_code, new_code, 1)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(updated_content)
        
    update_office(log=f"🔧 แก้ไขโค้ดเฉพาะจุด (Patch) ในไฟล์: <b>{filename}</b>")
    return f"อัปเดตโค้ดเฉพาะจุดในไฟล์ {filename} สำเร็จแล้ว"

@tool("Read File Tool")
def read_file_tool(filename: str) -> str:
    """อ่านเนื้อหาไฟล์จากในโฟลเดอร์โปรเจกต์ปัจจุบัน"""
    workspace_dir = get_workspace_dir()
    filepath = os.path.abspath(os.path.join(workspace_dir, filename))
    if not filepath.startswith(workspace_dir) or not os.path.exists(filepath):
        return f"ไม่พบไฟล์ {filename}"
    update_office(log=f"📖 เปิดอ่านไฟล์: <b>{filename}</b>")
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

@tool("List Files Tool")
def list_files_tool() -> str:
    """แสดงรายชื่อไฟล์และโครงสร้างโฟลเดอร์ทั้งหมดในโปรเจกต์ปัจจุบัน"""
    workspace_dir = get_workspace_dir()
    if not os.path.exists(workspace_dir):
        return "โฟลเดอร์โปรเจกต์ยังว่างเปล่า"
    
    file_list = []
    for root, dirs, files in os.walk(workspace_dir):
        dirs[:] = [d for d in dirs if d not in ['bin', 'obj', '.git', '.vs']]
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), workspace_dir)
            file_list.append(rel_path)
    update_office(log="📂 สแกนโครงสร้างไฟล์ทั้งหมดในโปรเจกต์")
    return "\n".join(file_list) if file_list else "ไม่มีไฟล์ในโฟลเดอร์โปรเจกต์"

@tool("Dotnet CLI Tool")
def dotnet_cli_tool(arguments: str) -> str:
    """รันคำสั่ง dotnet CLI ในโฟลเดอร์โปรเจกต์ปัจจุบัน"""
    workspace_dir = get_workspace_dir()
    cmd = f"dotnet {arguments}"
    update_office(log=f"⚡ รันคำสั่ง CLI: <code>{cmd}</code>")
    try:
        result = subprocess.run(
            cmd, cwd=workspace_dir, shell=True, capture_output=True, text=True, timeout=120
        )
        return f"Exit Code: {result.returncode}\nOutput:\n{result.stdout}\nError:\n{result.stderr}"
    except Exception as e:
        return f"Error: {str(e)}"

@tool("Git CLI Tool")
def git_cli_tool(arguments: str) -> str:
    """รันคำสั่ง git ในโฟลเดอร์โปรเจกต์ปัจจุบัน"""
    workspace_dir = get_workspace_dir()
    cmd = f"git {arguments}"
    update_office(log=f"🔧 รันคำสั่ง Git: <code>{cmd}</code>")
    try:
        result = subprocess.run(
            cmd, cwd=workspace_dir, shell=True, capture_output=True, text=True, timeout=60
        )
        return f"Exit Code: {result.returncode}\nOutput:\n{result.stdout}\nError:\n{result.stderr}"
    except Exception as e:
        return f"Error: {str(e)}"

# ==========================================
# 2. สร้าง Agents ระดับ Enterprise
# ==========================================
def make_step_callback(role_name):
    def callback(step_output):
        tool_name = getattr(step_output, 'tool', None)
        if tool_name:
            action_text = f"กำลังใช้เครื่องมือ: {tool_name} 🛠️"
        else:
            action_text = "กำลังคิดวิเคราะห์และปรับปรุงโค้ด 💻"
        update_office(active_role=role_name, action=action_text, status="Working")
    return callback

sa_agent = Agent(
    role='System Analyst (SA)',
    goal='สำรวจระบบเดิม (ถ้ามี) วิเคราะห์ความต้องการใหม่ของลูกค้า และอัปเดตเอกสาร SRS ให้สมบูรณ์',
    backstory=(
        'คุณคือ System Analyst ระดับอาวุโส เวลาได้รับงานต่อยอด (Enhancement/Scalability) '
        
    ),
    tools=[list_files_tool, read_file_tool, write_file_tool, replace_in_file_tool],
    step_callback=make_step_callback('System Analyst (SA)'),
    verbose=True,
    llm=SMART_LLM
)

architect_agent = Agent(
    role='Solution Architect (.NET)',
    goal='ตรวจสอบโครงสร้างโค้ดเดิม และวางแผนการเพิ่มไฟล์/แก้ไขไฟล์ใน `Docs/ARCHITECTURE.md` เพื่อรองรับฟีเจอร์ใหม่หรือการขยายสเกล',
    backstory=(
        'คุณคือ Solution Architect ผู้เชี่ยวชาญการทำ System Evolution และ Scalability (Caching, Pagination, Async, Indexing) '
       
    ),
    tools=[list_files_tool, read_file_tool, write_file_tool, replace_in_file_tool],
    step_callback=make_step_callback('Solution Architect (.NET)'),
    verbose=True,
    llm=SMART_LLM
)

dev_agent = Agent(
    role='Senior .NET Backend Developer',
    goal='สถาปัตยกรรมและพัฒนา Enterprise .NET Web API, EF Core และ Business Services ที่มีความเสถียร ปลอดภัย รองรับโหลดสูง และสมบูรณ์แบบ 100%',
    backstory=(
        'คุณคือ Principal .NET Backend Engineer ระดับโลกที่เชี่ยวชาญ C# 12 และ .NET 8+ กฎเหล็กในการเขียนโค้ดระดับ Enterprise ของคุณ:\n'
        
    ),
    tools=[write_file_tool, replace_in_file_tool, read_file_tool, list_files_tool, dotnet_cli_tool],
    step_callback=make_step_callback('Senior .NET Backend Developer'),
    verbose=True,
    llm=SMART_LLM
)

frontend_agent = Agent(
    role='Senior Blazor Frontend Developer',
    goal='สร้าง Enterprise Web Application ด้วย Blazor ที่สวยงามระดับโลก ทันสมัย (Modern SaaS UI) และทำงานร่วมกับ Web API ได้อย่างสมบูรณ์แบบ 100%',
    backstory=(
        'คุณคือ Principal Frontend Architect และ UI/UX Designer มือหนึ่งด้าน Blazor (.NET 8+) กฎเหล็กในการทำงานของคุณ:\n'
        
    ),
    tools=[write_file_tool, replace_in_file_tool, read_file_tool, list_files_tool, dotnet_cli_tool],
    step_callback=make_step_callback('Senior Blazor Frontend Developer'),
    verbose=True,
    llm=SMART_LLM
)

qa_agent = Agent(
    role='QA Automation Engineer (.NET)',
    goal='รักษา Unit Tests เดิมไว้ และเขียน xUnit Tests เพิ่มเติมเพื่อทดสอบฟีเจอร์ใหม่หรือประสิทธิภาพที่เพิ่งอัปเกรด',
    backstory=(
        'คุณคือ QA ที่เชี่ยวชาญการทำ Regression Testing และทดสอบฟีเจอร์ใหม่ '
        
    ),
    tools=[write_file_tool, replace_in_file_tool, read_file_tool, list_files_tool, dotnet_cli_tool],
    step_callback=make_step_callback('QA Automation Engineer (.NET)'),
    verbose=True,
    llm=SMART_LLM
)
tech_writer_agent = Agent(
    role='Technical Writer & Product Specialist',
    goal='จัดทำคู่มือการใช้งานระบบสำหรับผู้ใช้ทั่วไป (End-User Manual) และคู่มือดูแลระบบ (Admin/API Guide) เป็นภาษาไทยที่ละเอียดและเข้าใจง่ายที่สุด',
    backstory=(
        'คุณคือ Technical Writer มืออาชีพที่เชี่ยวชาญการแกะโค้ดหน้าบ้าน (Blazor `.razor`) และหลังบ้าน (`.cs`) '
        
    ),
    tools=[list_files_tool, read_file_tool, write_file_tool, replace_in_file_tool],
    step_callback=make_step_callback('Technical Writer & Product Specialist'),
    verbose=True,
    llm=SMART_LLM
)

devops_agent = Agent(
    role='DevOps Engineer',
    goal='อัปเดต README, Docker, CI/CD และ Commit & Push การเปลี่ยนแปลงขึ้น GitHub',
    backstory='คุณเชี่ยวชาญการจัดการ Git Versioning, Docker และการอัปเดตเอกสารระบบเมื่อมีการเพิ่มฟีเจอร์หรือขยายสเกล',
    tools=[write_file_tool, replace_in_file_tool, read_file_tool, list_files_tool, git_cli_tool],
    step_callback=make_step_callback('DevOps Engineer'),
    verbose=True,
    llm=FAST_LLM
)

# ==========================================
# 3. สร้าง Flow ควบคุมการผลิต (รองรับทั้ง New / Feature / Scale)
# ==========================================
class SelfHealingState(BaseModel):
    work_mode: str = "feature"  # 'new', 'feature', 'scale'
    project_name: str = "OrderSystem"
    workspace_path: str = "./workspace"
    repo_url: str = ""
    customer_requirement: str = ""
    retry_count: int = 0
    max_retries: int = 10
    test_passed: bool = False
    last_error_log: str = ""

class DotnetProductionFlow(Flow[SelfHealingState]):

    @start()
    def initial_build_phase(self):
        p_name = self.state.project_name
        api_proj = f"{p_name}.Api"
        web_proj = f"{p_name}.Web"
        test_proj = f"{p_name}.Tests"
        req = self.state.customer_requirement
        mode = self.state.work_mode
        workspace_dir = get_workspace_dir()

        existing_files = os.listdir(workspace_dir) if os.path.exists(workspace_dir) else []
        has_existing_project = any(f.endswith(('.sln', '.slnx')) or os.path.isdir(os.path.join(workspace_dir, api_proj)) for f in existing_files)

        if mode in ["feature", "scale"] and has_existing_project:
            mode_label = "ต่อยอดเพิ่มฟีเจอร์ใหม่ (Feature Addition)" if mode == "feature" else "ขยายสเกลและเพิ่มประสิทธิภาพ (Scalability)"
            update_office(
                phase=f"PHASE 1: สำรวจโปรเจกต์เดิมและดำเนินการ {mode_label}",
                active_role='System Analyst (SA)',
                action=f"กำลังสแกนโปรเจกต์เดิมเพื่อวางสเปค {mode_label} 📋",
                status="Working",
                log=f"🔄 ตรวจพบโปรเจกต์เดิมใน <code>{workspace_dir}</code> เข้าสู่โหมด <b>{mode_label}</b>"
            )

            task_sa = Task(
                description=(
                    f'โหมดการทำงาน: **{mode_label}** บนโปรเจกต์เดิมชื่อ "{p_name}"\n'
                    f'ความต้องการเพิ่มเติมจากลูกค้า:\n"{req}"\n\n'
                    
                ),
                expected_output='อัปเดตไฟล์ `Docs/SRS.md` ที่รวมสเปคเดิมและสเปคใหม่เข้าด้วยกันอย่างสมบูรณ์',
                agent=sa_agent,
                callback=lambda out: update_office(active_role='System Analyst (SA)', action="อัปเดตเอกสาร SRS.md เรียบร้อย ✅", status="Done", log="✅ SA วิเคราะห์ระบบเดิมและอัปเดต SRS เสร็จสมบูรณ์")
            )

            task_arch = Task(
                description=(
                    f'อ่านไฟล์ `Docs/SRS.md` ล่าสุดและใช้ List Files Tool ตรวจสอบโครงสร้างไฟล์เดิมของ "{p_name}"\n'
                   
                ),
                expected_output='อัปเดตไฟล์ `Docs/ARCHITECTURE.md` ที่ระบุแผนการต่อยอดโค้ดเดิมอย่างชัดเจน',
                agent=architect_agent,
                callback=lambda out: update_office(active_role='Solution Architect (.NET)', action="วางแผนต่อยอดสถาปัตยกรรมเสร็จสิ้น ✅", status="Done", log="✅ Architect วางแผนจุดที่ต้องสร้างเพิ่มและแก้ไขเสร็จสมบูรณ์")
            )

            task_backend_enhance = Task(
                description=(
                    f'ดำเนินการต่อยอดและยกระดับฝั่ง Backend (`{api_proj}`) สู่ระดับ Enterprise Architecture ตามไฟล์ `Docs/SRS.md` และ `Docs/ARCHITECTURE.md`:\n'
                     
                ),
                expected_output=f'ต่อยอดโค้ดระดับ Enterprise ใน `{api_proj}` และสั่ง build ผ่านสำเร็จ 0 Error',
                agent=dev_agent,
                callback=lambda out: update_office(active_role='Senior .NET Backend Developer', action=f"อัปเกรด Enterprise Backend ({api_proj}) เสร็จสิ้น ✅", status="Done", log=f"✅ Backend Dev ต่อยอดโค้ดระดับ Enterprise ใน {api_proj} สำเร็จ")
            )

            task_frontend_enhance = Task(
                description=(
                    f'ดำเนินการต่อยอดและยกระดับฝั่ง Frontend Blazor (`{web_proj}`) ให้เป็นระดับ Enterprise SaaS:\n'
                    
                ),
                expected_output=f'อัปเกรดหน้าเว็บ Blazor ใน `{web_proj}` ให้รองรับฟีเจอร์ใหม่ด้วยดีไซน์ระดับ Enterprise และสั่ง build ผ่านสำเร็จ',
                agent=frontend_agent,
                callback=lambda out: update_office(active_role='Senior Blazor Frontend Developer', action=f"อัปเกรด Enterprise UI ({web_proj}) เสร็จสิ้น ✅", status="Done", log=f"✅ Frontend Dev อัปเกรด UI ใน {web_proj} สำเร็จ")
            )

            task_qa_enhance = Task(
                description=(
                    f'ดำเนินการอัปเดตชุดทดสอบ xUnit ใน `{test_proj}`:\n'
                    f'1. ใช้ List Files Tool และ Read File Tool อ่านไฟล์ Unit Tests เดิมใน `{test_proj}/` และอ่านไฟล์ Services ล่าสุดใน `{api_proj}/`\n'
                    '2. เขียน Test Cases (`[Fact]`) เพิ่มเติมเพื่อทดสอบฟีเจอร์ใหม่ หรือทดสอบการแบ่งหน้า (Pagination) / การทำงานที่เพิ่งอัปเกรด โดยห้ามลบ Test Cases เดิมที่ยังใช้งานได้'
                ),
                expected_output=f'เพิ่ม Unit Tests สำหรับฟีเจอร์ใหม่ใน `{test_proj}` เสร็จสมบูรณ์',
                agent=qa_agent,
                callback=lambda out: update_office(active_role='QA Automation Engineer (.NET)', action="เพิ่มชุดทดสอบ xUnit สำหรับฟีเจอร์ใหม่เสร็จสิ้น ✅", status="Done", log="✅ QA อัปเดต Unit Tests เสร็จสมบูรณ์")
            )

            enhance_crew = Crew(
                agents=[sa_agent, architect_agent, dev_agent, frontend_agent, qa_agent],
                tasks=[task_sa, task_arch, task_backend_enhance, task_frontend_enhance, task_qa_enhance],
                process=Process.sequential
            )
            enhance_crew.kickoff()

        # =========================================================================
        # กรณีเลือกโหมด 'new' หรือในโฟลเดอร์ยังว่างเปล่า (สร้างใหม่ตั้งแต่ต้น)
        # =========================================================================
        else:
            update_office(
                phase=f"PHASE 1: สร้างโปรเจกต์ใหม่ {p_name} ตั้งแต่ต้น (Greenfield Mode)",
                active_role='System Analyst (SA)',
                action="เริ่มวิเคราะห์โจทย์และจัดทำเอกสาร SRS ฉบับละเอียด 📋",
                status="Working",
                log=f"🚀 เริ่มต้นสร้างโปรเจกต์ใหม่ <b>{p_name}</b> ตั้งแต่ศูนย์"
            )
            
            task_sa = Task(
                description=(
                    f'ชื่อโปรเจกต์คือ "{p_name}"\n'
                    f'ความต้องการของลูกค้า:\n"{req}"\n\n'
                    'จัดทำเอกสาร Software Requirements Specification (SRS) ฉบับสมบูรณ์ลงไฟล์ `Docs/SRS.md` ระบุ Entity Models, Business Rules, REST API Contracts และ UI/UX Requirements'
                ),
                expected_output='บันทึกไฟล์ `Docs/SRS.md` ที่มีรายละเอียดครบถ้วนสมบูรณ์',
                agent=sa_agent,
                callback=lambda out: update_office(active_role='System Analyst (SA)', action="ส่งมอบเอกสาร SRS.md เรียบร้อย ✅", status="Done", log="✅ SA จัดทำเอกสาร SRS เสร็จสมบูรณ์")
            )

            task_arch = Task(
                description=(
                    f'อ่านไฟล์ `Docs/SRS.md` แล้วออกแบบโครงสร้าง Solution ชื่อ "{p_name}" บันทึกลงไฟล์ `Docs/ARCHITECTURE.md` ประกอบด้วย:\n'
                    f'1. "{api_proj}" (ASP.NET Core Web API - พอร์ต `http://localhost:5050`)\n'
                    f'2. "{web_proj}" (Blazor Web App Interactive Server)\n'
                    f'3. "{test_proj}" (xUnit Test Project)'
                ),
                expected_output='บันทึกไฟล์ `Docs/ARCHITECTURE.md` เรียบร้อย',
                agent=architect_agent,
                callback=lambda out: update_office(active_role='Solution Architect (.NET)', action="ส่งมอบพิมพ์เขียว ARCHITECTURE.md ✅", status="Done", log="✅ Architect วางโครงสร้างระบบเสร็จสมบูรณ์")
            )

            # 3.1 Backend Micro-Task 1: Enterprise Data Layer, DTOs & EF Core DbContext
            task_backend_data = Task(
                description=(
                    f'อ่านไฟล์ `Docs/SRS.md` และ `Docs/ARCHITECTURE.md` แล้วดำเนินการสร้าง Enterprise Data Layer (`{api_proj}`):\n'
                   
                ),
                expected_output=f'สร้างโปรเจกต์ {api_proj}, Entities, DTOs พร้อม Validation และ Enterprise DbContext พร้อม Fluent API & Seed Data สำเร็จ',
                agent=dev_agent,
                callback=lambda out: update_office(active_role='Senior .NET Backend Developer', action="สร้าง Enterprise Data Layer & DbContext เสร็จสิ้น ✅", status="Working", log="✅ Backend Dev สร้าง Models, DTOs และ DbContext ระดับ Enterprise เสร็จแล้ว")
            )

            # 3.2 Backend Micro-Task 2: Enterprise Business Logic & Services Layer
            task_backend_services = Task(
                description=(
                    f'อ่านไฟล์ `Docs/SRS.md` และใช้ Read File Tool อ่านไฟล์ใน `{api_proj}/Models/`, `{api_proj}/DTOs/` และ `{api_proj}/Data/` เพื่อเขียนโค้ดส่วน Enterprise Business Services:\n'
                    
                ),
                expected_output=f'สร้างไฟล์ Interfaces และ Services ใน `{api_proj}/Services/` ที่ครบถ้วนตามหลัก Enterprise Architecture 100%',
                agent=dev_agent,
                callback=lambda out: update_office(active_role='Senior .NET Backend Developer', action="พัฒนา Enterprise Business Services เสร็จสิ้น ✅", status="Working", log="✅ Backend Dev พัฒนาส่วน Business Logic Services เสร็จสมบูรณ์")
            )

            # 3.3 Backend Micro-Task 3: Resilient RESTful Controllers & Production-Ready Program.cs
            task_backend_api = Task(
                description=(
                    f'ดำเนินการขั้นสุดท้ายของฝั่ง Backend (`{api_proj}`) เพื่อสร้าง RESTful API และตั้งค่าระดับ Production:\n'
                   
                ),
                expected_output=f'สร้าง Controllers, ตั้งค่า Program.cs ระดับ Enterprise และสั่ง build {api_proj} ผ่านสำเร็จ 0 Error',
                agent=dev_agent,
                callback=lambda out: update_office(active_role='Senior .NET Backend Developer', action=f"พัฒนาและ Build Enterprise API ({api_proj}) ผ่าน 100% ✅", status="Done", log=f"✅ Backend Developer พัฒนา {api_proj} เสร็จสมบูรณ์")
            )

            task_frontend = Task(
                description=(
                    f'พัฒนาโปรเจกต์ Frontend (`{web_proj}`) ให้มี UI/UX สวยงามระดับ Enterprise SaaS และเชื่อมต่อกับ `{api_proj}` อย่างสมบูรณ์:\n'
                   
                ),
                expected_output=f'สร้างโปรเจกต์ {web_proj} ระดับ Enterprise UI ด้วย Tailwind CSS + Bootstrap Icons และสั่ง build ผ่านสำเร็จ 0 Error',
                agent=frontend_agent,
                callback=lambda out: update_office(active_role='Senior Blazor Frontend Developer', action=f"เนรมิต Enterprise UI ({web_proj}) เสร็จสิ้น ✅", status="Done", log=f"✅ Frontend Developer สร้าง Enterprise UI สำหรับ {web_proj} เสร็จสมบูรณ์")
            )

            task_qa = Task(
                description=(
                    f'1. รัน CLI สร้างเทสต์: `new xunit -n {test_proj} --force` และผูกเข้า sln: `sln add {test_proj}/{test_proj}.csproj`\n'
                    f'2. ผูก Reference ไปยัง {api_proj} และติดตั้ง `Microsoft.EntityFrameworkCore.InMemory`\n'
                    f'3. เขียนไฟล์ Unit Tests ใน `{test_proj}/` อย่างน้อย 5 Test Cases'
                ),
                expected_output=f'สร้างโปรเจกต์ {test_proj} และเขียน Unit Tests ครบถ้วน',
                agent=qa_agent,
                callback=lambda out: update_office(active_role='QA Automation Engineer (.NET)', action="เขียนชุดทดสอบ xUnit เสร็จสิ้น ✅", status="Done", log="✅ QA เขียน Unit Tests เสร็จสมบูรณ์")
            )

            build_crew = Crew(
                agents=[sa_agent, architect_agent, dev_agent, frontend_agent, qa_agent],
                tasks=[task_sa, task_arch, task_backend_data, task_backend_services, task_backend_api, task_frontend, task_qa],
                process=Process.sequential
            )
            build_crew.kickoff()

    @listen(initial_build_phase)
    def evaluate_build_and_test(self):
        round_num = self.state.retry_count + 1
        workspace_dir = get_workspace_dir()
        update_office(
            phase=f"PHASE 2: ตรวจสอบคุณภาพโค้ดและรัน Unit Tests (รอบที่ {round_num})",
            active_role='QA Automation Engineer (.NET)',
            action=f"กำลังรัน dotnet test และสแกนความสมบูรณ์ของโค้ด (รอบที่ {round_num}) 🧪",
            status="Working",
            log=f"🔍 ระบบกำลังรัน <code>dotnet test</code> และตรวจสอบคุณภาพโค้ด (รอบที่ {round_num})..."
        )
        
        result = subprocess.run(
            "dotnet test", cwd=workspace_dir, shell=True, capture_output=True, text=True
        )
        
        incomplete_files = []
        for root, dirs, files in os.walk(workspace_dir):
            dirs[:] = [d for d in dirs if d not in ['bin', 'obj', '.git', '.vs']]
            for file in files:
                if file.endswith(('.cs', '.razor')) and file not in ['WeatherForecast.cs', 'WeatherForecastController.cs', 'UnitTest1.cs']:
                    fpath = os.path.join(root, file)
                    rel_path = os.path.relpath(fpath, workspace_dir)
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if "// TODO" in content or "NotImplementedException" in content:
                            incomplete_files.append(f"{rel_path} (มีโค้ดที่ยังเขียนไม่เสร็จ // TODO หรือ NotImplementedException)")

        if result.returncode == 0 and not incomplete_files:
            self.state.test_passed = True
            update_office(
                phase="PHASE 2: ผ่านเกณฑ์คุณภาพและ Unit Tests 100%!",
                active_role='QA Automation Engineer (.NET)',
                action="ผลทดสอบผ่าน 100% ทั้งฟีเจอร์เก่าและใหม่! 🎉",
                status="Done",
                log="✅ <b>[SUCCESS] คอมไพล์ผ่าน, Unit Tests ผ่าน 100% และโค้ดสมบูรณ์ครบถ้วน!</b>"
            )
        else:
            self.state.test_passed = False
            error_details = f"Return Code: {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\n"
            if incomplete_files:
                error_details += "\n[QUALITY GATE FAILED - พบไฟล์ที่ยังเขียนโค้ดไม่สมบูรณ์]:\n" + "\n".join(incomplete_files)
            
            self.state.last_error_log = error_details
            update_office(
                phase=f"PHASE 2: พบข้อผิดพลาด! กำลังเข้าสู่โหมดซ่อมแซมอัตโนมัติ",
                active_role='QA Automation Engineer (.NET)',
                action="ตรวจพบ Bug หรือโค้ดไม่สมบูรณ์! กำลังสั่งทีม Dev แก้ไข 🚨",
                status="Working",
                log="❌ <b>[FAILED] พบข้อผิดพลาดในการ Build/Test หรือโค้ดยังไม่สมบูรณ์!</b>"
            )

    @router(evaluate_build_and_test)
    def route_next_step(self):
        if self.state.test_passed:
            return "deploy_phase"
        elif self.state.retry_count < self.state.max_retries:
            return "self_healing_phase"
        else:
            return "max_retries_exceeded"

    @listen("self_healing_phase")
    def heal_code(self):
        self.state.retry_count += 1
        p_name = self.state.project_name
        web_proj = f"{p_name}.Web"
        err_log = self.state.last_error_log

        # Smart Routing: ตรวจจับว่า Error เกิดที่ฝั่งไหนเพื่อเรียกเฉพาะคนที่เกี่ยวข้องมาซ่อม
        has_frontend_err = (web_proj in err_log) or (".razor" in err_log)
        has_backend_err = (f"{p_name}.Api" in err_log) or (f"{p_name}.Tests" in err_log) or not has_frontend_err

        update_office(
            phase=f"SELF-HEALING LOOP: ซ่อมแซมโค้ดอัตโนมัติ (ครั้งที่ {self.state.retry_count}/{self.state.max_retries})",
            log=f"🛠️ เริ่มกระบวนการ Smart Self-Healing ครั้งที่ {self.state.retry_count} (Backend Fix: {has_backend_err}, Frontend Fix: {has_frontend_err})"
        )

        task_analyze_bug = Task(
            description=(
                f'จากการตรวจสอบล่าสุด ระบบล้มเหลวด้วยรายละเอียดดังนี้:\n\n{err_log}\n\n'
                'ให้ใช้ List Files Tool และ Read File Tool เปิดอ่านไฟล์ที่มีปัญหา แล้วสรุปวิธีแก้ไขแบบระบุชื่อไฟล์และโค้ดที่ต้องแก้ให้ชัดเจน'
            ),
            expected_output='รายงานวิเคราะห์สาเหตุของปัญหาและจุดที่ต้องแก้ไขอย่างชัดเจน',
            agent=qa_agent
        )

        tasks_to_run = [task_analyze_bug]
        agents_to_run = [qa_agent]

        if has_backend_err:
            task_apply_backend_fix = Task(
                description=(
                    'นำรายงานจาก QA ไปแก้ไขไฟล์ในโปรเจกต์ `.Api` หรือ `.Tests` '
                    'โดยใช้ Read File Tool อ่านไฟล์ก่อน แล้วใช้ Replace In File Tool (หรือ Write File Tool) แก้ไขโค้ด และรัน `build` เช็คความถูกต้อง'
                ),
                expected_output='แก้ไขไฟล์ฝั่ง Backend และ Test เรียบร้อยแล้ว',
                agent=dev_agent,
                callback=lambda out: update_office(active_role='Senior .NET Backend Developer', action="แก้ไขโค้ดฝั่ง Backend/Test เสร็จสิ้น 🔄", status="Done")
            )
            tasks_to_run.append(task_apply_backend_fix)
            agents_to_run.append(dev_agent)

        if has_frontend_err:
            task_apply_frontend_fix = Task(
                description=(
                    'นำรายงานจาก QA ไปแก้ไขไฟล์ในโปรเจกต์ `.Web` (Blazor) '
                    'โดยใช้ Read File Tool อ่านไฟล์เดิมและใช้ Replace In File Tool (หรือ Write File Tool) แก้ไขทันที จากนั้นรันคำสั่ง `test` เพื่อเช็คผลรวมทั้ง Solution'
                ),
                expected_output='แก้ไขไฟล์ฝั่ง Frontend และรันทดสอบซ้ำเรียบร้อยแล้ว',
                agent=frontend_agent,
                callback=lambda out: update_office(active_role='Senior Blazor Frontend Developer', action="แก้ไขโค้ดฝั่ง Blazor UI เสร็จสิ้น 🔄", status="Done")
            )
            tasks_to_run.append(task_apply_frontend_fix)
            agents_to_run.append(frontend_agent)

        fix_crew = Crew(
            agents=agents_to_run,
            tasks=tasks_to_run,
            process=Process.sequential
        )
        fix_crew.kickoff()
        
        self.evaluate_build_and_test()

    @listen("deploy_phase")
    def prepare_production_deployment(self):
        p_name = self.state.project_name
        api_proj = f"{p_name}.Api"
        web_proj = f"{p_name}.Web"
        repo_url = self.state.repo_url
        mode = self.state.work_mode

        commit_prefix = "feat: enhance and add new features to" if mode == "feature" else ("perf: optimize scalability for" if mode == "scale" else "feat: initial full-stack solution for")

        update_office(
            phase="PHASE 3: จัดทำคู่มือผู้ใช้งาน (User Manual) และเตรียมส่งขึ้น GitHub",
            active_role='Technical Writer & Product Specialist',
            action="กำลังอ่านโค้ด UI เพื่อเขียนคู่มือการใช้งาน (User Manual) 📖",
            status="Working",
            log="📖 เริ่มต้นขั้นตอนการจัดทำ User Manual และเตรียม Deployment..."
        )

        # 1. ให้ Technical Writer เขียนคู่มือการใช้งานจากหน้าจอจริงที่เพิ่งสร้างเสร็จ
        task_user_manual = Task(
            description=(
                f'จัดทำหรืออัปเดตเอกสารคู่มือผู้ใช้งานฉบับสมบูรณ์ลงในไฟล์ `Docs/USER_MANUAL.md` สำหรับโปรเจกต์ `{p_name}`:\n'
               
            ),
            expected_output='สร้างหรืออัปเดตไฟล์ `Docs/USER_MANUAL.md` ฉบับภาษาไทยที่ละเอียดและตรงกับหน้าจอจริง 100%',
            agent=tech_writer_agent,
            callback=lambda out: update_office(
                active_role='Technical Writer & Product Specialist',
                action="จัดทำคู่มือ USER_MANUAL.md เสร็จสมบูรณ์ ✅",
                status="Done",
                log="✅ Technical Writer จัดทำคู่มือผู้ใช้งาน <code>Docs/USER_MANUAL.md</code> เสร็จสมบูรณ์"
            )
        )
        
        git_instructions = (
            f'5. ใช้ Git CLI Tool รันคำสั่งตามลำดับ: init (ถ้ายังไม่ได้ init), branch -M main, add ., commit -m "{commit_prefix} {p_name} with User Manual", '
            f'remote add origin {repo_url} (หากมี origin อยู่แล้วให้ใช้ remote set-url origin {repo_url}), และ push -u origin main --force'
            if repo_url else
            f'5. ใช้ Git CLI Tool รันคำสั่ง init, branch -M main, add ., และ commit -m "{commit_prefix} {p_name} with User Manual"'
        )

        # 2. ให้ DevOps อัปเดต README (ผูกลิงก์ไปยัง USER_MANUAL.md) และ Push ขึ้น GitHub
        task_devops = Task(
            description=(
                f'1. ตรวจสอบหรือสร้างไฟล์ `.gitignore` ที่โฟลเดอร์หลักของโปรเจกต์ (ข้าม bin/, obj/, .vs/)\n'
                f'2. สร้างหรืออัปเดตไฟล์ `README.md` ที่อธิบายโครงสร้างโปรเจกต์ วิธีรัน และใส่ลิงก์เชื่อมต่อไปยังคู่มือผู้ใช้งาน `[📖 อ่านคู่มือผู้ใช้งานฉบับเต็ม (User Manual)](Docs/USER_MANUAL.md)`\n'
                f'3. ตรวจสอบและอัปเดต `Dockerfile` และ `docker-compose.yml` ให้สอดคล้องกับระบบล่าสุด\n'
                f'4. ตรวจสอบไฟล์ `.github/workflows/deploy.yml` สำหรับ CI/CD\n'
                f'{git_instructions}'
            ),
            expected_output='ยืนยันการอัปเดตไฟล์โครงสร้างพื้นฐานและ Commit/Push Git สำเร็จ',
            agent=devops_agent,
            callback=lambda out: update_office(active_role='DevOps Engineer', action="อัปเดต Git & DevOps เสร็จสิ้น! 🎉", status="Done")
        )

        release_crew = Crew(
            agents=[tech_writer_agent, devops_agent],
            tasks=[task_user_manual, task_devops],
            process=Process.sequential
        )
        release_crew.kickoff()
        
        update_office(
            is_running=False,
            phase=f"🎉 COMPLETE: โปรเจกต์ {p_name} พร้อมคู่มือ User Manual เสร็จสมบูรณ์!",
            log=f"🎉 <b>[COMPLETE] สร้างระบบพร้อมคู่มือ <code>Docs/USER_MANUAL.md</code> และ Push ขึ้น GitHub เสร็จสมบูรณ์!</b>"
        )

    @listen("max_retries_exceeded")
    def handle_failure(self):
        update_office(
            is_running=False,
            phase="⚠️ ABORTED: แก้บั๊กเกินจำนวนครั้งสูงสุด (สามารถสั่งรันซ้ำเพื่อซ่อมต่อได้)",
            log="⚠️ AI พยายามแก้บั๊กครบจำนวนครั้งสูงสุดแล้วแต่ยังไม่ผ่าน"
        )

def run_ai_flow(work_mode: str, proj_name: str, workspace_path: str, repo_url: str, req_text: str):
    try:
        flow = DotnetProductionFlow()
        flow.state.work_mode = work_mode
        flow.state.project_name = proj_name
        flow.state.workspace_path = workspace_path
        flow.state.repo_url = repo_url
        flow.state.customer_requirement = req_text
        flow.kickoff()
    except Exception as e:
        update_office(
            is_running=False,
            phase=f"❌ เกิดข้อผิดพลาดในระบบ: {str(e)}",
            log=f"❌ <b>[SYSTEM ERROR]:</b> {str(e)}"
        )
        print(f"Error in run_ai_flow: {e}")

if __name__ == "__main__":
    PORT = 8000
    update_office(log=f"🏢 เปิดออฟฟิศเสมือนจริงแล้วที่ http://localhost:{PORT}/office.html รอรับคำสั่งจากหน้าเว็บ...")
    server = HTTPServer(('localhost', PORT), OfficeHTTPHandler)
    
    print("\n" + "="*60)
    print(f"🏢 AI Software House (Enterprise & Live Preview Edition) เปิดทำการแล้ว!")
    print(f"👉 เปิดหน้าเว็บได้ที่: http://localhost:{PORT}/office.html")
    print("💡 เลือกโหมด (เพิ่มฟีเจอร์ / ขยายสเกล / สร้างใหม่) และกดรันเว็บจริงจากหน้าจอได้เลยครับ")
    print("="*60 + "\n")
    
    webbrowser.open(f"http://localhost:{PORT}/office.html")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        stop_running_apps()
        print("\nปิดออฟฟิศเรียบร้อยครับ!")