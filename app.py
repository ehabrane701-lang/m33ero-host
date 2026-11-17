

# app.py - نظام استضافة متطور مع دعم Python و Node.js
import os
import json
import re
import subprocess
import psutil
import socket
import sys
import hashlib
import secrets
import time
import threading
import requests
import shutil
import zipfile
import signal
from datetime import datetime, timedelta
from flask import Flask, send_from_directory, request, jsonify, session, redirect, make_response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_DIR = os.path.join(BASE_DIR, "USERS")
os.makedirs(USERS_DIR, exist_ok=True)

app = Flask(__name__, static_folder=BASE_DIR)
app.secret_key = "ZIAD_HOST_GOLD_2026_SUPER_SECRET_KEY"
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# ============== إعدادات البوت والإشعارات ==============
BOT_TOKEN = "9026885072:AAFjPAQQbEQObK5mbTO8eWKA5xXOBEHvWD8"
ADMIN_TELEGRAM_IDS = [7970883512]

def notify_admin(message: str):
    """إرسال إشعار لكل مسؤولي تليجرام"""
    for admin_id in ADMIN_TELEGRAM_IDS:
        try:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": admin_id, "text": message, "parse_mode": "Markdown"},
                timeout=3
            )
        except Exception:
            pass

# ============== قاعدة البيانات ==============
DB_FILE = os.path.join(BASE_DIR, "db.json")

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "plans" not in data:
                    data["plans"] = {}
                if "server_types" not in data:
                    data["server_types"] = ["Python", "Node.js"]
                if "pending_requests" not in data:
                    data["pending_requests"] = {}
                return data
        except Exception:
            pass
    
    admin_hash = hashlib.sha256(ADMIN_PASSWORD_RAW.encode()).hexdigest()
    default_db = {
        "users": {
            ADMIN_EMAIL: {
                "password": admin_hash,
                "is_admin": True,
                "created_at": str(datetime.now()),
                "max_servers": 999999,
                "expiry_days": 3650,
                "last_login": None,
                "telegram_id": 7970883512,
                "api_key": "admin_master_key_ziadhost",
                "storage_limit": 10240000,
                "plan": "admin"
            }
        },
        "servers": {},
        "logs": [],
        "pending_requests": {},
        "plans": {
            "free": {"name": "🎁 مجاني", "storage": 512000, "ram": 256, "cpu": 0.5, "max_servers": 2, "price": 0},
            "4gb": {"name": "💎 4 جيجا", "storage": 4096000, "ram": 1024, "cpu": 1, "max_servers": 5, "price": 5},
            "10gb": {"name": "💎 10 جيجا", "storage": 10240000, "ram": 2048, "cpu": 2, "max_servers": 10, "price": 10},
            "40gb": {"name": "💎 40 جيجا", "storage": 40960000, "ram": 4096, "cpu": 4, "max_servers": 20, "price": 25}
        },
        "server_types": ["Python", "Node.js"]
    }
    save_db(default_db)
    return default_db

def save_db(db_data):
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(db_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ خطأ في حفظ DB: {e}")
        return False

db = load_db()

# ============== المنافذ ==============
PORT_RANGE_START = 8100
PORT_RANGE_END = 9100

def get_assigned_port():
    used = set()
    for srv in db.get("servers", {}).values():
        if srv.get("port"):
            used.add(srv["port"])
    for port in range(PORT_RANGE_START, PORT_RANGE_END):
        if port not in used:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.1)
                result = s.connect_ex(('127.0.0.1', port))
                s.close()
                if result != 0:
                    return port
            except Exception:
                return port
    return PORT_RANGE_START

# ============== دوال مساعدة ==============
def get_current_user():
    if "email" in session:
        return db["users"].get(session["email"])
    return None

def get_user_servers_dir(email):
    safe_email = email.replace('@', '_at_').replace('.', '_dot_')
    path = os.path.join(USERS_DIR, safe_email, "SERVERS")
    os.makedirs(path, exist_ok=True)
    return path

def is_admin(email):
    if email == ADMIN_EMAIL:
        return True
    u = db["users"].get(email)
    return u.get("is_admin", False) if u else False

def get_public_ip():
    try:
        return requests.get('https://api.ipify.org', timeout=3).text
    except Exception:
        return "127.0.0.1"

def generate_api_key():
    return secrets.token_urlsafe(32)

def get_user_by_api_key(api_key):
    for email, udata in db["users"].items():
        if udata.get("api_key") == api_key:
            return email, udata
    return None, None

def uptime_str(start_time):
    if not start_time:
        return "0 ثانية"
    diff = time.time() - start_time
    days = int(diff // 86400)
    hours = int((diff % 86400) // 3600)
    mins = int((diff % 3600) // 60)
    parts = []
    if days > 0: parts.append(f"{days} يوم")
    if hours > 0: parts.append(f"{hours} ساعة")
    if mins > 0: parts.append(f"{mins} دقيقة")
    return " و ".join(parts) if parts else "أقل من دقيقة"

def _check_admin_access():
    if "email" in session and is_admin(session["email"]):
        return True
    api_key = None
    if request.is_json:
        try:
            api_key = request.get_json().get("api_key")
        except Exception:
            pass
    if not api_key:
        api_key = request.args.get("api_key")
    if api_key:
        email, user = get_user_by_api_key(api_key)
        if email and is_admin(email):
            return True
    return False

# ============== دوال Python و Node.js ==============
def detect_main_file(srv_path: str) -> str:
    for candidate in ["main.py", "bot.py", "app.py", "index.py", "run.py", "start.py"]:
        if os.path.exists(os.path.join(srv_path, candidate)):
            return candidate
    py_files = [f for f in os.listdir(srv_path) if f.endswith('.py')]
    return py_files[0] if py_files else ""

def auto_install_deps(srv_path: str, log_file):
    try:
        req = os.path.join(srv_path, "requirements.txt")
        if os.path.exists(req):
            log_file.write(f"\n📦 تثبيت requirements.txt...\n")
            log_file.flush()
            proc = subprocess.Popen(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                cwd=srv_path,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                env=os.environ.copy()
            )
            proc.wait(timeout=180)
            log_file.write("✅ تم تثبيت المكتبات\n")
    except Exception as e:
        log_file.write(f"\n⚠️ تثبيت تلقائي: {e}\n")
    log_file.flush()

def detect_node_main_file(srv_path: str) -> str:
    candidates = ["index.js", "server.js", "app.js", "main.js", "bot.js", "start.js"]
    for candidate in candidates:
        if os.path.exists(os.path.join(srv_path, candidate)):
            return candidate
    js_files = [f for f in os.listdir(srv_path) if f.endswith('.js')]
    return js_files[0] if js_files else ""

def auto_install_node_deps(srv_path: str, log_file):
    try:
        package_json = os.path.join(srv_path, "package.json")
        if os.path.exists(package_json):
            log_file.write(f"\n📦 تثبيت حزم Node.js...\n")
            log_file.flush()
            proc = subprocess.Popen(
                ["npm", "install"],
                cwd=srv_path,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                env=os.environ.copy()
            )
            proc.wait(timeout=180)
            log_file.write("✅ تم تثبيت حزم Node.js\n")
    except Exception as e:
        log_file.write(f"\n⚠️ تثبيت تلقائي Node.js فشل: {e}\n")
    log_file.flush()

def start_server_process(folder):
    srv = db["servers"].get(folder)
    if not srv:
        return False, "السيرفر غير موجود"

    server_type = srv.get("server_type", "Python")
    main_file = srv.get("startup_file", "")
    
    if server_type == "Node.js":
        if not main_file:
            main_file = detect_node_main_file(srv["path"])
            if main_file:
                srv["startup_file"] = main_file
                save_db(db)
            else:
                return False, "لا يوجد ملف تشغيل JavaScript (.js)"
        cmd = ["node", main_file]
    else:
        if not main_file:
            main_file = detect_main_file(srv["path"])
            if main_file:
                srv["startup_file"] = main_file
                save_db(db)
            else:
                return False, "لا يوجد ملف تشغيل Python (.py)"
        cmd = [sys.executable, "-u", main_file]

    file_path = os.path.join(srv["path"], main_file)
    if not os.path.exists(file_path):
        return False, f"الملف '{main_file}' غير موجود"

    port = srv.get("port") or get_assigned_port()
    srv["port"] = port
    save_db(db)

    log_path = os.path.join(srv["path"], "out.log")
    error_path = os.path.join(srv["path"], "errors.log")
    log_file = open(log_path, "a", encoding='utf-8')
    log_file.write(
        f"\n{'='*50}\n🚀 بدء التشغيل ({server_type}) - {datetime.now()}\n"
        f"📁 {main_file}\n🔌 المنفذ: {port}\n{'='*50}\n\n"
    )
    log_file.flush()

    try:
        env = os.environ.copy()
        env["PORT"] = str(port)
        env["SERVER_PORT"] = str(port)
        proc = subprocess.Popen(
            cmd,
            cwd=srv["path"],
            stdout=log_file,
            stderr=open(error_path, "a", encoding='utf-8'),
            env=env,
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None
        )
        srv["status"] = "Running"
        srv["pid"] = proc.pid
        srv["start_time"] = time.time()
        save_db(db)
        return True, "✅ تم التشغيل"
    except Exception as e:
        log_file.write(f"\n❌ خطأ: {e}\n")
        log_file.close()
        return False, str(e)

def stop_server_process(folder):
    srv = db["servers"].get(folder)
    if not srv:
        return
    if srv.get("pid"):
        try:
            p = psutil.Process(srv["pid"])
            if hasattr(os, 'killpg'):
                try:
                    os.killpg(os.getpgid(p.pid), signal.SIGTERM)
                except Exception:
                    pass
            for child in p.children(recursive=True):
                child.kill()
            p.kill()
        except Exception:
            pass
    srv["status"] = "Stopped"
    srv["pid"] = None
    save_db(db)

def restart_server(folder):
    stop_server_process(folder)
    time.sleep(2)
    start_server_process(folder)

def process_monitor():
    while True:
        try:
            for folder, srv in list(db["servers"].items()):
                if srv.get("status") == "Running" and srv.get("pid"):
                    try:
                        p = psutil.Process(srv["pid"])
                        if not p.is_running() or p.status() == psutil.STATUS_ZOMBIE:
                            restart_server(folder)
                    except psutil.NoSuchProcess:
                        restart_server(folder)
                    except Exception:
                        pass
        except Exception:
            pass
        time.sleep(15)

threading.Thread(target=process_monitor, daemon=True).start()

# ============== المسارات الأساسية ==============
@app.route('/')
def home():
    if 'email' in session:
        if is_admin(session['email']):
            return redirect('/admin')
        return redirect('/dashboard')
    return send_from_directory(BASE_DIR, 'landing.html')

@app.route('/login')
def login_page():
    if 'email' in session:
        return redirect('/')
    return send_from_directory(BASE_DIR, 'login.html')

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect('/login')
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/admin')
def admin_panel():
    if 'email' not in session or not is_admin(session['email']):
        return redirect('/login')
    return send_from_directory(BASE_DIR, 'admin_panel.html')

# ============== API المصادقة والتسجيل مع التليجرام ==============
@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()
    
    if not email or not password:
        return jsonify({"success": False, "message": "جميع الحقول مطلوبة"})
    if '@' not in email or '.' not in email:
        return jsonify({"success": False, "message": "البريد الإلكتروني غير صالح"})
    if email in db["users"] or email in db.get("pending_requests", {}):
        return jsonify({"success": False, "message": "البريد الإلكتروني موجود بالفعل أو قيد الانتظار"})

    # حفظ في الطلبات المعلقة ليقوم الأدمن بالموافقة عبر التليجرام
    db.setdefault("pending_requests", {})[email] = {
        "password": hashlib.sha256(password.encode()).hexdigest(),
        "created_at": str(datetime.now())
    }
    save_db(db)

    # إشعار المسؤول عبر التليجرام مع اسم المستخدم
    notify_admin(f"🔔 *طلب تسجيل حساب جديد!*\n📧 البريد: `{email}`\n\nيرجى الدخول إلى لوحة إدارة البوت للقبول أو الرفض.")

    return jsonify({"success": True, "message": "✅ تم إرسال طلبك بنجاح، بانتظار موافقة المسؤول عبر تيليجرام!"})

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD_RAW:
        session.clear()
        session['email'] = email
        session.permanent = True
        db["users"][ADMIN_EMAIL]["last_login"] = str(datetime.now())
        save_db(db)
        return jsonify({"success": True, "redirect": "/admin", "is_admin": True})

    user = db["users"].get(email)
    if user and user["password"] == hashlib.sha256(password.encode()).hexdigest():
        session.clear()
        session['email'] = email
        session.permanent = True
        user["last_login"] = str(datetime.now())
        save_db(db)
        return jsonify({"success": True, "redirect": "/dashboard", "is_admin": False})

    return jsonify({"success": False, "message": "بيانات غير صحيحة أو لم يتم قبول الحساب بعد"})

@app.route('/api/logout', methods=['GET', 'POST'])
def api_logout():
    session.clear()
    return jsonify({"success": True})

@app.route('/api/current_user')
def api_current_user():
    if "email" in session:
        u = db["users"].get(session["email"])
        if u:
            return jsonify({
                "success": True,
                "email": session["email"],
                "is_admin": u.get("is_admin", False),
                "plan": u.get("plan", "free")
            })
    return jsonify({"success": False})

@app.route('/api/create_api_key', methods=['POST'])
def create_api_key():
    if 'email' not in session:
        return jsonify({"success": False, "message": "غير مصرح"}), 401
    email = session['email']
    new_key = generate_api_key()
    db["users"][email]["api_key"] = new_key
    save_db(db)
    return jsonify({"success": True, "api_key": new_key})

# ============== API الإدارة والطلبات المعلقة للتليجرام ==============
@app.route('/api/admin/pending')
def admin_pending():
    if not _check_admin_access():
        return jsonify({"success": False}), 403
    reqs = []
    for email, info in db.get("pending_requests", {}).items():
        reqs.append({
            "username": email,
            "created_at": info.get("created_at")
        })
    return jsonify({"success": True, "requests": reqs})

@app.route('/api/admin/approve', methods=['POST'])
def admin_approve():
    if not _check_admin_access():
        return jsonify({"success": False}), 403
    data = request.get_json()
    username = data.get("username", "").strip().lower()
    
    if username in db.get("pending_requests", {}):
        req_info = db["pending_requests"].pop(username)
        db["users"][username] = {
            "password": req_info["password"],
            "is_admin": False,
            "created_at": str(datetime.now()),
            "max_servers": db["plans"]["free"]["max_servers"],
            "expiry_days": 365,
            "last_login": None,
            "telegram_id": None,
            "api_key": generate_api_key(),
            "storage_limit": db["plans"]["free"]["storage"],
            "plan": "free"
        }
        save_db(db)
        
        # إنشاء المجلدات الخاصة بالمستخدم
        safe_email = username.replace('@', '_at_').replace('.', '_dot_')
        user_dir = os.path.join(USERS_DIR, safe_email)
        os.makedirs(user_dir, exist_ok=True)
        os.makedirs(os.path.join(user_dir, "SERVERS"), exist_ok=True)
        
        return jsonify({"success": True, "message": "تم قبول المستخدم بنجاح"})
    return jsonify({"success": False, "message": "الطلب غير موجود"})

@app.route('/api/admin/reject', methods=['POST'])
def admin_reject():
    if not _check_admin_access():
        return jsonify({"success": False}), 403
    data = request.get_json()
    username = data.get("username", "").strip().lower()
    
    if username in db.get("pending_requests", {}):
        db["pending_requests"].pop(username)
        save_db(db)
        return jsonify({"success": True, "message": "تم رفض الطلب"})
    return jsonify({"success": False, "message": "الطلب غير موجود"})

@app.route('/api/admin/users')
def admin_users():
    if not _check_admin_access():
        return jsonify({"success": False}), 403
    users_list = []
    for uemail, udata in db["users"].items():
        users_list.append({
            "username": uemail,
            "is_admin": udata.get("is_admin", False),
            "created_at": udata.get("created_at"),
            "max_servers": udata.get("max_servers", 1),
            "plan": udata.get("plan", "free")
        })
    return jsonify({"success": True, "users": users_list})

@app.route('/api/admin/delete-user', methods=['POST'])
def admin_delete_user():
    if not _check_admin_access():
        return jsonify({"success": False}), 403
    data = request.get_json()
    username = data.get("username", "").strip().lower()
    if username == ADMIN_EMAIL:
        return jsonify({"success": False, "message": "لا يمكن حذف الأدمن"})
    
    if username in db["users"]:
        for fid, srv in list(db["servers"].items()):
            if srv["owner"] == username:
                stop_server_process(fid)
                if os.path.exists(srv["path"]):
                    shutil.rmtree(srv["path"], ignore_errors=True)
                del db["servers"][fid]
        
        del db["users"][username]
        save_db(db)
        return jsonify({"success": True, "message": f"تم حذف المستخدم"})
    return jsonify({"success": False, "message": "المستخدم غير موجود"})

# ============== بقية الروابط والمخدمات ==============
@app.route('/api/system/metrics')
def get_metrics():
    return jsonify({
        "cpu": psutil.cpu_percent(),
        "memory": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('/').percent
    })

@app.route('/api/servers')
def list_servers():
    if "email" not in session:
        return jsonify({"success": False}), 401
    user_servers = []
    for folder, srv in db["servers"].items():
        if srv["owner"] == session["email"]:
            user_servers.append({
                "folder": folder,
                "title": srv["name"],
                "server_type": srv.get("server_type", "Python"),
                "status": srv.get("status", "Stopped"),
                "uptime": uptime_str(srv.get("start_time")) if srv.get("status") == "Running" else "0 ثانية",
                "port": srv.get("port", "N/A"),
                "type": srv.get("server_type", "Python")
            })
    return jsonify({"success": True, "servers": user_servers})

@app.route('/api/server/add', methods=['POST'])
@app.route('/api/bot/create_server', methods=['POST'])
def add_server():
    api_key = request.headers.get('api_key') or (request.get_json() or {}).get("api_key")
    email = None
    if "email" in session:
        email = session["email"]
    elif api_key:
        email, _ = get_user_by_api_key(api_key)
        
    if not email:
        return jsonify({"success": False, "message": "غير مصرح"}), 401
    
    user = db["users"].get(email)
    data = request.get_json()
    name = data.get("name", "").strip()
    server_type = data.get("server_type", "Python")
    
    if not name:
        return jsonify({"success": False, "message": "الرجاء إدخال اسم للسيرفر"})
    
    safe_email = email.replace('@', '_at_').replace('.', '_dot_')
    folder = f"{safe_email}_{re.sub(r'[^a-zA-Z0-9]', '', name)}_{int(time.time())}"
    path = os.path.join(get_user_servers_dir(email), folder)
    os.makedirs(path, exist_ok=True)
    assigned_port = get_assigned_port()
    
    db["servers"][folder] = {
        "name": name,
        "owner": email,
        "path": path,
        "server_type": server_type,
        "status": "Stopped",
        "created_at": str(datetime.now()),
        "startup_file": "",
        "pid": None,
        "port": assigned_port,
        "plan": user.get("plan", "free")
    }
    save_db(db)
    return jsonify({"success": True, "message": f"✅ تم إنشاء {server_type} سيرفر: {name}"})

@app.route('/api/server/action/<folder>/<action>', methods=['POST'])
def server_action(folder, action):
    if "email" not in session:
        return jsonify({"success": False}), 401
    srv = db["servers"].get(folder)
    if not srv or srv["owner"] != session["email"]:
        return jsonify({"success": False})
    
    if action == "start":
        ok, msg = start_server_process(folder)
        return jsonify({"success": ok, "message": msg})
    elif action == "stop":
        stop_server_process(folder)
        return jsonify({"success": True})
    elif action == "restart":
        restart_server(folder)
        return jsonify({"success": True})
    elif action == "delete":
        stop_server_process(folder)
        if os.path.exists(srv["path"]):
            shutil.rmtree(srv["path"], ignore_errors=True)
        del db["servers"][folder]
        save_db(db)
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route('/api/bot/verify', methods=['POST'])
def bot_verify():
    data = request.get_json()
    api_key = data.get('api_key', '').strip()
    if not api_key:
        return jsonify({"success": False})
    email, user = get_user_by_api_key(api_key)
    if not email:
        return jsonify({"success": False})
    return jsonify({
        "success": True,
        "username": email,
        "is_admin": is_admin(email),
        "max_servers": user.get("max_servers", 2)
    })

@app.route('/api/bot/servers', methods=['GET'])
def bot_list_servers():
    api_key = request.args.get('api_key')
    if not api_key:
        return jsonify({"success": False}), 401
    email, _ = get_user_by_api_key(api_key)
    if not email:
        return jsonify({"success": False}), 401
    
    user_servers = []
    for folder, srv in db["servers"].items():
        if srv["owner"] == email:
            user_servers.append({
                "folder": folder,
                "title": srv["name"],
                "status": srv.get("status", "Stopped"),
                "port": srv.get("port", "N/A"),
                "type": srv.get("server_type", "Python"),
                "uptime": uptime_str(srv.get("start_time")) if srv.get("status") == "Running" else "0 ثانية"
            })
    return jsonify({"success": True, "servers": user_servers})

@app.route('/api/bot/server/action', methods=['POST'])
def bot_server_action():
    data = request.get_json()
    api_key = data.get('api_key')
    folder = data.get('folder')
    action = data.get('action')
    if not all([api_key, folder, action]):
        return jsonify({"success": False}), 400
    email, _ = get_user_by_api_key(api_key)
    if not email:
        return jsonify({"success": False}), 401
    srv = db["servers"].get(folder)
    if not srv or srv["owner"] != email:
        return jsonify({"success": False}), 403
    
    if action == "start":
        ok, msg = start_server_process(folder)
        return jsonify({"success": ok, "message": msg})
    elif action == "stop":
        stop_server_process(folder)
        return jsonify({"success": True})
    elif action == "restart":
        restart_server(folder)
        return jsonify({"success": True})
    elif action == "delete":
        stop_server_process(folder)
        if os.path.exists(srv["path"]):
            shutil.rmtree(srv["path"], ignore_errors=True)
        del db["servers"][folder]
        save_db(db)
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route('/api/bot/console', methods=['GET'])
def bot_console():
    api_key = request.args.get('api_key')
    folder = request.args.get('folder')
    if not api_key or not folder:
        return jsonify({"success": False}), 400
    email, _ = get_user_by_api_key(api_key)
    if not email:
        return jsonify({"success": False}), 401
    srv = db["servers"].get(folder)
    if not srv or srv["owner"] != email:
        return jsonify({"success": False}), 403
    
    log_path = os.path.join(srv["path"], "out.log")
    logs = ""
    if os.path.exists(log_path):
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                logs = f.read()[-3000:]
        except Exception:
            pass
    return jsonify({"success": True, "logs": logs})

@app.route('/api/bot/errors', methods=['GET'])
def bot_errors():
    api_key = request.args.get('api_key')
    folder = request.args.get('folder')
    if not api_key or not folder:
        return jsonify({"success": False}), 400
    email, _ = get_user_by_api_key(api_key)
    if not email:
        return jsonify({"success": False}), 401
    srv = db["servers"].get(folder)
    if not srv or srv["owner"] != email:
        return jsonify({"success": False}), 403
    
    error_path = os.path.join(srv["path"], "errors.log")
    errors = "✅ لا توجد أخطاء"
    if os.path.exists(error_path):
        try:
            with open(error_path, 'r', encoding='utf-8', errors='ignore') as f:
                errors = f.read()[-3000:]
        except Exception:
            pass
    return jsonify({"success": True, "errors": errors if errors else "✅ لا توجد أخطاء"})

@app.route('/api/bot/install', methods=['POST'])
def bot_install():
    data = request.get_json()
    api_key = data.get('api_key')
    folder = data.get('folder')
    if not api_key or not folder:
        return jsonify({"success": False}), 400
    email, _ = get_user_by_api_key(api_key)
    if not email:
        return jsonify({"success": False}), 401
    srv = db["servers"].get(folder)
    if not srv or srv["owner"] != email:
        return jsonify({"success": False}), 403
    
    if srv.get("server_type") == "Node.js":
        threading.Thread(target=auto_install_node_deps, args=(srv["path"], open(os.path.join(srv["path"], "out.log"), "id" if False else "a", encoding='utf-8')), daemon=True).start()
    else:
        threading.Thread(target=auto_install_deps, args=(srv["path"], open(os.path.join(srv["path"], "out.log"), "a", encoding='utf-8')), daemon=True).start()
    return jsonify({"success": True, "message": "📦 بدأ تثبيت المكتبات"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
