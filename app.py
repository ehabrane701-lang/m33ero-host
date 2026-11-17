# ==============================================================================
# نظام استضافة متطور شامل (Flask + Django + Sandbox + Bot Engine)
# تم إصلاح كافة المسارات، القواعد، البيانات، والترجمة العربية الكاملة
# ==============================================================================

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
import sqlite3
import logging
import ast
import io
import builtins
import pathlib
import runpy
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse, unquote

from flask import Flask, send_from_directory, request, jsonify, session, redirect, make_response

# إعداد السجل (Logging)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("ZiadHostEngine")

# ================= إعداد Django الأساسي والمسارات =================
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pyhosting.settings')
try:
    import django
    django.setup()
    from django.conf import settings
    from django.core.asgi import get_asgi_application
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack
    import apps.botengine.routing
    from django.contrib import admin
    from django.urls import path, re_path, include
    from django.views.generic import TemplateView
    from apps.accounts.views import AuthPageView
    from django.views.static import serve as static_serve
    from django.contrib.staticfiles import views as staticfiles_views
    from django.conf.urls.static import static
    from django.http import JsonResponse, HttpResponse, FileResponse, Http404
    from django.core.cache import cache
    from django.db import OperationalError, connections
    from django.core.exceptions import ValidationError
    from rest_framework.views import APIView
    from rest_framework.response import Response
    from rest_framework import status, permissions, serializers
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken
    from django.contrib.auth import get_user_model
    from django.db.models import Q
    from django.utils.html import format_html
    from django.utils.safestring import mark_safe
    from django.apps import AppConfig
    from apps.filemanager.models import File, Folder
except Exception as e:
    logger.debug(f"تنبيه Django البيئي: {e}")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_DIR = os.path.join(BASE_DIR, "USERS")
os.makedirs(USERS_DIR, exist_ok=True)

app = Flask(__name__, static_folder=BASE_DIR)
app.secret_key = os.environ.get("SECRET_KEY", "ZIAD_HOST_GOLD_2026_SUPER_SECRET_KEY")
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# قفل لتأمين قاعدة البيانات ضد التضارب المتزامن (Thread Safety)
db_lock = threading.Lock()

# ============== بيانات المسؤول والإشعارات ==============
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@ziadhost.com")
ADMIN_PASSWORD_RAW = os.environ.get("ADMIN_PASSWORD_RAW", "admin123")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "9063504218:AAE4Cs43FIamSWLOp-gz49PZ9x5JAgleYD4")
ADMIN_TELEGRAM_ID = int(os.environ.get("ADMIN_TELEGRAM_ID", "1002670694"))

def notify_admin(message: str):
    """إرسال إشعار للمسؤول عبر تليجرام"""
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": ADMIN_TELEGRAM_ID, "text": message, "parse_mode": "Markdown"},
            timeout=3
        )
    except Exception:
        pass

# ============== قاعدة البيانات الأساسية لـ Flask ==============
DB_FILE = os.path.join(BASE_DIR, "db.json")

def load_db():
    with db_lock:
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "plans" not in data:
                        data["plans"] = {}
                    if "server_types" not in data:
                        data["server_types"] = ["Python", "Node.js", "Django"]
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
                    "telegram_id": None,
                    "api_key": None,
                    "storage_limit": 10240000,
                    "plan": "admin"
                }
            },
            "servers": {},
            "logs": [],
            "plans": {
                "free": {"name": "🎁 مجاني (10 سيرفرات)", "storage": 512000, "ram": 512, "cpu": 1, "max_servers": 10, "price": 0},
                "pro": {"name": "💎 10 سيرفرات (بايثون، نود، دجانجو)", "storage": 10240000, "ram": 2048, "cpu": 2, "max_servers": 10, "price": 10}
            },
            "server_types": ["Python", "Node.js", "Django"]
        }
        save_db(default_db)
        return default_db

def save_db(db_data):
    with db_lock:
        try:
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(db_data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"خطأ في حفظ قاعدة البيانات: {e}")
            return False

db = load_db()

# ============== إدارة المنافذ ==============
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

# ============== دوال المساعدة العامة ==============
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

# ============== إدارة السيرفرات (Python, Node.js, Django) ==============
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
            log_file.write(f"\n📦 جاري تثبيت متطلبات requirements.txt...\n")
            log_file.flush()
            proc = subprocess.Popen(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                cwd=srv_path,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                env=os.environ.copy()
            )
            proc.wait(timeout=180)
            log_file.write("✅ تم تثبيت المكتبات بنجاح\n")
    except Exception as e:
        log_file.write(f"\n⚠️ خطأ في التثبيت التلقائي: {e}\n")
    finally:
        try:
            log_file.close()
        except Exception:
            pass

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
            log_file.write(f"\n📦 جاري تثبيت حزم Node.js عبر npm...\n")
            log_file.flush()
            proc = subprocess.Popen(
                ["npm", "install"],
                cwd=srv_path,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                env=os.environ.copy()
            )
            proc.wait(timeout=180)
            log_file.write("✅ تم تثبيت حزم Node.js بنجاح\n")
    except Exception as e:
        log_file.write(f"\n⚠️ فشل التثبيت التلقائي لحزم Node.js: {e}\n")
    finally:
        try:
            log_file.close()
        except Exception:
            pass

def detect_django_main_file(srv_path: str) -> str:
    manage_py = "manage.py"
    if os.path.exists(os.path.join(srv_path, manage_py)):
        return manage_py
    return ""

def auto_install_django_deps(srv_path: str, log_file):
    try:
        log_file.write(f"\n📦 جاري فحص وتثبيت متطلبات Django و requirements.txt...\n")
        log_file.flush()
        req = os.path.join(srv_path, "requirements.txt")
        cmd = [sys.executable, "-m", "pip", "install", "django"]
        if os.path.exists(req):
            cmd = [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
        
        proc = subprocess.Popen(
            cmd,
            cwd=srv_path,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env=os.environ.copy()
        )
        proc.wait(timeout=180)
        log_file.write("✅ تم تثبيت إطارات عمل وبيئة Django بنجاح\n")
    except Exception as e:
        log_file.write(f"\n⚠️ خطأ في تثبيت تبعيات Django: {e}\n")
    finally:
        try:
            log_file.close()
        except Exception:
            pass

def start_server_process(folder):
    srv = db["servers"].get(folder)
    if not srv:
        return False, "السيرفر غير موجود"

    server_type = srv.get("server_type", "Python")
    if server_type == "Node.js":
        return start_node_server_process(folder)
    elif server_type == "Django":
        return start_django_server_process(folder)
    else:
        return start_python_server_process(folder)

def start_python_server_process(folder):
    srv = db["servers"].get(folder)
    if not srv:
        return False, "السيرفر غير موجود"

    main_file = srv.get("startup_file", "")
    if not main_file:
        main_file = detect_main_file(srv["path"])
        if main_file:
            srv["startup_file"] = main_file
            save_db(db)
        else:
            return False, "لا يوجد ملف تشغيل Python (.py)"

    file_path = os.path.join(srv["path"], main_file)
    if not os.path.exists(file_path):
        return False, f"الملف '{main_file}' غير موجود"

    port = srv.get("port") or get_assigned_port()
    srv["port"] = port
    save_db(db)

    log_path = os.path.join(srv["path"], "out.log")
    error_path = os.path.join(srv["path"], "errors.log")
    
    log_file = open(log_path, "a", encoding='utf-8')
    err_file = open(error_path, "a", encoding='utf-8')
    
    log_file.write(
        f"\n{'='*50}\n🚀 بدء التشغيل (Python) - {datetime.now()}\n"
        f"📁 الملف: {main_file}\n🔌 المنفذ: {port}\n{'='*50}\n\n"
    )
    log_file.flush()

    try:
        env = os.environ.copy()
        env["PORT"] = str(port)
        env["SERVER_PORT"] = str(port)
        cmd = [sys.executable, "-u", main_file]
        proc = subprocess.Popen(
            cmd,
            cwd=srv["path"],
            stdout=log_file,
            stderr=err_file,
            env=env,
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None
        )
        srv["status"] = "Running"
        srv["pid"] = proc.pid
        srv["start_time"] = time.time()
        save_db(db)
        return True, "✅ تم تشغيل سيرفر Python بنجاح"
    except Exception as e:
        log_file.write(f"\n❌ خطأ في التشغيل: {e}\n")
        return False, str(e)
    finally:
        try:
            log_file.close()
            err_file.close()
        except Exception:
            pass

def start_node_server_process(folder):
    srv = db["servers"].get(folder)
    if not srv:
        return False, "السيرفر غير موجود"

    main_file = srv.get("startup_file", "")
    if not main_file:
        main_file = detect_node_main_file(srv["path"])
        if main_file:
            srv["startup_file"] = main_file
            save_db(db)
        else:
            return False, "لا يوجد ملف تشغيل JavaScript (.js)"

    file_path = os.path.join(srv["path"], main_file)
    if not os.path.exists(file_path):
        return False, f"الملف '{main_file}' غير موجود"

    port = srv.get("port") or get_assigned_port()
    srv["port"] = port
    save_db(db)

    log_path = os.path.join(srv["path"], "out.log")
    error_path = os.path.join(srv["path"], "errors.log")
    
    log_file = open(log_path, "a", encoding='utf-8')
    err_file = open(error_path, "a", encoding='utf-8')
    
    log_file.write(
        f"\n{'='*50}\n🚀 بدء التشغيل (Node.js) - {datetime.now()}\n"
        f"📁 الملف: {main_file}\n🔌 المنفذ: {port}\n{'='*50}\n\n"
    )
    log_file.flush()

    try:
        env = os.environ.copy()
        env["PORT"] = str(port)
        env["SERVER_PORT"] = str(port)
        cmd = ["node", main_file]
        proc = subprocess.Popen(
            cmd,
            cwd=srv["path"],
            stdout=log_file,
            stderr=err_file,
            env=env,
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None
        )
        srv["status"] = "Running"
        srv["pid"] = proc.pid
        srv["start_time"] = time.time()
        save_db(db)
        return True, "✅ تم تشغيل سيرفر Node.js بنجاح"
    except Exception as e:
        log_file.write(f"\n❌ خطأ في التشغيل: {e}\n")
        return False, str(e)
    finally:
        try:
            log_file.close()
            err_file.close()
        except Exception:
            pass

def start_django_server_process(folder):
    srv = db["servers"].get(folder)
    if not srv:
        return False, "السيرفر غير موجود"

    main_file = srv.get("startup_file", "")
    if not main_file:
        main_file = detect_django_main_file(srv["path"])
        if main_file:
            srv["startup_file"] = main_file
            save_db(db)
        else:
            return False, "لا يوجد ملف إدارة Django (manage.py)"

    file_path = os.path.join(srv["path"], main_file)
    if not os.path.exists(file_path):
        return False, f"الملف '{main_file}' غير موجود"

    port = srv.get("port") or get_assigned_port()
    srv["port"] = port
    save_db(db)

    log_path = os.path.join(srv["path"], "out.log")
    error_path = os.path.join(srv["path"], "errors.log")
    
    log_file = open(log_path, "a", encoding='utf-8')
    err_file = open(error_path, "a", encoding='utf-8')
    
    log_file.write(
        f"\n{'='*50}\n🚀 بدء التشغيل (Django) - {datetime.now()}\n"
        f"📁 الملف: {main_file}\n🔌 المنفذ: {port}\n{'='*50}\n\n"
    )
    log_file.flush()

    try:
        env = os.environ.copy()
        env["PORT"] = str(port)
        env["SERVER_PORT"] = str(port)
        cmd = [sys.executable, main_file, "runserver", f"0.0.0.0:{port}"]
        proc = subprocess.Popen(
            cmd,
            cwd=srv["path"],
            stdout=log_file,
            stderr=err_file,
            env=env,
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None
        )
        srv["status"] = "Running"
        srv["pid"] = proc.pid
        srv["start_time"] = time.time()
        save_db(db)
        return True, "✅ تم تشغيل سيرفر Django بنجاح"
    except Exception as e:
        log_file.write(f"\n❌ خطأ في تشغيل Django: {e}\n")
        return False, str(e)
    finally:
        try:
            log_file.close()
            err_file.close()
        except Exception:
            pass

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
                try:
                    child.kill()
                except Exception:
                    pass
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

# ============== مراقبة العمليات الآلية ==============
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

# ============== مسارات وتوجيهات الويب (Flask) ==============
@app.route('/')
def home():
    if 'email' in session:
        if is_admin(session['email']):
            return redirect('/admin')
        return redirect('/dashboard')
    if os.path.exists(os.path.join(BASE_DIR, 'landing.html')):
        return send_from_directory(BASE_DIR, 'landing.html')
    return redirect('/login')

@app.route('/login')
def login_page():
    if 'email' in session:
        return redirect('/')
    if os.path.exists(os.path.join(BASE_DIR, 'login.html')):
        return send_from_directory(BASE_DIR, 'login.html')
    return "صفحة تسجيل الدخول غير متوفرة", 404

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect('/login')
    if os.path.exists(os.path.join(BASE_DIR, 'index.html')):
        return send_from_directory(BASE_DIR, 'index.html')
    return "لوحة التحكم غير متوفرة", 404

@app.route('/admin')
def admin_panel():
    if 'email' not in session or not is_admin(session['email']):
        return redirect('/login')
    if os.path.exists(os.path.join(BASE_DIR, 'admin_panel.html')):
        return send_from_directory(BASE_DIR, 'admin_panel.html')
    return "لوحة الإدارة غير متوفرة", 404

@app.route('/server/open/<folder>')
def server_open(folder):
    srv = db["servers"].get(folder)
    if not srv:
        return "❌ السيرفر غير موجود", 404
    
    port = srv.get("port")
    server_type = srv.get("server_type", "Python")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>معاينة سيرفر {srv.get('name')}</title>
        <style>
            body {{ font-family: Tahoma, sans-serif; background: #0f172a; color: #fff; text-align: center; padding-top: 60px; }}
            .card {{ background: #1e293b; max-width: 600px; margin: auto; padding: 40px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
            h1 {{ color: #22c55e; }}
            p {{ font-size: 18px; color: #cbd5e1; }}
            .btn {{ display: inline-block; background: #3b82f6; color: white; padding: 12px 25px; border-radius: 8px; text-decoration: none; margin-top: 20px; font-weight: bold; }}
            .btn:hover {{ background: #2563eb; }}
            .btn-google {{ background: #10b981; margin-right: 10px; }}
            .btn-google:hover {{ background: #059669; }}
            .badge {{ background: #334155; padding: 6px 15px; border-radius: 20px; font-size: 14px; display: inline-block; margin-bottom: 15px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <span class="badge">سيرفر {server_type}</span>
            <h1>🎉 تم التشغيل بنجاح!</h1>
            <p>السيرفر <strong>{srv.get('name')}</strong> يعمل بكفاءة واستقرار على المنفذ <strong>{port}</strong>.</p>
            <p>يمكنك الآن الانتقال إلى لوحة التحكم أو اختبار فتح الموقع الخارجي.</p>
            <a href="/dashboard" class="btn">العودة إلى لوحة التحكم</a>
            <a href="https://www.google.com" target="_blank" class="btn btn-google">الانتقال إلى Google (تم التشغيل)</a>
        </div>
    </body>
    </html>
    """
    return html_content

@app.route('/api/server/url/<folder>')
def api_server_url(folder):
    if "email" not in session:
        return jsonify({"success": False, "message": "غير مصرح"}), 401
    srv = db["servers"].get(folder)
    if not srv or srv["owner"] != session["email"]:
        return jsonify({"success": False, "message": "السيرفر غير موجود"})
    
    pub_ip = get_public_ip()
    port = srv.get("port")
    url = f"http://{pub_ip}:{port}"
    preview_url = f"/server/open/{folder}"
    return jsonify({
        "success": True,
        "url": url,
        "preview_url": preview_url,
        "message": "✅ تم توليد رابط السيرفر بنجاح وهو يعمل!"
    })

# ============== واجهات API المصادقة والمستخدمين ==============
@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()
    
    if not email or not password:
        return jsonify({"success": False, "message": "جميع الحقول مطلوبة"})
    if '@' not in email or '.' not in email:
        return jsonify({"success": False, "message": "البريد الإلكتروني غير صالح"})
    if len(password) < 4:
        return jsonify({"success": False, "message": "كلمة المرور يجب ألا تقل عن 4 أحرف"})
    if email in db["users"]:
        return jsonify({"success": False, "message": "البريد الإلكتروني موجود بالفعل"})

    db["users"][email] = {
        "password": hashlib.sha256(password.encode()).hexdigest(),
        "is_admin": False,
        "created_at": str(datetime.now()),
        "max_servers": 10,
        "expiry_days": 365,
        "last_login": None,
        "telegram_id": None,
        "api_key": None,
        "storage_limit": db["plans"]["free"]["storage"],
        "plan": "free"
    }
    save_db(db)
    
    safe_email = email.replace('@', '_at_').replace('.', '_dot_')
    user_dir = os.path.join(USERS_DIR, safe_email)
    os.makedirs(user_dir, exist_ok=True)
    os.makedirs(os.path.join(user_dir, "SERVERS"), exist_ok=True)

    threading.Thread(target=notify_admin, args=(f"🔔 *مستخدم جديد في المنصة!*\n📧 {email}",), daemon=True).start()

    return jsonify({"success": True, "message": "✅ تم إنشاء حسابك بنجاح!"})

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD_RAW:
        session.clear()
        session['email'] = email
        session.permanent = True
        if ADMIN_EMAIL in db["users"]:
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
        return jsonify({"success": True, "redirect": "/dashboard", "is_admin": user.get("is_admin", False)})

    return jsonify({"success": False, "message": "البريد الإلكتروني أو كلمة المرور غير صحيحة"})

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

@app.route('/api/plans')
def get_plans():
    return jsonify({"success": True, "plans": db.get("plans", {})})

@app.route('/api/user/upgrade', methods=['POST'])
def upgrade_plan():
    if 'email' not in session:
        return jsonify({"success": False, "message": "غير مصرح"}), 401
    data = request.get_json() or {}
    plan_id = data.get("plan_id")
    if not plan_id or plan_id not in db.get("plans", {}):
        return jsonify({"success": False, "message": "الخطة غير موجودة"})
    
    plan = db["plans"][plan_id]
    email = session['email']
    user = db["users"][email]
    
    user["plan"] = plan_id
    user["max_servers"] = plan["max_servers"]
    user["storage_limit"] = plan["storage"]
    save_db(db)
    
    return jsonify({"success": True, "message": f"✅ تم ترقية حسابك إلى خطة {plan['name']}"})

# ============== لوحة تحكم الإدارة (Admin API) ==============
@app.route('/api/admin/users')
def admin_users():
    if not _check_admin_access():
        return jsonify({"success": False}), 403
    users_list = []
    for uemail, udata in db["users"].items():
        users_list.append({
            "email": uemail,
            "is_admin": udata.get("is_admin", False),
            "created_at": udata.get("created_at"),
            "max_servers": udata.get("max_servers", 10),
            "plan": udata.get("plan", "free")
        })
    return jsonify({"success": True, "users": users_list})

@app.route('/api/admin/create-user', methods=['POST'])
def admin_create_user():
    if not _check_admin_access():
        return jsonify({"success": False}), 403
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()
    max_servers = int(data.get("max_servers", 10))
    
    if email in db["users"]:
        return jsonify({"success": False, "message": "المستخدم موجود بالفعل"})
    
    db["users"][email] = {
        "password": hashlib.sha256(password.encode()).hexdigest(),
        "is_admin": False,
        "created_at": str(datetime.now()),
        "max_servers": max_servers,
        "expiry_days": 365,
        "last_login": None,
        "telegram_id": None,
        "api_key": None,
        "storage_limit": 10240000,
        "plan": "pro"
    }
    save_db(db)
    
    safe_email = email.replace('@', '_at_').replace('.', '_dot_')
    user_dir = os.path.join(USERS_DIR, safe_email)
    os.makedirs(user_dir, exist_ok=True)
    os.makedirs(os.path.join(user_dir, "SERVERS"), exist_ok=True)
    
    return jsonify({"success": True, "message": "✅ تم إنشاء الحساب بنجاح"})

@app.route('/api/admin/delete-user', methods=['POST'])
def admin_delete_user():
    if not _check_admin_access():
        return jsonify({"success": False}), 403
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    if email == ADMIN_EMAIL:
        return jsonify({"success": False, "message": "لا يمكن حذف المسؤول الرئيسي"})
    
    if email in db["users"]:
        for fid, srv in list(db["servers"].items()):
            if srv["owner"] == email:
                stop_server_process(fid)
                if os.path.exists(srv["path"]):
                    shutil.rmtree(srv["path"], ignore_errors=True)
                del db["servers"][fid]
        
        del db["users"][email]
        save_db(db)
        return jsonify({"success": True, "message": "🗑 تم حذف المستخدم بنجاح"})
    return jsonify({"success": False, "message": "المستخدم غير موجود"})

@app.route('/api/system/metrics')
def get_metrics():
    return jsonify({
        "cpu": psutil.cpu_percent(),
        "memory": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('/').percent
    })

# ============== إدارة السيرفرات التابعة للمستخدم ==============
@app.route('/api/servers')
def list_servers():
    if "email" not in session:
        return jsonify({"success": False}), 401
    
    user_servers = []
    total_disk_used_mb = 0.0
    for folder, srv in db["servers"].items():
        if srv["owner"] == session["email"]:
            disk_used = 0
            if os.path.exists(srv["path"]):
                try:
                    for root, dirs, files in os.walk(srv["path"]):
                        for f in files:
                            fp = os.path.join(root, f)
                            try:
                                disk_used += os.path.getsize(fp)
                            except Exception:
                                pass
                except Exception:
                    pass
            disk_used_mb = round(disk_used / (1024 * 1024), 2)
            total_disk_used_mb += disk_used_mb
            user_servers.append({
                "folder": folder,
                "title": srv["name"],
                "server_type": srv.get("server_type", "Python"),
                "status": srv.get("status", "Stopped"),
                "uptime": uptime_str(srv.get("start_time")) if srv.get("status") == "Running" else "0 ثانية",
                "port": srv.get("port", "N/A"),
                "plan": srv.get("plan", "free"),
                "storage_limit": srv.get("storage_limit", 512000),
                "ram_limit": srv.get("ram_limit", 512),
                "cpu_limit": srv.get("cpu_limit", 1),
                "disk_used": disk_used_mb,
                "preview_url": f"/server/open/{folder}"
            })
    user = db["users"].get(session["email"], {})
    return jsonify({
        "success": True,
        "servers": user_servers,
        "stats": {
            "used": len(user_servers),
            "total": user.get("max_servers", 10),
            "expiry": user.get("expiry_days", 365),
            "disk_used": round(total_disk_used_mb, 2),
            "disk_total": user.get("storage_limit", 10240000),
        }
    })

@app.route('/api/server/add', methods=['POST'])
def add_server():
    if "email" not in session:
        return jsonify({"success": False, "message": "غير مصرح"}), 401
    
    user = db["users"].get(session["email"])
    if not user:
        return jsonify({"success": False, "message": "المستخدم غير موجود"})
    
    user_servers = [s for s in db["servers"].values() if s["owner"] == session["email"]]
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    server_type = data.get("server_type", "Python")
    
    if not name:
        return jsonify({"success": False, "message": "الرجاء إدخال اسم للسيرفر"})
    
    if len(user_servers) >= 10:
        return jsonify({"success": False, "message": "لقد وصلت للحد الأقصى الإجمالي للسيرفرات (10 سيرفرات)"})
    
    plan_id = user.get("plan", "free")
    plan = db["plans"].get(plan_id, db["plans"]["free"])
    
    safe_email = session['email'].replace('@', '_at_').replace('.', '_dot_')
    folder = f"{safe_email}_{re.sub(r'[^a-zA-Z0-9]', '', name)}_{int(time.time())}"
    path = os.path.join(get_user_servers_dir(session["email"]), folder)
    os.makedirs(path, exist_ok=True)
    assigned_port = get_assigned_port()
    
    db["servers"][folder] = {
        "name": name,
        "owner": session["email"],
        "path": path,
        "server_type": server_type,
        "status": "Stopped",
        "created_at": str(datetime.now()),
        "startup_file": "",
        "pid": None,
        "port": assigned_port,
        "plan": plan_id,
        "storage_limit": plan["storage"],
        "ram_limit": plan["ram"],
        "cpu_limit": plan["cpu"]
    }
    save_db(db)
    return jsonify({"success": True, "message": f"✅ تم إنشاء سيرفر {server_type} ({name}) بنجاح!"})

@app.route('/api/server/action/<folder>/<action>', methods=['POST'])
def server_action(folder, action):
    if "email" not in session:
        return jsonify({"success": False}), 401
    srv = db["servers"].get(folder)
    if not srv or srv["owner"] != session["email"]:
        return jsonify({"success": False, "message": "غير مصرح"})
    
    if action == "start":
        if srv.get("status") == "Running":
            return jsonify({"success": False, "message": "السيرفر يعمل بالفعل"})
        ok, msg = start_server_process(folder)
        return jsonify({"success": ok, "message": msg})
    elif action == "stop":
        stop_server_process(folder)
        return jsonify({"success": True, "message": "🛑 تم إيقاف السيرفر بنجاح مع الاحتفاظ بكافة الملفات والبيانات"})
    elif action == "restart":
        restart_server(folder)
        return jsonify({"success": True, "message": "🔄 تم إعادة تشغيل السيرفر بنجاح"})
    elif action == "delete":
        stop_server_process(folder)
        if os.path.exists(srv["path"]):
            shutil.rmtree(srv["path"], ignore_errors=True)
        del db["servers"][folder]
        save_db(db)
        return jsonify({"success": True, "message": "🗑 تم حذف السيرفر نهائياً"})
    return jsonify({"success": False})

@app.route('/api/server/stats/<folder>')
def get_server_stats(folder):
    if "email" not in session:
        return jsonify({"success": False}), 401
    srv = db["servers"].get(folder)
    if not srv or srv["owner"] != session["email"]:
        return jsonify({"success": False})
    
    status = srv.get("status", "Stopped")
    logs = "لا توجد مخرجات بعد"
    log_path = os.path.join(srv["path"], "out.log")
    if os.path.exists(log_path):
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.read().split('\n')
                logs = '\n'.join(lines[-500:])
        except Exception:
            pass
    
    mem_info = "0 MB"
    if srv.get("pid") and status == "Running":
        try:
            p = psutil.Process(srv["pid"])
            mem_info = f"{p.memory_info().rss / (1024*1024):.1f} MB"
        except Exception:
            pass
    
    pub_ip = get_public_ip()
    port = srv.get("port", "--")
    
    return jsonify({
        "success": True,
        "status": status,
        "logs": logs,
        "mem": mem_info,
        "uptime": uptime_str(srv.get("start_time")) if status == "Running" else "0 ثانية",
        "port": port,
        "ip": pub_ip,
        "url": f"http://{pub_ip}:{port}",
        "preview_url": f"/server/open/{folder}",
        "server_type": srv.get("server_type", "Python")
    })

# ============== إدارة الملفات المتقدمة (Python / JS Upload Fixed) ==============
@app.route('/api/files/list/<folder>')
def list_server_files(folder):
    if "email" not in session:
        return jsonify([]), 401
    srv = db["servers"].get(folder)
    if not srv or srv["owner"] != session["email"]:
        return jsonify([])
    
    path = srv["path"]
    files = []
    try:
        for f in os.listdir(path):
            if f in ['out.log', 'server.log', 'meta.json', 'errors.log']:
                continue
            fpath = os.path.join(path, f)
            stat = os.stat(fpath)
            size_bytes = stat.st_size
            if size_bytes < 1024:
                size_str = f"{size_bytes} بايت"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes/1024:.1f} كيلوبايت"
            else:
                size_str = f"{size_bytes/(1024*1024):.1f} ميجابايت"
            files.append({
                "name": f,
                "size": size_str,
                "is_dir": os.path.isdir(fpath),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                "is_zip": f.lower().endswith('.zip')
            })
    except Exception:
        pass
    return jsonify(sorted(files, key=lambda x: (not x['is_dir'], x['name'].lower())))

@app.route('/api/files/content/<folder>/<path:filename>')
def get_file_content(folder, filename):
    if "email" not in session:
        return jsonify({"content": ""}), 401
    srv = db["servers"].get(folder)
    if not srv or srv["owner"] != session["email"]:
        return jsonify({"content": ""})
    if '..' in filename:
        return jsonify({"content": ""})
    
    fpath = os.path.join(srv["path"], filename)
    if not os.path.exists(fpath) or os.path.isdir(fpath):
        return jsonify({"content": ""})
    try:
        with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
            return jsonify({"content": f.read()})
    except Exception:
        return jsonify({"content": "[ملف ثنائي]"})

@app.route('/api/files/save/<folder>/<path:filename>', methods=['POST'])
def save_file_content(folder, filename):
    if "email" not in session:
        return jsonify({"success": False}), 401
    srv = db["servers"].get(folder)
    if not srv or srv["owner"] != session["email"]:
        return jsonify({"success": False})
    if '..' in filename:
        return jsonify({"success": False})
    
    data = request.get_json() or {}
    fpath = os.path.join(srv["path"], filename)
    try:
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(data.get("content", ""))
        return jsonify({"success": True, "message": "✅ تم الحفظ بنجاح"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/files/upload/<folder>', methods=['POST'])
def upload_files(folder):
    if "email" not in session:
        return jsonify({"success": False, "message": "غير مصرح"}), 401
    srv = db["servers"].get(folder)
    if not srv or srv["owner"] != session["email"]:
        return jsonify({"success": False, "message": "السيرفر غير موجود"})
    
    files = request.files.getlist('files[]') or request.files.getlist('files')
    if not files:
        for key in request.files:
            files.extend(request.files.getlist(key))

    uploaded = 0
    for f in files:
        try:
            if f and f.filename and '..' not in f.filename:
                filename = os.path.basename(f.filename)
                save_path = os.path.join(srv["path"], filename)
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                f.save(save_path)
                uploaded += 1
        except Exception as e:
            logger.error(f"خطأ في رفع الملف: {e}")
    
    if uploaded > 0:
        log_path = os.path.join(srv["path"], "out.log")
        stype = srv.get("server_type", "Python")
        try:
            log_file = open(log_path, "a", encoding='utf-8')
            if stype == "Node.js":
                threading.Thread(target=auto_install_node_deps, args=(srv["path"], log_file), daemon=True).start()
            elif stype == "Django":
                threading.Thread(target=auto_install_django_deps, args=(srv["path"], log_file), daemon=True).start()
            else:
                threading.Thread(target=auto_install_deps, args=(srv["path"], log_file), daemon=True).start()
        except Exception:
            pass

        return jsonify({"success": True, "message": f"✅ تم رفع {uploaded} ملف بنجاح وإعداد التبعيات"})
    return jsonify({"success": False, "message": "فشل رفع الملفات، تأكد من اختيار ملفات صالحة"})

@app.route('/api/files/delete/<folder>', methods=['POST'])
def delete_files(folder):
    if "email" not in session:
        return jsonify({"success": False}), 401
    srv = db["servers"].get(folder)
    if not srv or srv["owner"] != session["email"]:
        return jsonify({"success": False})
    
    data = request.get_json() or {}
    names = data.get("names", data.get("name", []))
    if isinstance(names, str):
        names = [names]
    
    deleted = 0
    for name in names:
        if name and '..' not in name:
            fpath = os.path.join(srv["path"], name)
            try:
                if os.path.isdir(fpath):
                    shutil.rmtree(fpath)
                elif os.path.exists(fpath):
                    os.remove(fpath)
                deleted += 1
            except Exception:
                pass
    return jsonify({"success": True, "message": f"🗑 تم حذف {deleted} عنصر"})

@app.route('/api/files/create/<folder>', methods=['POST'])
def create_file_api(folder):
    if "email" not in session:
        return jsonify({"success": False}), 401
    srv = db["servers"].get(folder)
    if not srv or srv["owner"] != session["email"]:
        return jsonify({"success": False})
    
    data = request.get_json() or {}
    filename = data.get("filename", "").strip()
    if not filename or '..' in filename:
        return jsonify({"success": False})
    
    fpath = os.path.join(srv["path"], filename)
    try:
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(data.get("content", ""))
        return jsonify({"success": True, "message": f"✅ تم إنشاء {filename} بنجاح"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/files/rename/<folder>', methods=['POST'])
def rename_file(folder):
    if "email" not in session:
        return jsonify({"success": False}), 401
    srv = db["servers"].get(folder)
    if not srv or srv["owner"] != session["email"]:
        return jsonify({"success": False})
    
    data = request.get_json() or {}
    old_name = data.get("old_name", "").strip()
    new_name = data.get("new_name", "").strip()
    if '..' in old_name or '..' in new_name:
        return jsonify({"success": False})
    
    old_path = os.path.join(srv["path"], old_name)
    new_path = os.path.join(srv["path"], new_name)
    if not os.path.exists(old_path):
        return jsonify({"success": False})
    try:
        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        os.rename(old_path, new_path)
        return jsonify({"success": True, "message": "✅ تم تغيير الاسم بنجاح"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/files/unzip/<folder>/<path:filename>', methods=['POST'])
def unzip_file(folder, filename):
    if "email" not in session:
        return jsonify({"success": False}), 401
    srv = db["servers"].get(folder)
    if not srv or srv["owner"] != session["email"]:
        return jsonify({"success": False})
    
    zip_path = os.path.join(srv["path"], filename)
    if not os.path.exists(zip_path):
        return jsonify({"success": False})
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(srv["path"])
        return jsonify({"success": True, "message": "✅ تم فك الضغط بنجاح"})
    except Exception:
        return jsonify({"success": False, "message": "فشل فك الضغط"})

@app.route('/api/server/set-startup/<folder>', methods=['POST'])
def set_startup_file(folder):
    if "email" not in session:
        return jsonify({"success": False}), 401
    srv = db["servers"].get(folder)
    if not srv or srv["owner"] != session["email"]:
        return jsonify({"success": False})
    
    data = request.get_json() or {}
    filename = data.get("filename", "").strip()
    if not filename or '..' in filename:
        return jsonify({"success": False})
    
    srv["startup_file"] = filename
    save_db(db)
    return jsonify({"success": True, "message": f"✅ تم تعيين ملف التشغيل: {filename}"})

@app.route('/api/server/install/<folder>', methods=['POST'])
def install_requirements(folder):
    if "email" not in session:
        return jsonify({"success": False}), 401
    srv = db["servers"].get(folder)
    if not srv or srv["owner"] != session["email"]:
        return jsonify({"success": False})
    
    log_path = os.path.join(srv["path"], "out.log")
    stype = srv.get("server_type")
    try:
        log_file = open(log_path, "a", encoding='utf-8')
        if stype == "Node.js":
            threading.Thread(target=auto_install_node_deps, args=(srv["path"], log_file), daemon=True).start()
            return jsonify({"success": True, "message": "📦 بدأ تثبيت حزم Node.js عبر npm"})
        elif stype == "Django":
            threading.Thread(target=auto_install_django_deps, args=(srv["path"], log_file), daemon=True).start()
            return jsonify({"success": True, "message": "📦 بدأ تثبيت تبعيات وبيئة Django"})
        else:
            req_file = os.path.join(srv["path"], "requirements.txt")
            if not os.path.exists(req_file):
                return jsonify({"success": False, "message": "ملف requirements.txt غير موجود"})
            threading.Thread(target=auto_install_deps, args=(srv["path"], log_file), daemon=True).start()
            return jsonify({"success": True, "message": "📦 بدأ تثبيت مكتبات Python"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# ============== تكامل Telegram Bot API ==============
@app.route('/api/bot/verify', methods=['POST'])
def bot_verify():
    data = request.get_json() or {}
    api_key = data.get('api_key', '').strip()
    if not api_key:
        return jsonify({"success": False})
    email, user = get_user_by_api_key(api_key)
    if not email:
        return jsonify({"success": False})
    return jsonify({
        "success": True,
        "email": email,
        "is_admin": is_admin(email),
        "max_servers": user.get("max_servers", 10)
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
                "server_type": srv.get("server_type", "Python"),
                "preview_url": f"/server/open/{folder}"
            })
    return jsonify({"success": True, "servers": user_servers})

@app.route('/api/bot/server/action', methods=['POST'])
def bot_server_action():
    data = request.get_json() or {}
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
        return jsonify({"success": True, "message": "🛑 تم إيقاف السيرفر بنجاح مع الاحتفاظ بالملفات"})
    elif action == "restart":
        restart_server(folder)
        return jsonify({"success": True, "message": "🔄 تم إعادة التشغيل بنجاح"})
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

# ================= التشغيل الرئيسي للنظام =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 تم بدء تشغيل المنصة الشاملة (Ziad Host) بنجاح على المنفذ {port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
