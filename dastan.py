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
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db():
    return pymysql.connect(**DB_CONFIG)

def normalize_digits(text):
    if not text:
        return ""
    text = str(text).strip()
    return text.translate(str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789'))

def ensure_all_tables():
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
        conn.close()
    except Exception as ex:
        print("Setup tables error:", ex)

ensure_all_tables()

@app.before_request
def enforce_security():
    exempt_endpoints = ['login', 'customer_table_view', 'save_customer_order', 'static', 'index']
    if request.endpoint in exempt_endpoints:
        return

    is_api = request.path.startswith(('/get_', '/save_', '/clear_', '/change_', '/set_', '/toggle_', '/api_'))
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
                <div class="module-desc">ڕاپۆرتی گشتی فرۆش لە froshtn، کۆی مەسرووفات و کرێی شاگرد، و قازانجی صافی.</div>
            </a>

            <a href="/admin/cashier" class="module-card" style="border: 2px solid #10b981;">
                <div class="module-top"><div class="module-icon">🛎️</div><span class="module-badge">کاشێر</span></div>
                <div class="module-title">کاشێر و واصڵکردن (پرێنتەری کاشێر)</div>
                <div class="module-desc">شاشەی مێزە داواکراوەکان بە شێوازی سی شارپ، دوگمەی +٥٠٠ و -٥٠٠، و چاپی وەسڵی ٨٠مم.</div>
            </a>

            <a href="/admin/users" class="module-card">
                <div class="module-top"><div class="module-icon">🔐</div><span class="module-badge">بەکارهێنەر</span></div>
                <div class="module-title">بەکارهێنەران و دەسەڵاتەکان</div>
                <div class="module-desc">دانانی ناوی بەکارهێنەر و وشەی نهێنی، دەستکاری، بلۆککردن، سڕینەوە و دیاریکردنی ڕۆڵ.</div>
            </a>

            <a href="/admin/qasa" class="module-card">
                <div class="module-top"><div class="module-icon">💵</div><span class="module-badge">قاسە</span></div>
                <div class="module-title">قاسەی فرۆشتن (٢٤ کاتژمێر)</div>
                <div class="module-desc">بینینی تەواوی پسولە واصڵکراوەکان، کۆی داهات، داشکاندن و کاتی وەسڵەکان.</div>
            </a>

            <a href="/admin/masrwf" class="module-card">
                <div class="module-top"><div class="module-icon">💸</div><span class="module-badge">مەسرووف</span></div>
                <div class="module-title">مەسرووفات و خەرجی</div>
                <div class="module-desc">تۆمارکردن بە کۆمبۆبۆکس، دەستکاری، سڕینەوە، و فلتەری بەروارەکان.</div>
            </a>

            <a href="/admin/workers" class="module-card">
                <div class="module-top"><div class="module-icon">👥</div><span class="module-badge">شاگرد</span></div>
                <div class="module-title">حیساباتی شاگردەکان</div>
                <div class="module-desc">تۆماری ئامادەبوون (هاتوو/نەهاتوو/مۆڵەت)، بەخشش، و ڕاپۆرتی حیساباتی شایستە.</div>
            </a>

            <a href="/admin/menu_manager" class="module-card">
                <div class="module-top"><div class="module-icon">📖</div><span class="module-badge">مێنۆ</span></div>
                <div class="module-title">بەڕێوەبردنی خواردنەکان (ئیدیت و ئەپلۆد)</div>
                <div class="module-desc">زیادکردنی خواردنی نوێ، کۆمبۆبۆکسی پۆلێن، و ئەپلۆدکردنی وێنە ڕاستەوخۆ.</div>
            </a>

            <a href="/desktop/tables" class="module-card">
                <div class="module-top"><div class="module-icon">🍽️</div><span class="module-badge">ئایپاد</span></div>
                <div class="module-title">مێزەکان و گارسۆن (ئایپاد)</div>
                <div class="module-desc">چوونە ناو شاشەی مێزەکان و ئۆردەرکردنی خواردن بۆ ئایپاد و دیسکتۆپ.</div>
            </a>

            <a href="/mobile/tables" class="module-card">
                <div class="module-top"><div class="module-icon">📱</div><span class="module-badge">مۆبایل</span></div>
                <div class="module-title">مێزەکانی مۆبایل</div>
                <div class="module-desc">شاشەی ئۆردەرکردنی خواردن تایبەت بە قەبارە و شاشەی مۆبایل.</div>
            </a>

            <a href="/qr_manager" class="module-card">
                <div class="module-top"><div class="module-icon">🖨️</div><span class="module-badge">QR</span></div>
                <div class="module-title">بەڕێوەبردنی QR مێزەکان</div>
                <div class="module-desc">چاپی ٩٠ کیوئاڕ کۆدەکە لەگەڵ دیاریکردنی مۆڵەت بۆ موشتەری.</div>
            </a>
        </div>
    </main>
</body>
</html>
"""

# ==========================================
# پەڕەی ئامار و قازانج (WEB_AMAR_TEMPLATE)
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

        .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-bottom: 22px; }
        .sum-card { background: #1e293b; border: 1.5px solid #334155; border-radius: 14px; padding: 16px; text-align: center; }
        .sum-label { font-size: 12.5px; color: #94a3b8; font-weight: 700; margin-bottom: 6px; }
        .sum-val { font-size: 20px; font-weight: 800; }

        .table-responsive { overflow-x: auto; background: #1e293b; border: 1px solid #334155; border-radius: 12px; }
        table { width: 100%; border-collapse: collapse; text-align: center; }
        th { background: #d97706; padding: 12px; color: #fff; font-size: 13px; font-weight: 800; border-bottom: 1px solid #334155; }
        td { padding: 10px; border-bottom: 1px solid #334155; font-size: 13px; }
        tr:nth-child(even) { background: #162032; }

        @media print {
            body { background: #fff !important; color: #000 !important; padding: 0 !important; }
            .top-bar, .filter-card, .btn-print, .btn-dash { display: none !important; }
            .sum-card { border: 1px solid #000 !important; background: #fff !important; color: #000 !important; }
            .sum-val { color: #000 !important; }
            table { border: 1px solid #000 !important; }
            th { background: #e2e8f0 !important; color: #000 !important; border: 1px solid #000 !important; }
            td { color: #000 !important; border: 1px solid #000 !important; }
            tr:nth-child(even) { background: #fff !important; }
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
            <div class="sum-label">💸 کۆی مەسرووفات</div>
            <div class="sum-val" style="color: #ef4444;">{{ "{:,.0f}".format(total_expenses) }} د.ع</div>
        </div>
        <div class="sum-card">
            <div class="sum-label">👥 کرێی شاگردەکان</div>
            <div class="sum-val" style="color: #f59e0b;">{{ "{:,.0f}".format(total_workers_wage) }} د.ع</div>
        </div>
        <div class="sum-card">
            <div class="sum-label">✨ قازانجی سافی</div>
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
                    <th>ڕیزبەندی</th>
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
</body>
</html>
"""

# ==========================================
# تەمپلیتی بەڕێوەبردنی بەکارهێنەران
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
        .user-form-card input:focus, .user-form-card select:focus { border-color: #10b981; }
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
        .btn-edit { background: #3b82f6; color: #fff; }
        .btn-del { background: #ef4444; color: #fff; }

        .modal-edit { position: fixed; top:0; left:0; right:0; bottom:0; background: rgba(0,0,0,0.75); display: none; align-items: center; justify-content: center; z-index: 2000; padding: 16px; }
        .modal-edit-box { background: #064032; border: 2px solid #0b5e4a; border-radius: 16px; width: 100%; max-width: 440px; padding: 22px; color: #fff; }
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
                    <input type="text" name="username" required placeholder="یوسەر بۆ نموونە: dastan">
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
                    <th>دۆخ (Status)</th>
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
                    <td>
                        {% if u.role == 'Manager' %}👑 بەڕێوەبەر
                        {% elif u.role == 'Waiter' %}🍽️ ئایپاد
                        {% elif u.role == 'Mobile_Waiter' %}📱 مۆبایل
                        {% elif u.role == 'Cashier' %}💵 کاشێر
                        {% else %}{{ u.role }}{% endif %}
                    </td>
                    <td>
                        <span class="status-badge {{ 'status-active' if u.is_active else 'status-blocked' }}">
                            {{ 'چالاکە' if u.is_active else 'بلۆککراوە' }}
                        </span>
                    </td>
                    <td>
                        <a href="/admin/toggle_user/{{ u.id }}" class="action-btn btn-toggle">
                            {{ '⛔ بلۆککردن' if u.is_active else '✅ کاراکردن' }}
                        </a>
                        <button type="button" class="action-btn btn-edit" onclick="openUserEdit({{ u.id }}, '{{ u.username }}', '{{ u.password }}', '{{ u.full_name }}', '{{ u.role }}')">✏️ دەستکاری</button>
                        {% if u.username != 'admin' %}
                        <a href="/admin/delete_user/{{ u.id }}" class="action-btn btn-del" onclick="return confirm('ئایا دڵنیایت لە سڕینەوەی ئەم بەکارهێنەرە؟')">🗑️ سڕینەوە</a>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <div class="modal-edit" id="userEditModal">
        <div class="modal-edit-box">
            <h3 style="color:#10b981; margin-bottom:14px; text-align:center;">✏️ دەستکاریکردنی بەکارهێنەر</h3>
            <form id="userEditForm" method="POST" action="">
                <label style="font-size:12px; color:#a7f3d0;">ناوی بەکارهێنەر (Username):</label>
                <input type="text" id="edit_username" name="username" style="width:100%; padding:9px; margin-bottom:10px; border-radius:8px; border:1px solid #0b5e4a; background:#03261d; color:#fff;" required>
                
                <label style="font-size:12px; color:#a7f3d0;">وشەی نهێنی (Password):</label>
                <input type="text" id="edit_password" name="password" style="width:100%; padding:9px; margin-bottom:10px; border-radius:8px; border:1px solid #0b5e4a; background:#03261d; color:#fff;" required>
                
                <label style="font-size:12px; color:#a7f3d0;">ناوی تەواو (Full Name):</label>
                <input type="text" id="edit_fullname" name="full_name" style="width:100%; padding:9px; margin-bottom:10px; border-radius:8px; border:1px solid #0b5e4a; background:#03261d; color:#fff;">
                
                <label style="font-size:12px; color:#a7f3d0;">ڕۆڵ لە سیستەم:</label>
                <select id="edit_role" name="role" style="width:100%; padding:9px; margin-bottom:14px; border-radius:8px; border:1px solid #0b5e4a; background:#03261d; color:#fff;">
                    <option value="Manager">👑 بەڕێوەبەر (Manager)</option>
                    <option value="Waiter">🍽️ گارسۆنی ئایپاد (Waiter)</option>
                    <option value="Mobile_Waiter">📱 گارسۆنی مۆبایل (Mobile Waiter)</option>
                    <option value="Cashier">💵 کاشێر (Cashier)</option>
                </select>
                
                <button type="submit" class="btn-save-u">💾 پاشەکەوتکردنی گۆڕانکاری</button>
                <button type="button" onclick="closeUserEdit()" style="background:none; border:none; color:#94a3b8; width:100%; margin-top:10px; cursor:pointer;">داخستن</button>
            </form>
        </div>
    </div>

    <script>
        function openUserEdit(id, user, pass, full, role) {
            document.getElementById('userEditForm').action = '/admin/edit_user/' + id;
            document.getElementById('edit_username').value = user;
            document.getElementById('edit_password').value = pass;
            document.getElementById('edit_fullname').value = full;
            document.getElementById('edit_role').value = role;
            document.getElementById('userEditModal').style.display = 'flex';
        }
        function closeUserEdit() {
            document.getElementById('userEditModal').style.display = 'none';
        }
    </script>
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

        setInterval(() => {
            if (document.getElementById('checkoutModal').style.display !== 'flex' && document.getElementById('txtSearch').value.trim() === '') {
                fetch(window.location.href)
                    .then(r => r.text())
                    .then(html => {
                        let parser = new DOMParser();
                        let doc = parser.parseFromString(html, 'text/html');
                        let newGrid = doc.getElementById('tablesGrid');
                        let newBadge = doc.getElementById('lblActiveCount');
                        if (newGrid && newBadge) {
                            document.getElementById('tablesGrid').innerHTML = newGrid.innerHTML;
                            document.getElementById('lblActiveCount').innerText = newBadge.innerText;
                        }
                    });
            }
        }, 4000);
    </script>
</body>
</html>
"""

# ==========================================
# پەڕەی مێنۆی دیسکتۆپ و ئایپاد (DESKTOP_TEMPLATE)
# ==========================================
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
    </style>
</head>
<body>
    <div id="toastMsg">✅ داواکارییەکە بۆ مەتبەخ نێردرا</div>
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
        window.onload = function() { fetchTableOrders(); };
    </script>
</body>
</html>
"""

# ==========================================
# پەڕەی مێزەکانی مۆبایل (MOBILE_TABLES_TEMPLATE)
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

# ==========================================
# پەڕەی مێنیوی موشتەری و مۆبایل (CUSTOMER_MENU_TEMPLATE)
# ==========================================
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
# پەڕەی مێزەکان و مێنۆکان لە پایسۆن
# ==========================================
@app.route('/desktop/tables')
def desktop_tables():
    if not session.get('authenticated'): return redirect(url_for('login'))
    active_takeaways = []
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT table_cabin FROM froshtn WHERE table_cabin LIKE 'سەفەری%'")
            active_takeaways = [r['table_cabin'] for r in cur.fetchall()]
        conn.close()
    except Exception as ex:
        print("Desktop tables error:", ex)
    return render_template_string(DESKTOP_TABLES_TEMPLATE, active_takeaways=active_takeaways)

@app.route('/desktop')
def desktop_menu():
    if not session.get('authenticated'): return redirect(url_for('login'))
    tbl = request.args.get('table')
    if not tbl: return redirect(url_for('desktop_tables'))
    categories = {}
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT food_name, price, category, image_path FROM nse WHERE food_name != ''")
            for f in cur.fetchall():
                c = f['category'].strip() if f.get('category') else 'گشتی'
                categories.setdefault(c, []).append(f)
        conn.close()
    except Exception as ex:
        print("Desktop menu error:", ex)
    return render_template_string(DESKTOP_TEMPLATE, categories=categories, selected_table=tbl)

@app.route('/mobile/tables')
def mobile_waiter_tables():
    if not session.get('authenticated'): return redirect(url_for('login'))
    active_takeaways = []
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT table_cabin FROM froshtn WHERE table_cabin LIKE 'سەفەری%'")
            active_takeaways = [r['table_cabin'] for r in cur.fetchall()]
        conn.close()
    except Exception as ex:
        print("Mobile tables error:", ex)
    return render_template_string(MOBILE_TABLES_TEMPLATE, active_takeaways=active_takeaways)

@app.route('/mobile/menu')
def mobile_waiter_menu():
    if not session.get('authenticated'): return redirect(url_for('login'))
    tbl = request.args.get('table', '1')
    categories = {}
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT food_name, price, category, image_path FROM nse WHERE food_name != ''")
            for f in cur.fetchall():
                c = f['category'].strip() if f.get('category') else 'گشتی'
                categories.setdefault(c, []).append(f)
        conn.close()
    except Exception as ex:
        print("Mobile menu error:", ex)
    return render_template_string(CUSTOMER_MENU_TEMPLATE, table_num=tbl, categories=categories, allow_ordering=True)

@app.route('/table/<path:table_num>')
def customer_table_view(table_num):
    allow_ordering = True
    categories = {}
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
        conn.close()
    except Exception as ex:
        print("Customer table view error:", ex)

    return render_template_string(CUSTOMER_MENU_TEMPLATE, table_num=table_num, categories=categories, allow_ordering=allow_ordering)

@app.route('/qr_manager')
def qr_manager():
    if not session.get('authenticated'): return redirect(url_for('login'))
    return render_template_string(QR_MANAGER_TEMPLATE, base_url=request.host_url.rstrip('/'))

@app.route('/save_customer_order', methods=['POST'])
def save_customer_order():
    data = request.get_json()
    tbl = str(data.get('table_number'))
    items = data.get('cart_items', [])
    if not items:
        return jsonify({'status': 'error', 'message': 'هیچ خواردنێک دیاری نەکراوە!'})

    conn = get_db()
    try:
        with conn.cursor() as cur:
            if tbl.isdigit():
                cur.execute("SELECT allow_ordering FROM table_permissions WHERE table_number = %s", (int(tbl),))
                p_row = cur.fetchone()
                if p_row and not p_row['allow_ordering'] and session.get('role') not in ['mobile_waiter', 'admin']:
                    conn.close()
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
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as ex:
        if conn: conn.close()
        return jsonify({'status': 'error', 'message': str(ex)})

@app.route('/save_cart_order', methods=['POST'])
def save_cart_order():
    data = request.get_json()
    tbl = str(data.get('table_number'))
    cart = data.get('cart_items', [])
    orig = data.get('original_items', [])

    def make_map(its):
        return {it['food_name']: {'qty': int(it['qty']), 'price': float(it['price']), 'cat': it.get('cat', 'گشتی')} for it in its if not it.get('is_divider')}

    old_map = make_map(orig)
    new_map = make_map(cart)
    conn = get_db()
    try:
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
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as ex:
        if conn: conn.close()
        return jsonify({'status': 'error', 'message': str(ex)})

@app.route('/get_table_orders/<path:table_num>')
def get_table_orders(table_num):
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT food_name, price, quantity, category FROM froshtn WHERE table_cabin = %s", (str(table_num),))
            orders = cur.fetchall()
        conn.close()
        return jsonify(orders)
    except: return jsonify([])

@app.route('/clear_table_orders', methods=['POST'])
def clear_table_orders():
    tbl = str(request.get_json().get('table_number'))
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM froshtn WHERE table_cabin = %s OR table_cabin LIKE %s", (tbl, f"{tbl} [%"))
        conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/get_active_tables')
def get_active_tables():
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT table_cabin FROM froshtn WHERE table_cabin NOT LIKE '%%[%%' AND table_cabin != ''")
            rows = cur.fetchall()
        conn.close()
        return jsonify([str(r['table_cabin']).strip() for r in rows])
    except: return jsonify([])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
