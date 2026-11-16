import os
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# صفحة المنصة الأمامية والخارقة المطابقة تماماً لتصميمك
INDEX_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>𝑰𝑪𝑶 | منصة الاستضافة الخارقة والذكية</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #311042 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 24px;
            color: #f8fafc;
            direction: rtl;
            font-size: 14px;
        }
        :root {
            --primary: #6366f1; --primary-light: #818cf8; --primary-dark: #4f46e5;
            --secondary: #ec4899; --accent: #8b5cf6; --success: #10b981;
            --warning: #f59e0b; --danger: #ef4444;
            --shadow-sm: 0 4px 12px rgba(0, 0, 0, 0.2);
            --shadow-md: 0 10px 30px rgba(0, 0, 0, 0.3);
            --shadow-lg: 0 20px 40px rgba(0, 0, 0, 0.4);
            --shadow-xl: 0 30px 60px rgba(0, 0, 0, 0.6);
            --radius-sm: 8px; --radius-md: 16px; --radius-lg: 24px; --radius-xl: 32px;
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .hidden { display: none !important; }
        .btn {
            padding: 12px 24px; border: none; border-radius: var(--radius-md);
            font-weight: 600; font-size: 14px; cursor: pointer; transition: var(--transition);
            display: inline-flex; align-items: center; justify-content: center; gap: 8px;
        }
        .btn-primary { background: linear-gradient(135deg, var(--primary), var(--accent)); color: white; box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4); }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(99, 102, 241, 0.6); }
        .btn-outline { background: rgba(255, 255, 255, 0.05); border: 2px solid rgba(255, 255, 255, 0.1); color: #f8fafc; }
        .btn-outline:hover { border-color: var(--primary-light); color: var(--primary-light); background: rgba(99, 102, 241, 0.1); }
        .btn-danger { background: linear-gradient(135deg, var(--danger), #dc2626); color: white; }
        .btn-danger:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(239, 68, 68, 0.4); }
        .login-wrapper {
            width: 100%; max-width: 450px; background: rgba(30, 41, 59, 0.7);
            backdrop-filter: blur(20px); border-radius: var(--radius-xl); box-shadow: var(--shadow-xl);
            border: 1px solid rgba(255, 255, 255, 0.1); overflow: hidden;
        }
        .login-header { background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); padding: 30px; text-align: center; color: white; }
        .login-header h1 { font-size: 28px; font-weight: 700; margin-bottom: 6px; }
        .login-header p { font-size: 14px; opacity: 0.9; }
        .login-tabs { display: flex; padding: 12px 12px 0; gap: 8px; background: rgba(15, 23, 42, 0.5); }
        .login-tab {
            flex: 1; padding: 12px; border: none; background: rgba(255, 255, 255, 0.05); color: #94a3b8;
            font-weight: 600; cursor: pointer; border-radius: var(--radius-md) var(--radius-md) 0 0;
            transition: var(--transition); font-size: 14px; display: flex; align-items: center; justify-content: center; gap: 8px;
        }
        .login-tab.active { background: rgba(30, 41, 59, 0.9); color: var(--primary-light); border-top: 2px solid var(--primary); }
        .login-content { background: rgba(30, 41, 59, 0.9); padding: 24px; }
        .form-group { margin-bottom: 20px; }
        .form-label { display: block; margin-bottom: 6px; color: #cbd5e1; font-weight: 500; font-size: 13px; }
        .form-input {
            width: 100%; padding: 12px 16px; border: 2px solid rgba(255, 255, 255, 0.1);
            border-radius: var(--radius-md); font-size: 14px; transition: var(--transition);
            background: rgba(15, 23, 42, 0.6); color: white;
        }
        .form-input:focus { outline: none; border-color: var(--primary); background: rgba(15, 23, 42, 0.9); box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.2); }
        .form-error { color: var(--danger); font-size: 12px; margin-top: 4px; display: none; }
        .form-error.show { display: block; }
        .form-info { color: #94a3b8; font-size: 11px; margin-top: 4px; }
        .app-wrapper {
            width: 100%; max-width: 1300px; margin: 0 auto; background: rgba(15, 23, 42, 0.75);
            backdrop-filter: blur(25px); border-radius: var(--radius-xl); box-shadow: var(--shadow-xl);
            border: 1px solid rgba(255, 255, 255, 0.1); overflow: hidden;
        }
        .navbar {
            background: rgba(30, 41, 59, 0.85); padding: 12px 24px; border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px;
        }
        .logo-area { display: flex; align-items: center; gap: 10px; }
        .logo-icon {
            width: 40px; height: 40px; background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: var(--radius-md); display: flex; align-items: center; justify-content: center; color: white; font-size: 20px;
        }
        .logo-text h1 { font-size: 20px; font-weight: 700; background: linear-gradient(135deg, #818cf8, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .logo-text p { font-size: 11px; color: #94a3b8; }
        .user-area { display: flex; align-items: center; gap: 12px; }
        .user-badge {
            background: rgba(255, 255, 255, 0.08); padding: 6px 16px; border-radius: 40px; font-weight: 600;
            font-size: 13px; color: #e2e8f0; display: flex; align-items: center; gap: 6px; border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .dev-card {
            background: rgba(30, 41, 59, 0.6); margin: 20px 24px; padding: 16px 24px; border-radius: var(--radius-lg);
            display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px; border: 1px solid rgba(255, 255, 255, 0.08);
        }
        .dev-badge { background: linear-gradient(135deg, #334155, #1e293b); color: white; padding: 6px 16px; border-radius: 40px; font-weight: 600; font-size: 13px; }
        .dev-links { display: flex; gap: 10px; }
        .dev-link {
            background: rgba(255, 255, 255, 0.05); color: #e2e8f0; padding: 6px 16px; border-radius: 40px; text-decoration: none;
            font-weight: 500; font-size: 13px; transition: var(--transition); display: flex; align-items: center; gap: 6px; border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .dev-link:hover { background: var(--primary); color: white; }
        .welcome-banner {
            background: linear-gradient(135deg, #3730a3 0%, #6d28d9 50%, #9333ea 100%);
            margin: 0 24px 20px; padding: 30px; border-radius: var(--radius-lg); color: white; text-align: center; box-shadow: var(--shadow-lg);
        }
        .welcome-banner h2 { font-size: 28px; font-weight: 700; margin-bottom: 12px; }
        .welcome-banner p { font-size: 15px; opacity: 0.95; max-width: 550px; margin: 0 auto 20px; line-height: 1.6; }
        .plans-section { padding: 0 24px 24px; }
        .section-title { text-align: center; margin-bottom: 24px; }
        .section-title h2 { font-size: 26px; font-weight: 700; color: #f8fafc; margin-bottom: 6px; }
        .section-title p { color: #94a3b8; font-size: 14px; }
        .plans-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 20px; }
        .plan-card {
            background: rgba(30, 41, 59, 0.75); border-radius: var(--radius-lg); padding: 24px;
            box-shadow: var(--shadow-md); border: 1px solid rgba(255, 255, 255, 0.1); transition: var(--transition); position: relative; overflow: hidden;
        }
        .plan-card:hover { transform: translateY(-8px); border-color: var(--primary-light); background: rgba(30, 41, 59, 0.95); }
        .plan-name { font-size: 20px; font-weight: 700; color: #f8fafc; margin-bottom: 6px; }
        .plan-price { font-size: 28px; font-weight: 800; color: var(--primary-light); margin-bottom: 20px; }
        .plan-feature { padding: 8px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.08); color: #cbd5e1; font-size: 13px; display: flex; align-items: center; gap: 10px; }
        .plan-feature i { color: var(--success); width: 18px; }
        .plan-btn {
            width: 100%; padding: 12px; margin-top: 20px; background: linear-gradient(135deg, var(--primary), var(--accent));
            color: white; border: none; border-radius: var(--radius-md); font-weight: 600; font-size: 14px; cursor: pointer; transition: var(--transition);
        }
        .files-section { padding: 0 24px 24px; }
        .files-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 16px; margin-top: 20px; }
        .file-card { background: rgba(30, 41, 59, 0.8); border-radius: var(--radius-lg); padding: 16px; border: 1px solid rgba(255, 255, 255, 0.1); }
        .file-name { font-size: 16px; font-weight: 600; color: #f8fafc; margin-bottom: 6px; word-break: break-word; }
        .upload-area {
            margin: 0 24px 24px; border: 3px dashed rgba(255, 255, 255, 0.2); border-radius: var(--radius-lg);
            padding: 36px; text-align: center; background: rgba(30, 41, 59, 0.5); transition: var(--transition); cursor: pointer;
        }
        .upload-area:hover { border-color: var(--primary-light); background: rgba(30, 41, 59, 0.8); }
        .file-input { display: none; }
        .file-input-label {
            background: linear-gradient(135deg, var(--primary), var(--accent)); color: white; padding: 10px 28px;
            border-radius: var(--radius-md); font-weight: 600; font-size: 14px; cursor: pointer; display: inline-block;
        }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 16px; margin: 0 24px 24px; }
        .stat-card { background: rgba(30, 41, 59, 0.8); border-radius: var(--radius-lg); padding: 20px; border: 1px solid rgba(255, 255, 255, 0.1); display: flex; align-items: center; gap: 12px; }
        .stat-icon { width: 48px; height: 48px; background: linear-gradient(135deg, var(--primary), var(--accent)); border-radius: var(--radius-md); display: flex; align-items: center; justify-content: center; color: white; font-size: 20px; }
        .result-card { background: rgba(30, 41, 59, 0.85); margin: 0 24px 24px; border-radius: var(--radius-lg); padding: 24px; border: 1px solid rgba(255, 255, 255, 0.1); }
        .result-url { background: rgba(15, 23, 42, 0.8); padding: 12px 20px; border-radius: var(--radius-md); font-family: monospace; font-size: 14px; color: var(--primary-light); word-break: break-all; margin: 16px 0; }
        .admin-panel { background: rgba(30, 41, 59, 0.9); margin: 0 24px 24px; border-radius: var(--radius-lg); padding: 24px; border: 1px solid rgba(255, 255, 255, 0.15); }
        .admin-actions { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin-top: 20px; }
        .admin-btn { padding: 12px; border: none; border-radius: var(--radius-md); font-weight: 600; font-size: 13px; cursor: pointer; background: rgba(255, 255, 255, 0.05); color: #e2e8f0; border: 1px solid rgba(255, 255, 255, 0.1); }
        .toast {
            position: fixed; top: 20px; left: 20px; background: rgba(30, 41, 59, 0.95); color: white; padding: 12px 20px;
            border-radius: var(--radius-md); box-shadow: var(--shadow-xl); display: flex; align-items: center; gap: 10px; z-index: 9999;
            transform: translateX(150%); transition: transform 0.3s ease; border-right: 4px solid var(--success); min-width: 280px;
        }
        .toast.show { transform: translateX(0); }
        .footer { background: rgba(30, 41, 59, 0.85); padding: 20px 24px; border-top: 1px solid rgba(255, 255, 255, 0.1); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; margin-top: 24px; }
    </style>
</head>
<body>
    <div class="toast" id="toast"><div id="toastIcon"></div><div id="toastText">تمت العملية بنجاح</div></div>

    <div class="login-wrapper" id="loginContainer">
        <div class="login-header"><h1>منصة ICO الخارقة</h1><p>بواسطة Y_20_20 | استضافة متكاملة (HTML, JS, PHP, Python)</p></div>
        <div class="login-tabs">
            <button class="login-tab active" data-tab="login"><i class="fas fa-sign-in-alt"></i> تسجيل الدخول</button>
            <button class="login-tab" data-tab="register"><i class="fas fa-user-plus"></i> إنشاء حساب</button>
        </div>
        <div class="login-content">
            <div id="loginForm">
                <div class="form-group"><label class="form-label">اسم المستخدم</label><input type="text" id="loginUsername" class="form-input" placeholder="اسم المستخدم"></div>
                <div class="form-group"><label class="form-label">كلمة المرور</label><input type="password" id="loginPassword" class="form-input" placeholder="كلمة المرور"></div>
                <button class="btn btn-primary" id="loginSubmit" style="width: 100%;">دخول</button>
                <button class="btn btn-outline" id="adminAccessBtn" style="margin-top: 16px; width: 100%;">دخول كأدمن</button>
            </div>
            <div id="registerForm" class="hidden">
                <div class="form-group"><label class="form-label">اسم المستخدم (إنجليزي)</label><input type="text" id="registerUsername" class="form-input" placeholder="Username"></div>
                <div class="form-group"><label class="form-label">كلمة المرور</label><input type="password" id="registerPassword" class="form-input" placeholder="Password"></div>
                <button class="btn btn-primary" id="registerSubmit" style="width: 100%;">تسجيل حساب جديد</button>
            </div>
        </div>
    </div>

    <div class="app-wrapper hidden" id="mainContainer">
        <nav class="navbar">
            <div class="logo-area"><div class="logo-icon"><i class="fas fa-rocket"></i></div><div class="logo-text"><h1>Y_20_20</h1><p>منصة استضافة خارقة</p></div></div>
            <div class="user-area">
                <div class="user-badge" id="userNameDisplay"><i class="fas fa-user"></i> <span>زائر</span></div>
                <button class="btn btn-outline" id="logoutBtn">خروج</button>
            </div>
        </nav>
        <div class="dev-card">
            <span class="dev-badge"><i class="fas fa-code"></i> المطور الرئيسي</span>
            <div class="dev-links"><a href="https://t.me/Y_20_20" target="_blank" class="dev-link"><i class="fab fa-telegram"></i> @Y_20_20</a></div>
        </div>
        <div class="plans-section" id="plansSection">
            <div class="section-title"><h2>اختر خطتك المثالية</h2><p>استضافة ملفات HTML, JS, PHP, Python بكفاءة عالية</p></div>
            <div class="plans-grid" id="plansGrid"></div>
        </div>
        <div class="upload-area hidden" id="uploadArea">
            <h3>رفع ملف جديد (HTML, JS, PHP, Python)</h3>
            <label class="file-input-label"><i class="fas fa-folder-open"></i> اختر ملف<input type="file" id="fileInput" class="file-input"></label>
            <div id="fileName" style="margin-top:10px; color:#818cf8;"></div>
        </div>
        <div style="padding:0 24px 24px;" class="hidden" id="actionButtonsContainer">
            <button class="btn btn-primary" id="uploadBtn" style="width:100%;">رفع الملف وتشغيل السيرفر</button>
        </div>
        <div class="result-card hidden" id="resultSection">
            <h3>رابط السيرفر:</h3>
            <div class="result-url" id="urlDisplay"></div>
            <button class="btn btn-primary" id="openBtn">فتح الموقع</button>
        </div>
    </div>

    <script>
        const E = {
            loginContainer: document.getElementById('loginContainer'),
            mainContainer: document.getElementById('mainContainer'),
            loginSubmit: document.getElementById('loginSubmit'),
            registerSubmit: document.getElementById('registerSubmit'),
            loginUsername: document.getElementById('loginUsername'),
            loginPassword: document.getElementById('loginPassword'),
            registerUsername: document.getElementById('registerUsername'),
            registerPassword: document.getElementById('registerPassword'),
            userNameDisplay: document.getElementById('userNameDisplay').querySelector('span'),
            logoutBtn: document.getElementById('logoutBtn'),
            plansGrid: document.getElementById('plansGrid'),
            uploadArea: document.getElementById('uploadArea'),
            actionButtonsContainer: document.getElementById('actionButtonsContainer'),
            fileInput: document.getElementById('fileInput'),
            uploadBtn: document.getElementById('uploadBtn'),
            resultSection: document.getElementById('resultSection'),
            urlDisplay: document.getElementById('urlDisplay'),
            openBtn: document.getElementById('openBtn'),
            toast: document.getElementById('toast'),
            toastText: document.getElementById('toastText')
        };

        function showToast(msg) {
            E.toastText.textContent = msg;
            E.toast.classList.add('show');
            setTimeout(() => E.toast.classList.remove('show'), 3000);
        }

        let currentUser = null;

        E.registerSubmit.addEventListener('click', async () => {
            const u = E.registerUsername.value, p = E.registerPassword.value;
            const res = await fetch('/api/register', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username: u, password: p}) });
            const data = await res.json();
            if(data.success) { currentUser = u; E.userNameDisplay.textContent = u; E.loginContainer.classList.add('hidden'); E.mainContainer.classList.remove('hidden'); loadPlans(); showToast("تم التسجيل بنجاح"); }
            else showToast(data.error);
        });

        E.loginSubmit.addEventListener('click', async () => {
            const u = E.loginUsername.value, p = E.loginPassword.value;
            const res = await fetch('/api/login', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username: u, password: p}) });
            const data = await res.json();
            if(data.success) { currentUser = u; E.userNameDisplay.textContent = u; E.loginContainer.classList.add('hidden'); E.mainContainer.classList.remove('hidden'); loadPlans(); showToast("مرحباً بك"); }
            else showToast(data.error);
        });

        async function loadPlans() {
            E.plansGrid.innerHTML = `
                <div class="plan-card">
                    <div class="plan-name">الخطة المجانية</div>
                    <div class="plan-price">مجاناً</div>
                    <div class="plan-feature"><i class="fas fa-hdd"></i> المساحة: 5 جيجا</div>
                    <button class="plan-btn" onclick="activatePlan('free')">تفعيل فوراً</button>
                </div>
            `;
        }

        window.activatePlan = function(planKey) {
            E.plansGrid.parentElement.classList.add('hidden');
            E.uploadArea.classList.remove('hidden');
            E.actionButtonsContainer.classList.remove('hidden');
            showToast("تم تفعيل الخطة، ارفع ملفك الآن!");
        }

        E.uploadBtn.addEventListener('click', async () => {
            const file = E.fileInput.files[0];
            if(!file) return showToast("اختر ملفاً أولاً");
            const formData = new FormData();
            formData.append('file', file);
            formData.append('username', currentUser);

            const res = await fetch('/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if(data.success) {
                E.urlDisplay.textContent = data.url;
                E.resultSection.classList.remove('hidden');
                showToast("تم رفع الملف بنجاح!");
            } else {
                showToast("حدث خطأ أثناء الرفع");
            }
        });

        E.openBtn.addEventListener('click', () => {
            window.open(E.urlDisplay.textContent, '_blank');
        });
    </script>
</body>
</html>
"""

# قواعد بيانات مؤقتة للذاكرة
users_db = {}
sites_db = {}

@app.route('/')
def index():
    site_id = request.args.get('site')
    if site_id and site_id in sites_db:
        return render_template_string(sites_db[site_id]['content'])
    return render_template_string(INDEX_HTML)

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'success': False, 'error': 'أدخل بيانات صحيحة'})
    if username in users_db:
        return jsonify({'success': False, 'error': 'المستخدم موجود مسبقاً'})
    users_db[username] = {'password': password}
    return jsonify({'success': True})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if username in users_db and users_db[username]['password'] == password:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'بيانات الدخول غير صحيحة'})

@app.route('/api/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    username = request.form.get('username')
    if not file:
        return jsonify({'success': False})
    
    filename = file.filename
    content = file.read().decode('utf-8', errors='ignore')
    site_id = f"site_{abs(hash(filename + username))}"
    
    # دعم عرض محتوى الملفات المرفوعة
    formatted_content = f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head><meta charset="UTF-8"><title>{filename}</title>
    <style>body{{background:#0f172a;color:#fff;font-family:Tahoma;padding:30px;text-align:center;}}pre{{background:#1e293b;padding:20px;border-radius:10px;text-align:left;direction:ltr;color:#38bdf8;overflow:auto;max-width:800px;margin:20px auto;}}</style>
    </head>
    <body>
        <h1>⚡ تم تشغيل ملفك بنجاح على استضافة ICO</h1>
        <p>اسم الملف المرفوع: <b>{filename}</b></p>
        <pre>{content}</pre>
    </body>
    </html>
    """
    
    sites_db[site_id] = {'content': formatted_content, 'owner': username}
    full_url = f"{request.host_url}?site={site_id}"
    return jsonify({'success': True, 'url': full_url})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
