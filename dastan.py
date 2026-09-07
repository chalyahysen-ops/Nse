from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session
from datetime import timedelta, datetime
from werkzeug.utils import secure_filename
import pymysql
import os

app = Flask(__name__)
app.secret_key = 'shahoor_all_in_one_pos_2026'

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

DB_CONFIG = {
    'host': 'sakura.proxy.rlwy.net',
    'port': 31707,
    'user': 'root',
    'password': 'HITVDFaMFehpQFmWrZlnaTKtavNtBZyw',
    'database': 'nrx',
    'charset': 'utf8mb4',
    'connect_timeout': 10,
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db():
    conn = pymysql.connect(**DB_CONFIG)
    conn.ping(reconnect=True)
    return conn

def normalize_digits(text):
    if not text:
        return ""
    text = str(text).strip()
    return text.translate(str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789'))

def ensure_all_tables():
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(100) NOT NULL UNIQUE,
                    password VARCHAR(100) NOT NULL,
                    full_name VARCHAR(150) DEFAULT '',
                    role VARCHAR(50) DEFAULT 'Waiter',
                    can_view_menu TINYINT DEFAULT 1,
                    can_view_tables TINYINT DEFAULT 1,
                    can_view_cashier TINYINT DEFAULT 0,
                    can_view_qsa TINYINT DEFAULT 0,
                    can_view_reports TINYINT DEFAULT 0,
                    can_view_settings TINYINT DEFAULT 0,
                    is_active TINYINT DEFAULT 1
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nse (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    food_name VARCHAR(255) NOT NULL,
                    price DECIMAL(18, 0) NOT NULL DEFAULT 0,
                    category VARCHAR(150) DEFAULT 'گشتی',
                    image_path TEXT,
                    nsecol VARCHAR(50) DEFAULT ''
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS froshtn (
                    order_id INT AUTO_INCREMENT PRIMARY KEY,
                    quantity INT DEFAULT 1,
                    food_name VARCHAR(255),
                    price DECIMAL(18, 0),
                    category VARCHAR(150),
                    table_cabin VARCHAR(150),
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50) DEFAULT 'Active',
                    is_printed TINYINT DEFAULT 0
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS table_permissions (
                    table_number INT PRIMARY KEY,
                    allow_ordering TINYINT DEFAULT 1
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workers (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(150) NOT NULL,
                    phone VARCHAR(50) DEFAULT '',
                    salary DECIMAL(18, 0) NOT NULL DEFAULT 0
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS worker_attendance (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    worker_id INT NOT NULL,
                    date DATE NOT NULL,
                    status VARCHAR(50) DEFAULT 'نەهاتوو',
                    bonus DECIMAL(18, 0) DEFAULT 0,
                    UNIQUE KEY uniq_worker_date (worker_id, date)
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS masrwf (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    masrwf_date DATETIME NOT NULL,
                    masrwf_name VARCHAR(150) DEFAULT '',
                    masrwf_type VARCHAR(100) NOT NULL,
                    spent_by VARCHAR(100) DEFAULT '',
                    amount DECIMAL(18, 0) NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            try:
                cursor.execute("ALTER TABLE masrwf ADD COLUMN IF NOT EXISTS spent_by VARCHAR(100) DEFAULT '' AFTER masrwf_type;")
            except:
                pass

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS qasa (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    transaction_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    place_id VARCHAR(150),
                    amount DECIMAL(18, 0),
                    discount DECIMAL(18, 0) DEFAULT 0
                );
            """)

            cursor.execute("SELECT id FROM users WHERE username = 'admin'")
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO users (username, password, full_name, role, is_active)
                    VALUES ('admin', '1234', 'بەڕێوەبەری سەرەکی', 'Manager', 1)
                """)

        conn.commit()
    except Exception as ex:
        print("Setup tables error:", ex)
    finally:
        if conn:
            try: conn.close()
            except: pass

ensure_all_tables()

@app.before_request
def enforce_security():
    endpoint = request.endpoint or ''
    exempt_endpoints = ['login', 'customer_table_view', 'save_customer_order', 'static', 'index']
    if endpoint in exempt_endpoints:
        return

    is_api = request.path.startswith(('/get_', '/save_', '/clear_', '/change_', '/set_', '/toggle_', '/api_', '/admin/toggle_att'))
    if is_api:
        return

    if not session.get('authenticated'):
        return redirect(url_for('login'))

    if request.path.startswith('/admin') and session.get('role') != 'admin':
        return redirect(url_for('login'))

# ==========================================
# پەڕەی چوونەژوورەوە
# ==========================================
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>چوونەژوورەوە - شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background: #03261d; color: #f8fafc; display: flex; align-items: center; justify-content: center; min-height: 100vh; padding: 16px; }
        .login-card { background: #064032; border: 1.5px solid #0b5e4a; padding: 36px 28px; border-radius: 20px; width: 100%; max-width: 400px; text-align: center; box-shadow: 0 15px 35px rgba(0,0,0,0.5); }
        .brand-title { color: #10b981; font-size: 26px; font-weight: 800; margin-bottom: 6px; }
        .brand-sub { color: #a7f3d0; font-size: 13px; margin-bottom: 24px; }
        .input-group { text-align: right; margin-bottom: 16px; }
        .input-group label { display: block; font-size: 12px; font-weight: 700; color: #a7f3d0; margin-bottom: 6px; }
        .login-input { width: 100%; padding: 13px 14px; background: #03261d; border: 2px solid #0b5e4a; border-radius: 12px; color: #10b981; font-size: 16px; font-weight: 700; outline: none; }
        .login-input:focus { border-color: #10b981; }
        .btn-submit { width: 100%; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #ffffff; border: none; padding: 14px; border-radius: 12px; font-size: 16px; font-weight: 800; cursor: pointer; margin-top: 10px; }
        .error-msg { color: #ef4444; font-size: 13px; margin-top: 14px; font-weight: 700; }
        .quick-hint { margin-top: 20px; font-size: 11px; color: #94a3b8; border-top: 1px solid #0b5e4a; padding-top: 14px; }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="brand-title">✨ شاهور ڕێستۆرانت</div>
        <div class="brand-sub">تکایە ناوی بەکارهێنەر و وشەی نهێنی بنووسە</div>
        <form method="POST" action="/login">
            <div class="input-group">
                <label>ناوی بەکارهێنەر (Username):</label>
                <input type="text" name="username" class="login-input" placeholder="یوسەر..." autofocus>
            </div>
            <div class="input-group">
                <label>وشەی نهێنی (Password):</label>
                <input type="password" name="password" class="login-input" placeholder="پاسوۆرد...">
            </div>
            <button type="submit" class="btn-submit">چوونەژوورەوە ➔</button>
        </form>
        {% if error %}<div class="error-msg">{{ error }}</div>{% endif %}
        <div class="quick-hint">
            👑 بەڕێوەبەر: admin / 1234 | بەتاڵ جێی بهێڵە بۆ گارسۆن
        </div>
    </div>
</body>
</html>
"""

# ==========================================
# داشبۆردی بەڕێوەبەر
# ==========================================
ADMIN_DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>داشبۆردی سەرەکی - شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background-color: #03261d; color: #ffffff; min-height: 100vh; display: flex; flex-direction: column; }
        .admin-nav { background: #064032; padding: 14px 28px; display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #0b5e4a; }
        .admin-brand { font-size: 20px; font-weight: 800; color: #10b981; }
        .btn-exit { background: #ef4444; color: #fff; text-decoration: none; padding: 8px 18px; border-radius: 8px; font-weight: 800; font-size: 13px; }
        .admin-content { flex: 1; padding: 24px; max-width: 1400px; margin: 0 auto; width: 100%; }
        
        .stats-cards-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 28px; }
        .stat-card { background: #064032; border: 1.5px solid #0b5e4a; border-radius: 16px; padding: 20px; display: flex; align-items: center; justify-content: space-between; }
        .stat-info { display: flex; flex-direction: column; gap: 6px; }
        .stat-label { font-size: 13px; font-weight: 700; color: #a7f3d0; }
        .stat-value { font-size: 21px; font-weight: 800; }
        
        .section-header { font-size: 18px; font-weight: 800; color: #10b981; margin-bottom: 16px; border-bottom: 1px solid #0b5e4a; padding-bottom: 8px; }
        .dashboard-modules-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 18px; }
        .module-card { background: #ffffff; border-radius: 18px; padding: 22px; text-decoration: none; color: #0f172a; display: flex; flex-direction: column; gap: 10px; transition: transform 0.2s; }
        .module-card:hover { transform: translateY(-4px); }
        .module-top { display: flex; align-items: center; justify-content: space-between; }
        .module-icon { font-size: 30px; background: #f1f5f9; width: 54px; height: 54px; display: flex; align-items: center; justify-content: center; border-radius: 14px; }
        .module-badge { background: #10b981; color: #03261d; font-size: 11px; font-weight: 800; padding: 4px 10px; border-radius: 10px; }
        .module-title { font-size: 17px; font-weight: 800; }
        .module-desc { font-size: 12.5px; color: #64748b; font-weight: 600; line-height: 1.4; }
    </style>
</head>
<body>
    <header class="admin-nav">
        <div class="admin-brand">✨ شاهور ڕێستۆرانت - داشبۆردی بەڕێوەبەر</div>
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="color:#a7f3d0; font-size:13px; font-weight:700;">👑 {{ session.get('full_name', 'بەڕێوەبەر') }}</span>
            <a href="/logout" class="btn-exit">✕ دەرچوون</a>
        </div>
    </header>

    <main class="admin-content">
        <div class="stats-cards-grid">
            <div class="stat-card">
                <div class="stat-info">
                    <span class="stat-label">💰 فرۆشی ٢٤ کاتژمێر</span>
                    <span class="stat-value" style="color: #10b981;">{{ "{:,.0f}".format(today_sales) }} د.ع</span>
                </div>
                <div style="font-size: 36px;">📈</div>
            </div>
            <div class="stat-card">
                <div class="stat-info">
                    <span class="stat-label">💸 مەسرووفی ئەمڕۆ</span>
                    <span class="stat-value" style="color: #ef4444;">{{ "{:,.0f}".format(today_expense) }} د.ع</span>
                </div>
                <div style="font-size: 36px;">🧾</div>
            </div>
            <div class="stat-card">
                <div class="stat-info">
                    <span class="stat-label">🛎️ مێزە کراوەکان</span>
                    <span class="stat-value" style="color: #f59e0b;">{{ active_tables_count }} مێز</span>
                </div>
                <div style="font-size: 36px;">🍽️</div>
            </div>
            <div class="stat-card">
                <div class="stat-info">
                    <span class="stat-label">👥 ژمارەی شاگرد</span>
                    <span class="stat-value" style="color: #38bdf8;">{{ total_workers }} شاگرد</span>
                </div>
                <div style="font-size: 36px;">👤</div>
            </div>
        </div>

        <div class="section-header">📁 بەشە کارگێڕییەکانی سیستەم</div>
        <div class="dashboard-modules-grid">
            <a href="/admin/amar" class="module-card" style="border: 2px solid #f59e0b;">
                <div class="module-top"><div class="module-icon">📊</div><span class="module-badge" style="background:#f59e0b; color:#fff;">سەربەخۆ</span></div>
                <div class="module-title">ئامار و قازانج (ڕاپۆرت)</div>
                <div class="module-desc">ڕاپۆرتی فرۆش بە دەرهێنانی وردی هەموو خواردنە فرۆشراوەکان، مەسرووف و قازانج.</div>
            </a>

            <a href="/admin/workers" class="module-card" style="border: 2px solid #38bdf8;">
                <div class="module-top"><div class="module-icon">👥</div><span class="module-badge" style="background:#38bdf8; color:#03261d;">شاگرد</span></div>
                <div class="module-title">حیساباتی شاگردەکان</div>
                <div class="module-desc">تۆمارکردن، ئامادەبوونی ڕۆژانەی کرێکاران بە یەک کلیک، و ئاماری شایستەی دارایی.</div>
            </a>

            <a href="/admin/cashier" class="module-card" style="border: 2px solid #10b981;">
                <div class="module-top"><div class="module-icon">🛎️</div><span class="module-badge">کاشێر</span></div>
                <div class="module-title">کاشێر و واصڵکردن</div>
                <div class="module-desc">شاشەی مێزە داواکراوەکان، دوگمەی +٥٠٠ و -٥٠٠، و چاپی وەسڵی ٨٠مم.</div>
            </a>

            <a href="/admin/masrwf" class="module-card" style="border: 2px solid #ef4444;">
                <div class="module-top"><div class="module-icon">🧾</div><span class="module-badge" style="background:#ef4444; color:#fff;">مەسرووف</span></div>
                <div class="module-title">مەسرووفات و خەرجییەکان</div>
                <div class="module-desc">تۆمارکردن، دەستکاری، سڕینەوە بە شێوازی فۆڕمی سی شارپ لەگەڵ فلتەر.</div>
            </a>

            <a href="/admin/qasa" class="module-card">
                <div class="module-top"><div class="module-icon">💵</div><span class="module-badge">قاسە</span></div>
                <div class="module-title">قاسەی فرۆشتن (٢٤ کاتژمێر)</div>
                <div class="module-desc">بینینی پسولە واصڵکراوەکان، کۆی داهات، داشکاندن و کاتی وەسڵەکان.</div>
            </a>

            <a href="/admin/users" class="module-card">
                <div class="module-top"><div class="module-icon">🔐</div><span class="module-badge">بەکارهێنەر</span></div>
                <div class="module-title">بەکارهێنەران و دەسەڵاتەکان</div>
                <div class="module-desc">دانانی ناوی بەکارهێنەر و وشەی نهێنی، دەستکاری، بلۆککردن، سڕینەوە.</div>
            </a>

            <a href="/admin/menu_manager" class="module-card">
                <div class="module-top"><div class="module-icon">📖</div><span class="module-badge">مێنۆ</span></div>
                <div class="module-title">بەڕێوەبردنی خواردنەکان</div>
                <div class="module-desc">زیادکردنی خواردنی نوێ، کۆمبۆبۆکسی پۆلێن، و ئەپلۆدکردنی وێنە.</div>
            </a>

            <a href="/desktop/tables" class="module-card">
                <div class="module-top"><div class="module-icon">🍽️</div><span class="module-badge">ئایپاد</span></div>
                <div class="module-title">مێزەکان و گارسۆن (ئایپاد)</div>
                <div class="module-desc">شاشەی مێزەکان، ئۆردەری خواردن و گواستنەوەی مێز.</div>
            </a>

            <a href="/mobile/tables" class="module-card">
                <div class="module-top"><div class="module-icon">📱</div><span class="module-badge">مۆبایل</span></div>
                <div class="module-title">مێزەکانی مۆبایل</div>
                <div class="module-desc">شاشەی ئۆردەرکردنی خواردن تایبەت بە مۆبایل.</div>
            </a>

            <a href="/qr_manager" class="module-card">
                <div class="module-top"><div class="module-icon">🖨️</div><span class="module-badge">QR</span></div>
                <div class="module-title">بەڕێوەبردنی QR مێزەکان</div>
                <div class="module-desc">چاپی ٩٠ کیوئاڕ کۆدەکە لەگەڵ دیاریکردنی مۆڵەتی ئۆردەر.</div>
            </a>
        </div>
    </main>
</body>
</html>
"""

# ==========================================
# پەڕەی ئامار و قازانج (کۆدی خاوێنکراوەی فرۆشتن لە froshtn)
# ==========================================
WEB_AMAR_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ئامار و قازانج - شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background-color: #0f172a; color: #ffffff; min-height: 100vh; padding: 20px; }
        .top-bar { display: flex; justify-content: space-between; align-items: center; background: #1e293b; padding: 14px 20px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 20px; }
        .btn-dash { background: #334155; color: #fff; padding: 8px 16px; border-radius: 8px; text-decoration: none; font-weight: 800; font-size: 13px; }
        .btn-print { background: #d97706; color: #fff; border: none; padding: 8px 18px; border-radius: 8px; font-weight: 800; font-size: 13px; cursor: pointer; }

        .filter-card { background: #1e293b; border: 1.5px solid #334155; border-radius: 14px; padding: 18px; margin-bottom: 20px; }
        .filter-form { display: flex; gap: 14px; align-items: flex-end; flex-wrap: wrap; }
        .filter-item { display: flex; flex-direction: column; gap: 5px; }
        .filter-item label { font-size: 12px; font-weight: 700; color: #cbd5e1; }
        .filter-item input { background: #0f172a; border: 1.5px solid #334155; border-radius: 8px; padding: 8px 14px; color: #fff; font-size: 13px; outline: none; }
        .btn-search { background: #10b981; color: #03261d; border: none; padding: 9px 22px; border-radius: 8px; font-weight: 800; cursor: pointer; }

        .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 22px; }
        .sum-card { background: #1e293b; border: 1.5px solid #334155; border-radius: 14px; padding: 16px; text-align: center; }
        .sum-label { font-size: 12.5px; color: #94a3b8; font-weight: 700; margin-bottom: 6px; }
        .sum-val { font-size: 18px; font-weight: 800; }

        .table-responsive { overflow-x: auto; background: #1e293b; border: 1px solid #334155; border-radius: 12px; }
        table { width: 100%; border-collapse: collapse; text-align: center; }
        th { background: #d97706; padding: 12px; color: #fff; font-size: 13px; font-weight: 800; border-bottom: 1px solid #334155; }
        td { padding: 10px; border-bottom: 1px solid #334155; font-size: 13px; }
        tr:nth-child(even) { background: #162032; }

        .print-only-header, .print-only-footer { display: none; }

        @media print {
            body { background: #fff !important; color: #000 !important; padding: 10mm !important; }
            .top-bar, .filter-card, .btn-print, .btn-dash, .summary-grid { display: none !important; }
            .print-only-header { display: block !important; text-align: center; margin-bottom: 15px; }
            .print-only-header h2 { font-size: 18px; color: #d97706 !important; margin-bottom: 4px; }
            .print-only-header p { font-size: 12px; color: #333; margin-bottom: 10px; }
            .print-divider { border-top: 2px solid #d97706; margin-bottom: 15px; }
            .table-responsive { background: #fff !important; border: 1px solid #000 !important; }
            table { border: 1px solid #000 !important; }
            th { background: #e2e8f0 !important; color: #000 !important; border: 1px solid #000 !important; font-size: 11px; }
            td { color: #000 !important; border: 1px solid #000 !important; font-size: 11px; padding: 6px; }
            tr:nth-child(even) { background: #fff !important; }
            .print-only-footer { display: block !important; margin-top: 15px; border: 1px solid #000; background: #f8fafc; padding: 12px; border-radius: 6px; }
            .print-footer-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 12px; font-weight: bold; }
        }
    </style>
</head>
<body>
    <div class="top-bar">
        <h2 style="color:#f59e0b;">📊 ڕاپۆرتی گشتی فرۆش، مەسرووف و قازانج</h2>
        <div style="display:flex; gap:8px;">
            <button type="button" class="btn-print" onclick="window.print()">🖨️ چاپی ڕاپۆرت (A4)</button>
            <a href="/admin" class="btn-dash">⬅️ داشبۆرد</a>
        </div>
    </div>

    <div class="print-only-header">
        <h2>✨ شاهور ڕێستۆرانت - ڕاپۆرتی گشتی فرۆش و دارایی</h2>
        <p>ماوەی بەروار: لە [{{ start_date }}] تا [{{ end_date }}]</p>
        <div class="print-divider"></div>
    </div>

    <div class="filter-card">
        <form method="GET" action="/admin/amar" class="filter-form">
            <div class="filter-item">
                <label>لە بەرواری:</label>
                <input type="date" name="start_date" value="{{ start_date }}" required>
            </div>
            <div class="filter-item">
                <label>تا بەرواری:</label>
                <input type="date" name="end_date" value="{{ end_date }}" required>
            </div>
            <button type="submit" class="btn-search">🔍 گەڕان و حیسابکردن</button>
        </form>
    </div>

    <div class="summary-grid">
        <div class="sum-card">
            <div class="sum-label">💰 کۆی گشتی فرۆش</div>
            <div class="sum-val" style="color: #10b981;">{{ "{:,.0f}".format(total_sales) }} د.ع</div>
        </div>
        <div class="sum-card">
            <div class="sum-label">💸 کۆی خەرجی مەسرووف</div>
            <div class="sum-val" style="color: #ef4444;">{{ "{:,.0f}".format(total_expenses) }} د.ع</div>
        </div>
        <div class="sum-card">
            <div class="sum-label">👥 کرێی شاگردەکان</div>
            <div class="sum-val" style="color: #f59e0b;">{{ "{:,.0f}".format(total_workers_wage) }} د.ع</div>
        </div>
        <div class="sum-card">
            <div class="sum-label">🧾 کۆی هەموو خەرجییەکان</div>
            <div class="sum-val" style="color: #e2e8f0;">{{ "{:,.0f}".format(total_all_expenses) }} د.ع</div>
        </div>
        <div class="sum-card">
            <div class="sum-label">✨ قازانجی سافی (بڕی ماوە)</div>
            <div class="sum-val" style="color: {{ '#10b981' if net_profit >= 0 else '#ef4444' }};">
                {{ "{:,.0f}".format(net_profit) }} د.ع
            </div>
        </div>
        <div class="sum-card">
            <div class="sum-label">🍽️ کۆی ژمارەی خواردن</div>
            <div class="sum-val" style="color: #38bdf8;">{{ "{:,.0f}".format(total_items_count) }} دانە</div>
        </div>
    </div>

    <div class="table-responsive">
        <table>
            <thead>
                <tr>
                    <th style="width: 70px;">ڕیزبەندی</th>
                    <th style="text-align:right;">ناوی خواردن / خواردنەوە</th>
                    <th>کۆی ژمارەی فرۆشراو</th>
                    <th>نرخی تاک</th>
                    <th>کۆی داهات (دینار)</th>
                </tr>
            </thead>
            <tbody>
                {% for r in report_rows %}
                <tr>
                    <td>{{ loop.index }}</td>
                    <td style="text-align:right; font-weight:700;">{{ r.clean_food_name }}</td>
                    <td style="color:#38bdf8; font-weight:800;">{{ "{:,.0f}".format(r.qty) }}</td>
                    <td>{{ "{:,.0f}".format(r.price) }} د.ع</td>
                    <td style="color:#10b981; font-weight:800;">{{ "{:,.0f}".format(r.total) }} د.ع</td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="5" style="padding:30px; color:#94a3b8;">هیچ فرۆشێک لەم ماوەیەدا تۆمار نەکراوە</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <div class="print-only-footer">
        <div class="print-footer-grid">
            <div>کۆی گشتی ژمارەی خواردن: {{ "{:,.0f}".format(total_items_count) }} دانە</div>
            <div style="color: darkgreen;">کۆی گشتی فرۆش: {{ "{:,.0f}".format(total_sales) }} دینار</div>
            <div style="color: darkred;">کۆی خەرجی مەسرووف: {{ "{:,.0f}".format(total_expenses) }} دینار</div>
            <div style="color: darkred;">کۆی کرێی شاگردەکان: {{ "{:,.0f}".format(total_workers_wage) }} دینار</div>
            <div>کۆی هەموو خەرجییەکان: {{ "{:,.0f}".format(total_all_expenses) }} دینار</div>
            <div style="font-size: 13px; color: {{ 'darkgreen' if net_profit >= 0 else 'red' }};">
                قازانجی سافی (بڕی ماوە): {{ "{:,.0f}".format(net_profit) }} دینار
            </div>
        </div>
    </div>
</body>
</html>
"""

# ==========================================
# پەڕەی شاگردەکان (بەشی ١: تۆمار، بەشی ٢: ئامادەبوونی ڕۆژانە، بەشی ٣: ئاماری مووچە)
# ==========================================
WEB_WORKERS_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>حیساباتی شاگردەکان - شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background-color: #03261d; color: #ffffff; min-height: 100vh; padding: 20px; }
        .top-bar { display: flex; justify-content: space-between; align-items: center; background: #064032; padding: 14px 20px; border-radius: 12px; border: 1px solid #0b5e4a; margin-bottom: 20px; }
        .btn-dash { background: #334155; color: #fff; padding: 8px 16px; border-radius: 8px; text-decoration: none; font-weight: 800; font-size: 13px; }
        
        .section-box { background: #064032; border: 1.5px solid #0b5e4a; border-radius: 14px; padding: 18px; margin-bottom: 24px; }
        .sec-title { color: #10b981; font-size: 16px; font-weight: 800; margin-bottom: 14px; border-bottom: 1px solid #0b5e4a; padding-bottom: 6px; display: flex; justify-content: space-between; align-items: center; }
        
        .form-row { display: flex; gap: 10px; flex-wrap: wrap; align-items: flex-end; }
        .form-group { display: flex; flex-direction: column; gap: 4px; }
        .form-group label { font-size: 12px; font-weight: 700; color: #a7f3d0; }
        .form-input { padding: 9px 12px; background: #03261d; border: 1.5px solid #0b5e4a; border-radius: 8px; color: #fff; font-size: 13px; outline: none; }
        .form-input:focus { border-color: #10b981; }
        .btn-act { padding: 9px 18px; border-radius: 8px; border: none; font-weight: 800; cursor: pointer; font-size: 13px; }
        .btn-add { background: #10b981; color: #03261d; }
        .btn-filter { background: #3b82f6; color: #fff; }

        .table-wrap { overflow-x: auto; background: #03261d; border: 1px solid #0b5e4a; border-radius: 10px; margin-top: 12px; }
        table { width: 100%; border-collapse: collapse; text-align: center; }
        th { background: #085341; padding: 11px; color: #a7f3d0; font-size: 13px; font-weight: 800; border-bottom: 1px solid #0b5e4a; }
        td { padding: 10px; border-bottom: 1px solid #0b5e4a; font-size: 13px; }
        tr:hover { background: #085341; }
        
        .btn-status-present { background: #10b981; color: #03261d; font-weight: 800; border: none; padding: 6px 14px; border-radius: 8px; cursor: pointer; }
        .btn-status-absent { background: #ef4444; color: #ffffff; font-weight: 800; border: none; padding: 6px 14px; border-radius: 8px; cursor: pointer; }
        .btn-edit { background: #3b82f6; color: #fff; padding: 4px 8px; border-radius: 6px; font-size: 11px; cursor: pointer; border: none; font-weight: 700; }
        .btn-del { color: #ef4444; text-decoration: none; font-weight: bold; font-size: 13px; }

        .modal { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.75); display: none; align-items: center; justify-content: center; z-index: 2000; padding: 16px; }
        .modal-content { background: #064032; border: 2px solid #0b5e4a; border-radius: 14px; width: 100%; max-width: 420px; padding: 20px; }
    </style>
</head>
<body>
    <div class="top-bar">
        <h2 style="color:#38bdf8;">👥 سیستەمی بەڕێوەبردن و حیساباتی شاگردەکان</h2>
        <a href="/admin" class="btn-dash">⬅️ داشبۆرد</a>
    </div>

    <!-- بەشی ١: تۆمارکردنی کرێکار و لیستی کرێکارەکان بۆ دەستکاری و سڕینەوە -->
    <div class="section-box">
        <div class="sec-title"><span>➕ بەشی ١: تۆمارکردن و بەڕێوەبردنی کرێکارەکان</span></div>
        <form method="POST" action="/admin/add_worker" class="form-row">
            <div class="form-group"><label>ناوی شاگرد:</label><input type="text" name="name" class="form-input" required placeholder="ناوی تەواو"></div>
            <div class="form-group"><label>تەلەفۆن:</label><input type="text" name="phone" class="form-input" placeholder="0770xxxxxxx"></div>
            <div class="form-group"><label>مووچەی ڕۆژانە (دینار):</label><input type="number" name="salary" class="form-input" required placeholder="25000"></div>
            <button type="submit" class="btn-act btn-add">💾 زیادکردنی شاگرد</button>
        </form>

        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>ناوی شاگرد</th>
                        <th>تەلەفۆن</th>
                        <th>مووچەی دیاریکراوی ڕۆژانە</th>
                        <th>کردارەکان (دەستکاری / سڕینەوە)</th>
                    </tr>
                </thead>
                <tbody>
                    {% for w in raw_workers %}
                    <tr>
                        <td>{{ loop.index }}</td>
                        <td style="font-weight:bold; color:#10b981;">{{ w.name }}</td>
                        <td>{{ w.phone }}</td>
                        <td style="color:#f59e0b; font-weight:bold;">{{ "{:,.0f}".format(w.salary) }} د.ع</td>
                        <td>
                            <button type="button" class="btn-edit" onclick="openWorkerModal({{ w.id }}, '{{ w.name }}', '{{ w.phone }}', {{ w.salary }})">✏️ دەستکاری</button>
                            <a href="/admin/delete_worker/{{ w.id }}" class="btn-del" onclick="return confirm('ئایا دڵنیایت لە سڕینەوەی ئەم کرێکارە؟')">🗑️ سڕینەوە</a>
                        </td>
                    </tr>
                    {% else %}
                    <tr><td colspan="5" style="padding:15px; color:#94a3b8;">هیچ شاگردێک تۆمار نەکراوە</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <!-- بەشی ٢: تۆماری ئامادەبوونی ڕۆژانە (بە پیشاندانی هاتوو / نەهاتوو) -->
    <div class="section-box">
        <div class="sec-title">
            <span>📝 بەشی ٢: ئامادەبوونی ڕۆژانەی کرێکاران (ئەمڕۆ)</span>
            <span style="font-size:12px; color:#a7f3d0;">بەرواری ئەمڕۆ: {{ today_date }}</span>
        </div>
        <p style="font-size:12.5px; color:#cbd5e1; margin-bottom:10px;">
            ⚠️ کرێکاران بە شێوەی خۆکارانە لەسەر <b>«❌ نەهاتوو»</b> دانراون و ڕۆژانەیان بۆ ناژمێردرێت، تەنها کلیک بکە لەسەر دوگمەکە تا ببێتە <b>«✅ هاتوو»</b> و ڕۆژانەی بۆ حیساب بکرێت:
        </p>

        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>ناوی شاگرد</th>
                        <th>مووچەی ڕۆژانە</th>
                        <th>دۆخی ئامادەبوون بۆ ئەمڕۆ (کلیک بکە بۆ گۆڕین)</th>
                        <th>پاداشت (Bonus) بۆ ئەمڕۆ</th>
                    </tr>
                </thead>
                <tbody>
                    {% for a in today_attendance_list %}
                    <tr>
                        <td>{{ loop.index }}</td>
                        <td style="font-weight:bold; color:#fff;">{{ a.name }}</td>
                        <td>{{ "{:,.0f}".format(a.salary) }} د.ع</td>
                        <td>
                            {% if a.status == 'هاتوو' %}
                                <button type="button" class="btn-status-present" onclick="toggleAttendance({{ a.worker_id }}, 'نەهاتوو')">✅ هاتوو (ڕۆژانە هەژمار دەکرێت)</button>
                            {% else %}
                                <button type="button" class="btn-status-absent" onclick="toggleAttendance({{ a.worker_id }}, 'هاتوو')">❌ نەهاتوو (مووچەی بۆ ناژمێردرێت)</button>
                            {% endif %}
                        </td>
                        <td>
                            <input type="number" value="{{ a.bonus }}" style="width:110px; padding:5px; background:#064032; border:1px solid #10b981; color:#fff; text-align:center; border-radius:6px; font-weight:bold;" onchange="updateBonus({{ a.worker_id }}, this.value)"> د.ع
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <!-- بەشی ٣: ئاماری مووچەی شایستە و حیسابات بە فلتەر -->
    <div class="section-box">
        <div class="sec-title"><span>📊 بەشی ٣: ئاماری مووچە و حیساباتی شایستەی دارایی</span></div>
        
        <form method="GET" action="/admin/workers" class="form-row" style="margin-bottom:14px;">
            <div class="form-group">
                <label>لە بەرواری:</label>
                <input type="date" name="start_date" class="form-input" value="{{ start_date }}" required>
            </div>
            <div class="form-group">
                <label>تا بەرواری:</label>
                <input type="date" name="end_date" class="form-input" value="{{ end_date }}" required>
            </div>
            <button type="submit" class="btn-act btn-filter">🔍 حیسابکردنی ماوە</button>
            <a href="/admin/workers" style="color:#94a3b8; font-size:12px; margin-bottom:10px; text-decoration:none;">پاککردنەوە (مانگی ئێستا)</a>
        </form>

        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>ناوی شاگرد</th>
                        <th>ڕۆژانی ئامادەبوون (هاتوو)</th>
                        <th>ڕۆژانەی مووچە</th>
                        <th>کۆی مووچەی ڕۆژانە</th>
                        <th>کۆی بەخشش</th>
                        <th>کۆی گشتی شایستە لەم ماوەیەدا</th>
                    </tr>
                </thead>
                <tbody>
                    {% for w in wage_rows %}
                    <tr>
                        <td>{{ loop.index }}</td>
                        <td style="font-weight:bold; color:#10b981;">{{ w.name }}</td>
                        <td style="color:#38bdf8; font-weight:bold;">{{ w.work_days }} ڕۆژ</td>
                        <td>{{ "{:,.0f}".format(w.salary) }} د.ع</td>
                        <td>{{ "{:,.0f}".format(w.total_salary) }} د.ع</td>
                        <td style="color:#f59e0b;">{{ "{:,.0f}".format(w.total_bonus) }} د.ع</td>
                        <td style="color:#10b981; font-weight:bold; font-size:14px;">{{ "{:,.0f}".format(w.total_due) }} د.ع</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <!-- مۆداڵی دەستکاریکردنی شاگرد -->
    <div class="modal" id="workerEditModal">
        <div class="modal-content">
            <h3 style="color:#10b981; margin-bottom:14px; text-align:center;">✏️ دەستکاریکردنی زانیاری شاگرد</h3>
            <form id="editWorkerForm" method="POST" action="">
                <div class="form-group" style="margin-bottom:10px;">
                    <label>ناوی شاگرد:</label>
                    <input type="text" id="m_worker_name" name="name" class="form-input" style="width:100%;" required>
                </div>
                <div class="form-group" style="margin-bottom:10px;">
                    <label>تەلەفۆن:</label>
                    <input type="text" id="m_worker_phone" name="phone" class="form-input" style="width:100%;">
                </div>
                <div class="form-group" style="margin-bottom:14px;">
                    <label>مووچەی ڕۆژانە (دینار):</label>
                    <input type="number" id="m_worker_salary" name="salary" class="form-input" style="width:100%;" required>
                </div>
                <button type="submit" class="btn-act btn-add" style="width:100%;">💾 پاشەکەوتکردن</button>
                <button type="button" onclick="closeWorkerModal()" style="background:none; border:none; color:#94a3b8; width:100%; margin-top:10px; cursor:pointer;">داخستن</button>
            </form>
        </div>
    </div>

    <script>
        function openWorkerModal(id, name, phone, salary) {
            document.getElementById('editWorkerForm').action = '/admin/edit_worker/' + id;
            document.getElementById('m_worker_name').value = name;
            document.getElementById('m_worker_phone').value = phone;
            document.getElementById('m_worker_salary').value = salary;
            document.getElementById('workerEditModal').style.display = 'flex';
        }
        function closeWorkerModal() {
            document.getElementById('workerEditModal').style.display = 'none';
        }

        function toggleAttendance(workerId, newStatus) {
            fetch('/admin/toggle_attendance', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ worker_id: workerId, status: newStatus, att_date: '{{ today_date }}' })
            }).then(r => r.json()).then(res => {
                if(res.status === 'success') {
                    location.reload();
                }
            });
        }

        function updateBonus(workerId, bonusVal) {
            fetch('/admin/update_worker_bonus', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ worker_id: workerId, bonus: bonusVal, att_date: '{{ today_date }}' })
            }).then(r => r.json()).then(res => {
                if(res.status === 'success') {
                    location.reload();
                }
            });
        }
    </script>
</body>
</html>
"""

# ==========================================
# پەڕەی بەڕێوەبردنی QR
# ==========================================
QR_MANAGER_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>بەڕێوەبردنی QR - شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background-color: #03261d; color: #ffffff; min-height: 100vh; padding: 20px; }
        .top-bar { display: flex; justify-content: space-between; align-items: center; background: #064032; padding: 14px 20px; border-radius: 12px; border: 1px solid #0b5e4a; margin-bottom: 20px; }
        .btn-action { background: #10b981; color: #03261d; padding: 8px 16px; border-radius: 8px; text-decoration: none; font-weight: 800; border: none; cursor: pointer; font-size: 13px; }
        .controls-panel { background: #064032; padding: 14px 20px; border-radius: 12px; border: 1px solid #0b5e4a; margin-bottom: 24px; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
        .qr-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; }
        .qr-card { background: #ffffff; color: #0f172a; border-radius: 14px; padding: 16px; display: flex; flex-direction: column; align-items: center; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.3); border: 2px solid #e2e8f0; }
        .qr-card img { width: 140px; height: 140px; border-radius: 8px; margin: 10px 0; }
        .qr-title { font-size: 18px; font-weight: 800; color: #03261d; }
        .perm-toggle-btn { margin-top: 8px; width: 100%; border: none; padding: 8px; border-radius: 8px; font-weight: 800; font-size: 12px; cursor: pointer; }
        .perm-enabled { background: #dcfce7; color: #166534; }
        .perm-disabled { background: #fee2e2; color: #991b1b; }
        @media print {
            body { background: #fff !important; color: #000 !important; padding: 0 !important; }
            .top-bar, .controls-panel, .perm-toggle-btn { display: none !important; }
            .qr-grid { grid-template-columns: repeat(4, 1fr) !important; gap: 10px !important; }
            .qr-card { border: 1px solid #000 !important; page-break-inside: avoid; }
        }
    </style>
</head>
<body>
    <div class="top-bar">
        <h2 style="color:#10b981;">📱 بەڕێوەبردنی QR کۆد و مۆڵەتی مێزەکان</h2>
        <div style="display:flex; gap:8px;">
            <button class="btn-action" onclick="window.print()">🖨️ چاپی هەموو QRەکان</button>
            <a href="/admin" class="btn-action" style="background:#334155; color:#fff;">⬅️ داشبۆرد</a>
        </div>
    </div>

    <div class="controls-panel">
        <span style="font-weight:700; color:#a7f3d0;">کۆنتڕۆڵی گشتی ئۆردەرکردنی موشتەری:</span>
        <button class="btn-action" onclick="setAllPermissions(1)">✅ کاراکردنی هەموو مێزەکان</button>
        <button class="btn-action" style="background:#ef4444; color:#fff;" onclick="setAllPermissions(0)">⛔ ناچالاککردنی هەموو مێزەکان (تەنها بینین)</button>
    </div>

    <div class="qr-grid">
        {% for num in range(1, 91) %}
        {% set is_allowed = perm_dict.get(num, 1) %}
        <div class="qr-card">
            <div class="qr-title">مێزی {{ num }}</div>
            <img src="https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={{ base_url }}/table/{{ num }}" alt="QR Table {{ num }}">
            <button type="button" class="perm-toggle-btn {{ 'perm-enabled' if is_allowed else 'perm-disabled' }}" id="btn-perm-{{ num }}" onclick="togglePerm({{ num }})">
                {{ 'ئۆردەر: کراوەیە' if is_allowed else 'ئۆردەر: داخراوە (تەنها بینین)' }}
            </button>
        </div>
        {% endfor %}
    </div>

    <script>
        function togglePerm(tableNum) {
            fetch('/toggle_table_permission', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ table_number: tableNum })
            }).then(r => r.json()).then(data => {
                if (data.status === 'success') {
                    const btn = document.getElementById('btn-perm-' + tableNum);
                    if (data.allow_ordering) {
                        btn.innerText = 'ئۆردەر: کراوەیە';
                        btn.className = 'perm-toggle-btn perm-enabled';
                    } else {
                        btn.innerText = 'ئۆردەر: داخراوە (تەنها بینین)';
                        btn.className = 'perm-toggle-btn perm-disabled';
                    }
                }
            });
        }

        function setAllPermissions(allow) {
            if (confirm(allow ? "ئایا هەموو مێزەکان ڕێگەی ئۆردەریان پێبدرێت؟" : "ئایا هەموو مێزەکان ببنە تەنها بینین؟")) {
                fetch('/set_all_table_permissions', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ allow_ordering: allow })
                }).then(r => r.json()).then(data => {
                    if (data.status === 'success') location.reload();
                });
            }
        }
    </script>
</body>
</html>
"""

# ==========================================
# تێمپلێتەکانی ئایپاد و دیسکتۆپ
# ==========================================
DESKTOP_TABLES_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>هەڵبژاردنی مێز - شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        html, body { background-color: #03261d; color: #ffffff; min-height: 100%; height: auto; overflow-x: hidden; overflow-y: scroll; }
        .header-bar { background-color: #064032; padding: 12px 20px; display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #0b5e4a; position: sticky; top: 0; z-index: 1000; }
        .header-title { font-size: 16px; font-weight: 800; color: #ffffff; text-align: center; flex: 1; }
        .header-actions { display: flex; gap: 8px; align-items: center; }
        .btn-header { color: #ffffff; border: none; padding: 8px 14px; border-radius: 8px; font-size: 13px; font-weight: 800; text-decoration: none; cursor: pointer; display: flex; align-items: center; gap: 4px; }
        .btn-takeaway-hdr { background-color: #0284c7; border: 1.5px solid #38bdf8; }
        .btn-qr-mgr { background-color: #3b82f6; }
        .btn-exit { background-color: #ef4444; }
        
        .active-takeaways-bar { padding: 10px 20px 0 20px; width: 100%; max-width: 1500px; margin: 0 auto; }
        .active-takeaways-container { display: flex; flex-wrap: wrap; gap: 8px; background: #064032; padding: 10px; border-radius: 12px; border: 1.5px solid #0284c7; }
        .active-takeaway-btn { background: #0284c7; color: #fff; text-decoration: none; padding: 8px 12px; border-radius: 8px; font-weight: 800; font-size: 13px; display: flex; align-items: center; gap: 6px; }

        .tables-grid-wrapper { padding: 16px 20px 80px 20px; width: 100%; max-width: 1500px; margin: 0 auto; }
        .tables-grid { display: grid; grid-template-columns: repeat(10, 1fr); gap: 12px; width: 100%; }
        .table-box { background-color: #ffffff; border: 2px solid #e2e8f0; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 28px; font-weight: 800; color: #03261d; text-decoration: none; height: 90px; cursor: pointer; }
        .table-box.active-occupied { background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important; color: #ffffff !important; border-color: #047857 !important; }
        
        .modal { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.75); display: none; align-items: center; justify-content: center; z-index: 2000; padding: 16px; }
        .modal-box { background: #064032; border: 2px solid #0b5e4a; border-radius: 16px; width: 100%; max-width: 440px; padding: 24px; color: #fff; }
        .modal-box input { width: 100%; padding: 12px; background: #03261d; border: 1.5px solid #0b5e4a; border-radius: 8px; color: #fff; font-size: 14px; margin-bottom: 12px; outline: none; }
        @media (max-width: 900px) { .tables-grid { grid-template-columns: repeat(8, 1fr); gap: 10px; } .table-box { height: 80px; font-size: 24px; } }
    </style>
</head>
<body>
    <div class="header-bar">
        <a href="/logout" class="btn-header btn-exit">✕ دەرچوون</a>
        <div class="header-title">تکایە بۆ ئۆردەرکردنی خواردن و خواردنەوە مێزێک دیاری بکە!</div>
        <div class="header-actions">
            {% if session.get('role') == 'admin' %}
            <a href="/admin" class="btn-header" style="background-color:#10b981;">👑 داشبۆرد</a>
            {% endif %}
            <button type="button" class="btn-header btn-takeaway-hdr" onclick="document.getElementById('takeawayModal').style.display='flex'">🥡 سەفەری</button>
            <a href="/qr_manager" class="btn-header btn-qr-mgr">📱 بەڕێوەبردنی QR</a>
        </div>
    </div>

    {% if active_takeaways %}
    <div class="active-takeaways-bar">
        <div class="active-takeaways-container">
            <span style="font-size:12px; font-weight:bold; color:#38bdf8; display:flex; align-items:center;">سەفەرییە چالاکەکان:</span>
            {% for t in active_takeaways %}
                <a href="/desktop?table={{ t|urlencode }}" class="active-takeaway-btn">
                    <span>🛵</span>
                    <span>{{ t }}</span>
                </a>
            {% endfor %}
        </div>
    </div>
    {% endif %}

    <div class="tables-grid-wrapper">
        <div class="tables-grid" id="tablesGrid">
            {% for num in range(1, 91) %}
                <a href="/desktop?table={{ num }}" class="table-box" id="tbl-box-{{ num }}">{{ num }}</a>
            {% endfor %}
        </div>
    </div>

    <div class="modal" id="takeawayModal">
        <div class="modal-box">
            <h3 style="color:#38bdf8; margin-bottom:14px; text-align:center;">🥡 تۆمارکردنی داواکاری سەفەری</h3>
            <label style="font-size:12px; color:#a7f3d0;">ناوی موشتەری:</label>
            <input type="text" id="custName" placeholder="بۆ نموونە: ئەحمەد">
            
            <label style="font-size:12px; color:#a7f3d0;">ژمارەی مۆبایل:</label>
            <input type="text" id="custPhone" placeholder="0770xxxxxxx">
            
            <label style="font-size:12px; color:#a7f3d0;">ناونیشان (ئەگەر دلیڤەری بێت):</label>
            <input type="text" id="custAddress" placeholder="گەڕەک، شەقام، خانوو">
            
            <button type="button" class="btn-header btn-takeaway-hdr" onclick="startTakeawayOrder()" style="margin-top:10px; font-size:15px; padding:12px; width:100%; justify-content:center;">دەستپێکردنی ئۆردەر ➔</button>
            <button type="button" onclick="document.getElementById('takeawayModal').style.display='none'" style="background:none; border:none; color:#94a3b8; width:100%; margin-top:10px; cursor:pointer;">پاشگەزبوونەوە</button>
        </div>
    </div>

    <script>
        function startTakeawayOrder() {
            let name = document.getElementById('custName').value.trim() || 'کڕیار';
            let phone = document.getElementById('custPhone').value.trim();
            let addr = document.getElementById('custAddress').value.trim();
            let idStr = "سەفەری (" + name;
            if(phone) idStr += " - " + phone;
            if(addr) idStr += " - " + addr;
            idStr += ")";
            window.location.href = "/desktop?table=" + encodeURIComponent(idStr);
        }

        function refreshTableStatus() {
            fetch('/get_active_tables?t=' + new Date().getTime())
                .then(res => res.json())
                .then(activeTables => {
                    for (let i = 1; i <= 90; i++) {
                        const box = document.getElementById('tbl-box-' + i);
                        if (box) {
                            if (activeTables.includes(i.toString())) {
                                box.classList.add('active-occupied');
                            } else {
                                box.classList.remove('active-occupied');
                            }
                        }
                    }
                }).catch(() => {});
        }
        refreshTableStatus();
        setInterval(refreshTableStatus, 2500);
    </script>
</body>
</html>
"""

DESKTOP_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مێنیوی شاهور - {{ selected_table }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        :root { --bg-main: #0b0f19; --bg-card: #151d30; --bg-sidebar: #101726; --gold: #f59e0b; --text-main: #f8fafc; --text-muted: #94a3b8; --border-color: #334155; --success: #10b981; --danger: #ef4444; }
        body { background-color: var(--bg-main); color: var(--text-main); height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
        .desktop-main-layout { display: grid; grid-template-columns: 1fr 480px; flex: 1; overflow: hidden; }
        .menu-section { display: flex; flex-direction: column; padding: 16px 20px; overflow-y: auto; }
        .categories-visual-bar { display: flex; gap: 12px; margin-bottom: 22px; overflow-x: auto; padding: 6px 4px 10px 4px; flex-shrink: 0; }
        .cat-visual-btn { background: #151d30; border: 2px solid #334155; border-radius: 14px; padding: 8px 10px; display: flex; flex-direction: column; align-items: center; min-width: 90px; cursor: pointer; }
        .cat-visual-btn.active { background: #1e293b; border-color: var(--gold); }
        .cat-visual-img { width: 60px; height: 60px; border-radius: 10px; object-fit: cover; margin-bottom: 6px; }
        .cat-visual-title { font-size: 13px; font-weight: 700; color: #f8fafc; }
        .food-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 14px; padding-bottom: 20px; }
        .desktop-food-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; padding: 10px; display: flex; flex-direction: column; gap: 8px; min-height: 235px; justify-content: space-between; }
        .desktop-food-img { width: 100%; height: 125px; border-radius: 8px; object-fit: cover; cursor: pointer; }
        .desktop-food-info { display: flex; flex-direction: column; gap: 3px; text-align: center; }
        .desktop-food-name { font-size: 13.5px; font-weight: 700; min-height: 36px; display: flex; align-items: center; justify-content: center; }
        .desktop-food-price { font-size: 13px; font-weight: 800; color: var(--success); }
        .opt-select { width: 100%; background: var(--bg-main); color: var(--gold); border: 1px solid var(--border-color); border-radius: 6px; padding: 4px; font-size: 11px; font-weight: 700; outline: none; }
        .cart-sidebar { background: var(--bg-sidebar); border-right: 1px solid var(--border-color); display: flex; flex-direction: column; padding: 16px; height: 100%; overflow: hidden; }
        .cart-top-bar { display: flex; align-items: center; justify-content: space-between; background: var(--bg-card); padding: 8px 12px; border-radius: 10px; margin-bottom: 12px; }
        .table-badge-header { background: var(--gold); color: var(--bg-main); padding: 5px 12px; border-radius: 6px; font-size: 14px; font-weight: 800; max-width: 250px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .btn-top-action { background: #1e293b; color: var(--text-main); border: 1px solid var(--border-color); padding: 5px 10px; border-radius: 6px; font-size: 11px; font-weight: 700; cursor: pointer; text-decoration: none; }
        .cart-items-container { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; margin-bottom: 10px; }
        .desktop-cart-row { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; padding: 10px; }
        .desktop-counter-group { display: flex; align-items: center; background: var(--bg-main); border-radius: 6px; padding: 2px; gap: 4px; }
        .desktop-btn-count { width: 30px; height: 30px; border-radius: 6px; border: none; background: #1e293b; color: #fff; font-size: 14px; font-weight: 800; cursor: pointer; }
        .btn-send-desktop { flex: 2; background: linear-gradient(135deg, var(--gold) 0%, #d97706 100%); color: var(--bg-main); border: none; padding: 11px; border-radius: 8px; font-size: 14px; font-weight: 800; cursor: pointer; }
        .btn-add-plate-desktop { flex: 1; background: #8b5cf6; color: #fff; border: none; padding: 11px; border-radius: 8px; font-size: 12px; font-weight: 800; cursor: pointer; display: none; }
        #toastMsg { position: fixed; top: 20px; left: 50%; transform: translateX(-50%); background: var(--success); color: #fff; padding: 10px 24px; border-radius: 30px; font-size: 14px; font-weight: 700; z-index: 1000; display: none; }

        .modal-transfer { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.75); display: none; align-items: center; justify-content: center; z-index: 2000; padding: 16px; }
        .modal-transfer-box { background: #151d30; border: 2px solid var(--border-color); border-radius: 14px; padding: 20px; width: 100%; max-width: 360px; color: #fff; text-align: center; }
    </style>
</head>
<body>
    <div id="toastMsg">✅ بە سەرکەوتوویی نێردرا</div>
    <div class="desktop-main-layout">
        <div class="menu-section">
            <div class="categories-visual-bar">
                <div class="cat-visual-btn active" onclick="filterCat('all', this)">
                    <img src="https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=140" class="cat-visual-img">
                    <span class="cat-visual-title">هەموو</span>
                </div>
                {% for cat, items in categories.items() %}
                    <div class="cat-visual-btn" onclick="filterCat('cat-group-{{ loop.index }}', this)">
                        <img src="{{ items[0].image_path if items[0].image_path else 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=140' }}" class="cat-visual-img" onerror="this.src='https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=140'">
                        <span class="cat-visual-title">{{ cat }}</span>
                    </div>
                {% endfor %}
            </div>
            
            <div class="menu-container-desktop">
                {% for cat, items in categories.items() %}
                <div class="category-desktop-group category-group-item" id="cat-group-{{ loop.index }}">
                    <div class="food-grid">
                        {% for item in items %}
                        {% set d_safe = loop.index ~ '_' ~ cat ~ '_' ~ item.food_name|replace(' ', '_') %}
                        <div class="desktop-food-card">
                            <img src="{{ item.image_path if item.image_path else 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=300' }}" class="desktop-food-img" onclick="addFromDesktopCard('{{ item.food_name }}', {{ item.price }}, '{{ item.category }}', '{{ d_safe }}')" onerror="this.src='https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=300'">
                            <div class="desktop-food-info">
                                <div class="desktop-food-name">{{ item.food_name }}</div>
                                <div class="desktop-food-price">{{ "{:,.0f}".format(item.price) }} دینار</div>
                            </div>
                            
                            {% set show_r = item.category in ['کوڵاو', 'پەلەوەر', 'کوردیەکان'] %}
                            {% set show_c = (item.category == 'پەلەوەر') %}
                            {% if show_r or show_c %}
                            <div style="display:flex; flex-direction:row; gap:4px; width:100%;">
                                {% if show_r %}
                                <select class="opt-select" id="d_rice_{{ d_safe }}" style="flex:1; min-width:0;">
                                    <option value="">ج. برنج</option>
                                    <option value="برنجی درێژ">برنجی درێژ</option>
                                    <option value="برنجی خڕ">برنجی خڕ</option>
                                    <option value="برنجی کوردی">برنجی کوردی</option>
                                    <option value="برنج بە سرکە">برنج بە سرکە</option>
                                </select>
                                {% endif %}
                                {% if show_c %}
                                <select class="opt-select" id="d_chick_{{ d_safe }}" style="flex:1; min-width:0;">
                                    <option value="">ب. مریشک</option>
                                    <option value="سینگ">سینگ</option>
                                    <option value="ڕان">ڕان</option>
                                </select>
                                {% endif %}
                            </div>
                            {% endif %}
                        </div>
                        {% endfor %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <div class="cart-sidebar">
            <div class="cart-top-bar">
                <div class="table-badge-header">📍 {{ selected_table }}</div>
                <input type="hidden" id="currentTableNum" value="{{ selected_table }}">
                <div style="display:flex; gap:4px;">
                    <button type="button" class="btn-top-action" style="background:#3b82f6;" onclick="openTransferModal()">🔄 گواستنەوە</button>
                    <a href="/desktop/tables" class="btn-top-action">⬅️ گەڕانەوە</a>
                    <button type="button" class="btn-top-action" style="color:var(--danger);" onclick="clearCurrentTableOrders()">🗑 سڕینەوە</button>
                </div>
            </div>
            <div class="cart-items-container" id="cartItemsList"></div>
            <div style="border-top:1px solid var(--border-color); padding-top:10px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:10px; font-weight:800;">
                    <span>کۆی گشتی:</span>
                    <span id="cartTotalTxt" style="color:var(--success); font-size:18px;">0 دینار</span>
                </div>
                <div style="display:flex; gap:8px;">
                    <button type="button" id="btnAddPlateDesktop" class="btn-add-plate-desktop" onclick="addNewPlateDivider()">➕ قاپی نوێ</button>
                    <button type="button" id="btnSubmitDesktop" class="btn-send-desktop" onclick="submitFinalOrder()">ناردن بۆ مەتبەخ ➔</button>
                </div>
            </div>
        </div>
    </div>

    <div class="modal-transfer" id="transferModal">
        <div class="modal-transfer-box">
            <h3 style="color:var(--gold); margin-bottom:12px;">گواستنەوە بۆ مێزێکی تر</h3>
            <p style="font-size:12px; color:var(--text-muted); margin-bottom:12px;">مێزی نوێ هەڵبژێرە بۆ گواستنەوەی هەموو داواکارییەکان:</p>
            <select id="newTableSelect" style="width:100%; padding:10px; background:var(--bg-main); border:1px solid var(--border-color); color:#fff; border-radius:8px; font-weight:bold; margin-bottom:14px;">
                {% for n in range(1, 91) %}
                    <option value="{{ n }}">مێزی {{ n }}</option>
                {% endfor %}
            </select>
            <button type="button" onclick="confirmTransferTable()" style="background:var(--success); border:none; color:#fff; padding:10px; border-radius:8px; font-weight:bold; width:100%; cursor:pointer;">پشتڕاستکردنەوە و گواستنەوە</button>
            <button type="button" onclick="closeTransferModal()" style="background:none; border:none; color:#94a3b8; margin-top:10px; cursor:pointer;">داخستن</button>
        </div>
    </div>

    <script>
        let cartItems = [], originalTableOrders = [];
        const tableNum = document.getElementById('currentTableNum').value;

        function showToast(text, isError = false) {
            const toast = document.getElementById('toastMsg');
            toast.innerText = text;
            toast.style.background = isError ? 'var(--danger)' : 'var(--success)';
            toast.style.display = 'block';
            setTimeout(() => { toast.style.display = 'none'; }, 2200);
        }
        function checkHasGrill() {
            let hasGrill = cartItems.some(i => !i.is_divider && (i.cat === 'برژاو' || i.food_name.includes('کەباب') || i.food_name.includes('تکە')));
            document.getElementById('btnAddPlateDesktop').style.display = hasGrill ? 'block' : 'none';
        }
        function addNewPlateDivider() {
            if (cartItems.length === 0 || cartItems[cartItems.length - 1].is_divider) return;
            cartItems.push({ is_divider: true, food_name: '--- قاپی نوێ ---', price: 0, qty: 1, cat: 'مەتبەخ' });
            renderCart();
            checkHasGrill();
        }
        function addFromDesktopCard(baseName, price, cat, safeId) {
            let rEl = document.getElementById('d_rice_' + safeId);
            let cEl = document.getElementById('d_chick_' + safeId);
            let fullName = baseName;
            let rVal = rEl ? rEl.value : '';
            let cVal = cEl ? cEl.value : '';
            if (rVal) fullName += ` (${rVal})`;
            if (cVal) fullName += ` (${cVal})`;
            updateQty(fullName, 1, price, cat);
        }
        function updateQty(foodName, change, price, cat) {
            let found = false;
            for (let i = cartItems.length - 1; i >= 0; i--) {
                if (cartItems[i].is_divider) break;
                if (cartItems[i].food_name === foodName) {
                    cartItems[i].qty += change;
                    if (cartItems[i].qty <= 0) cartItems.splice(i, 1);
                    found = true;
                    break;
                }
            }
            if (!found && change > 0) cartItems.push({ is_divider: false, food_name: foodName, price: price, qty: 1, cat: cat || '' });
            checkHasGrill();
            renderCart();
        }
        function renderCart() {
            const list = document.getElementById('cartItemsList');
            list.innerHTML = '';
            if (cartItems.length === 0) {
                list.innerHTML = '<div style="text-align:center; color:var(--text-muted); padding:40px 0;">سەبەتە بەتاڵە</div>';
                document.getElementById('cartTotalTxt').innerText = '0 دینار';
                return;
            }
            let total = 0, plateNum = 1;
            cartItems.forEach((item, index) => {
                if (item.is_divider) {
                    plateNum++;
                    list.innerHTML += `<div style="background:#8b5cf6; padding:6px 10px; border-radius:8px; font-size:12px; font-weight:800; display:flex; justify-content:space-between;"><span>🍽 قاپی ${plateNum}</span><button onclick="cartItems.splice(${index},1); renderCart();" style="background:#ef4444; border:none; color:#fff; border-radius:4px; padding:2px 6px;">✕</button></div>`;
                } else {
                    total += item.qty * item.price;
                    list.innerHTML += `<div class="desktop-cart-row"><div style="display:flex; justify-content:space-between; align-items:center;"><div class="desktop-counter-group"><button class="desktop-btn-count" onclick="updateQty('${item.food_name}', -1, ${item.price}, '${item.cat}')">-</button><span style="padding:0 8px; font-weight:800;">${item.qty}</span><button class="desktop-btn-count" style="background:var(--gold); color:#000;" onclick="updateQty('${item.food_name}', 1, ${item.price}, '${item.cat}')">+</button></div><div style="text-align:left;"><div style="font-weight:800; font-size:13px;">${item.food_name}</div><div style="color:var(--success); font-size:11px;">${(item.qty * item.price).toLocaleString()} دینار</div></div></div></div>`;
                }
            });
            document.getElementById('cartTotalTxt').innerText = total.toLocaleString() + ' دینار';
        }
        function filterCat(catId, btn) {
            document.querySelectorAll('.cat-visual-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            document.querySelectorAll('.category-group-item').forEach(g => {
                g.style.display = (catId === 'all' || g.id === catId) ? 'block' : 'none';
            });
        }
        function fetchTableOrders() {
            fetch('/get_table_orders/' + encodeURIComponent(tableNum)).then(r => r.json()).then(data => {
                cartItems = []; originalTableOrders = [];
                if (data && data.length > 0) {
                    data.forEach(item => {
                        let isDiv = item.food_name.includes('قاپی نوێ');
                        let it = { is_divider: isDiv, food_name: item.food_name, qty: parseInt(item.quantity), price: parseFloat(item.price), cat: item.category || '' };
                        cartItems.push(it); originalTableOrders.push(JSON.parse(JSON.stringify(it)));
                    });
                }
                checkHasGrill(); renderCart();
            });
        }
        function submitFinalOrder() {
            if (cartItems.length === 0) { showToast("تکایە سەرەتا خواردن دیاری بکە!", true); return; }
            fetch('/save_cart_order', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ table_number: tableNum, cart_items: cartItems, original_items: originalTableOrders })
            }).then(r => r.json()).then(data => {
                if (data.status === 'success') {
                    showToast("✅ داواکارییەکە بۆ مەتبەخ نێردرا");
                    setTimeout(() => { window.location.href = '/desktop/tables'; }, 800);
                }
            });
        }
        function clearCurrentTableOrders() {
            if (confirm("ئایا دڵنیایت لە سڕینەوە؟")) {
                fetch('/clear_table_orders', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ table_number: tableNum }) })
                .then(() => fetchTableOrders());
            }
        }

        function openTransferModal() {
            document.getElementById('transferModal').style.display = 'flex';
        }
        function closeTransferModal() {
            document.getElementById('transferModal').style.display = 'none';
        }
        function confirmTransferTable() {
            let target = document.getElementById('newTableSelect').value;
            if (target === tableNum) {
                alert("مێزی مەبەست ناتوانێت هەمان مێز بێت!");
                return;
            }
            fetch('/transfer_table_orders', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ from_table: tableNum, to_table: target })
            }).then(r => r.json()).then(res => {
                if(res.status === 'success') {
                    showToast("مێزەکە بەسەرکەوتوویی گوازرایەوە");
                    setTimeout(() => { window.location.href = '/desktop?table=' + target; }, 800);
                } else {
                    alert("هەڵە: " + res.message);
                }
            });
        }

        window.onload = function() { fetchTableOrders(); };
    </script>
</body>
</html>
"""

# ==========================================
# تێمپلێتەکانی مۆبایل و موشتەری
# ==========================================
MOBILE_TABLES_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>هەڵبژاردنی مێز - مۆبایل</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background-color: #03261d; color: #ffffff; min-height: 100vh; padding: 12px; }
        .m-header { display: flex; justify-content: space-between; align-items: center; background: #064032; padding: 12px 14px; border-radius: 12px; margin-bottom: 12px; border: 1px solid #0b5e4a; }
        .m-title { font-size: 15px; font-weight: 800; color: #10b981; }
        .btn-logout { background: #ef4444; color: #fff; text-decoration: none; padding: 6px 14px; border-radius: 8px; font-weight: 800; font-size: 12px; }
        
        .btn-takeaway-mobile { width: 100%; background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); color: #fff; border: 2px solid #38bdf8; padding: 12px; border-radius: 10px; font-size: 15px; font-weight: 800; cursor: pointer; margin-bottom: 8px; display: flex; align-items: center; justify-content: center; gap: 8px; }
        
        .active-takeaways-box { background: #064032; border: 1.5px solid #0284c7; border-radius: 10px; padding: 8px; margin-bottom: 12px; display: flex; flex-direction: column; gap: 6px; }
        .active-takeaway-link { background: #0284c7; color: #fff; text-decoration: none; padding: 8px 10px; border-radius: 8px; font-weight: 800; font-size: 13px; display: flex; align-items: center; gap: 6px; }
        
        .tables-grid-mobile { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
        .m-table-btn { background: #ffffff; color: #03261d; border-radius: 12px; height: 75px; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 20px; font-weight: 800; text-decoration: none; box-shadow: 0 3px 6px rgba(0,0,0,0.3); border: 2px solid #e2e8f0; }
        .m-table-btn.active-occupied { background: #10b981 !important; color: #ffffff !important; border-color: #047857 !important; }
        .t-sub { font-size: 10px; font-weight: 700; margin-top: 2px; }
        
        .modal { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.75); display: none; align-items: center; justify-content: center; z-index: 2000; padding: 16px; }
        .modal-box { background: #064032; border: 2px solid #0b5e4a; border-radius: 16px; width: 100%; max-width: 380px; padding: 20px; color: #fff; }
        .modal-box input { width: 100%; padding: 10px; background: #03261d; border: 1.5px solid #0b5e4a; border-radius: 8px; color: #fff; font-size: 13px; margin-bottom: 10px; outline: none; }
    </style>
</head>
<body>
    <div class="m-header">
        <div class="m-title">📱 مێزەکان (گارسۆنی مۆبایل)</div>
        <a href="/logout" class="btn-logout">✕ دەرچوون</a>
    </div>

    <button type="button" class="btn-takeaway-mobile" onclick="document.getElementById('mTakeawayModal').style.display = 'flex'">
        <span>🥡</span>
        <span>ئۆردەری نوێی سەفەری / دلیڤەری</span>
    </button>

    {% if active_takeaways %}
    <div class="active-takeaways-box">
        <div style="font-size:11px; font-weight:800; color:#38bdf8;">داواکارییە چالاکەکان:</div>
        {% for t in active_takeaways %}
            <a href="/mobile/menu?table={{ t|urlencode }}" class="active-takeaway-link">
                <span>🛵</span>
                <span>{{ t }}</span>
            </a>
        {% endfor %}
    </div>
    {% endif %}

    <div class="tables-grid-mobile">
        {% for num in range(1, 91) %}
            <a href="/mobile/menu?table={{ num }}" class="m-table-btn" id="m-tbl-{{ num }}">
                <span>{{ num }}</span>
                <span class="t-sub">مێز</span>
            </a>
        {% endfor %}
    </div>

    <div class="modal" id="mTakeawayModal">
        <div class="modal-box">
            <h3 style="color:#38bdf8; margin-bottom:12px; text-align:center;">🥡 ئۆردەری نوێی سەفەری</h3>
            <input type="text" id="mCustName" placeholder="ناوی کڕیار">
            <input type="text" id="mCustPhone" placeholder="ژمارەی مۆبایل">
            <input type="text" id="mCustAddress" placeholder="ناونیشان">
            <button type="button" class="btn-takeaway-mobile" onclick="startMobileTakeaway()" style="margin-top:6px;">دەستپێکردن ➔</button>
            <button type="button" onclick="document.getElementById('mTakeawayModal').style.display='none'" style="background:none; border:none; color:#94a3b8; width:100%; margin-top:8px; cursor:pointer;">پاشگەزبوونەوە</button>
        </div>
    </div>

    <script>
        function startMobileTakeaway() {
            let name = document.getElementById('mCustName').value.trim() || 'کڕیار';
            let phone = document.getElementById('mCustPhone').value.trim();
            let addr = document.getElementById('mCustAddress').value.trim();
            let idStr = "سەفەری (" + name;
            if(phone) idStr += " - " + phone;
            if(addr) idStr += " - " + addr;
            idStr += ")";
            window.location.href = "/mobile/menu?table=" + encodeURIComponent(idStr);
        }

        function checkTables() {
            fetch('/get_active_tables?t=' + new Date().getTime())
                .then(r => r.json())
                .then(activeTables => {
                    for(let i = 1; i <= 90; i++) {
                        const el = document.getElementById('m-tbl-' + i);
                        if(el) {
                            if(activeTables.includes(i.toString())) el.classList.add('active-occupied');
                            else el.classList.remove('active-occupied');
                        }
                    }
                }).catch(()=>{});
        }
        checkTables();
        setInterval(checkTables, 3000);
    </script>
</body>
</html>
"""

CUSTOMER_MENU_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>مێنیوی شاهور - {{ table_num }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background-color: #03261d; color: #ffffff; padding-bottom: {{ '115px' if allow_ordering else '30px' }}; min-height: 100vh; }
        .top-header-bar { background-color: #03261d; padding: 10px 14px 6px; display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 100; }
        .header-brand { display: flex; align-items: center; gap: 6px; font-size: 17px; font-weight: 800; color: #ffffff; }
        .table-pill { background-color: #059669; color: #ffffff; font-size: 12px; font-weight: 800; padding: 4px 12px; border-radius: 20px; max-width: 180px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

        .categories-carousel { display: flex; overflow-x: auto; gap: 10px; padding: 10px 12px 14px; }
        .cat-card-item { background: #064032; border-radius: 12px; padding: 5px; display: flex; flex-direction: column; align-items: center; width: 76px; flex-shrink: 0; cursor: pointer; }
        .cat-card-item.active { border: 2px solid #ef4444; background: #085341; }
        .cat-img-box { width: 62px; height: 62px; border-radius: 10px; overflow: hidden; margin-bottom: 5px; }
        .cat-img-box img { width: 100%; height: 100%; object-fit: cover; }
        .cat-title-text { font-size: 11px; font-weight: 700; color: #ffffff; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; width: 100%; }

        .foods-container { padding: 0 12px; }
        .food-grid-2col { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
        .food-card-white { background: #ffffff; border-radius: 14px; padding: 8px; display: flex; flex-direction: column; align-items: center; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.25); }
        .food-img-hero { width: 100%; height: 120px; border-radius: 10px; object-fit: cover; margin-bottom: 8px; }
        .food-title-main { font-size: 14px; font-weight: 800; color: #0f172a; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; width: 100%; }
        .food-price-red { font-size: 14px; font-weight: 800; color: #e11d48; margin-bottom: 6px; }

        .options-group { width: 100%; display: flex; flex-direction: row; gap: 4px; margin-bottom: 6px; }
        .select-sub-opt { flex: 1; min-width: 0; padding: 4px; border-radius: 6px; border: 1px solid #cbd5e1; background: #f8fafc; font-size: 11px; font-weight: 700; color: #03261d; outline: none; }

        .mini-stepper { display: flex; align-items: center; background: #f1f5f9; border-radius: 8px; padding: 2px; gap: 4px; width: 100%; justify-content: space-between; }
        .btn-step { width: 32px; height: 32px; border-radius: 6px; border: none; background: #e2e8f0; color: #0f172a; font-size: 16px; font-weight: 800; cursor: pointer; }
        .btn-step.add { background: #10b981; color: #ffffff; }
        .qty-val-display { font-size: 14px; font-weight: 800; color: #0f172a; }

        .bottom-checkout-bar { position: fixed; bottom: 0; left: 0; right: 0; background: rgba(3, 38, 29, 0.95); border-top: 1px solid #0b5e4a; padding: 12px 16px; display: flex; align-items: center; justify-content: space-between; z-index: 200; }
        .cart-bubble-btn { display: flex; align-items: center; gap: 8px; background: #064032; padding: 8px 14px; border-radius: 10px; cursor: pointer; }
        .cart-counter-pill { background: #10b981; color: #03261d; font-size: 12px; font-weight: 800; padding: 2px 8px; border-radius: 12px; }
        .cart-sum-txt { color: #ffffff; font-weight: 800; font-size: 13.5px; }
        .btn-submit-order { background: #10b981; color: #ffffff; border: none; padding: 10px 20px; border-radius: 10px; font-size: 13.5px; font-weight: 800; cursor: pointer; }

        .modal-shade { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.75); z-index: 300; display: none; align-items: flex-end; }
        .modal-bottom-box { background: #064032; width: 100%; max-height: 80vh; border-radius: 20px 20px 0 0; padding: 18px 16px; display: flex; flex-direction: column; border-top: 2px solid #10b981; }
        .modal-items-scroller { overflow-y: auto; flex: 1; margin: 12px 0; }
        .cart-row-item { background: #03261d; padding: 10px 12px; border-radius: 10px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
        #toastBox { position: fixed; top: 65px; left: 50%; transform: translateX(-50%); background: #10b981; color: #ffffff; padding: 9px 20px; border-radius: 30px; font-size: 13px; font-weight: 700; z-index: 1000; display: none; }
    </style>
</head>
<body>
    <div id="toastBox">✅ داواکارییەکەت بۆ مەتبەخ نێردرا</div>

    <header class="top-header-bar">
        <div class="header-brand"><span>✨ شاهور ڕێستۆرانت</span></div>
        <div class="table-pill">{{ table_num }}</div>
    </header>

    {% if not allow_ordering %}
    <div style="background:#064032; color:#a7f3d0; font-size:11px; text-align:center; padding:6px; border-bottom:1px solid #0b5e4a;">
        ℹ️ تەنها بینینی مێنیوە. بۆ داواکردن پەیوەندی بە کارمەند بکەن.
    </div>
    {% endif %}

    <div class="categories-carousel">
        <div class="cat-card-item active" onclick="filterMenu('all', this)">
            <div class="cat-img-box"><img src="https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=150"></div>
            <div class="cat-title-text">هەموو</div>
        </div>
        {% for cat, items in categories.items() %}
        <div class="cat-card-item" onclick="filterMenu('group-{{ loop.index }}', this)">
            <div class="cat-img-box"><img src="{{ items[0].image_path if items[0].image_path else 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=150' }}" onerror="this.src='https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=150'"></div>
            <div class="cat-title-text">{{ cat }}</div>
        </div>
        {% endfor %}
    </div>

    <div class="foods-container">
        {% for cat, items in categories.items() %}
        <div class="category-block-wrapper" id="group-{{ loop.index }}" style="margin-bottom: 16px;">
            <div class="food-grid-2col">
                {% for item in items %}
                {% set item_id_safe = loop.index ~ '_' ~ cat ~ '_' ~ item.food_name|replace(' ', '_') %}
                <div class="food-card-white">
                    <img src="{{ item.image_path if item.image_path else 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=300' }}" class="food-img-hero" onerror="this.src='https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=300'">
                    <div class="food-title-main">{{ item.food_name }}</div>
                    <div class="food-price-red">{{ "{:,.0f}".format(item.price) }} د.ع</div>

                    {% if allow_ordering %}
                    {% set show_rice = item.category in ['کوڵاو', 'پەلەوەر', 'کوردیەکان'] %}
                    {% set show_chicken = (item.category == 'پەلەوەر') %}
                    {% if show_rice or show_chicken %}
                    <div class="options-group">
                        {% if show_rice %}
                        <select class="select-sub-opt" id="opt_rice_{{ item_id_safe }}">
                            <option value="">ج. برنج</option>
                            <option value="برنجی درێژ">برنجی درێژ</option>
                            <option value="برنجی خڕ">برنجی خڕ</option>
                            <option value="برنجی کوردی">برنجی کوردی</option>
                            <option value="برنج بە سرکە">برنج بە سرکە</option>
                        </select>
                        {% endif %}
                        {% if show_chicken %}
                        <select class="select-sub-opt" id="opt_chicken_{{ item_id_safe }}">
                            <option value="">ب. مریشک</option>
                            <option value="سینگ">سینگ</option>
                            <option value="ڕان">ڕان</option>
                        </select>
                        {% endif %}
                    </div>
                    {% endif %}

                    <div class="mini-stepper">
                        <button type="button" class="btn-step" onclick="changeCustomerQty('{{ item.food_name }}', -1, {{ item.price }}, '{{ item.category }}', '{{ item_id_safe }}')">-</button>
                        <span class="qty-val-display" id="count_{{ item_id_safe }}">0</span>
                        <button type="button" class="btn-step add" onclick="changeCustomerQty('{{ item.food_name }}', 1, {{ item.price }}, '{{ item.category }}', '{{ item_id_safe }}')">+</button>
                    </div>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
        </div>
        {% endfor %}
    </div>

    {% if allow_ordering %}
    <div class="bottom-checkout-bar">
        <div class="cart-bubble-btn" onclick="openCartView()">
            <span style="font-size: 18px;">🛒</span>
            <span class="cart-counter-pill" id="cartBadgeCount">0</span>
            <span class="cart-sum-txt" id="cartTotalDisplay">0 د.ع</span>
        </div>
        <button type="button" class="btn-submit-order" onclick="sendFinalOrder()">ناردن بۆ مەتبەخ ➔</button>
    </div>

    <div class="modal-shade" id="cartModalShade" onclick="closeCartView(event)">
        <div class="modal-bottom-box" onclick="event.stopPropagation()">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #0b5e4a; padding-bottom: 8px;">
                <span style="font-size: 15px; font-weight: 800; color: #ffffff;">🛒 داواکارییەکانی: {{ table_num }}</span>
                <button type="button" style="background:none; border:none; color:#ef4444; font-size:18px; font-weight:800;" onclick="toggleCartModal(false)">✕</button>
            </div>
            <div class="modal-items-scroller" id="cartScrollerList"></div>
            <button type="button" class="btn-submit-order" style="width: 100%; padding: 13px; font-size: 15px;" onclick="sendFinalOrder()">پشتڕاستکردنەوە و ناردن</button>
        </div>
    </div>
    {% endif %}

    <script>
        let myCart = [];
        const tableId = {{ table_num|tojson }};

        function showNotification(text, isError = false) {
            const toast = document.getElementById('toastBox');
            toast.innerText = text;
            toast.style.background = isError ? '#ef4444' : '#10b981';
            toast.style.display = 'block';
            setTimeout(() => { toast.style.display = 'none'; }, 2500);
        }

        function filterMenu(groupId, el) {
            document.querySelectorAll('.cat-card-item').forEach(c => c.classList.remove('active'));
            el.classList.add('active');
            document.querySelectorAll('.category-block-wrapper').forEach(g => {
                g.style.display = (groupId === 'all' || g.id === groupId) ? 'block' : 'none';
            });
        }

        function changeCustomerQty(baseName, delta, price, cat, safeId) {
            let riceVal = '', chickenVal = '';
            const rEl = document.getElementById('opt_rice_' + safeId);
            const cEl = document.getElementById('opt_chicken_' + safeId);
            if (rEl) riceVal = rEl.value;
            if (cEl) chickenVal = cEl.value;

            let finalName = baseName;
            if (riceVal) finalName += ` (${riceVal})`;
            if (chickenVal) finalName += ` (${chickenVal})`;

            let found = false;
            for (let i = myCart.length - 1; i >= 0; i--) {
                if (myCart[i].full_name === finalName) {
                    myCart[i].qty += delta;
                    if (myCart[i].qty <= 0) myCart.splice(i, 1);
                    found = true;
                    break;
                }
            }
            if (!found && delta > 0) {
                myCart.push({ base_name: baseName, full_name: finalName, price: price, qty: 1, cat: cat || '', safe_id: safeId, rice_type: riceVal, chicken_part: chickenVal });
            }
            refreshCounterDisplays();
            renderCartUI();
        }

        function refreshCounterDisplays() {
            document.querySelectorAll('.qty-val-display').forEach(d => d.innerText = '0');
            myCart.forEach(item => {
                const el = document.getElementById('count_' + item.safe_id);
                if (el) el.innerText = (parseInt(el.innerText) || 0) + item.qty;
            });
        }

        function renderCartUI() {
            let total = 0, count = 0;
            const scroller = document.getElementById('cartScrollerList');
            if (scroller) scroller.innerHTML = '';

            myCart.forEach((item, index) => {
                total += item.qty * item.price;
                count += item.qty;
                if (scroller) {
                    scroller.innerHTML += `
                        <div class="cart-row-item">
                            <div style="text-align: right;">
                                <div style="font-weight:700; font-size:13.5px; color:#fff;">${item.full_name}</div>
                                <div style="color:#10b981; font-size:12px; font-weight:700;">${(item.qty * item.price).toLocaleString()} د.ع</div>
                            </div>
                            <div style="display:flex; align-items:center; gap:6px;">
                                <button type="button" style="background:#ef4444; color:#fff; border:none; width:26px; height:26px; border-radius:4px; font-weight:800; cursor:pointer;" onclick="modifyCustomerCart(${index}, -1)">-</button>
                                <span style="background:#064032; border:1px solid #10b981; padding:3px 10px; border-radius:6px; font-weight:800;">${item.qty}</span>
                                <button type="button" style="background:#10b981; color:#fff; border:none; width:26px; height:26px; border-radius:4px; font-weight:800; cursor:pointer;" onclick="modifyCustomerCart(${index}, 1)">+</button>
                            </div>
                        </div>`;
                }
            });
            if (document.getElementById('cartBadgeCount')) {
                document.getElementById('cartBadgeCount').innerText = count;
                document.getElementById('cartTotalDisplay').innerText = total.toLocaleString() + ' د.ع';
            }
        }

        function modifyCustomerCart(index, delta) {
            if (myCart[index]) {
                myCart[index].qty += delta;
                if (myCart[index].qty <= 0) myCart.splice(index, 1);
                refreshCounterDisplays();
                renderCartUI();
            }
        }

        function openCartView() { toggleCartModal(true); }
        function toggleCartModal(show) { 
            const m = document.getElementById('cartModalShade'); 
            if (m) m.style.display = show ? 'flex' : 'none'; 
        }
        function closeCartView(e) { if (e.target.id === 'cartModalShade') toggleCartModal(false); }

        function sendFinalOrder() {
            if (myCart.length === 0) { showNotification("سەرەتا خواردن هەڵبژێرە!", true); return; }
            fetch('/save_customer_order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ table_number: tableId, cart_items: myCart })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    myCart = [];
                    refreshCounterDisplays();
                    renderCartUI();
                    toggleCartModal(false);
                    showNotification("✅ داواکارییەکەت بۆ مەتبەخ نێردرا");
                } else showNotification(data.message || 'هەڵە لە ناردن', true);
            });
        }
    </script>
</body>
</html>
"""

# ==========================================
# ڕێڕەوی سەرەکی چوونەژوورەوە
# ==========================================
@app.route('/')
def index():
    session.clear()
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        uname = normalize_digits(request.form.get('username', '')).strip()
        pwd = normalize_digits(request.form.get('password', '')).strip()

        if uname == '' and pwd == '':
            session.permanent = True
            session['authenticated'] = True
            session['role'] = 'waiter'
            session['full_name'] = 'گارسۆن'
            return redirect(url_for('desktop_tables'))

        conn = None
        user_row = None
        try:
            conn = get_db()
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE username = %s AND password = %s", (uname, pwd))
                user_row = cur.fetchone()
        except Exception as ex:
            print("Login error:", ex)
        finally:
            if conn:
                try: conn.close()
                except: pass

        if user_row:
            if not user_row.get('is_active', 1):
                return render_template_string(LOGIN_TEMPLATE, error='ئەم بەکارهێنەرە بلۆککراوە!')

            session.permanent = True
            session['authenticated'] = True
            session['user_id'] = user_row['id']
            session['username'] = user_row['username']
            session['full_name'] = user_row.get('full_name', '')
            role = user_row.get('role', 'Waiter')

            if role in ['Manager', 'Admin', 'admin']:
                session['role'] = 'admin'
                return redirect(url_for('admin_dashboard'))
            elif role == 'Mobile_Waiter':
                session['role'] = 'mobile_waiter'
                return redirect(url_for('mobile_waiter_tables'))
            elif role == 'Cashier':
                session['role'] = 'admin'
                return redirect(url_for('admin_cashier'))
            else:
                session['role'] = 'waiter'
                return redirect(url_for('desktop_tables'))

        if pwd in ['99', '٩٩', '222', '٢٢٢']:
            session.permanent = True
            session['authenticated'] = True
            session['role'] = 'admin'
            session['full_name'] = 'بەڕێوەبەر'
            return redirect(url_for('admin_dashboard'))
        elif pwd in ['345678', '٣٤٥٦٧٨']:
            session.permanent = True
            session['authenticated'] = True
            session['role'] = 'mobile_waiter'
            session['full_name'] = 'گارسۆنی مۆبایل'
            return redirect(url_for('mobile_waiter_tables'))
        elif pwd in ['22', '٢٢']:
            session.permanent = True
            session['authenticated'] = True
            session['role'] = 'waiter'
            session['full_name'] = 'گارسۆنی ئایپاد'
            return redirect(url_for('desktop_tables'))

        error = 'ناوی بەکارهێنەر یان وشەی نهێنی هەڵەیە!'

    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==========================================
# ڕێڕەوەکانی ئەدمین
# ==========================================
@app.route('/admin')
def admin_dashboard():
    if not session.get('authenticated') or session.get('role') != 'admin':
        return redirect(url_for('login'))

    today_sales, today_expense, active_tables, total_workers = 0, 0, 0, 0
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT IFNULL(SUM(amount), 0) AS s FROM qasa WHERE transaction_time >= NOW() - INTERVAL 1 DAY")
            today_sales = float(cur.fetchone()['s'])
            cur.execute("SELECT IFNULL(SUM(amount), 0) AS e FROM masrwf WHERE DATE(masrwf_date) = CURDATE()")
            today_expense = float(cur.fetchone()['e'])
            cur.execute("SELECT COUNT(DISTINCT table_cabin) AS c FROM froshtn WHERE table_cabin NOT LIKE '%[%' AND table_cabin != ''")
            active_tables = int(cur.fetchone()['c'])
            cur.execute("SELECT COUNT(*) AS w FROM workers")
            total_workers = int(cur.fetchone()['w'])
    except Exception as ex:
        print("Dashboard stats error:", ex)
    finally:
        if conn:
            try: conn.close()
            except: pass

    return render_template_string(
        ADMIN_DASHBOARD_TEMPLATE,
        today_sales=today_sales,
        today_expense=today_expense,
        active_tables_count=active_tables,
        total_workers=total_workers
    )

# ==========================================
# ڕێڕەوی ئاماری فرۆشتن بە دەرهێنانی ناوی پاكکراوە
# ==========================================
@app.route('/admin/amar')
def admin_amar():
    if not session.get('authenticated') or session.get('role') != 'admin':
        return redirect(url_for('login'))

    today = datetime.now()
    first_day_of_month = today.replace(day=1).strftime('%Y-%m-%d')
    today_str = today.strftime('%Y-%m-%d')

    start_date = request.args.get('start_date', first_day_of_month)
    end_date = request.args.get('end_date', today_str)

    start_dt = f"{start_date} 00:00:00"
    end_dt = f"{end_date} 23:59:59"

    report_rows = []
    total_sales = 0.0
    total_expenses = 0.0
    total_workers_wage = 0.0
    total_items_count = 0

    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            # پاککردنەوەی ناوی خواردنەکان لە هەموو + و سەفەری بۆ ئەوەی فرۆشی ناو froshtn ون نەبێت
            query_sales = """
                SELECT 
                    TRIM(BOTH '+' FROM TRIM(food_name)) AS clean_food_name,
                    CAST(SUM(quantity) AS SIGNED) AS qty,
                    ROUND(AVG(price), 0) AS price,
                    CAST(SUM(quantity * price) AS DECIMAL(18, 0)) AS total
                FROM froshtn
                WHERE created_at >= %s AND created_at <= %s
                  AND food_name NOT LIKE '%%قاپی نوێ%%'
                  AND food_name != ''
                  AND food_name IS NOT NULL
                  AND food_name NOT LIKE '%%سڕاوەتەوە%%'
                GROUP BY TRIM(BOTH '+' FROM TRIM(food_name))
                ORDER BY SUM(quantity) DESC;
            """
            cur.execute(query_sales, (start_dt, end_dt))
            report_rows = cur.fetchall()

            items_total_sum = sum(float(r['total']) for r in report_rows) if report_rows else 0.0
            total_items_count = sum(int(r['qty']) for r in report_rows) if report_rows else 0

            try:
                cur.execute("SELECT IFNULL(SUM(amount), 0) AS s FROM qasa WHERE transaction_time >= %s AND transaction_time <= %s", (start_dt, end_dt))
                qasa_row = cur.fetchone()
                total_sales = float(qasa_row['s']) if qasa_row else 0.0
            except:
                total_sales = 0.0

            if total_sales == 0:
                total_sales = items_total_sum

            try:
                cur.execute("SELECT IFNULL(SUM(amount), 0) AS e FROM masrwf WHERE masrwf_date >= %s AND masrwf_date <= %s", (start_dt, end_dt))
                exp_row = cur.fetchone()
                total_expenses = float(exp_row['e']) if exp_row else 0.0
            except:
                total_expenses = 0.0

            try:
                query_workers = """
                    SELECT IFNULL(SUM((CASE WHEN wa.status = 'هاتوو' THEN w.salary ELSE 0 END) + IFNULL(wa.bonus, 0)), 0) AS w_due
                    FROM workers w
                    INNER JOIN worker_attendance wa ON w.id = wa.worker_id
                    WHERE wa.date >= %s AND wa.date <= %s;
                """
                cur.execute(query_workers, (start_date, end_date))
                work_row = cur.fetchone()
                total_workers_wage = float(work_row['w_due']) if work_row else 0.0
            except:
                total_workers_wage = 0.0

    except Exception as ex:
        print("Amar query error:", ex)
    finally:
        if conn:
            try: conn.close()
            except: pass

    total_all_expenses = total_expenses + total_workers_wage
    net_profit = total_sales - total_all_expenses

    return render_template_string(
        WEB_AMAR_TEMPLATE,
        start_date=start_date,
        end_date=end_date,
        report_rows=report_rows,
        total_sales=total_sales,
        total_expenses=total_expenses,
        total_workers_wage=total_workers_wage,
        total_all_expenses=total_all_expenses,
        net_profit=net_profit,
        total_items_count=total_items_count
    )

# ==========================================
# بەشی حیساباتی شاگردەکان
# ==========================================
@app.route('/admin/workers')
def admin_workers():
    if not session.get('authenticated') or session.get('role') != 'admin': return redirect(url_for('login'))
    today_dt = datetime.now()
    first_day_of_month = today_dt.replace(day=1).strftime('%Y-%m-%d')
    today_str = today_dt.strftime('%Y-%m-%d')

    start_date = request.args.get('start_date', first_day_of_month)
    end_date = request.args.get('end_date', today_str)

    raw_workers = []
    today_attendance_list = []
    wage_rows = []

    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, phone, salary FROM workers ORDER BY id DESC")
            raw_workers = cur.fetchall()

            for w in raw_workers:
                cur.execute("INSERT IGNORE INTO worker_attendance (worker_id, date, status, bonus) VALUES (%s, %s, 'نەهاتوو', 0)", (w['id'], today_str))
            conn.commit()

            cur.execute("""
                SELECT w.id AS worker_id, w.name, w.salary, IFNULL(wa.status, 'نەهاتوو') AS status, IFNULL(wa.bonus, 0) AS bonus
                FROM workers w
                LEFT JOIN worker_attendance wa ON w.id = wa.worker_id AND wa.date = %s
                ORDER BY w.id DESC
            """, (today_str,))
            today_attendance_list = cur.fetchall()

            cur.execute("""
                SELECT w.id, w.name, w.phone, w.salary,
                       COUNT(CASE WHEN wa.status = 'هاتوو' THEN 1 END) AS work_days,
                       (COUNT(CASE WHEN wa.status = 'هاتوو' THEN 1 END) * w.salary) AS total_salary,
                       IFNULL(SUM(wa.bonus), 0) AS total_bonus,
                       ((COUNT(CASE WHEN wa.status = 'هاتوو' THEN 1 END) * w.salary) + IFNULL(SUM(wa.bonus), 0)) AS total_due
                FROM workers w
                LEFT JOIN worker_attendance wa ON w.id = wa.worker_id AND wa.date >= %s AND wa.date <= %s
                GROUP BY w.id, w.name, w.phone, w.salary
                ORDER BY w.id DESC
            """, (start_date, end_date))
            wage_rows = cur.fetchall()

    except Exception as e:
        print("Worker list error:", e)
    finally:
        if conn:
            try: conn.close()
            except: pass

    return render_template_string(
        WEB_WORKERS_TEMPLATE,
        raw_workers=raw_workers,
        today_attendance_list=today_attendance_list,
        wage_rows=wage_rows,
        start_date=start_date,
        end_date=end_date,
        today_date=today_str
    )

@app.route('/admin/add_worker', methods=['POST'])
def admin_add_worker():
    name = request.form.get('name')
    phone = request.form.get('phone', '')
    salary = float(request.form.get('salary', 25000))
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("INSERT INTO workers (name, phone, salary) VALUES (%s, %s, %s)", (name, phone, salary))
            conn.commit()
    except Exception as ex:
        print("Add worker error:", ex)
    finally:
        if conn:
            try: conn.close()
            except: pass
    return redirect(url_for('admin_workers'))

@app.route('/admin/edit_worker/<int:wid>', methods=['POST'])
def admin_edit_worker(wid):
    name = request.form.get('name')
    phone = request.form.get('phone', '')
    salary = float(request.form.get('salary', 0))
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("UPDATE workers SET name = %s, phone = %s, salary = %s WHERE id = %s", (name, phone, salary, wid))
            conn.commit()
    except Exception as ex:
        print("Edit worker error:", ex)
    finally:
        if conn:
            try: conn.close()
            except: pass
    return redirect(url_for('admin_workers'))

@app.route('/admin/delete_worker/<int:wid>')
def admin_delete_worker(wid):
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM worker_attendance WHERE worker_id = %s", (wid,))
            cur.execute("DELETE FROM workers WHERE id = %s", (wid,))
            conn.commit()
    except Exception as ex:
        print("Delete worker error:", ex)
    finally:
        if conn:
            try: conn.close()
            except: pass
    return redirect(url_for('admin_workers'))

@app.route('/admin/toggle_attendance', methods=['POST'])
def admin_toggle_attendance():
    data = request.get_json() or {}
    w_id = int(data.get('worker_id'))
    status = data.get('status', 'هاتوو')
    a_date = data.get('att_date', datetime.now().strftime('%Y-%m-%d'))
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO worker_attendance (worker_id, date, status, bonus)
                VALUES (%s, %s, %s, 0)
                ON DUPLICATE KEY UPDATE status = %s
            """, (w_id, a_date, status, status))
            conn.commit()
        return jsonify({'status': 'success'})
    except Exception as ex:
        return jsonify({'status': 'error', 'message': str(ex)})
    finally:
        if conn:
            try: conn.close()
            except: pass

@app.route('/admin/update_worker_bonus', methods=['POST'])
def admin_update_worker_bonus():
    data = request.get_json() or {}
    w_id = int(data.get('worker_id'))
    bonus = float(data.get('bonus', 0))
    a_date = data.get('att_date', datetime.now().strftime('%Y-%m-%d'))
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO worker_attendance (worker_id, date, status, bonus)
                VALUES (%s, %s, 'نەهاتوو', %s)
                ON DUPLICATE KEY UPDATE bonus = %s
            """, (w_id, a_date, bonus, bonus))
            conn.commit()
        return jsonify({'status': 'success'})
    except Exception as ex:
        return jsonify({'status': 'error', 'message': str(ex)})
    finally:
        if conn:
            try: conn.close()
            except: pass

# ==========================================
# پەڕەی بەڕێوەبردنی مەسرووفات
# ==========================================
@app.route('/admin/masrwf')
def admin_masrwf():
    if not session.get('authenticated') or session.get('role') != 'admin': return redirect(url_for('login'))
    
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')

    rows = []
    tot = 0
    existing_types = ['کڕین بۆ چێشتخانە', 'خەرجی گشتی', 'خزمەتگوزاری', 'کرێ و پسولە', 'کەلوپەل', 'ترانسپۆرت', 'چاککردنەوە', 'کڕینی گۆشت', 'کڕینی سەوزە', 'کڕینی برنج', 'گاز و نەوت']
    existing_spenders = ['بەڕێوەبەر', 'کاشێر', 'مەتبەخ', 'گارسۆن', 'شۆفێر', 'کڕیار']
    
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            query = """
                SELECT 
                    id, 
                    DATE_FORMAT(masrwf_date, '%Y/%m/%d') AS m_date, 
                    DATE_FORMAT(masrwf_date, '%Y-%m-%d') AS m_date_raw, 
                    masrwf_type, 
                    spent_by, 
                    amount, 
                    IFNULL(notes, '') AS notes 
                FROM masrwf 
            """
            params = []
            if from_date and to_date:
                query += " WHERE masrwf_date BETWEEN %s AND %s "
                params.append(f"{from_date} 00:00:00")
                params.append(f"{to_date} 23:59:59")
            
            query += " ORDER BY id DESC;"
            cur.execute(query, params)
            rows = cur.fetchall()
            tot = sum(float(r['amount']) for r in rows)

            cur.execute("SELECT DISTINCT masrwf_type FROM masrwf WHERE masrwf_type != '' AND masrwf_type IS NOT NULL ORDER BY masrwf_type ASC;")
            for r in cur.fetchall():
                t = r['masrwf_type'].strip()
                if t and t not in existing_types:
                    existing_types.append(t)

            cur.execute("SELECT DISTINCT spent_by FROM masrwf WHERE spent_by != '' AND spent_by IS NOT NULL ORDER BY spent_by ASC;")
            for r in cur.fetchall():
                s = r['spent_by'].strip()
                if s and s not in existing_spenders:
                    existing_spenders.append(s)

    except Exception as ex:
        print("Masrwf error:", ex)
    finally:
        if conn:
            try: conn.close()
            except: pass

    return render_template_string(
        WEB_MASRWF_TEMPLATE, 
        rows=rows, 
        total_m=tot, 
        today_date=datetime.now().strftime('%Y-%m-%d'),
        from_date=from_date,
        to_date=to_date,
        existing_types=existing_types,
        existing_spenders=existing_spenders
    )

@app.route('/admin/save_masrwf', methods=['POST'])
def admin_save_masrwf():
    m_date = request.form.get('masrwf_date')
    m_type = request.form.get('masrwf_type', '').strip()
    spent_by = request.form.get('spent_by', '').strip()
    amt = float(request.form.get('amount', 0))
    notes = request.form.get('notes', '').strip()
    
    if m_type and amt > 0:
        conn = None
        try:
            conn = get_db()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO masrwf (masrwf_date, masrwf_type, spent_by, amount, notes) 
                    VALUES (%s, %s, %s, %s, %s)
                """, (m_date, m_type, spent_by, amt, notes))
                conn.commit()
        except Exception as ex:
            print("Save masrwf error:", ex)
        finally:
            if conn:
                try: conn.close()
                except: pass
    return redirect(url_for('admin_masrwf'))

@app.route('/admin/update_masrwf', methods=['POST'])
def admin_update_masrwf():
    m_id = int(request.form.get('id', 0))
    m_date = request.form.get('masrwf_date')
    m_type = request.form.get('masrwf_type', '').strip()
    spent_by = request.form.get('spent_by', '').strip()
    amt = float(request.form.get('amount', 0))
    notes = request.form.get('notes', '').strip()
    
    if m_id > 0 and m_type and amt > 0:
        conn = None
        try:
            conn = get_db()
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE masrwf 
                    SET masrwf_date = %s, masrwf_type = %s, spent_by = %s, amount = %s, notes = %s 
                    WHERE id = %s
                """, (m_date, m_type, spent_by, amt, notes, m_id))
                conn.commit()
        except Exception as ex:
            print("Update masrwf error:", ex)
        finally:
            if conn:
                try: conn.close()
                except: pass
    return redirect(url_for('admin_masrwf'))

@app.route('/admin/delete_masrwf/<int:mid>')
def admin_delete_masrwf(mid):
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM masrwf WHERE id = %s", (mid,))
            conn.commit()
    except Exception as ex:
        print("Delete masrwf error:", ex)
    finally:
        if conn:
            try: conn.close()
            except: pass
    return redirect(url_for('admin_masrwf'))

# ==========================================
# پەڕەی بەڕێوەبردنی خواردن و بەکارهێنەران و کاشێر
# ==========================================
@app.route('/admin/users')
def admin_users():
    if not session.get('authenticated') or session.get('role') != 'admin':
        return redirect(url_for('login'))
    users = []
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users ORDER BY id DESC")
            users = cur.fetchall()
    except Exception as ex:
        print("Fetch users error:", ex)
    finally:
        if conn:
            try: conn.close()
            except: pass
    return render_template_string(WEB_USERS_TEMPLATE, users=users)

@app.route('/admin/add_user', methods=['POST'])
def admin_add_user():
    if not session.get('authenticated') or session.get('role') != 'admin':
        return redirect(url_for('login'))
    uname = request.form.get('username', '').strip()
    pwd = request.form.get('password', '').strip()
    full_name = request.form.get('full_name', '').strip()
    role = request.form.get('role', 'Waiter')

    if uname and pwd:
        conn = None
        try:
            conn = get_db()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (username, password, full_name, role, can_view_menu, can_view_tables, can_view_cashier, can_view_qsa, can_view_reports, can_view_settings, is_active)
                    VALUES (%s, %s, %s, %s, 1, 1, 1, 1, 1, 1, 1)
                """, (uname, pwd, full_name, role))
                conn.commit()
        except Exception as ex:
            print("Insert user error:", ex)
        finally:
            if conn:
                try: conn.close()
                except: pass
    return redirect(url_for('admin_users'))

@app.route('/admin/edit_user/<int:uid>', methods=['POST'])
def admin_edit_user(uid):
    if not session.get('authenticated') or session.get('role') != 'admin':
        return redirect(url_for('login'))
    uname = request.form.get('username', '').strip()
    pwd = request.form.get('password', '').strip()
    full_name = request.form.get('full_name', '').strip()
    role = request.form.get('role', 'Waiter')

    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users SET username = %s, password = %s, full_name = %s, role = %s WHERE id = %s
            """, (uname, pwd, full_name, role, uid))
            conn.commit()
    except Exception as ex:
        print("Update user error:", ex)
    finally:
        if conn:
            try: conn.close()
            except: pass
    return redirect(url_for('admin_users'))

@app.route('/admin/toggle_user/<int:uid>')
def admin_toggle_user(uid):
    if not session.get('authenticated') or session.get('role') != 'admin':
        return redirect(url_for('login'))
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT is_active FROM users WHERE id = %s", (uid,))
            row = cur.fetchone()
            if row:
                new_state = 0 if row.get('is_active', 1) else 1
                cur.execute("UPDATE users SET is_active = %s WHERE id = %s", (new_state, uid))
                conn.commit()
    except Exception as ex:
        print("Toggle user error:", ex)
    finally:
        if conn:
            try: conn.close()
            except: pass
    return redirect(url_for('admin_users'))

@app.route('/admin/delete_user/<int:uid>')
def admin_delete_user(uid):
    if not session.get('authenticated') or session.get('role') != 'admin':
        return redirect(url_for('login'))
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s AND username != 'admin'", (uid,))
            conn.commit()
    except Exception as ex:
        print("Delete user error:", ex)
    finally:
        if conn:
            try: conn.close()
            except: pass
    return redirect(url_for('admin_users'))

@app.route('/admin/cashier')
def admin_cashier():
    if not session.get('authenticated') or session.get('role') != 'admin': return redirect(url_for('login'))
    active_tables = []
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            query = """
                SELECT table_cabin, COUNT(DISTINCT created_at) AS rounds 
                FROM froshtn 
                WHERE table_cabin IS NOT NULL AND table_cabin != '' AND table_cabin NOT LIKE '%[%'
                GROUP BY table_cabin
            """
            cur.execute(query)
            rows = cur.fetchall()

            def sort_key(x):
                val = str(x['table_cabin'])
                if val.isdigit():
                    return (0, int(val))
                return (1, val)

            active_tables = sorted(rows, key=sort_key)
    except Exception as ex:
        print("Cashier tables error:", ex)
    finally:
        if conn:
            try: conn.close()
            except: pass
    return render_template_string(WEB_CASHIER_TEMPLATE, active_tables=active_tables)

@app.route('/admin/complete_payment', methods=['POST'])
def admin_complete_payment():
    data = request.get_json() or {}
    t_num = str(data.get('table_number', '')).strip()
    tot = float(data.get('total_amount', 0))
    paid = float(data.get('amount_paid', 0))
    disc = max(0, tot - paid)
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            p_id = t_num if ('سەفەری' in t_num or t_num.startswith('m')) else f"m{t_num}"
            cur.execute("INSERT INTO qasa (transaction_time, place_id, amount, discount) VALUES (NOW(), %s, %s, %s)", (p_id, paid, disc))
            cur.execute("DELETE FROM froshtn WHERE table_cabin = %s OR table_cabin LIKE %s", (t_num, f"{t_num} [%"))
            conn.commit()
        return jsonify({'status': 'success'})
    except Exception as ex:
        return jsonify({'status': 'error', 'message': str(ex)})
    finally:
        if conn:
            try: conn.close()
            except: pass

@app.route('/admin/qasa')
def admin_qasa():
    if not session.get('authenticated') or session.get('role') != 'admin': return redirect(url_for('login'))
    rows = []
    tot_rec, tot_disc = 0, 0
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT DATE_FORMAT(transaction_time, '%Y-%m-%d %H:%i') AS transaction_time, place_id, amount, discount FROM qasa WHERE transaction_time >= NOW() - INTERVAL 1 DAY ORDER BY transaction_time DESC")
            rows = cur.fetchall()
            tot_rec = sum(float(r['amount']) for r in rows)
            tot_disc = sum(float(r['discount']) for r in rows)
    except Exception as ex:
        print("Qasa error:", ex)
    finally:
        if conn:
            try: conn.close()
            except: pass
    return render_template_string(WEB_QASA_TEMPLATE, qasa_rows=rows, total_received=tot_rec, total_discount=tot_disc)

@app.route('/admin/menu_manager')
def admin_menu_manager():
    if not session.get('authenticated') or session.get('role') != 'admin': return redirect(url_for('login'))
    foods = []
    categories = ['برژاو', 'کوڵاو', 'پەلەوەر', 'شەربەت و خواردنەوە', 'سەوزە و زەڵاتە', 'کوردیەکان', 'خواردنی خێرا', 'شۆربا', 'شیرینی']
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT id, food_name, price, category, image_path FROM nse ORDER BY id DESC")
            foods = cur.fetchall()
            for f in foods:
                c = f.get('category')
                if c and c.strip() and c.strip() not in categories:
                    categories.append(c.strip())
    except Exception as ex:
        print("Menu fetch error:", ex)
    finally:
        if conn:
            try: conn.close()
            except: pass
    return render_template_string(WEB_MENU_MANAGER_TEMPLATE, foods=foods, existing_categories=categories)

@app.route('/admin/add_food', methods=['POST'])
def admin_add_food():
    name = request.form.get('food_name')
    price = float(request.form.get('price', 0))
    cat = request.form.get('category', 'گشتی').strip()
    img = request.form.get('image_path', '').strip()

    if 'food_image' in request.files:
        file = request.files['food_image']
        if file and file.filename != '' and allowed_file(file.filename):
            fname = secure_filename(f"{int(datetime.now().timestamp())}_{file.filename}")
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
            file.save(save_path)
            img = url_for('static', filename=f'uploads/{fname}')

    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("INSERT INTO nse (food_name, price, category, image_path, nsecol) VALUES (%s, %s, %s, %s, '')", (name, price, cat, img))
            conn.commit()
    except Exception as ex:
        print("Add food error:", ex)
    finally:
        if conn:
            try: conn.close()
            except: pass
    return redirect(url_for('admin_menu_manager'))

@app.route('/admin/edit_food/<int:fid>', methods=['POST'])
def admin_edit_food(fid):
    if not session.get('authenticated') or session.get('role') != 'admin': return redirect(url_for('login'))
    name = request.form.get('food_name')
    price = float(request.form.get('price', 0))
    cat = request.form.get('category', 'گشتی').strip()
    img = request.form.get('image_path', '').strip()

    if 'food_image' in request.files:
        file = request.files['food_image']
        if file and file.filename != '' and allowed_file(file.filename):
            fname = secure_filename(f"{int(datetime.now().timestamp())}_{file.filename}")
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
            file.save(save_path)
            img = url_for('static', filename=f'uploads/{fname}')

    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            if img:
                cur.execute("UPDATE nse SET food_name = %s, price = %s, category = %s, image_path = %s WHERE id = %s", (name, price, cat, img, fid))
            else:
                cur.execute("UPDATE nse SET food_name = %s, price = %s, category = %s WHERE id = %s", (name, price, cat, fid))
            conn.commit()
    except Exception as ex:
        print("Edit food error:", ex)
    finally:
        if conn:
            try: conn.close()
            except: pass
    return redirect(url_for('admin_menu_manager'))

@app.route('/admin/delete_food/<int:fid>')
def admin_delete_food(fid):
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM nse WHERE id = %s", (fid,))
            conn.commit()
    except Exception as ex:
        print("Delete food error:", ex)
    finally:
        if conn:
            try: conn.close()
            except: pass
    return redirect(url_for('admin_menu_manager'))

# ==========================================
# ڕێڕەوەکانی ئۆردەر، دیسکتۆپ و مۆبایل
# ==========================================
@app.route('/desktop/tables')
def desktop_tables():
    if not session.get('authenticated'): return redirect(url_for('login'))
    active_takeaways = []
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT table_cabin FROM froshtn WHERE table_cabin LIKE 'سەفەری%'")
            active_takeaways = [r['table_cabin'] for r in cur.fetchall()]
    except Exception as ex:
        print("Desktop tables error:", ex)
    finally:
        if conn:
            try: conn.close()
            except: pass
    return render_template_string(DESKTOP_TABLES_TEMPLATE, active_takeaways=active_takeaways)

@app.route('/desktop')
def desktop_menu():
    if not session.get('authenticated'): return redirect(url_for('login'))
    tbl = request.args.get('table')
    if not tbl: return redirect(url_for('desktop_tables'))
    categories = {}
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT food_name, price, category, image_path FROM nse WHERE food_name != ''")
            for f in cur.fetchall():
                c = f['category'].strip() if f.get('category') else 'گشتی'
                categories.setdefault(c, []).append(f)
    except Exception as ex:
        print("Desktop menu error:", ex)
    finally:
        if conn:
            try: conn.close()
            except: pass
    return render_template_string(DESKTOP_TEMPLATE, categories=categories, selected_table=tbl)

@app.route('/transfer_table_orders', methods=['POST'])
def transfer_table_orders():
    if not session.get('authenticated'): return jsonify({'status': 'error', 'message': 'ڕێگەپێنەدراو'})
    data = request.get_json() or {}
    from_tbl = str(data.get('from_table', '')).strip()
    to_tbl = str(data.get('to_table', '')).strip()

    if not from_tbl or not to_tbl:
        return jsonify({'status': 'error', 'message': 'تکایە هەردوو مێز دیاری بکە'})

    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE froshtn 
                SET table_cabin = REPLACE(table_cabin, %s, %s)
                WHERE table_cabin = %s OR table_cabin LIKE %s
            """, (from_tbl, to_tbl, from_tbl, f"{from_tbl} [%"))
            conn.commit()
        return jsonify({'status': 'success'})
    except Exception as ex:
        return jsonify({'status': 'error', 'message': str(ex)})
    finally:
        if conn:
            try: conn.close()
            except: pass

@app.route('/mobile/tables')
def mobile_waiter_tables():
    if not session.get('authenticated'): return redirect(url_for('login'))
    active_takeaways = []
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT table_cabin FROM froshtn WHERE table_cabin LIKE 'سەفەری%'")
            active_takeaways = [r['table_cabin'] for r in cur.fetchall()]
    except Exception as ex:
        print("Mobile tables error:", ex)
    finally:
        if conn:
            try: conn.close()
            except: pass
    return render_template_string(MOBILE_TABLES_TEMPLATE, active_takeaways=active_takeaways)

@app.route('/mobile/menu')
def mobile_waiter_menu():
    if not session.get('authenticated'): return redirect(url_for('login'))
    tbl = request.args.get('table', '1')
    categories = {}
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT food_name, price, category, image_path FROM nse WHERE food_name != ''")
            for f in cur.fetchall():
                c = f['category'].strip() if f.get('category') else 'گشتی'
                categories.setdefault(c, []).append(f)
    except Exception as ex:
        print("Mobile menu error:", ex)
    finally:
        if conn:
            try: conn.close()
            except: pass
    return render_template_string(CUSTOMER_MENU_TEMPLATE, table_num=tbl, categories=categories, allow_ordering=True)

@app.route('/table/<path:table_num>')
def customer_table_view(table_num):
    allow_ordering = True
    categories = {}
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            if table_num.isdigit():
                cur.execute("SELECT allow_ordering FROM table_permissions WHERE table_number = %s", (int(table_num),))
                row = cur.fetchone()
                if row:
                    allow_ordering = bool(row['allow_ordering'])

            cur.execute("SELECT food_name, price, category, image_path FROM nse WHERE food_name != ''")
            foods = cur.fetchall()
            for f in foods:
                c = f['category'].strip() if f.get('category') else 'گشتی'
                categories.setdefault(c, []).append(f)
    except Exception as ex:
        print("Customer table view error:", ex)
    finally:
        if conn:
            try: conn.close()
            except: pass

    return render_template_string(CUSTOMER_MENU_TEMPLATE, table_num=table_num, categories=categories, allow_ordering=allow_ordering)

@app.route('/qr_manager')
def qr_manager():
    if not session.get('authenticated'): return redirect(url_for('login'))
    perm_dict = {}
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT table_number, allow_ordering FROM table_permissions")
            for r in cur.fetchall():
                perm_dict[r['table_number']] = r['allow_ordering']
    except Exception as ex:
        print("QR fetch error:", ex)
    finally:
        if conn:
            try: conn.close()
            except: pass
    return render_template_string(QR_MANAGER_TEMPLATE, base_url=request.host_url.rstrip('/'), perm_dict=perm_dict)

@app.route('/toggle_table_permission', methods=['POST'])
def toggle_table_permission():
    if not session.get('authenticated'): return jsonify({'status': 'error'})
    t_num = int(request.get_json().get('table_number'))
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT allow_ordering FROM table_permissions WHERE table_number = %s", (t_num,))
            row = cur.fetchone()
            new_val = 0 if (row and row['allow_ordering']) else 1
            cur.execute("INSERT INTO table_permissions (table_number, allow_ordering) VALUES (%s, %s) ON DUPLICATE KEY UPDATE allow_ordering = %s", (t_num, new_val, new_val))
            conn.commit()
        return jsonify({'status': 'success', 'allow_ordering': new_val})
    except Exception as ex:
        return jsonify({'status': 'error', 'message': str(ex)})
    finally:
        if conn:
            try: conn.close()
            except: pass

@app.route('/set_all_table_permissions', methods=['POST'])
def set_all_table_permissions():
    if not session.get('authenticated'): return jsonify({'status': 'error'})
    allow = int(request.get_json().get('allow_ordering', 1))
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            for i in range(1, 91):
                cur.execute("INSERT INTO table_permissions (table_number, allow_ordering) VALUES (%s, %s) ON DUPLICATE KEY UPDATE allow_ordering = %s", (i, allow, allow))
            conn.commit()
        return jsonify({'status': 'success'})
    except Exception as ex:
        return jsonify({'status': 'error', 'message': str(ex)})
    finally:
        if conn:
            try: conn.close()
            except: pass

@app.route('/save_customer_order', methods=['POST'])
def save_customer_order():
    data = request.get_json() or {}
    tbl = str(data.get('table_number', ''))
    items = data.get('cart_items', [])
    if not items:
        return jsonify({'status': 'error', 'message': 'هیچ خواردنێک دیاری نەکراوە!'})

    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            if tbl.isdigit():
                cur.execute("SELECT allow_ordering FROM table_permissions WHERE table_number = %s", (int(tbl),))
                p_row = cur.fetchone()
                if p_row and not p_row['allow_ordering'] and session.get('role') not in ['mobile_waiter', 'admin']:
                    return jsonify({'status': 'error', 'message': 'ئەم مێزە تەنها بۆ بینینە!'})

            for it in items:
                fname = it.get('full_name') or it.get('food_name') or it.get('base_name')
                qty = int(it.get('qty', 1))
                price = float(it.get('price', 0))
                cat = it.get('cat', 'گشتی')
                rice_t = it.get('rice_type', '')
                chick_p = it.get('chicken_part', '')

                if '(' not in fname:
                    if cat in ['کوڵاو', 'پەلەوەر', 'کوردیەکان'] and rice_t:
                        fname += f" ({rice_t})"
                    if cat == 'پەلەوەر' and chick_p:
                        fname += f" ({chick_p})"

                cur.execute("""
                    INSERT INTO froshtn (table_cabin, food_name, quantity, price, category, created_at, is_printed) 
                    VALUES (%s, %s, %s, %s, %s, NOW(), 0)
                """, (tbl, fname, qty, price, cat))

            conn.commit()
        return jsonify({'status': 'success'})
    except Exception as ex:
        return jsonify({'status': 'error', 'message': str(ex)})
    finally:
        if conn:
            try: conn.close()
            except: pass

@app.route('/save_cart_order', methods=['POST'])
def save_cart_order():
    data = request.get_json() or {}
    tbl = str(data.get('table_number', ''))
    cart = data.get('cart_items', [])
    orig = data.get('original_items', [])

    def make_map(its):
        return {it['food_name']: {'qty': int(it['qty']), 'price': float(it['price']), 'cat': it.get('cat', 'گشتی')} for it in its if not it.get('is_divider')}

    old_map = make_map(orig)
    new_map = make_map(cart)
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM froshtn WHERE table_cabin = %s", (tbl,))
            for it in cart:
                fname = "--- قاپی نوێ ---" if it.get('is_divider') else it['food_name']
                cur.execute("""
                    INSERT INTO froshtn (table_cabin, food_name, quantity, price, category, created_at, is_printed) 
                    VALUES (%s, %s, %s, %s, %s, NOW(), 1)
                """, (tbl, fname, it['qty'], it['price'], it.get('cat', 'گشتی')))

            for k in set(old_map.keys()).union(set(new_map.keys())):
                diff = new_map.get(k, {}).get('qty', 0) - old_map.get(k, {}).get('qty', 0)
                if diff > 0:
                    cur.execute("""
                        INSERT INTO froshtn (table_cabin, food_name, quantity, price, category, created_at, is_printed) 
                        VALUES (%s, %s, %s, %s, %s, NOW(), 0)
                    """, (tbl + " [زیادکراو]", f"+ {k}", diff, new_map[k]['price'], new_map[k]['cat']))
                elif diff < 0:
                    cur.execute("""
                        INSERT INTO froshtn (table_cabin, food_name, quantity, price, category, created_at, is_printed) 
                        VALUES (%s, %s, %s, %s, %s, NOW(), 0)
                    """, (tbl + " [سڕاوەتەوە]", f"سڕاوەتەوە: {k}", abs(diff), old_map[k]['price'], old_map[k]['cat']))
            conn.commit()
        return jsonify({'status': 'success'})
    except Exception as ex:
        return jsonify({'status': 'error', 'message': str(ex)})
    finally:
        if conn:
            try: conn.close()
            except: pass

@app.route('/get_table_orders/<path:table_num>')
def get_table_orders(table_num):
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT food_name, price, quantity, category FROM froshtn WHERE table_cabin = %s", (str(table_num),))
            orders = cur.fetchall()
        return jsonify(orders)
    except: return jsonify([])
    finally:
        if conn:
            try: conn.close()
            except: pass

@app.route('/clear_table_orders', methods=['POST'])
def clear_table_orders():
    tbl = str(request.get_json().get('table_number'))
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM froshtn WHERE table_cabin = %s OR table_cabin LIKE %s", (tbl, f"{tbl} [%"))
            conn.commit()
        return jsonify({'status': 'success'})
    except Exception as ex:
        return jsonify({'status': 'error', 'message': str(ex)})
    finally:
        if conn:
            try: conn.close()
            except: pass

@app.route('/get_active_tables')
def get_active_tables():
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT table_cabin FROM froshtn WHERE table_cabin NOT LIKE '%%[%%' AND table_cabin != ''")
            rows = cur.fetchall()
        return jsonify([str(r['table_cabin']).strip() for r in rows])
    except: return jsonify([])
    finally:
        if conn:
            try: conn.close()
            except: pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
