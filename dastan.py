from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session
from datetime import timedelta, datetime
from werkzeug.utils import secure_filename
import pymysql
import os
import re

app = Flask(__name__)
app.secret_key = 'shahoor_all_in_one_pos_2026'

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
                    status VARCHAR(50) DEFAULT 'هاتوو',
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
                cursor.execute("ALTER TABLE masrwf ADD COLUMN IF NOT EXISTS masrwf_name VARCHAR(150) DEFAULT '' AFTER masrwf_date;")
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

    is_api = request.path.startswith(('/get_', '/save_', '/clear_', '/change_', '/set_', '/toggle_', '/api_'))
    if is_api:
        return

    if not session.get('authenticated'):
        return redirect(url_for('login'))

    if request.path.startswith('/admin') and session.get('role') != 'admin':
        session.clear()
        return redirect(url_for('login'))

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
                <div class="module-desc">ڕاپۆرتی فرۆش، کۆی مەسرووفات بەپێی بەروار، کرێی شاگرد و قازانجی صافی.</div>
            </a>

            <a href="/admin/cashier" class="module-card" style="border: 2px solid #10b981;">
                <div class="module-top"><div class="module-icon">🛎️</div><span class="module-badge">کاشێر</span></div>
                <div class="module-title">کاشێر و واصڵکردن</div>
                <div class="module-desc">شاشەی مێزە داواکراوەکان، دوگمەی +٥٠٠ و -٥٠٠، و چاپی وەسڵی ٨٠مم.</div>
            </a>

            <a href="/admin/users" class="module-card">
                <div class="module-top"><div class="module-icon">🔐</div><span class="module-badge">بەکارهێنەر</span></div>
                <div class="module-title">بەکارهێنەران و دەسەڵاتەکان</div>
                <div class="module-desc">دانانی ناوی بەکارهێنەر و وشەی نهێنی، دەستکاری، بلۆککردن، سڕینەوە.</div>
            </a>

            <a href="/admin/qasa" class="module-card">
                <div class="module-top"><div class="module-icon">💵</div><span class="module-badge">قاسە</span></div>
                <div class="module-title">قاسەی فرۆشتن (٢٤ کاتژمێر)</div>
                <div class="module-desc">بینینی تەواوی پسولە واصڵکراوەکان، کۆی داهات، داشکاندن و کاتی وەسڵەکان.</div>
            </a>

            <a href="/admin/masrwf" class="module-card" style="border: 2px solid #ef4444;">
                <div class="module-top"><div class="module-icon">🧾</div><span class="module-badge" style="background:#ef4444; color:#fff;">مەسرووف</span></div>
                <div class="module-title">مەسرووفات و خەرجییەکان</div>
                <div class="module-desc">تۆمارکردنی ناوی مەسرووف، جۆر، خەرجکەر بە شێوازی فۆڕمی سی شارپ.</div>
            </a>

            <a href="/admin/workers" class="module-card">
                <div class="module-top"><div class="module-icon">👥</div><span class="module-badge">شاگرد</span></div>
                <div class="module-title">حیساباتی شاگردەکان</div>
                <div class="module-desc">ئامادەبوونی ڕۆژانە، فلتەری ماوە، بەخشش و حیسابی شایستە بە دیزاینی نوێ.</div>
            </a>

            <a href="/admin/menu_manager" class="module-card">
                <div class="module-top"><div class="module-icon">📖</div><span class="module-badge">مێنۆ</span></div>
                <div class="module-title">بەڕێوەبردنی خواردنەکان</div>
                <div class="module-desc">زیادکردنی خواردنی نوێ، کۆمبۆبۆکسی پۆلێن، و ئەپلۆدکردنی وێنە ڕاستەوخۆ.</div>
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
# پەڕەی ئامار و قازانج (مۆدێرن و داینامیکی بەپێی بەروار)
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

        .filter-card { background: #1e293b; border: 1.5px solid #334155; border-radius: 14px; padding: 18px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .filter-form { display: flex; gap: 14px; align-items: flex-end; flex-wrap: wrap; }
        .filter-item { display: flex; flex-direction: column; gap: 6px; }
        .filter-item label { font-size: 13px; font-weight: 700; color: #38bdf8; }
        .date-input-wrap { position: relative; display: flex; align-items: center; }
        .date-input-wrap input[type="date"] { background: #0f172a; border: 1.5px solid #475569; border-radius: 10px; padding: 10px 14px; color: #fff; font-size: 14px; font-weight: 700; outline: none; cursor: pointer; color-scheme: dark; }
        .date-input-wrap input[type="date"]:focus { border-color: #10b981; }
        .btn-search { background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #fff; border: none; padding: 11px 24px; border-radius: 10px; font-weight: 800; cursor: pointer; font-size: 14px; box-shadow: 0 4px 10px rgba(16, 185, 129, 0.2); }
        .btn-search:hover { opacity: 0.9; }

        .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 22px; }
        .sum-card { background: #1e293b; border: 1.5px solid #334155; border-radius: 14px; padding: 18px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .sum-label { font-size: 13px; color: #94a3b8; font-weight: 700; margin-bottom: 8px; }
        .sum-val { font-size: 20px; font-weight: 900; }

        .table-responsive { overflow-x: auto; background: #1e293b; border: 1px solid #334155; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; text-align: center; }
        th { background: #d97706; padding: 14px; color: #fff; font-size: 13.5px; font-weight: 800; border-bottom: 1px solid #334155; }
        td { padding: 12px; border-bottom: 1px solid #334155; font-size: 13px; }
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
        <p>ماوەی دیاریکراو: لە [{{ start_date }}] تا [{{ end_date }}]</p>
        <div class="print-divider"></div>
    </div>

    <div class="filter-card">
        <form method="GET" action="/admin/amar" class="filter-form">
            <div class="filter-item">
                <label>📅 لە بەرواری:</label>
                <div class="date-input-wrap">
                    <input type="date" name="start_date" value="{{ start_date }}" required>
                </div>
            </div>
            <div class="filter-item">
                <label>📅 تا بەرواری:</label>
                <div class="date-input-wrap">
                    <input type="date" name="end_date" value="{{ end_date }}" required>
                </div>
            </div>
            <button type="submit" class="btn-search">🔍 فلتەر و حیسابکردن</button>
        </form>
    </div>

    <div class="summary-grid">
        <div class="sum-card">
            <div class="sum-label">💰 کۆی فرۆشی ماوەکە</div>
            <div class="sum-val" style="color: #10b981;">{{ "{:,.0f}".format(total_sales) }} د.ع</div>
        </div>
        <div class="sum-card">
            <div class="sum-label">💸 کۆی مەسرووفاتی ماوەکە</div>
            <div class="sum-val" style="color: #ef4444;">{{ "{:,.0f}".format(total_expenses) }} د.ع</div>
        </div>
        <div class="sum-card">
            <div class="sum-label">👥 کرێی شاگرد لە ماوەکەدا</div>
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
                    <td style="text-align:right; font-weight:700;">{{ r.food_name }}</td>
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
# پەڕەی مەسرووفات (دیزاینی مۆدێرن لەگەڵ ئایکۆنی بەروار و کۆی فلتەرکراو)
# ==========================================
WEB_MASRWF_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مەسرووفات و خەرجییەکان - شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background-color: #0f172a; color: #f8fafc; min-height: 100vh; display: flex; flex-direction: column; overflow-x: hidden; }

        .header-panel { background-color: #1e293b; height: 64px; display: flex; align-items: center; justify-content: space-between; padding: 0 24px; border-bottom: 2px solid #334155; }
        .header-title { font-size: 18px; font-weight: 800; color: #f59e0b; display: flex; align-items: center; gap: 10px; }
        .btn-dash { background: #334155; color: #ffffff; padding: 8px 16px; border-radius: 8px; text-decoration: none; font-weight: 800; font-size: 13px; }

        .masrwf-layout { display: grid; grid-template-columns: 1fr 400px; flex: 1; min-height: calc(100vh - 64px); background: #0f172a; }

        .grid-area { padding: 20px; display: flex; flex-direction: column; gap: 16px; overflow: hidden; }
        
        .filter-bar { background: #1e293b; border: 1.5px solid #334155; border-radius: 14px; padding: 16px 20px; display: flex; gap: 16px; align-items: flex-end; flex-wrap: wrap; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .filter-item { display: flex; flex-direction: column; gap: 6px; }
        .filter-item label { font-size: 13px; font-weight: 700; color: #38bdf8; }
        
        .date-input-wrap { position: relative; display: flex; align-items: center; }
        .date-input-wrap input[type="date"] { background: #0f172a; border: 1.5px solid #475569; border-radius: 10px; padding: 10px 14px; color: #fff; font-size: 14px; font-weight: 700; outline: none; cursor: pointer; color-scheme: dark; }
        .date-input-wrap input[type="date"]:focus { border-color: #10b981; }

        .btn-filter { background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #ffffff; border: none; padding: 11px 22px; border-radius: 10px; font-weight: 800; font-size: 14px; cursor: pointer; box-shadow: 0 4px 10px rgba(16, 185, 129, 0.2); }
        .btn-reset { background: #334155; color: #f8fafc; border: 1.5px solid #475569; padding: 10px 18px; border-radius: 10px; font-weight: 800; font-size: 14px; text-decoration: none; display: inline-flex; align-items: center; }

        .table-wrap { flex: 1; overflow-y: auto; background: #1e293b; border: 1.5px solid #334155; border-radius: 14px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; text-align: center; }
        th { background: #334155; color: #f8fafc; padding: 14px; font-size: 13.5px; font-weight: 800; position: sticky; top: 0; z-index: 10; border-bottom: 2px solid #475569; }
        td { padding: 12px 14px; border-bottom: 1px solid #334155; font-size: 13.5px; font-weight: 600; color: #cbd5e1; }
        tbody tr { cursor: pointer; transition: background 0.15s; }
        tbody tr:nth-child(even) { background: #162032; }
        tbody tr:hover { background: #1e293b !important; }
        tbody tr.selected-row { background: #1e293b !important; outline: 2px solid #f59e0b; }

        .input-sidebar { background: #1e293b; border-left: 2px solid #334155; padding: 20px; display: flex; flex-direction: column; gap: 14px; overflow-y: auto; box-shadow: -4px 0 15px rgba(0,0,0,0.2); }
        .field-group { display: flex; flex-direction: column; gap: 5px; text-align: right; }
        .field-group label { font-size: 13px; font-weight: 800; color: #cbd5e1; }
        .c-input { width: 100%; padding: 11px 14px; background: #0f172a; border: 1.5px solid #475569; border-radius: 10px; font-size: 14px; font-weight: 700; color: #fff; outline: none; }
        .c-input:focus { border-color: #10b981; }

        .c-amount { font-size: 18px; font-weight: 900; color: #10b981; background: #0f172a; text-align: center; }

        .btn-grid-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 8px; }
        .action-btn { border: none; padding: 12px; border-radius: 10px; font-size: 13.5px; font-weight: 800; cursor: pointer; text-align: center; }
        .btn-save { background: #10b981; color: #ffffff; }
        .btn-update { background: #f59e0b; color: #0f172a; }
        .btn-delete { background: #ef4444; color: #ffffff; }
        .btn-clear { background: #64748b; color: #ffffff; }

        .card-total-box { background: #0f172a; border: 2px solid #f59e0b; border-radius: 12px; padding: 14px 16px; text-align: right; margin-top: 10px; }
        .card-total-label { font-size: 12px; font-weight: 800; color: #f59e0b; margin-bottom: 4px; }
        .card-total-val { font-size: 22px; font-weight: 900; color: #f59e0b; }

        @media (max-width: 1000px) {
            .masrwf-layout { grid-template-columns: 1fr; }
            .input-sidebar { border-left: none; border-top: 2px solid #334155; }
        }
    </style>
</head>
<body>
    <header class="header-panel">
        <div class="header-title">🧾 بەڕێوەبردنی مەسرووفات و خەرجییەکان</div>
        <a href="/admin" class="btn-dash">⬅️ داشبۆرد</a>
    </header>

    <div class="masrwf-layout">
        <main class="grid-area">
            <div class="filter-bar">
                <form method="GET" action="/admin/masrwf" style="display:flex; gap:14px; align-items:flex-end; flex-wrap:wrap; width:100%;">
                    <div class="filter-item">
                        <label>📅 لە بەرواری:</label>
                        <div class="date-input-wrap">
                            <input type="date" name="from_date" value="{{ from_date }}" class="filter-input">
                        </div>
                    </div>
                    <div class="filter-item">
                        <label>📅 تا بەرواری:</label>
                        <div class="date-input-wrap">
                            <input type="date" name="to_date" value="{{ to_date }}" class="filter-input">
                        </div>
                    </div>
                    <button type="submit" class="btn-filter">🔍 فلتەری خەرجی</button>
                    <a href="/admin/masrwf" class="btn-reset">🔄 هەمووی</a>
                </form>
            </div>

            <div class="table-wrap">
                <table id="tblMasrwf">
                    <thead>
                        <tr>
                            <th style="width: 60px;">#</th>
                            <th>بەروار</th>
                            <th>ناوی مەسرووف</th>
                            <th>جۆری مەسرووف</th>
                            <th>مەسرووفکەر</th>
                            <th>بڕی پارە</th>
                            <th>تێبینی</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for r in rows %}
                        <tr onclick="selectMasrwfRow(this, {{ r.id }}, '{{ r.m_date_raw }}', '{{ r.masrwf_name }}', '{{ r.masrwf_type }}', '{{ r.spent_by }}', {{ r.amount }}, '{{ r.notes }}')">
                            <td>{{ loop.index }}</td>
                            <td style="color: #38bdf8;">{{ r.m_date }}</td>
                            <td style="font-weight:700; color:#fff;">{{ r.masrwf_name if r.masrwf_name else '—' }}</td>
                            <td style="font-weight:700; color:#f59e0b;">{{ r.masrwf_type }}</td>
                            <td style="color:#10b981; font-weight:700;">{{ r.spent_by }}</td>
                            <td style="color:#ef4444; font-weight:900; font-size:14.5px;">{{ "{:,.0f}".format(r.amount) }} د.ع</td>
                            <td style="color:#94a3b8; text-align:right;">{{ r.notes }}</td>
                        </tr>
                        {% else %}
                        <tr><td colspan="7" style="padding:50px; color:#94a3b8; font-size:15px;">هیچ مەسرووفێک لەم ماوەیەدا نەدۆزرایەوە</td></tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </main>

        <aside class="input-sidebar">
            <form id="masrwfForm" method="POST" action="/admin/save_masrwf">
                <input type="hidden" id="selected_id" name="id" value="0">

                <div class="field-group">
                    <label>📅 بەرواری خەرجی:</label>
                    <div class="date-input-wrap">
                        <input type="date" id="txt_date" name="masrwf_date" class="c-input" value="{{ today_date }}" required>
                    </div>
                </div>

                <div class="field-group">
                    <label>📝 ناوی مەسرووف (شتەکە):</label>
                    <input type="text" id="txt_name" name="masrwf_name" class="c-input" placeholder="بۆ نموونە: کڕینی سەوزە...">
                </div>

                <div class="field-group">
                    <label>🏷️ جۆری مەسرووف:</label>
                    <input list="typeOptions" id="txt_type" name="masrwf_type" class="c-input" placeholder="هەڵبژێرە یان بنووسە..." required autocomplete="off">
                    <datalist id="typeOptions">
                        {% for t in existing_types %}<option value="{{ t }}">{% endfor %}
                    </datalist>
                </div>

                <div class="field-group">
                    <label>👤 کێ مەسرووفی کردووە؟:</label>
                    <input list="spentOptions" id="txt_spent_by" name="spent_by" class="c-input" placeholder="هەڵبژێرە یان بنووسە..." autocomplete="off">
                    <datalist id="spentOptions">
                        {% for s in existing_spenders %}<option value="{{ s }}">{% endfor %}
                    </datalist>
                </div>

                <div class="field-group">
                    <label style="color:#f59e0b;">💵 بڕی پارە (دینار):</label>
                    <input type="text" id="txt_amount" name="amount_display" class="c-input c-amount" placeholder="0" required oninput="formatCurrency(this)">
                    <input type="hidden" id="real_amount" name="amount" value="0">
                </div>

                <div class="field-group">
                    <label>📄 تێبینی و وردەکاری:</label>
                    <textarea id="txt_notes" name="notes" class="c-input" style="height: 65px; resize:none;" placeholder="تێبینی بنووسە..."></textarea>
                </div>

                <div class="btn-grid-actions">
                    <button type="button" class="action-btn btn-save" onclick="submitForm('/admin/save_masrwf')">💾 تۆمارکردن</button>
                    <button type="button" class="action-btn btn-update" onclick="submitForm('/admin/update_masrwf')">✏️ گۆڕانکاری</button>
                    <button type="button" class="action-btn btn-delete" onclick="deleteRecord()">🗑️ سڕینەوە</button>
                    <button type="button" class="action-btn btn-clear" onclick="clearInputs()">🧹 پاککردنەوە</button>
                </div>
            </form>

            <div class="card-total-box">
                <div class="card-total-label">🧾 کۆی گشتی مەسرووفاتی فلتەرکراو:</div>
                <div class="card-total-val" id="lblTotal">{{ "{:,.0f}".format(total_m) }} دینار</div>
            </div>
        </aside>
    </div>

    <script>
        let currentSelectedId = 0;

        function formatCurrency(input) {
            let val = input.value.replace(/,/g, '').trim();
            if (!isNaN(val) && val.length > 0) {
                let num = parseFloat(val);
                input.value = num.toLocaleString('en-US');
                document.getElementById('real_amount').value = num;
            } else {
                input.value = '';
                document.getElementById('real_amount').value = '0';
            }
        }

        function selectMasrwfRow(row, id, date, name, type, spentBy, amount, notes) {
            document.querySelectorAll('#tblMasrwf tbody tr').forEach(r => r.classList.remove('selected-row'));
            row.classList.add('selected-row');

            currentSelectedId = id;
            document.getElementById('selected_id').value = id;
            document.getElementById('txt_date').value = date;
            document.getElementById('txt_name').value = (name === 'None' || !name) ? '' : name;
            document.getElementById('txt_type').value = (type === 'None' || !type) ? '' : type;
            document.getElementById('txt_spent_by').value = (spentBy === 'None' || !spentBy) ? '' : spentBy;
            
            document.getElementById('real_amount').value = amount;
            document.getElementById('txt_amount').value = Number(amount).toLocaleString('en-US');
            
            document.getElementById('txt_notes').value = (notes === 'None' || !notes) ? '' : notes;
        }

        function clearInputs() {
            currentSelectedId = 0;
            document.getElementById('selected_id').value = '0';
            document.getElementById('txt_name').value = '';
            document.getElementById('txt_type').value = '';
            document.getElementById('txt_spent_by').value = '';
            document.getElementById('txt_amount').value = '';
            document.getElementById('real_amount').value = '0';
            document.getElementById('txt_notes').value = '';
            document.getElementById('txt_date').value = '{{ today_date }}';
            document.querySelectorAll('#tblMasrwf tbody tr').forEach(r => r.classList.remove('selected-row'));
        }

        function submitForm(actionUrl) {
            let form = document.getElementById('masrwfForm');
            let amtVal = parseFloat(document.getElementById('real_amount').value) || 0;

            if (actionUrl.includes('update_masrwf') && currentSelectedId <= 0) {
                alert('تکایە سەرەتا دێڕێک لە خشتەکە دەستنیشان بکە بۆ گۆڕانکاری!');
                return;
            }

            if (amtVal <= 0) {
                alert('تکایە بڕی پارەکە بە دروستی بنووسە!');
                return;
            }

            form.action = actionUrl;
            form.submit();
        }

        function deleteRecord() {
            if (currentSelectedId <= 0) {
                alert('تکایە سەرەتا دێڕێک لە خشتەکە هەڵبژێرە بۆ سڕینەوە!');
                return;
            }

            if (confirm('ئایا دڵنیایت لە سڕینەوەی ئەم تۆمارەی خەرجییە؟')) {
                window.location.href = '/admin/delete_masrwf/' + currentSelectedId;
            }
        }
    </script>
</body>
</html>
"""

# ==========================================
# پەڕەی شاگردەکان
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
        
        .box-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; margin-bottom: 20px; }
        .box-card { background: #064032; border: 1.5px solid #0b5e4a; border-radius: 14px; padding: 18px; }
        .box-title { color: #10b981; font-size: 15px; font-weight: 800; margin-bottom: 12px; border-bottom: 1px solid #0b5e4a; padding-bottom: 6px; }
        
        .form-row { display: flex; gap: 10px; flex-wrap: wrap; align-items: flex-end; }
        .form-group { display: flex; flex-direction: column; gap: 4px; flex: 1; min-width: 130px; }
        .form-group label { font-size: 12px; font-weight: 700; color: #a7f3d0; }
        .form-input { padding: 9px 12px; background: #03261d; border: 1.5px solid #0b5e4a; border-radius: 8px; color: #fff; font-size: 13px; outline: none; width: 100%; color-scheme: dark; }
        .form-input:focus { border-color: #10b981; }
        
        .btn-act { padding: 9px 18px; border-radius: 8px; border: none; font-weight: 800; cursor: pointer; font-size: 13px; }
        .btn-add { background: #10b981; color: #03261d; }
        .btn-filter { background: #3b82f6; color: #fff; }

        .table-wrap { overflow-x: auto; background: #064032; border: 1px solid #0b5e4a; border-radius: 12px; }
        table { width: 100%; border-collapse: collapse; text-align: center; }
        th { background: #085341; padding: 12px; color: #a7f3d0; font-size: 13px; font-weight: 800; border-bottom: 1px solid #0b5e4a; }
        td { padding: 10px; border-bottom: 1px solid #0b5e4a; font-size: 13px; }
        tr:hover { background: #085341; }
        .btn-edit { background: #3b82f6; color: #fff; padding: 4px 8px; border-radius: 6px; font-size: 11px; cursor: pointer; border: none; font-weight: 700; }
        .btn-del { color: #ef4444; text-decoration: none; font-weight: bold; font-size: 13px; }

        .modal { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.75); display: none; align-items: center; justify-content: center; z-index: 2000; padding: 16px; }
        .modal-content { background: #064032; border: 2px solid #0b5e4a; border-radius: 14px; width: 100%; max-width: 420px; padding: 20px; }
    </style>
</head>
<body>
    <div class="top-bar">
        <h2 style="color:#10b981;">👥 بەڕێوەبردنی حیساباتی شاگردەکان</h2>
        <a href="/admin" class="btn-dash">⬅️ داشبۆرد</a>
    </div>

    <div class="box-grid">
        <div class="box-card">
            <div class="box-title">🗓️ فلتەری ماوەی حیسابات</div>
            <form method="GET" action="/admin/workers" class="form-row">
                <div class="form-group">
                    <label>لە بەرواری:</label>
                    <input type="date" name="start_date" class="form-input" value="{{ start_date }}" required>
                </div>
                <div class="form-group">
                    <label>تا بەرواری:</label>
                    <input type="date" name="end_date" class="form-input" value="{{ end_date }}" required>
                </div>
                <button type="submit" class="btn-act btn-filter">🔍 حیسابکردن</button>
            </form>
        </div>

        <div class="box-card">
            <div class="box-title">📝 تۆماری ئامادەبوونی ڕۆژانە</div>
            <form method="POST" action="/admin/save_attendance" class="form-row">
                <div class="form-group">
                    <label>بەروار:</label>
                    <input type="date" name="att_date" class="form-input" value="{{ today_date }}" required>
                </div>
                <div class="form-group">
                    <label>شاگرد:</label>
                    <select name="worker_id" class="form-input" required>
                        {% for w in wage_rows %}
                            <option value="{{ w.id }}">{{ w.name }} ({{ "{:,.0f}".format(w.salary) }})</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="form-group">
                    <label>دۆخ:</label>
                    <select name="status" class="form-input">
                        <option value="هاتوو">✅ هاتوو</option>
                        <option value="نەهاتوو">❌ نەهاتوو</option>
                        <option value="مۆڵەت">🏖️ مۆڵەت</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>بەخشش:</label>
                    <input type="number" name="bonus" class="form-input" value="0">
                </div>
                <button type="submit" class="btn-act btn-add">💾 پاشەکەوت</button>
            </form>
        </div>

        <div class="box-card" style="grid-column: 1 / -1;">
            <div class="box-title">➕ زیادکردنی شاگردی نوێ</div>
            <form method="POST" action="/admin/add_worker" class="form-row">
                <div class="form-group"><label>ناوی شاگرد:</label><input type="text" name="name" class="form-input" required placeholder="ناوی تەواو"></div>
                <div class="form-group"><label>ژمارەی مۆبایل:</label><input type="text" name="phone" class="form-input" placeholder="0770xxxxxxx"></div>
                <div class="form-group"><label>مووچەی ڕۆژانە (دینار):</label><input type="number" name="salary" class="form-input" required placeholder="25000"></div>
                <button type="submit" class="btn-act btn-add">➕ تۆمارکردن</button>
            </form>
        </div>
    </div>

    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>ناو</th>
                    <th>مۆبایل</th>
                    <th>مووچەی ڕۆژانە</th>
                    <th>ڕۆژانی ئامادەبوون</th>
                    <th>کۆی مووچە</th>
                    <th>کۆی بەخشش</th>
                    <th>کۆی گشتی شایستە</th>
                    <th>کردارەکان</th>
                </tr>
            </thead>
            <tbody>
                {% for w in wage_rows %}
                <tr>
                    <td>{{ loop.index }}</td>
                    <td style="font-weight:bold; color:#10b981;">{{ w.name }}</td>
                    <td>{{ w.phone }}</td>
                    <td>{{ "{:,.0f}".format(w.salary) }} د.ع</td>
                    <td style="color:#38bdf8; font-weight:bold;">{{ w.work_days }} ڕۆژ</td>
                    <td>{{ "{:,.0f}".format(w.total_salary) }} د.ع</td>
                    <td style="color:#f59e0b;">{{ "{:,.0f}".format(w.total_bonus) }} د.ع</td>
                    <td style="color:#10b981; font-weight:bold; font-size:14px;">{{ "{:,.0f}".format(w.total_due) }} د.ع</td>
                    <td>
                        <button type="button" class="btn-edit" onclick="openWorkerModal({{ w.id }}, '{{ w.name }}', '{{ w.phone }}', {{ w.salary }})">✏️ دەستکاری</button>
                        <a href="/admin/delete_worker/{{ w.id }}" class="btn-del" onclick="return confirm('دڵنیایت لە سڕینەوە؟')">🗑️ سڕینەوە</a>
                    </td>
                </tr>
                {% else %}
                <tr><td colspan="9" style="padding:25px; color:#94a3b8;">هیچ شاگردێک تۆمار نەکراوە</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <div class="modal" id="workerEditModal">
        <div class="modal-content">
            <h3 style="color:#10b981; margin-bottom:14px; text-align:center;">✏️ دەستکاریکردنی زانیاری شاگرد</h3>
            <form id="editWorkerForm" method="POST" action="">
                <div class="form-group" style="margin-bottom:10px;">
                    <label>ناوی شاگرد:</label>
                    <input type="text" id="m_worker_name" name="name" class="form-input" required>
                </div>
                <div class="form-group" style="margin-bottom:10px;">
                    <label>تەلەفۆن:</label>
                    <input type="text" id="m_worker_phone" name="phone" class="form-input">
                </div>
                <div class="form-group" style="margin-bottom:14px;">
                    <label>مووچەی ڕۆژانە (دینار):</label>
                    <input type="number" id="m_worker_salary" name="salary" class="form-input" required>
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
    </script>
</body>
</html>
"""

# ==========================================
# پەڕەی بەڕێوەبردنی بەکارهێنەران
# ==========================================
WEB_USERS_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>بەڕێوەبردنی بەکارهێنەران - شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background-color: #03261d; color: #ffffff; min-height: 100vh; padding: 20px; }
        .top-bar { display: flex; justify-content: space-between; align-items: center; background: #064032; padding: 14px 20px; border-radius: 12px; border: 1px solid #0b5e4a; margin-bottom: 20px; }
        .btn-dash { background: #334155; color: #fff; padding: 8px 16px; border-radius: 8px; text-decoration: none; font-weight: 800; font-size: 13px; }
        
        .user-form-card { background: #064032; border: 1.5px solid #0b5e4a; border-radius: 14px; padding: 20px; margin-bottom: 24px; }
        .user-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; align-items: flex-end; }
        .user-form-card label { display: block; font-size: 12px; font-weight: 700; color: #a7f3d0; margin-bottom: 5px; }
        .user-form-card input, .user-form-card select { width: 100%; padding: 10px; background: #03261d; border: 1.5px solid #0b5e4a; border-radius: 8px; color: #fff; font-size: 13px; outline: none; }
        .btn-save-u { background: #10b981; color: #03261d; border: none; padding: 11px; border-radius: 8px; font-weight: 800; cursor: pointer; font-size: 14px; width: 100%; }

        .table-responsive { overflow-x: auto; background: #064032; border: 1px solid #0b5e4a; border-radius: 12px; }
        table { width: 100%; border-collapse: collapse; text-align: right; }
        th { background: #085341; padding: 12px 14px; color: #a7f3d0; font-size: 13px; font-weight: 800; border-bottom: 1px solid #0b5e4a; }
        td { padding: 12px 14px; border-bottom: 1px solid #0b5e4a; font-size: 13px; color: #f8fafc; }
        tr:hover { background: #085341; }
        .status-badge { padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 800; }
        .status-active { background: #dcfce7; color: #166534; }
        .status-blocked { background: #fee2e2; color: #991b1b; }
        .action-btn { padding: 5px 10px; border-radius: 6px; font-size: 11px; font-weight: 700; text-decoration: none; display: inline-block; cursor: pointer; border: none; }
        .btn-toggle { background: #f59e0b; color: #000; }
        .btn-del { background: #ef4444; color: #fff; }
    </style>
</head>
<body>
    <div class="top-bar">
        <h2 style="color:#10b981;">🔐 بەڕێوەبردنی بەکارهێنەران و دەسەڵاتەکان</h2>
        <a href="/admin" class="btn-dash">⬅️ داشبۆرد</a>
    </div>

    <div class="user-form-card">
        <h3 style="color:#a7f3d0; margin-bottom:14px; font-size:15px;">➕ زیادکردنی بەکارهێنەری نوێ</h3>
        <form method="POST" action="/admin/add_user">
            <div class="user-grid">
                <div>
                    <label>ناوی بەکارهێنەر (Username):</label>
                    <input type="text" name="username" required placeholder="یوسەر">
                </div>
                <div>
                    <label>وشەی نهێنی (Password):</label>
                    <input type="text" name="password" required placeholder="پاسوۆرد">
                </div>
                <div>
                    <label>ناوی تەواو (Full Name):</label>
                    <input type="text" name="full_name" placeholder="ناوی کەسەکە">
                </div>
                <div>
                    <label>ڕۆڵ لە سیستەم (Role):</label>
                    <select name="role">
                        <option value="Manager">👑 بەڕێوەبەر (Manager)</option>
                        <option value="Waiter">🍽️ گارسۆنی ئایپاد (Waiter)</option>
                        <option value="Mobile_Waiter">📱 گارسۆنی مۆبایل (Mobile Waiter)</option>
                        <option value="Cashier">💵 کاشێر (Cashier)</option>
                    </select>
                </div>
                <div>
                    <button type="submit" class="btn-save-u">💾 دروستکردنی یوسەر</button>
                </div>
            </div>
        </form>
    </div>

    <div class="table-responsive">
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>ناوی بەکارهێنەر</th>
                    <th>وشەی نهێنی</th>
                    <th>ناوی تەواو</th>
                    <th>ڕۆڵ</th>
                    <th>دۆخ</th>
                    <th>کردارەکان</th>
                </tr>
            </thead>
            <tbody>
                {% for u in users %}
                <tr>
                    <td>{{ loop.index }}</td>
                    <td style="font-weight:700; color:#10b981;">{{ u.username }}</td>
                    <td style="color:#cbd5e1; font-family:monospace; font-weight:bold;">{{ u.password }}</td>
                    <td>{{ u.full_name }}</td>
                    <td>{{ u.role }}</td>
                    <td>
                        <span class="status-badge {{ 'status-active' if u.is_active else 'status-blocked' }}">
                            {{ 'چالاکە' if u.is_active else 'بلۆککراوە' }}
                        </span>
                    </td>
                    <td>
                        <a href="/admin/toggle_user/{{ u.id }}" class="action-btn btn-toggle">
                            {{ '⛔ بلۆککردن' if u.is_active else '✅ کاراکردن' }}
                        </a>
                        {% if u.username != 'admin' %}
                        <a href="/admin/delete_user/{{ u.id }}" class="action-btn btn-del" onclick="return confirm('ئایا دڵنیایت لە سڕینەوەی ئەم بەکارهێنەرە؟')">🗑️ سڕینەوە</a>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
"""

# ==========================================
# پەڕەی کاشێر
# ==========================================
WEB_CASHIER_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>کاشێر و واصڵکردن - شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background-color: #fef3c7; color: #1e293b; min-height: 100vh; display: flex; flex-direction: column; }
        
        .cashier-nav { background: #064032; padding: 14px 28px; display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #0b5e4a; color: #fff; }
        .cashier-brand { font-size: 20px; font-weight: 800; color: #10b981; }
        .btn-dash-back { background: #10b981; color: #03261d; text-decoration: none; padding: 8px 18px; border-radius: 8px; font-weight: 800; font-size: 13px; }

        .cashier-container { padding: 24px; max-width: 1400px; margin: 0 auto; width: 100%; }
        
        .header-status-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .active-count-badge { background: #047857; color: #fef08a; padding: 8px 18px; border-radius: 12px; font-size: 16px; font-weight: 800; }
        .search-box { padding: 10px 16px; border-radius: 10px; border: 2px solid #cbd5e1; width: 260px; font-size: 14px; font-weight: 700; outline: none; }
        .search-box:focus { border-color: #10b981; }

        .tables-flow-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 16px; }
        .table-card { background-color: #10b981; border: 2px solid #047857; border-radius: 14px; height: 160px; display: flex; flex-direction: column; justify-content: space-between; cursor: pointer; text-align: center; color: #fff; transition: transform 0.15s, background-color 0.15s; box-shadow: 0 4px 10px rgba(0,0,0,0.1); user-select: none; }
        .table-card:hover { background-color: #059669; transform: translateY(-3px); }
        .card-icon { font-size: 28px; margin-top: 10px; }
        .card-title { font-size: 18px; font-weight: 800; }
        .card-badge { background: #047857; color: #fef08a; padding: 8px; font-size: 12px; font-weight: 800; border-radius: 0 0 12px 12px; }

        .empty-container { background: #fffbeb; border: 2px dashed #fde68a; border-radius: 16px; padding: 50px; text-align: center; color: #78350f; grid-column: 1 / -1; }

        .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); display: none; align-items: center; justify-content: center; z-index: 1000; padding: 16px; }
        .modal-content { background: #ffffff; border-radius: 16px; width: 100%; max-width: 650px; padding: 24px; color: #0f172a; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
        .modal-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; margin-bottom: 16px; }
        .modal-title { font-size: 18px; font-weight: 800; color: #0f172a; }
        .btn-close-modal { background: none; border: none; font-size: 22px; cursor: pointer; color: #ef4444; font-weight: bold; }

        .items-table-wrap { max-height: 250px; overflow-y: auto; border: 1px solid #cbd5e1; border-radius: 8px; margin-bottom: 16px; }
        .items-table { width: 100%; border-collapse: collapse; text-align: center; font-size: 13px; }
        .items-table th { background: #1e293b; color: #fff; padding: 10px; font-weight: 800; position: sticky; top: 0; }
        .items-table td { padding: 8px; border-bottom: 1px solid #e2e8f0; font-weight: 700; }
        
        .checkout-calc-bar { background: #f8fafc; border: 1.5px solid #e2e8f0; border-radius: 12px; padding: 14px; display: flex; flex-direction: column; gap: 10px; margin-bottom: 16px; }
        .calc-row { display: flex; justify-content: space-between; align-items: center; font-weight: 800; }
        
        .amount-input-group { display: flex; align-items: center; justify-content: center; gap: 6px; }
        .btn-quick-amt { border: none; color: #fff; padding: 8px 12px; border-radius: 8px; font-weight: 800; font-size: 12px; cursor: pointer; }
        .btn-p500 { background: #10b981; }
        .btn-m500 { background: #e11d48; }
        .txt-paid { width: 130px; padding: 8px; font-size: 16px; font-weight: 800; text-align: center; border: 2px solid #cbd5e1; border-radius: 8px; outline: none; }
        .txt-paid:focus { border-color: #10b981; }

        .btn-confirm-pay { width: 100%; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #fff; border: none; padding: 14px; border-radius: 10px; font-size: 16px; font-weight: 800; cursor: pointer; }

        @media print {
            body * { visibility: hidden; }
            #receiptPrintArea, #receiptPrintArea * { visibility: visible; }
            #receiptPrintArea { position: absolute; left: 0; top: 0; width: 80mm; padding: 5px; color: #000; font-family: 'Noto Kufi Arabic', sans-serif; font-size: 12px; }
        }
    </style>
</head>
<body>
    <header class="cashier-nav">
        <div class="cashier-brand">✨ شاهور ڕێستۆرانت - کاشێر و واصڵکردن</div>
        <div style="display:flex; align-items:center; gap:10px;">
            <a href="/admin" class="btn-dash-back">⬅️ گەڕانەوە بۆ داشبۆرد</a>
        </div>
    </header>

    <main class="cashier-container">
        <div class="header-status-bar">
            <div class="active-count-badge" id="lblActiveCount">مێزی داواکراو: {{ active_tables|length }}</div>
            <input type="text" id="txtSearch" class="search-box" placeholder="🔍 گەڕان بەپێی ژمارەی مێز..." oninput="filterTables()">
        </div>

        <div class="tables-flow-grid" id="tablesGrid">
            {% for t in active_tables %}
            <div class="table-card" onclick="openCheckout('{{ t.table_cabin }}')" data-table="{{ t.table_cabin }}">
                <div class="card-icon">🍽️</div>
                <div class="card-title">مێزی {{ t.table_cabin }}</div>
                <div class="card-badge">
                    {{ '🔥 ' ~ t.rounds ~ ' جار داواکراوە' if t.rounds > 1 else '✓ ١ جار داواکراوە' }}
                </div>
            </div>
            {% else %}
            <div class="empty-container">
                <div style="font-size: 45px; margin-bottom: 10px;">✨</div>
                <div style="font-size: 18px; font-weight: 800;">لە ئێستادا سەرجەم مێزەکان بەتاڵن و هیچ داواکارییەکی کراوە نییە</div>
            </div>
            {% endfor %}
        </div>
    </main>

    <div class="modal-overlay" id="checkoutModal">
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-title" id="checkoutTitle">واصڵکردنی مێزی ژمارە: </div>
                <button type="button" class="btn-close-modal" onclick="closeCheckout()">✕</button>
            </div>

            <div class="items-table-wrap">
                <table class="items-table">
                    <thead>
                        <tr>
                            <th style="text-align:right;">ناوی خواردن</th>
                            <th>ژمارە</th>
                            <th>نرخی تاک</th>
                            <th>کۆی گشتی</th>
                        </tr>
                    </thead>
                    <tbody id="checkoutItemsList"></tbody>
                </table>
            </div>

            <div class="checkout-calc-bar">
                <div class="calc-row">
                    <span>کۆی گشتی حساب:</span>
                    <span id="lblTotalSum" style="font-size: 18px; color: #059669;">0 دینار</span>
                </div>

                <div class="calc-row">
                    <span>پارەی وەرگیراو:</span>
                    <div class="amount-input-group">
                        <button type="button" class="btn-quick-amt btn-m500" onclick="adjustAmount(-500)">-٥٠٠</button>
                        <button type="button" class="btn-quick-amt btn-p500" onclick="adjustAmount(500)">+٥٠٠</button>
                        <input type="number" id="txtPaidAmount" class="txt-paid" oninput="calculateChange()">
                    </div>
                </div>

                <div class="calc-row">
                    <span>گێڕاوە (باقی):</span>
                    <span id="lblChange" style="font-size: 16px; color: #10b981;">0 دینار</span>
                </div>
            </div>

            <button type="button" class="btn-confirm-pay" onclick="submitAndPrintPayment()">🖨️ واصڵکردن و چاپکردنی وەسڵ</button>
        </div>
    </div>

    <div id="receiptPrintArea" style="display:none;"></div>

    <script>
        let currentTable = '';
        let totalSum = 0;
        let currentItems = [];

        function filterTables() {
            let val = document.getElementById('txtSearch').value.trim().toLowerCase();
            document.querySelectorAll('.table-card').forEach(card => {
                let tbl = card.getAttribute('data-table').toLowerCase();
                card.style.display = tbl.includes(val) ? 'flex' : 'none';
            });
        }

        function openCheckout(tableNum) {
            currentTable = tableNum;
            document.getElementById('checkoutTitle').innerText = 'واصڵکردنی: ' + tableNum;
            fetch('/get_table_orders/' + encodeURIComponent(tableNum))
                .then(r => r.json())
                .then(items => {
                    currentItems = items;
                    let tbody = document.getElementById('checkoutItemsList');
                    tbody.innerHTML = '';
                    totalSum = 0;

                    items.forEach(it => {
                        let lineTotal = it.price * it.quantity;
                        totalSum += lineTotal;
                        tbody.innerHTML += `
                            <tr>
                                <td style="text-align:right;">${it.food_name}</td>
                                <td>${it.quantity}</td>
                                <td>${Number(it.price).toLocaleString()}</td>
                                <td>${lineTotal.toLocaleString()}</td>
                            </tr>
                        `;
                    });

                    document.getElementById('lblTotalSum').innerText = totalSum.toLocaleString() + ' دینار';
                    document.getElementById('txtPaidAmount').value = totalSum;
                    calculateChange();
                    document.getElementById('checkoutModal').style.display = 'flex';
                });
        }

        function closeCheckout() {
            document.getElementById('checkoutModal').style.display = 'none';
        }

        function adjustAmount(delta) {
            let cur = parseInt(document.getElementById('txtPaidAmount').value) || 0;
            let n = cur + delta;
            if (n < 0) n = 0;
            document.getElementById('txtPaidAmount').value = n;
            calculateChange();
        }

        function calculateChange() {
            let paid = parseInt(document.getElementById('txtPaidAmount').value) || 0;
            let diff = paid - totalSum;
            let changeEl = document.getElementById('lblChange');
            if (diff >= 0) {
                changeEl.innerText = diff.toLocaleString() + ' دینار';
                changeEl.style.color = '#10b981';
            } else {
                changeEl.innerText = 'کەمترە بەبڕی: ' + Math.abs(diff).toLocaleString() + ' دینار';
                changeEl.style.color = '#e11d48';
            }
        }

        function submitAndPrintPayment() {
            let paid = parseFloat(document.getElementById('txtPaidAmount').value) || 0;
            if (paid <= 0) {
                alert('تکایە بڕی پارەی دروست بنووسە!');
                return;
            }

            fetch('/admin/complete_payment', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    table_number: currentTable,
                    amount_paid: paid,
                    total_amount: totalSum
                })
            }).then(r => r.json()).then(res => {
                if (res.status === 'success') {
                    printWebReceipt(paid);
                    closeCheckout();
                    setTimeout(() => { location.reload(); }, 600);
                } else {
                    alert('هەڵە لە واصڵکردن: ' + res.message);
                }
            });
        }

        function printWebReceipt(paid) {
            let area = document.getElementById('receiptPrintArea');
            let diff = paid - totalSum;
            let itemsRows = '';
            currentItems.forEach(it => {
                itemsRows += `
                    <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                        <span style="flex:2; text-align:right;">${it.food_name}</span>
                        <span style="flex:1; text-align:center;">${it.quantity}</span>
                        <span style="flex:1; text-align:center;">${Number(it.price).toLocaleString()}</span>
                        <span style="flex:1.5; text-align:left;">${(it.price * it.quantity).toLocaleString()}</span>
                    </div>
                `;
            });

            area.innerHTML = `
                <div style="text-align:center; font-family:'Noto Kufi Arabic',sans-serif; width:75mm; margin:0 auto; padding:4px; direction:rtl;">
                    <h2 style="font-size:16px; margin-bottom:4px;">شاهور ڕێستۆرانت</h2>
                    <div style="font-size:12px; font-weight:bold;">وەسڵی فرۆشتن و قاسە</div>
                    <div style="font-size:12px; font-weight:bold; margin-bottom:4px;">${currentTable}</div>
                    <div style="font-size:10px; color:#555;">کاتی وەسڵ: ${new Date().toLocaleString()}</div>
                    <div style="border-top:1px dashed #000; margin:6px 0;"></div>
                    <div style="display:flex; justify-content:space-between; font-weight:bold; font-size:11px; margin-bottom:4px;">
                        <span style="flex:2; text-align:right;">خواردن</span>
                        <span style="flex:1; text-align:center;">بڕ</span>
                        <span style="flex:1; text-align:center;">نرخ</span>
                        <span style="flex:1.5; text-align:left;">کۆی گشتی</span>
                    </div>
                    <div style="border-top:1px dashed #000; margin:4px 0;"></div>
                    ${itemsRows}
                    <div style="border-top:1px dashed #000; margin:6px 0;"></div>
                    <div style="display:flex; justify-content:space-between; font-weight:bold; font-size:13px;">
                        <span>کۆی گشتی:</span>
                        <span>${totalSum.toLocaleString()} دینار</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:11px; margin-top:4px;">
                        <span>پارەی وەرگیراو:</span>
                        <span>${paid.toLocaleString()} دینار</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:11px; margin-top:2px;">
                        <span>گێڕاوە (باقی):</span>
                        <span>${diff >= 0 ? diff.toLocaleString() : 0} دینار</span>
                    </div>
                    <div style="border-top:1px dashed #000; margin:8px 0;"></div>
                    <div style="text-align:center; font-size:11px; font-weight:bold;">بەخێر بێنەوە! سوپاس بۆ سەردانکردنتان</div>
                </div>
            `;

            area.style.display = 'block';
            window.print();
            area.style.display = 'none';
        }
    </script>
</body>
</html>
"""

# ==========================================
# پەڕەی بەڕێوەبردنی خواردنەکان
# ==========================================
WEB_MENU_MANAGER_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>بەڕێوەبردنی مێنۆ - شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background-color: #03261d; color: #ffffff; min-height: 100vh; padding: 20px; }
        .top-bar { display: flex; justify-content: space-between; align-items: center; background: #064032; padding: 14px 20px; border-radius: 12px; border: 1px solid #0b5e4a; margin-bottom: 20px; }
        .btn-dash { background: #334155; color: #fff; padding: 8px 16px; border-radius: 8px; text-decoration: none; font-weight: 800; font-size: 13px; }
        
        .form-card { background: #064032; border: 1.5px solid #0b5e4a; border-radius: 14px; padding: 18px; margin-bottom: 24px; }
        .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; align-items: flex-end; }
        .form-card label { display: block; font-size: 12px; font-weight: 700; color: #a7f3d0; margin-bottom: 4px; }
        .form-card input, .form-card select { width: 100%; padding: 10px; background: #03261d; border: 1.5px solid #0b5e4a; border-radius: 8px; color: #fff; font-size: 13px; outline: none; }
        .btn-add { background: #10b981; color: #03261d; border: none; padding: 11px; border-radius: 8px; font-weight: 800; cursor: pointer; font-size: 14px; }
        
        .food-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }
        .food-item-box { background: #ffffff; color: #0f172a; border-radius: 14px; padding: 12px; display: flex; flex-direction: column; gap: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
        .food-item-img { width: 100%; height: 130px; object-fit: cover; border-radius: 10px; }
        .food-item-title { font-size: 15px; font-weight: 800; }
        .food-item-details { display: flex; justify-content: space-between; font-size: 13px; font-weight: 700; color: #059669; }
        .btn-del-food { background: #ef4444; color: #fff; border: none; padding: 7px; border-radius: 6px; font-weight: 800; font-size: 12px; cursor: pointer; text-align: center; text-decoration: none; }
    </style>
</head>
<body>
    <div class="top-bar">
        <h2 style="color:#10b981;">📖 بەڕێوەبردنی خواردنەکان</h2>
        <a href="/admin" class="btn-dash">⬅️ داشبۆرد</a>
    </div>

    <div class="form-card">
        <h3 style="color:#a7f3d0; margin-bottom:12px; font-size:15px;">➕ زیادکردنی خواردنی نوێ</h3>
        <form method="POST" action="/admin/add_food" enctype="multipart/form-data">
            <div class="form-grid">
                <div><label>ناوی خواردن:</label><input type="text" name="food_name" required></div>
                <div><label>نرخ (د.ع):</label><input type="number" name="price" required></div>
                <div>
                    <label>پۆلێن:</label>
                    <input list="categoryList" name="category" required>
                    <datalist id="categoryList">
                        {% for c in existing_categories %}<option value="{{ c }}">{% endfor %}
                    </datalist>
                </div>
                <div><label>وێنە:</label><input type="file" name="food_image" accept="image/*"></div>
                <div><button type="submit" class="btn-add">➕ زیادکردن</button></div>
            </div>
        </form>
    </div>

    <div class="food-grid">
        {% for f in foods %}
        <div class="food-item-box">
            <img src="{{ f.image_path if f.image_path else 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=300' }}" class="food-item-img">
            <div class="food-item-title">{{ f.food_name }}</div>
            <div class="food-item-details">
                <span>{{ "{:,.0f}".format(f.price) }} د.ع</span>
                <span>{{ f.category }}</span>
            </div>
            <a href="/admin/delete_food/{{ f.id }}" class="btn-del-food" onclick="return confirm('سڕینەوە؟')">🗑️ سڕینەوە</a>
        </div>
        {% endfor %}
    </div>
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
    <title>بەڕێوەبردنی QR - شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background-color: #03261d; color: #ffffff; min-height: 100vh; padding: 20px; }
        .top-bar { display: flex; justify-content: space-between; align-items: center; background: #064032; padding: 14px 20px; border-radius: 12px; border: 1px solid #0b5e4a; margin-bottom: 20px; }
        .btn-action { background: #10b981; color: #03261d; padding: 8px 16px; border-radius: 8px; text-decoration: none; font-weight: 800; border: none; cursor: pointer; font-size: 13px; }
        .qr-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; }
        .qr-card { background: #ffffff; color: #0f172a; border-radius: 14px; padding: 16px; display: flex; flex-direction: column; align-items: center; text-align: center; }
        .qr-card img { width: 140px; height: 140px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="top-bar">
        <h2 style="color:#10b981;">📱 بەڕێوەبردنی QR کۆدەکانی مێز</h2>
        <a href="/admin" class="btn-action" style="background:#334155; color:#fff;">⬅️ داشبۆرد</a>
    </div>
    <div class="qr-grid">
        {% for num in range(1, 91) %}
        <div class="qr-card">
            <div style="font-size:18px; font-weight:800; color:#03261d;">مێزی {{ num }}</div>
            <img src="https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={{ base_url }}/table/{{ num }}">
        </div>
        {% endfor %}
    </div>
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
    <title>هەڵبژاردنی مێز - شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background-color: #03261d; color: #ffffff; min-height: 100vh; padding: 16px; }
        .header-bar { background-color: #064032; padding: 12px 20px; display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #0b5e4a; margin-bottom: 20px; border-radius: 12px; }
        .tables-grid { display: grid; grid-template-columns: repeat(10, 1fr); gap: 12px; }
        .table-box { background-color: #ffffff; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 28px; font-weight: 800; color: #03261d; text-decoration: none; height: 90px; }
        .table-box.active-occupied { background: #10b981 !important; color: #ffffff !important; }
    </style>
</head>
<body>
    <div class="header-bar">
        <a href="/logout" style="background:#ef4444; color:#fff; text-decoration:none; padding:8px 16px; border-radius:8px; font-weight:bold;">✕ دەرچوون</a>
        <div style="font-size:16px; font-weight:800;">تکایە مێزێک دیاری بکە بۆ ئۆردەر</div>
        <a href="/admin" style="background:#10b981; color:#03261d; text-decoration:none; padding:8px 16px; border-radius:8px; font-weight:bold;">👑 داشبۆرد</a>
    </div>
    <div class="tables-grid">
        {% for num in range(1, 91) %}
            <a href="/desktop?table={{ num }}" class="table-box" id="tbl-box-{{ num }}">{{ num }}</a>
        {% endfor %}
    </div>
</body>
</html>
"""

DESKTOP_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8"><title>ئۆردەر - {{ selected_table }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background:#03261d; color:#fff; padding:20px; display:flex; flex-direction:column; min-height:100vh; }
        .btn-send { background:#10b981; color:#fff; border:none; padding:12px 24px; border-radius:8px; font-weight:bold; cursor:pointer; }
    </style>
</head>
<body>
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
        <h2>ئۆردەری مێزی: {{ selected_table }}</h2>
        <a href="/desktop/tables" style="color:#fff; text-decoration:none; background:#334155; padding:8px 16px; border-radius:8px;">گەڕانەوە</a>
    </div>
    <div style="flex:1; display:flex; align-items:center; justify-content:center;">
        <div style="text-align:center;">
            <p style="margin-bottom:14px; font-size:16px;">مێزەکە چالاکە و ئامادەیە بۆ وەرگرتنی داواکاری</p>
            <a href="/desktop/tables" class="btn-send">گەڕانەوە بۆ خشتەی مێزەکان</a>
        </div>
    </div>
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
    <meta charset="UTF-8"><title>مێزەکان - مۆبایل</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background:#03261d; color:#fff; padding:12px; }
        .tables-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top:14px; }
        .m-btn { background:#fff; color:#03261d; height:70px; display:flex; align-items:center; justify-content:center; text-decoration:none; font-size:20px; font-weight:bold; border-radius:10px; }
    </style>
</head>
<body>
    <div style="display:flex; justify-content:space-between; align-items:center; background:#064032; padding:12px; border-radius:10px;">
        <span>📱 گارسۆنی مۆبایل</span>
        <a href="/logout" style="color:#ef4444; text-decoration:none;">دەرچوون</a>
    </div>
    <div class="tables-grid">
        {% for num in range(1, 91) %}
            <a href="/mobile/menu?table={{ num }}" class="m-btn">{{ num }}</a>
        {% endfor %}
    </div>
</body>
</html>
"""

CUSTOMER_MENU_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8"><title>مێنیو - {{ table_num }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background:#03261d; color:#fff; padding:16px; }
        .food-box { background:#fff; color:#0f172a; padding:12px; border-radius:10px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center; }
    </style>
</head>
<body>
    <div style="text-align:center; margin-bottom:20px;">
        <h2>✨ شاهور ڕێستۆرانت - مێزی {{ table_num }}</h2>
    </div>
    {% for cat, items in categories.items() %}
        <h3 style="color:#10b981; margin:14px 0 8px;">{{ cat }}</h3>
        {% for it in items %}
        <div class="food-box">
            <span style="font-weight:bold;">{{ it.food_name }}</span>
            <span style="color:#e11d48; font-weight:bold;">{{ "{:,.0f}".format(it.price) }} د.ع</span>
        </div>
        {% endfor %}
    {% endfor %}
</body>
</html>
"""

# ==========================================
# ڕێڕەوەکانی سەرەکی و چوونەژوورەوە
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
            session.clear()
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

            session.clear()
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
            session.clear()
            session.permanent = True
            session['authenticated'] = True
            session['role'] = 'admin'
            session['full_name'] = 'بەڕێوەبەر'
            return redirect(url_for('admin_dashboard'))

        error = 'ناوی بەکارهێنەر یان وشەی نهێنی هەڵەیە!'

    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
def admin_dashboard():
    if not session.get('authenticated') or session.get('role') != 'admin':
        session.clear()
        return redirect(url_for('login'))

    today_sales, today_expense, active_tables, total_workers = 0, 0, 0, 0
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT IFNULL(SUM(quantity * price), 0) AS s FROM froshtn WHERE food_name NOT LIKE '%قاپی نوێ%'")
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
# ئامار و قازانج
# ==========================================
@app.route('/admin/amar')
def admin_amar():
    if not session.get('authenticated') or session.get('role') != 'admin':
        session.clear()
        return redirect(url_for('login'))

    today = datetime.now()
    first_day_of_month = today.replace(day=1).strftime('%Y-%m-%d')
    today_str = today.strftime('%Y-%m-%d')

    start_date = request.args.get('start_date', first_day_of_month)
    end_date = request.args.get('end_date', today_str)

    report_rows = []
    total_sales = 0.0
    total_expenses = 0.0
    total_workers_wage = 0.0
    total_items_count = 0

    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            query_sales = """
                SELECT food_name, quantity, price
                FROM froshtn
                WHERE DATE(created_at) >= %s AND DATE(created_at) <= %s
                  AND food_name NOT LIKE '%%قاپی نوێ%%'
                  AND food_name != ''
                  AND food_name IS NOT NULL;
            """
            cur.execute(query_sales, (start_date, end_date))
            raw_data = cur.fetchall()

            aggregated = {}
            for item in raw_data:
                raw_name = str(item.get('food_name') or '').strip()
                clean_name = re.sub(r'^[+\s]+|[+\s]+$', '', raw_name)
                clean_name = clean_name.replace('+', '').strip()

                qty = int(item.get('quantity') or 1)
                price = float(item.get('price') or 0)

                if clean_name not in aggregated:
                    aggregated[clean_name] = {'food_name': clean_name, 'qty': 0, 'price': price, 'total': 0.0}
                
                aggregated[clean_name]['qty'] += qty
                aggregated[clean_name]['total'] += (qty * price)

            report_rows = sorted(list(aggregated.values()), key=lambda x: x['qty'], reverse=True)
            total_sales = sum(r['total'] for r in report_rows)
            total_items_count = sum(r['qty'] for r in report_rows)

            try:
                cur.execute("SELECT IFNULL(SUM(amount), 0) AS e FROM masrwf WHERE DATE(masrwf_date) >= %s AND DATE(masrwf_date) <= %s", (start_date, end_date))
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
        print("LoadAmarData error:", ex)
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
# مەسرووفات
# ==========================================
@app.route('/admin/masrwf')
def admin_masrwf():
    if not session.get('authenticated') or session.get('role') != 'admin':
        session.clear()
        return redirect(url_for('login'))
    
    from_date = request.args.get('from_date', '').strip()
    to_date = request.args.get('to_date', '').strip()

    rows = []
    tot = 0
    existing_types = ['کڕینی گۆشت', 'کڕینی سەوزە', 'کڕینی برنج', 'خەرجی گشتی', 'خزمەتگوزاری', 'کرێ و پسولە', 'کەلوپەل', 'گاز و نەوت']
    existing_spenders = ['ئادەم', 'کاک شاهۆ', 'ئازاد', 'بەڕێوەبەر', 'کاشێر', 'مەتبەخ']
    
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            query = """
                SELECT 
                    id, 
                    DATE_FORMAT(masrwf_date, '%Y/%m/%d') AS m_date, 
                    DATE_FORMAT(masrwf_date, '%Y-%m-%d') AS m_date_raw, 
                    COALESCE(masrwf_name, '') AS masrwf_name,
                    COALESCE(masrwf_type, '') AS masrwf_type, 
                    COALESCE(spent_by, '') AS spent_by, 
                    COALESCE(amount, 0) AS amount, 
                    COALESCE(notes, '') AS notes 
                FROM masrwf 
            """
            params = []
            if from_date and to_date:
                query += " WHERE DATE(masrwf_date) >= %s AND DATE(masrwf_date) <= %s "
                params.append(from_date)
                params.append(to_date)
            
            query += " ORDER BY id DESC;"
            cur.execute(query, params)
            rows = cur.fetchall() or []
            tot = sum(float(r.get('amount') or 0) for r in rows)

            try:
                cur.execute("SELECT DISTINCT masrwf_type FROM masrwf WHERE masrwf_type IS NOT NULL AND masrwf_type != '';")
                for r in cur.fetchall():
                    val = str(r.get('masrwf_type') or '').strip()
                    if val and val not in existing_types:
                        existing_types.append(val)
            except: pass

            try:
                cur.execute("SELECT DISTINCT spent_by FROM masrwf WHERE spent_by IS NOT NULL AND spent_by != '';")
                for r in cur.fetchall():
                    val = str(r.get('spent_by') or '').strip()
                    if val and val not in existing_spenders:
                        existing_spenders.append(val)
            except: pass

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
    if not session.get('authenticated') or session.get('role') != 'admin':
        return redirect(url_for('login'))
    m_date = request.form.get('masrwf_date')
    m_name = request.form.get('masrwf_name', '').strip()
    m_type = request.form.get('masrwf_type', '').strip()
    spent_by = request.form.get('spent_by', '').strip()
    amt = float(request.form.get('amount', 0))
    notes = request.form.get('notes', '').strip()
    
    if amt > 0:
        conn = None
        try:
            conn = get_db()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO masrwf (masrwf_date, masrwf_name, masrwf_type, spent_by, amount, notes) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (m_date, m_name, m_type, spent_by, amt, notes))
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
    if not session.get('authenticated') or session.get('role') != 'admin':
        return redirect(url_for('login'))
    m_id = int(request.form.get('id', 0))
    m_date = request.form.get('masrwf_date')
    m_name = request.form.get('masrwf_name', '').strip()
    m_type = request.form.get('masrwf_type', '').strip()
    spent_by = request.form.get('spent_by', '').strip()
    amt = float(request.form.get('amount', 0))
    notes = request.form.get('notes', '').strip()
    
    if m_id > 0 and amt > 0:
        conn = None
        try:
            conn = get_db()
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE masrwf 
                    SET masrwf_date = %s, masrwf_name = %s, masrwf_type = %s, spent_by = %s, amount = %s, notes = %s 
                    WHERE id = %s
                """, (m_date, m_name, m_type, spent_by, amt, notes, m_id))
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
    if not session.get('authenticated') or session.get('role') != 'admin':
        return redirect(url_for('login'))
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
# بەشی حیساباتی شاگردەکان
# ==========================================
@app.route('/admin/workers')
def admin_workers():
    if not session.get('authenticated') or session.get('role') != 'admin':
        session.clear()
        return redirect(url_for('login'))

    today_dt = datetime.now()
    first_day_of_month = today_dt.replace(day=1).strftime('%Y-%m-%d')
    today_str = today_dt.strftime('%Y-%m-%d')

    start_date = request.args.get('start_date', first_day_of_month)
    end_date = request.args.get('end_date', today_str)

    rows = []
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
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
            rows = cur.fetchall()
    except Exception as e:
        print("Worker list error:", e)
    finally:
        if conn:
            try: conn.close()
            except: pass
    return render_template_string(WEB_WORKERS_TEMPLATE, wage_rows=rows, start_date=start_date, end_date=end_date, today_date=today_str)

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
    if not session.get('authenticated') or session.get('role') != 'admin': return redirect(url_for('login'))
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

@app.route('/admin/save_attendance', methods=['POST'])
def admin_save_attendance():
    if not session.get('authenticated') or session.get('role') != 'admin': return redirect(url_for('login'))
    w_id = int(request.form.get('worker_id'))
    a_date = request.form.get('att_date')
    status = request.form.get('status', 'هاتوو')
    bonus = float(request.form.get('bonus', 0))
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO worker_attendance (worker_id, date, status, bonus)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE status = %s, bonus = %s
            """, (w_id, a_date, status, bonus, status, bonus))
            conn.commit()
    except Exception as ex:
        print("Save attendance error:", ex)
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

# ==========================================
# بەڕێوەبردنی خواردنەکان (Menu Manager)
# ==========================================
@app.route('/admin/menu_manager')
def admin_menu_manager():
    if not session.get('authenticated') or session.get('role') != 'admin':
        session.clear()
        return redirect(url_for('login'))
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
# بەڕێوەبردنی بەکارهێنەران
# ==========================================
@app.route('/admin/users')
def admin_users():
    if not session.get('authenticated') or session.get('role') != 'admin':
        session.clear()
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
    if not session.get('authenticated') or session.get('role') != 'admin': return redirect(url_for('login'))
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
                    INSERT INTO users (username, password, full_name, role, is_active)
                    VALUES (%s, %s, %s, %s, 1)
                """, (uname, pwd, full_name, role))
                conn.commit()
        except Exception as ex:
            print("Insert user error:", ex)
        finally:
            if conn:
                try: conn.close()
                except: pass
    return redirect(url_for('admin_users'))

@app.route('/admin/toggle_user/<int:uid>')
def admin_toggle_user(uid):
    if not session.get('authenticated') or session.get('role') != 'admin': return redirect(url_for('login'))
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
    if not session.get('authenticated') or session.get('role') != 'admin': return redirect(url_for('login'))
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

# ==========================================
# کاشێر و قاسە
# ==========================================
@app.route('/admin/cashier')
def admin_cashier():
    if not session.get('authenticated') or session.get('role') != 'admin':
        session.clear()
        return redirect(url_for('login'))
    active_tables = []
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT table_cabin FROM froshtn WHERE table_cabin IS NOT NULL AND table_cabin != '' AND table_cabin NOT LIKE '%[%'")
            active_tables = cur.fetchall()
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
    if not session.get('authenticated') or session.get('role') != 'admin':
        session.clear()
        return redirect(url_for('login'))
    rows = []
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT DATE_FORMAT(transaction_time, '%Y-%m-%d %H:%i') AS transaction_time, place_id, amount FROM qasa ORDER BY transaction_time DESC")
            rows = cur.fetchall()
    except Exception as ex:
        print("Qasa error:", ex)
    finally:
        if conn:
            try: conn.close()
            except: pass
    return render_template_string(WEB_QASA_TEMPLATE, qasa_rows=rows)

# ==========================================
# ئایپاد، مۆبایل و بینینی موشتەری (چارەسەری دووبارەبوونەوەی خواردن لە سەفەری)
# ==========================================
@app.route('/desktop/tables')
def desktop_tables():
    if not session.get('authenticated'): return redirect(url_for('login'))
    return render_template_string(DESKTOP_TABLES_TEMPLATE)

@app.route('/desktop')
def desktop_menu():
    if not session.get('authenticated'): return redirect(url_for('login'))
    tbl = request.args.get('table', '1')
    return render_template_string(DESKTOP_TEMPLATE, selected_table=tbl)

@app.route('/mobile/tables')
def mobile_waiter_tables():
    if not session.get('authenticated'): return redirect(url_for('login'))
    return render_template_string(MOBILE_TABLES_TEMPLATE)

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
    except: pass
    finally:
        if conn:
            try: conn.close()
            except: pass
    return render_template_string(CUSTOMER_MENU_TEMPLATE, table_num=tbl, categories=categories, allow_ordering=True)

@app.route('/table/<path:table_num>')
def customer_table_view(table_num):
    categories = {}
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT food_name, price, category, image_path FROM nse WHERE food_name != ''")
            for f in cur.fetchall():
                c = f['category'].strip() if f.get('category') else 'گشتی'
                categories.setdefault(c, []).append(f)
    except: pass
    finally:
        if conn:
            try: conn.close()
            except: pass
    return render_template_string(CUSTOMER_MENU_TEMPLATE, table_num=table_num, categories=categories, allow_ordering=True)

@app.route('/qr_manager')
def qr_manager():
    if not session.get('authenticated'): return redirect(url_for('login'))
    return render_template_string(QR_MANAGER_TEMPLATE, base_url=request.host_url.rstrip('/'))

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

                # پشکنین بۆ ئەگەر خواردنەکە پێشتر لەسەر ئەم مێزە هەبێت، تەنها بڕەکەی بۆ زیاد بکە با دووبارە نەبێتەوە
                cur.execute("SELECT order_id, quantity FROM froshtn WHERE table_cabin = %s AND food_name = %s", (tbl, fname))
                existing = cur.fetchone()
                if existing:
                    new_qty = existing['quantity'] + qty
                    cur.execute("UPDATE froshtn SET quantity = %s WHERE order_id = %s", (new_qty, existing['order_id']))
                else:
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
