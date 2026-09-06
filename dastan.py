from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session
from datetime import timedelta, datetime
import pymysql

app = Flask(__name__)
app.secret_key = 'shahoor_all_in_one_pos_2026'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)

DB_CONFIG = {
    'host': 'sakura.proxy.rlwy.net',
    'port': 31707,
    'user': 'root',
    'password': 'HITVDFaMFehpQFmWrZlnaTKtavNtBZyw',
    'database': 'nrx',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db():
    return pymysql.connect(**DB_CONFIG)

def normalize_digits(text):
    if not text:
        return ""
    text = str(text).strip()
    eastern_digits = '٠١٢٣٤٥٦٧٨٩'
    western_digits = '0123456789'
    trans_table = str.maketrans(eastern_digits, western_digits)
    return text.translate(trans_table)

def ensure_all_tables():
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS table_permissions (
                    table_number INT PRIMARY KEY,
                    allow_ordering TINYINT DEFAULT 0
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
                    place_id VARCHAR(50),
                    amount DECIMAL(18, 0),
                    discount DECIMAL(18, 0) DEFAULT 0
                );
            """)
        conn.commit()
        conn.close()
    except Exception as ex:
        print("Setup tables error:", ex)

ensure_all_tables()

# 🛡️ پاراستنی ئاسایش: هەر کاتێک ئینتەر لە ناونیشانی سێرچ بکرێت دەچێتەوە لۆگین
@app.before_request
def enforce_security():
    exempt_endpoints = ['login', 'customer_table_view', 'save_customer_order', 'static']
    if request.endpoint in exempt_endpoints:
        return

    is_api = request.path.startswith(('/get_', '/save_', '/clear_', '/change_', '/set_', '/toggle_', '/api_'))
    if is_api:
        return

    referer = request.headers.get('Referer')
    if not referer and request.endpoint != 'login':
        session.clear()
        return redirect(url_for('login'))

    if request.path.startswith('/admin') and session.get('role') != 'admin':
        return redirect(url_for('login'))

# ==========================================
# دیزاینی پەڕەی چوونەژوورەوە
# ==========================================
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>چوونەژوورەوە - شاهور ڕێستۆرانت</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background: #03261d; color: #f8fafc; display: flex; align-items: center; justify-content: center; min-height: 100vh; padding: 16px; }
        .login-card { background: #064032; border: 1.5px solid #0b5e4a; padding: 36px 28px; border-radius: 20px; width: 100%; max-width: 400px; text-align: center; box-shadow: 0 15px 35px rgba(0,0,0,0.5); }
        .brand-title { color: #10b981; font-size: 26px; font-weight: 800; margin-bottom: 6px; }
        .brand-sub { color: #a7f3d0; font-size: 13px; margin-bottom: 24px; }
        .pin-input { width: 100%; padding: 14px; background: #03261d; border: 2px solid #0b5e4a; border-radius: 12px; color: #10b981; font-size: 24px; text-align: center; font-weight: 800; letter-spacing: 6px; outline: none; margin-bottom: 20px; transition: border-color 0.2s; }
        .pin-input:focus { border-color: #10b981; }
        .btn-submit { width: 100%; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #ffffff; border: none; padding: 14px; border-radius: 12px; font-size: 16px; font-weight: 800; cursor: pointer; box-shadow: 0 4px 15px rgba(16,185,129,0.3); }
        .error-msg { color: #ef4444; font-size: 13px; margin-top: 14px; font-weight: 700; }
        .roles-hint { display: flex; justify-content: space-around; margin-top: 24px; border-top: 1px solid #0b5e4a; padding-top: 14px; color: #94a3b8; font-size: 11px; }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="brand-title">✨ شاهور ڕێستۆرانت</div>
        <div class="brand-sub">تکایە وشەی نهێنی بنووسە بۆ چوونەژوورەوە</div>
        <form method="POST" action="/login">
            <input type="password" name="pin" class="pin-input" placeholder="••••" inputmode="numeric" required autofocus>
            <button type="submit" class="btn-submit">چوونەژوورەوە ➔</button>
        </form>
        {% if error %}<div class="error-msg">{{ error }}</div>{% endif %}
        <div class="roles-hint">
            <span>👑 99: بەڕێوەبەر</span>
            <span>🍽️ 22: گارسۆن</span>
        </div>
    </div>
</body>
</html>
"""

# ==========================================
# داشبۆردی سەرەکی بەڕێوەبەر
# ==========================================
ADMIN_DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>داشبۆردی بەڕێوەبەر - شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background-color: #03261d; color: #ffffff; min-height: 100vh; display: flex; flex-direction: column; }
        .admin-nav { background: #064032; padding: 14px 28px; display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #0b5e4a; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
        .admin-brand { font-size: 20px; font-weight: 800; color: #10b981; }
        .admin-user-tag { background: #03261d; border: 1px solid #10b981; color: #10b981; padding: 5px 14px; border-radius: 20px; font-size: 13px; font-weight: 700; }
        .btn-exit { background: #ef4444; color: #fff; text-decoration: none; padding: 8px 18px; border-radius: 8px; font-weight: 800; font-size: 13px; }
        .admin-content { flex: 1; padding: 24px; max-width: 1400px; margin: 0 auto; width: 100%; }
        .stats-cards-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 28px; }
        .stat-card { background: #064032; border: 1.5px solid #0b5e4a; border-radius: 16px; padding: 20px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
        .stat-info { display: flex; flex-direction: column; gap: 6px; }
        .stat-label { font-size: 13px; font-weight: 700; color: #a7f3d0; }
        .stat-value { font-size: 22px; font-weight: 800; color: #ffffff; }
        .section-header { font-size: 18px; font-weight: 800; color: #10b981; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid #0b5e4a; padding-bottom: 8px; }
        .dashboard-modules-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 18px; }
        .module-card { background: #ffffff; border-radius: 18px; padding: 22px; text-decoration: none; color: #0f172a; display: flex; flex-direction: column; gap: 10px; transition: transform 0.2s, box-shadow 0.2s; box-shadow: 0 6px 18px rgba(0,0,0,0.25); }
        .module-card:hover { transform: translateY(-4px); box-shadow: 0 10px 25px rgba(0,0,0,0.35); }
        .module-top { display: flex; align-items: center; justify-content: space-between; }
        .module-icon { font-size: 32px; background: #f1f5f9; width: 56px; height: 56px; display: flex; align-items: center; justify-content: center; border-radius: 14px; }
        .module-badge { background: #10b981; color: #03261d; font-size: 11px; font-weight: 800; padding: 4px 10px; border-radius: 10px; }
        .module-title { font-size: 17px; font-weight: 800; margin-top: 4px; }
        .module-desc { font-size: 12.5px; color: #64748b; font-weight: 600; line-height: 1.4; }
    </style>
</head>
<body>
    <header class="admin-nav">
        <div class="admin-brand">✨ شاهور ڕێستۆرانت - پانێڵی بەڕێوەبەر</div>
        <div style="display: flex; align-items: center; gap: 12px;">
            <span class="admin-user-tag">👑 مۆڵەت: بەڕێوەبەر</span>
            <a href="/logout" class="btn-exit">✕ دەرچوون</a>
        </div>
    </header>

    <main class="admin-content">
        <div class="stats-cards-grid">
            <div class="stat-card">
                <div class="stat-info">
                    <span class="stat-label">💰 فرۆشی ٢٤ کاتژمێری ڕابردوو</span>
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
                    <span class="stat-label">🛎️ مێزە کراوەکانی ئێستا</span>
                    <span class="stat-value" style="color: #f59e0b;">{{ active_tables_count }} مێز</span>
                </div>
                <div style="font-size: 36px;">🍽️</div>
            </div>
            <div class="stat-card">
                <div class="stat-info">
                    <span class="stat-label">👥 کۆی شاگردەکان</span>
                    <span class="stat-value" style="color: #38bdf8;">{{ total_workers }} شاگرد</span>
                </div>
                <div style="font-size: 36px;">👤</div>
            </div>
        </div>

        <div class="section-header">📁 بەشە کارگێڕییەکان و سیستەمی کاشێر</div>
        <div class="dashboard-modules-grid">
            <a href="/admin/cashier" class="module-card">
                <div class="module-top"><div class="module-icon">🛎️</div><span class="module-badge">POS</span></div>
                <div class="module-title">کاشێر و واصڵکردن</div>
                <div class="module-desc">بینینی مێزە داواکراوەکان بە باگڕاوەندی زەرد، دوگمەی +٥٠٠ و -٥٠٠ و واصڵکردن بۆ قاسە.</div>
            </a>

            <a href="/admin/qasa" class="module-card">
                <div class="module-top"><div class="module-icon">💵</div><span class="module-badge">قاسە</span></div>
                <div class="module-title">قاسەی فرۆشتن (٢٤ کاتژمێر)</div>
                <div class="module-desc">بینینی تەواوی پسولە واصڵکراوەکان، کۆی داهات، داشکاندن و کاتی وەسڵەکان.</div>
            </a>

            <a href="/admin/masrwf" class="module-card">
                <div class="module-top"><div class="module-icon">💸</div><span class="module-badge">مەسرووف</span></div>
                <div class="module-title">مەسرووفات و خەرجی</div>
                <div class="module-desc">تۆمارکردن، دەستکاری، سڕینەوە، فلتەری بەروار و دیاریکردنی کەسی خەرجکار.</div>
            </a>

            <a href="/admin/workers" class="module-card">
                <div class="module-top"><div class="module-icon">👥</div><span class="module-badge">شاگرد</span></div>
                <div class="module-title">حیساباتی شاگردەکان</div>
                <div class="module-desc">تۆماری ئامادەبوون (هاتوو/نەهاتوو/مۆڵەت)، بەخشش، و ڕاپۆرتی حیساباتی شایستە.</div>
            </a>

            <a href="/admin/menu_manager" class="module-card">
                <div class="module-top"><div class="module-icon">📖</div><span class="module-badge">مێنۆ</span></div>
                <div class="module-title">بەڕێوەبردنی خواردنەکان</div>
                <div class="module-desc">زیادکردنی خواردنی نوێ، گۆڕینی نرخەکان، دەستکاریکردنی وێنە و بەشەکان.</div>
            </a>

            <a href="/desktop/tables" class="module-card">
                <div class="module-top"><div class="module-icon">🍽️</div><span class="module-badge">ئۆردەر</span></div>
                <div class="module-title">مێزەکان و گارسۆن</div>
                <div class="module-desc">چوونە ناو پەڕەی مێزەکان بۆ گرتنی داواکاری و ناردنی خواردن بۆ پرێنتەری مەتبەخ.</div>
            </a>

            <a href="/qr_manager" class="module-card">
                <div class="module-top"><div class="module-icon">📱</div><span class="module-badge">QR</span></div>
                <div class="module-title">بەڕێوەبردنی QR و مێزەکان</div>
                <div class="module-desc">چاپی ٩٠ کیوئاڕ کۆدەکە لەگەڵ دیاریکردنی دەسەڵاتی ئۆردەرکردن (تەنها بینین / ڕێگەپێدراو).</div>
            </a>
        </div>
    </main>
</body>
</html>
"""

# ==========================================
# پەڕەی بەڕێوەبردنی QR (دەسەڵاتی بینین و ئۆردەر)
# ==========================================
QR_MANAGER_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>بەڕێوەبردنی کیوئاڕ کۆدی مێزەکان</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background-color: #0b0f19; color: #f8fafc; padding: 20px; }
        .top-nav { display: flex; justify-content: space-between; align-items: center; background: #151d30; padding: 14px 20px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 20px; }
        .top-title { font-size: 18px; font-weight: 800; color: #f59e0b; }
        .nav-btns { display: flex; gap: 10px; }
        .btn { background: #3b82f6; color: #fff; border: none; padding: 8px 16px; border-radius: 8px; font-weight: 700; text-decoration: none; cursor: pointer; font-size: 13px; }
        .btn-green { background: #10b981; }
        .btn-red { background: #ef4444; }
        .btn-gold { background: #f59e0b; color: #0b0f19; font-weight: 800; }
        
        .tables-perm-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
        .table-perm-card { background: #151d30; border: 1.5px solid #334155; border-radius: 10px; padding: 12px; display: flex; flex-direction: column; gap: 8px; }
        .card-header { display: flex; justify-content: space-between; align-items: center; }
        .table-name { font-size: 16px; font-weight: 800; color: #ffffff; }
        .qr-thumb { width: 100%; text-align: center; padding: 8px; background: #ffffff; border-radius: 6px; }
        .qr-thumb img { width: 130px; height: 130px; }
        .status-badge { font-size: 11px; font-weight: 800; padding: 3px 8px; border-radius: 6px; text-align: center; }
        .status-view { background: #334155; color: #94a3b8; }
        .status-order { background: #059669; color: #ffffff; }
        
        @media print {
            body { background: #ffffff !important; color: #000000 !important; padding: 0 !important; }
            .top-nav { display: none !important; }
            .tables-perm-grid { display: grid; grid-template-columns: repeat(3, 1fr) !important; gap: 15px !important; }
            .table-perm-card { background: #ffffff !important; border: 1.5px solid #000 !important; break-inside: avoid; }
            .table-name { color: #000 !important; font-size: 18px !important; text-align: center !important; }
            .btn-toggle { display: none !important; }
            .status-badge { display: none !important; }
        }
    </style>
</head>
<body>
    <div class="top-nav">
        <div class="top-title">📱 بەڕێوەبردنی دەسەڵات و کیوئاڕ کۆدەکان (QR)</div>
        <div class="nav-btns">
            <button type="button" class="btn btn-gold" onclick="window.print()">🖨️ چاپی هەموو QR کۆدەکان</button>
            <button type="button" class="btn btn-green" onclick="setAllPermissions(1)">هەمووی بکرێت بە ئۆردەر</button>
            <button type="button" class="btn btn-red" onclick="setAllPermissions(0)">هەمووی تەنها بینین</button>
            <a href="/admin" class="btn">⬅️ داشبۆرد</a>
        </div>
    </div>

    <div class="tables-perm-grid">
        {% for num in range(1, 91) %}
        {% set is_allowed = perm_dict.get(num, 0) == 1 %}
        <div class="table-perm-card" id="perm-card-{{ num }}">
            <div class="card-header">
                <span class="table-name">مێزی {{ num }}</span>
                <span class="status-badge {{ 'status-order' if is_allowed else 'status-view' }}" id="status-badge-{{ num }}">
                    {{ 'دەتوانێت ئۆردەر بکات' if is_allowed else 'تەنها بینین' }}
                </span>
            </div>
            <div class="qr-thumb">
                <img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={{ base_url }}/table/{{ num }}" alt="QR مێزی {{ num }}">
                <div style="color:#000; font-size:11px; font-weight:800; margin-top:4px;">مێزی {{ num }}</div>
            </div>
            <button type="button" class="btn {{ 'btn-red' if is_allowed else 'btn-green' }} btn-toggle" id="btn-toggle-{{ num }}" onclick="togglePermission({{ num }})">
                {{ 'گۆڕین بۆ تەنها بینین' if is_allowed else 'ڕێگەدان بە ئۆردەر' }}
            </button>
        </div>
        {% endfor %}
    </div>

    <script>
        function togglePermission(tableNum) {
            fetch('/toggle_table_permission', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ table_number: tableNum })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    const badge = document.getElementById('status-badge-' + tableNum);
                    const btn = document.getElementById('btn-toggle-' + tableNum);
                    if (data.allow_ordering) {
                        badge.className = 'status-badge status-order';
                        badge.innerText = 'دەتوانێت ئۆردەر بکات';
                        btn.className = 'btn btn-red btn-toggle';
                        btn.innerText = 'گۆڕین بۆ تەنها بینین';
                    } else {
                        badge.className = 'status-badge status-view';
                        badge.innerText = 'تەنها بینین';
                        btn.className = 'btn btn-green btn-toggle';
                        btn.innerText = 'ڕێگەدان بە ئۆردەر';
                    }
                }
            });
        }

        function setAllPermissions(allow) {
            if (confirm("ئایا دڵنیایت لە گۆڕینی دەسەڵاتی هەموو مێزەکان؟")) {
                fetch('/set_all_table_permissions', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ allow_ordering: allow })
                })
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') location.reload();
                });
            }
        }
    </script>
</body>
</html>
"""

# ==========================================
# بەشی کاشێر (پاشبنەمای زەرد)
# ==========================================
WEB_CASHIER_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>کاشێر - شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background: #FEF3C7; color: #0f172a; min-height: 100vh; display: flex; flex-direction: column; }
        .top-bar { background: #0f172a; color: #fff; padding: 12px 24px; display: flex; justify-content: space-between; align-items: center; }
        .title { color: #f59e0b; font-size: 18px; font-weight: 800; }
        .btn-back { background: #334155; color: #fff; text-decoration: none; padding: 6px 14px; border-radius: 8px; font-weight: 700; }
        .tables-container { padding: 24px; display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 16px; }
        .table-card { background: #10b981; border: 2px solid #047857; color: #fff; border-radius: 12px; height: 160px; display: flex; flex-direction: column; justify-content: space-between; align-items: center; padding: 12px; cursor: pointer; transition: transform 0.2s; box-shadow: 0 4px 10px rgba(0,0,0,0.15); }
        .table-card:hover { transform: translateY(-3px); background: #059669; }
        .table-no { font-size: 24px; font-weight: 800; margin-top: 15px; }
        .table-badge { background: #047857; color: #fef08a; font-size: 11px; font-weight: 800; padding: 4px 12px; border-radius: 20px; }

        .modal { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); display: none; align-items: center; justify-content: center; z-index: 1000; padding: 16px; }
        .modal-box { background: #0f172a; color: #fff; border-radius: 16px; width: 100%; max-width: 500px; padding: 20px; }
        .modal-title { font-size: 17px; font-weight: 800; color: #f59e0b; margin-bottom: 12px; text-align: center; }
        .items-table { width: 100%; border-collapse: collapse; margin-bottom: 14px; }
        .items-table th { background: #1e293b; color: #f59e0b; padding: 8px; font-size: 12px; }
        .items-table td { padding: 8px; border-bottom: 1px solid #334155; font-size: 13px; text-align: center; }
        .total-banner { background: #1e293b; padding: 10px; border-radius: 8px; font-weight: 800; font-size: 16px; text-align: center; margin-bottom: 12px; color: #10b981; }
        .amount-control { display: flex; align-items: center; justify-content: center; gap: 8px; margin-bottom: 14px; }
        .btn-step { border: none; padding: 8px 14px; border-radius: 8px; font-weight: 800; cursor: pointer; color: #fff; }
        .btn-step.plus { background: #10b981; }
        .btn-step.minus { background: #ef4444; }
        .input-paid { width: 130px; text-align: center; font-size: 18px; font-weight: 800; padding: 8px; border-radius: 8px; border: 2px solid #f59e0b; background: #03261d; color: #fff; outline: none; }
        .change-text { text-align: center; font-weight: 800; font-size: 14px; margin-bottom: 14px; }
        .btn-confirm { width: 100%; background: #10b981; color: #0f172a; border: none; padding: 12px; border-radius: 10px; font-size: 15px; font-weight: 800; cursor: pointer; }
    </style>
</head>
<body>
    <div class="top-bar">
        <div class="title">🛎️ مێزە داواکراوەکانی کاشێر</div>
        <a href="/admin" class="btn-back">⬅️ داشبۆرد</a>
    </div>

    <div class="tables-container">
        {% if tables %}
            {% for t in tables %}
                <div class="table-card" onclick="openCheckout('{{ t }}')">
                    <div style="font-size:24px;">🍽️</div>
                    <div class="table-no">مێزی {{ t }}</div>
                    <div class="table-badge">داواکاری هەیە</div>
                </div>
            {% endfor %}
        {% else %}
            <div style="grid-column: 1/-1; text-align:center; padding: 60px 0; color:#78350f; font-size:18px; font-weight:800;">
                ✨ لە ئێستادا سەرجەم مێزەکان بەتاڵن و هیچ داواکارییەک نییە
            </div>
        {% endif %}
    </div>

    <div class="modal" id="checkoutModal">
        <div class="modal-box">
            <div class="modal-title" id="mTableTitle">واصڵکردنی مێز</div>
            <div style="max-height: 200px; overflow-y:auto; margin-bottom:10px;">
                <table class="items-table">
                    <thead><tr><th>خواردن</th><th>بڕ</th><th>نرخ</th><th>کۆی گشتی</th></tr></thead>
                    <tbody id="itemsBody"></tbody>
                </table>
            </div>
            <div class="total-banner" id="totalAmountText">کۆی گشتی: 0 د.ع</div>
            <div class="amount-control">
                <button type="button" class="btn-step minus" onclick="adjustPaid(-500)">-٥٠٠</button>
                <button type="button" class="btn-step plus" onclick="adjustPaid(500)">+٥٠٠</button>
                <input type="text" id="txtPaid" class="input-paid" oninput="calculateChange()">
            </div>
            <div class="change-text" id="changeText" style="color:#10b981;">گێڕاوە: 0 د.ع</div>
            <button type="button" class="btn-confirm" onclick="confirmPayment()">تۆمارکردن و واصڵکردنی پارە ➔</button>
            <button type="button" style="background:none; border:none; color:#94a3b8; width:100%; margin-top:8px; cursor:pointer;" onclick="closeModal()">پاشگەزبوونەوە</button>
        </div>
    </div>

    <script>
        let currentTotal = 0, currentTable = '';
        function openCheckout(tableNum) {
            currentTable = tableNum;
            document.getElementById('mTableTitle').innerText = "واصڵکردنی مێزی: " + tableNum;
            fetch('/get_table_orders/' + tableNum).then(r => r.json()).then(items => {
                const tbody = document.getElementById('itemsBody');
                tbody.innerHTML = '';
                currentTotal = 0;
                items.forEach(it => {
                    const tot = it.quantity * it.price;
                    currentTotal += tot;
                    tbody.innerHTML += `<tr><td>${it.food_name}</td><td>${it.quantity}</td><td>${Number(it.price).toLocaleString()}</td><td>${tot.toLocaleString()}</td></tr>`;
                });
                document.getElementById('totalAmountText').innerText = "کۆی گشتی: " + currentTotal.toLocaleString() + " د.ع";
                document.getElementById('txtPaid').value = currentTotal;
                calculateChange();
                document.getElementById('checkoutModal').style.display = 'flex';
            });
        }
        function closeModal() { document.getElementById('checkoutModal').style.display = 'none'; }
        function adjustPaid(delta) {
            let val = parseInt(document.getElementById('txtPaid').value) || 0;
            val = Math.max(0, val + delta);
            document.getElementById('txtPaid').value = val;
            calculateChange();
        }
        function calculateChange() {
            let paid = parseInt(document.getElementById('txtPaid').value) || 0;
            let diff = paid - currentTotal;
            const cText = document.getElementById('changeText');
            if (diff >= 0) {
                cText.innerText = "گێڕاوە: " + diff.toLocaleString() + " د.ع";
                cText.style.color = "#10b981";
            } else {
                cText.innerText = "کەمترە بەبڕی: " + Math.abs(diff).toLocaleString() + " د.ع";
                cText.style.color = "#ef4444";
            }
        }
        function confirmPayment() {
            let paid = parseInt(document.getElementById('txtPaid').value) || 0;
            fetch('/admin/complete_payment', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ table_number: currentTable, total_amount: currentTotal, amount_paid: paid })
            }).then(r => r.json()).then(data => {
                if (data.status === 'success') {
                    alert("پارەکە بە سەرکەوتوویی واصڵکرا و ڕەوانەی قاسە کرا!");
                    location.reload();
                } else alert("هەڵە: " + data.message);
            });
        }
    </script>
</body>
</html>
"""

# ==========================================
# بەشی قاسە (٢٤ کاتژمێر)
# ==========================================
WEB_QASA_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>قاسەی فرۆشتن - شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background: #03261d; color: #fff; min-height: 100vh; padding: 20px; }
        .top-bar { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #0b5e4a; padding-bottom: 14px; margin-bottom: 20px; }
        .title { font-size: 20px; font-weight: 800; color: #10b981; }
        .btn { background: #10b981; color: #03261d; text-decoration: none; padding: 8px 16px; border-radius: 8px; font-weight: 800; font-size: 13px; }
        .summary-card { background: #064032; border: 1.5px solid #0b5e4a; padding: 16px 20px; border-radius: 12px; margin-bottom: 18px; font-weight: 800; display: flex; justify-content: space-between; }
        .table-responsive { overflow-x: auto; background: #064032; border-radius: 14px; border: 1px solid #0b5e4a; }
        table { width: 100%; border-collapse: collapse; text-align: center; }
        th { background: #0f172a; color: #f59e0b; padding: 12px; font-size: 13px; }
        td { padding: 12px; border-bottom: 1px solid #0b5e4a; font-size: 13px; font-weight: 700; }
    </style>
</head>
<body>
    <div class="top-bar">
        <div class="title">💵 قاسەی فرۆشتنی ٢٤ کاتژمێری ڕابردوو</div>
        <a href="/admin" class="btn">⬅️ داشبۆرد</a>
    </div>
    <div class="summary-card">
        <span>💰 کۆی پارەی وەرگیراو: <strong style="color:#10b981;">{{ "{:,.0f}".format(total_received) }} د.ع</strong></span>
        <span>🏷️ کۆی داشکاندن (تەخفیف): <strong style="color:#ef4444;">{{ "{:,.0f}".format(total_discount) }} د.ع</strong></span>
    </div>
    <div class="table-responsive">
        <table>
            <thead>
                <tr>
                    <th>کات و بەروار</th>
                    <th>مێز</th>
                    <th>پارەی وەرگیراو (د.ع)</th>
                    <th>داشکاندن / تەخفیف (د.ع)</th>
                </tr>
            </thead>
            <tbody>
                {% for r in qasa_rows %}
                <tr>
                    <td>{{ r['transaction_time'] }}</td>
                    <td>{{ r['place_id'] }}</td>
                    <td style="color:#10b981;">{{ "{:,.0f}".format(r['amount']) }}</td>
                    <td style="color:#f59e0b;">{{ "{:,.0f}".format(r['discount']) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
"""

# ==========================================
# بەشی مەسرووفات
# ==========================================
WEB_MASRWF_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مەسرووفات و خەرجییەکان - شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background: #f8fafc; color: #0f172a; min-height: 100vh; padding: 20px; }
        .top-nav { background: #0f172a; color: #fff; padding: 12px 20px; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .layout-grid { display: grid; grid-template-columns: 360px 1fr; gap: 20px; }
        .card-box { background: #fff; border-radius: 14px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.06); }
        .form-group { margin-bottom: 12px; }
        .form-group label { display: block; font-weight: 700; font-size: 12.5px; margin-bottom: 5px; color: #475569; }
        .form-control { width: 100%; padding: 9px; border: 1.5px solid #cbd5e1; border-radius: 8px; font-weight: 700; outline: none; }
        .btn-act { width: 100%; border: none; padding: 11px; border-radius: 8px; font-weight: 800; cursor: pointer; margin-top: 6px; }
        .btn-green { background: #10b981; color: #fff; }
        table { width: 100%; border-collapse: collapse; text-align: center; }
        th { background: #1e293b; color: #f59e0b; padding: 10px; font-size: 12px; }
        td { padding: 10px; border-bottom: 1px solid #e2e8f0; font-size: 13px; }
    </style>
</head>
<body>
    <div class="top-nav">
        <span style="font-weight:800; color:#f59e0b; font-size:17px;">🧾 بەڕێوەبردنی مەسرووفات و خەرجییەکان</span>
        <a href="/admin" style="background:#334155; color:#fff; text-decoration:none; padding:6px 14px; border-radius:8px; font-weight:700;">⬅️ داشبۆرد</a>
    </div>

    <div class="layout-grid">
        <div class="card-box">
            <h3 style="margin-bottom:14px; font-size:16px;">💾 تۆمارکردنی خەرجی</h3>
            <form method="POST" action="/admin/save_masrwf">
                <div class="form-group">
                    <label>📅 بەروار:</label>
                    <input type="date" name="m_date" class="form-control" value="{{ today_date }}" required>
                </div>
                <div class="form-group">
                    <label>🏷️ جۆری مەسرووف:</label>
                    <input type="text" name="m_type" class="form-control" placeholder="نموونە: گۆشت، سەوزە، نەوت" required>
                </div>
                <div class="form-group">
                    <label>👤 کێ مەسرووفی کردووە؟:</label>
                    <input type="text" name="spent_by" class="form-control" placeholder="ناوی خەرجکار">
                </div>
                <div class="form-group">
                    <label>💵 بڕی پارە (دینار):</label>
                    <input type="number" name="amount" class="form-control" placeholder="0" required>
                </div>
                <div class="form-group">
                    <label>📝 تێبینی:</label>
                    <textarea name="notes" class="form-control" rows="2"></textarea>
                </div>
                <button type="submit" class="btn-act btn-green">تۆمارکردنی خەرجی</button>
            </form>
        </div>

        <div class="card-box" style="overflow-x:auto;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <h3 style="font-size:16px;">لیستەی مەسرووفەکان</h3>
                <span style="background:#fef3c7; color:#b45309; padding:6px 14px; border-radius:10px; font-weight:800;">کۆی گشتی: {{ "{:,.0f}".format(total_m) }} د.ع</span>
            </div>
            <table>
                <thead>
                    <tr><th>بەروار</th><th>جۆری مەسرووف</th><th>خەرجکار</th><th>بڕی پارە</th><th>تێبینی</th><th>کردار</th></tr>
                </thead>
                <tbody>
                    {% for row in rows %}
                    <tr>
                        <td>{{ row['m_date'] }}</td>
                        <td>{{ row['masrwf_type'] }}</td>
                        <td>{{ row['spent_by'] or '-' }}</td>
                        <td style="color:#ef4444; font-weight:800;">{{ "{:,.0f}".format(row['amount']) }}</td>
                        <td>{{ row['notes'] or '-' }}</td>
                        <td><a href="/admin/delete_masrwf/{{ row['id'] }}" onclick="return confirm('ئایا دڵنیایت لە سڕینەوەی ئەم مەسرووفە؟')" style="color:#ef4444; text-decoration:none; font-weight:800;">🗑️</a></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

# ==========================================
# بەشی شاگردەکان و دەوام
# ==========================================
WEB_WORKERS_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>حیساباتی شاگردەکان - شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background: #03261d; color: #fff; min-height: 100vh; padding: 20px; }
        .top-nav { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #0b5e4a; padding-bottom: 14px; margin-bottom: 20px; }
        .title { font-size: 20px; font-weight: 800; color: #10b981; }
        .btn { background: #10b981; color: #03261d; text-decoration: none; padding: 8px 16px; border-radius: 8px; font-weight: 800; font-size: 13px; }
        .layout-grid { display: grid; grid-template-columns: 340px 1fr; gap: 20px; }
        .box { background: #064032; border: 1.5px solid #0b5e4a; border-radius: 14px; padding: 18px; }
        .form-group { margin-bottom: 12px; }
        .form-group label { display: block; font-weight: 700; font-size: 12.5px; margin-bottom: 5px; color: #a7f3d0; }
        .form-control { width: 100%; padding: 9px; border: 1.5px solid #0b5e4a; background: #03261d; color: #fff; border-radius: 8px; font-weight: 700; outline: none; }
        table { width: 100%; border-collapse: collapse; text-align: center; }
        th { background: #0f172a; color: #f59e0b; padding: 10px; font-size: 12px; }
        td { padding: 10px; border-bottom: 1px solid #0b5e4a; font-size: 13px; font-weight: 700; }
        .btn-save { width: 100%; background: #10b981; color: #03261d; border: none; padding: 11px; border-radius: 8px; font-weight: 800; cursor: pointer; }
    </style>
</head>
<body>
    <div class="top-nav">
        <div class="title">👥 بەڕێوەبردنی شاگردەکان و حیساباتی شایستە</div>
        <a href="/admin" class="btn">⬅️ داشبۆرد</a>
    </div>

    <div class="layout-grid">
        <div class="box">
            <h3 style="margin-bottom:14px; color:#10b981; font-size:16px;">👤 زیادکردنی شاگرد</h3>
            <form method="POST" action="/admin/add_worker">
                <div class="form-group">
                    <label>ناوی شاگرد:</label>
                    <input type="text" name="name" class="form-control" required>
                </div>
                <div class="form-group">
                    <label>مۆبایل:</label>
                    <input type="text" name="phone" class="form-control">
                </div>
                <div class="form-group">
                    <label>مووچەی ڕۆژانە (دینار):</label>
                    <input type="number" name="salary" class="form-control" value="25000" required>
                </div>
                <button type="submit" class="btn-save">زیادکردنی شاگرد</button>
            </form>
        </div>

        <div class="box" style="overflow-x:auto;">
            <h3 style="margin-bottom:14px; color:#10b981; font-size:16px;">ڕاپۆرتی مانگانەی شایستەی شاگردەکان</h3>
            <table>
                <thead>
                    <tr><th>ناوی شاگرد</th><th>مۆبایل</th><th>ڕۆژانی دەوام</th><th>مووچەی ڕۆژانە</th><th>کۆی مووچە</th><th>کۆی بەخشش</th><th>کۆی گشتی شایستە</th><th>کردار</th></tr>
                </thead>
                <tbody>
                    {% for w in wage_rows %}
                    <tr>
                        <td>{{ w['name'] }}</td>
                        <td>{{ w['phone'] }}</td>
                        <td>{{ w['work_days'] }} ڕۆژ</td>
                        <td>{{ "{:,.0f}".format(w['salary']) }}</td>
                        <td style="color:#10b981;">{{ "{:,.0f}".format(w['total_salary']) }}</td>
                        <td style="color:#f59e0b;">{{ "{:,.0f}".format(w['total_bonus']) }}</td>
                        <td style="color:#38bdf8; font-weight:800;">{{ "{:,.0f}".format(w['total_due']) }} د.ع</td>
                        <td><a href="/admin/delete_worker/{{ w['id'] }}" onclick="return confirm('ئایا دڵنیایت لە سڕینەوەی ئەم شاگردە؟')" style="color:#ef4444; text-decoration:none;">🗑️</a></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

# ==========================================
# بەشی مێنۆ (Menu Manager)
# ==========================================
WEB_MENU_MANAGER_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>بەڕێوەبردنی مێنۆ - شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background: #03261d; color: #fff; min-height: 100vh; padding: 20px; }
        .top-nav { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #0b5e4a; padding-bottom: 14px; margin-bottom: 20px; }
        .title { font-size: 20px; font-weight: 800; color: #10b981; }
        .btn { background: #10b981; color: #03261d; text-decoration: none; padding: 8px 16px; border-radius: 8px; font-weight: 800; font-size: 13px; }
        .layout-grid { display: grid; grid-template-columns: 340px 1fr; gap: 20px; }
        .box { background: #064032; border: 1.5px solid #0b5e4a; border-radius: 14px; padding: 18px; }
        .form-group { margin-bottom: 12px; }
        .form-group label { display: block; font-weight: 700; font-size: 12.5px; margin-bottom: 5px; color: #a7f3d0; }
        .form-control { width: 100%; padding: 9px; border: 1.5px solid #0b5e4a; background: #03261d; color: #fff; border-radius: 8px; font-weight: 700; outline: none; }
        table { width: 100%; border-collapse: collapse; text-align: center; }
        th { background: #0f172a; color: #f59e0b; padding: 10px; font-size: 12px; }
        td { padding: 10px; border-bottom: 1px solid #0b5e4a; font-size: 13px; font-weight: 700; }
        .btn-save { width: 100%; background: #10b981; color: #03261d; border: none; padding: 11px; border-radius: 8px; font-weight: 800; cursor: pointer; }
    </style>
</head>
<body>
    <div class="top-nav">
        <div class="title">📖 بەڕێوەبردنی خواردن و خواردنەوەکانی مێنۆ</div>
        <a href="/admin" class="btn">⬅️ داشبۆرد</a>
    </div>

    <div class="layout-grid">
        <div class="box">
            <h3 style="margin-bottom:14px; color:#10b981; font-size:16px;">➕ زیادکردنی خواردن</h3>
            <form method="POST" action="/admin/add_food">
                <div class="form-group">
                    <label>ناوی خواردن:</label>
                    <input type="text" name="food_name" class="form-control" required>
                </div>
                <div class="form-group">
                    <label>نرخ (دینار):</label>
                    <input type="number" name="price" class="form-control" required>
                </div>
                <div class="form-group">
                    <label>بەش (Category):</label>
                    <input type="text" name="category" class="form-control" placeholder="نموونە: برژاو، کوڵاو، پەلەوەر" required>
                </div>
                <div class="form-group">
                    <label>لینکی وێنە (URL):</label>
                    <input type="text" name="image_path" class="form-control" placeholder="https://...">
                </div>
                <button type="submit" class="btn-save">تۆمارکردنی خواردن</button>
            </form>
        </div>

        <div class="box" style="overflow-x:auto;">
            <h3 style="margin-bottom:14px; color:#10b981; font-size:16px;">لیستەی سەرجەم خواردنەکان</h3>
            <table>
                <thead>
                    <tr><th>وێنە</th><th>ناوی خواردن</th><th>نرخ (د.ع)</th><th>بەش</th><th>کردار</th></tr>
                </thead>
                <tbody>
                    {% for f in foods %}
                    <tr>
                        <td><img src="{{ f['image_path'] if f['image_path'] else 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=100' }}" style="width:40px; height:40px; object-fit:cover; border-radius:6px;"></td>
                        <td>{{ f['food_name'] }}</td>
                        <td style="color:#10b981;">{{ "{:,.0f}".format(f['price']) }}</td>
                        <td><span style="background:#03261d; padding:3px 8px; border-radius:6px;">{{ f['category'] }}</span></td>
                        <td><a href="/admin/delete_food/{{ f['id'] }}" onclick="return confirm('ئایا دڵنیایت لە سڕینەوەی ئەم خواردنە؟')" style="color:#ef4444; text-decoration:none;">🗑️ سڕینەوە</a></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

# فۆڕمی مۆبایلی گشتی
HTML_TEMPLATE = CUSTOMER_MENU_TEMPLATE

# ==========================================
# ڕووتەکان و کردارەکانی داتابەیس
# ==========================================
@app.route('/')
def index():
    session.clear()
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        pin = normalize_digits(request.form.get('pin', ''))
        if pin in ['99', '٩٩', '222', '٢٢٢']:
            session.permanent = True
            session['authenticated'] = True
            session['role'] = 'admin'
            return redirect(url_for('admin_dashboard'))
        if pin in ['22', '٢٢']:
            session.permanent = True
            session['authenticated'] = True
            session['role'] = 'waiter'
            return redirect(url_for('desktop_tables'))
        if pin in ['345678', '٣٤٥٦٧٨']:
            session.permanent = True
            session['authenticated'] = True
            session['role'] = 'mobile'
            return redirect(url_for('menu'))
        return render_template_string(LOGIN_TEMPLATE, error='وشەی نهێنی هەڵەیە!')
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/admin')
def admin_dashboard():
    if not session.get('authenticated') or session.get('role') != 'admin':
        return redirect(url_for('login'))

    today_sales, today_expense, active_tables, total_workers = 0, 0, 0, 0
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
        conn.close()
    except Exception as e:
        print("Stats error:", e)

    return render_template_string(ADMIN_DASHBOARD_TEMPLATE, today_sales=today_sales, today_expense=today_expense, active_tables_count=active_tables, total_workers=total_workers)

@app.route('/admin/cashier')
def admin_cashier():
    if not session.get('authenticated') or session.get('role') != 'admin': return redirect(url_for('login'))
    tables = []
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cursor_sql = "SELECT DISTINCT table_cabin FROM froshtn WHERE table_cabin NOT LIKE '%[%' AND table_cabin != '' ORDER BY CAST(table_cabin AS UNSIGNED)"
            cur.execute(cursor_sql)
            tables = [r['table_cabin'] for r in cur.fetchall()]
        conn.close()
    except: pass
    return render_template_string(WEB_CASHIER_TEMPLATE, tables=tables)

@app.route('/admin/complete_payment', methods=['POST'])
def admin_complete_payment():
    data = request.get_json()
    t_num = str(data.get('table_number')).strip()
    tot = float(data.get('total_amount', 0))
    paid = float(data.get('amount_paid', 0))
    disc = max(0, tot - paid)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            p_id = t_num if t_num.startswith('m') else f"m{t_num}"
            cur.execute("INSERT INTO qasa (transaction_time, place_id, amount, discount) VALUES (NOW(), %s, %s, %s)", (p_id, paid, disc))
            cur.execute("DELETE FROM froshtn WHERE table_cabin = %s OR table_cabin LIKE %s", (t_num, f"{t_num} [%"))
            conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as ex:
        if conn: conn.close()
        return jsonify({'status': 'error', 'message': str(ex)})

@app.route('/admin/qasa')
def admin_qasa():
    if not session.get('authenticated') or session.get('role') != 'admin': return redirect(url_for('login'))
    rows = []
    tot_rec, tot_disc = 0, 0
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT DATE_FORMAT(transaction_time, '%Y-%m-%d %H:%i') AS transaction_time, place_id, amount, discount FROM qasa WHERE transaction_time >= NOW() - INTERVAL 1 DAY ORDER BY transaction_time DESC")
            rows = cur.fetchall()
            tot_rec = sum(float(r['amount']) for r in rows)
            tot_disc = sum(float(r['discount']) for r in rows)
        conn.close()
    except: pass
    return render_template_string(WEB_QASA_TEMPLATE, qasa_rows=rows, total_received=tot_rec, total_discount=tot_disc)

@app.route('/admin/masrwf')
def admin_masrwf():
    if not session.get('authenticated') or session.get('role') != 'admin': return redirect(url_for('login'))
    rows = []
    tot = 0
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT id, DATE_FORMAT(masrwf_date, '%Y-%m-%d') AS m_date, masrwf_type, spent_by, amount, notes FROM masrwf ORDER BY id DESC")
            rows = cur.fetchall()
            tot = sum(float(r['amount']) for r in rows)
        conn.close()
    except: pass
    return render_template_string(WEB_MASRWF_TEMPLATE, rows=rows, total_m=tot, today_date=datetime.now().strftime('%Y-%m-%d'))

@app.route('/admin/save_masrwf', methods=['POST'])
def admin_save_masrwf():
    m_date = request.form.get('m_date')
    m_type = request.form.get('m_type')
    spent_by = request.form.get('spent_by', '')
    amt = float(request.form.get('amount', 0))
    notes = request.form.get('notes', '')
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("INSERT INTO masrwf (masrwf_date, masrwf_type, spent_by, amount, notes) VALUES (%s, %s, %s, %s, %s)", (m_date, m_type, spent_by, amt, notes))
        conn.commit()
    conn.close()
    return redirect(url_for('admin_masrwf'))

@app.route('/admin/delete_masrwf/<int:mid>')
def admin_delete_masrwf(mid):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM masrwf WHERE id = %s", (mid,))
        conn.commit()
    conn.close()
    return redirect(url_for('admin_masrwf'))

@app.route('/admin/workers')
def admin_workers():
    if not session.get('authenticated') or session.get('role') != 'admin': return redirect(url_for('login'))
    rows = []
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
                LEFT JOIN worker_attendance wa ON w.id = wa.worker_id AND MONTH(wa.date) = MONTH(CURRENT_DATE())
                GROUP BY w.id, w.name, w.phone, w.salary
            """)
            rows = cur.fetchall()
        conn.close()
    except Exception as e:
        print("Worker list error:", e)
    return render_template_string(WEB_WORKERS_TEMPLATE, wage_rows=rows)

@app.route('/admin/add_worker', methods=['POST'])
def admin_add_worker():
    name = request.form.get('name')
    phone = request.form.get('phone', '')
    salary = float(request.form.get('salary', 25000))
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("INSERT INTO workers (name, phone, salary) VALUES (%s, %s, %s)", (name, phone, salary))
        conn.commit()
    conn.close()
    return redirect(url_for('admin_workers'))

@app.route('/admin/delete_worker/<int:wid>')
def admin_delete_worker(wid):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM worker_attendance WHERE worker_id = %s", (wid,))
        cur.execute("DELETE FROM workers WHERE id = %s", (wid,))
        conn.commit()
    conn.close()
    return redirect(url_for('admin_workers'))

@app.route('/admin/menu_manager')
def admin_menu_manager():
    if not session.get('authenticated') or session.get('role') != 'admin': return redirect(url_for('login'))
    foods = []
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT id, food_name, price, category, image_path FROM nse ORDER BY id DESC")
            foods = cur.fetchall()
        conn.close()
    except: pass
    return render_template_string(WEB_MENU_MANAGER_TEMPLATE, foods=foods)

@app.route('/admin/add_food', methods=['POST'])
def admin_add_food():
    name = request.form.get('food_name')
    price = float(request.form.get('price', 0))
    cat = request.form.get('category', 'گشتی')
    img = request.form.get('image_path', '')
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("INSERT INTO nse (food_name, price, category, image_path, nsecol) VALUES (%s, %s, %s, %s, '')", (name, price, cat, img))
        conn.commit()
    conn.close()
    return redirect(url_for('admin_menu_manager'))

@app.route('/admin/delete_food/<int:fid>')
def admin_delete_food(fid):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM nse WHERE id = %s", (fid,))
        conn.commit()
    conn.close()
    return redirect(url_for('admin_menu_manager'))

# ==========================================
# کردارەکانی ناردنی ئۆردەر و پشکنین بۆ چاپی مەتبەخ
# ==========================================
@app.route('/save_customer_order', methods=['POST'])
def save_customer_order():
    data = request.get_json()
    tbl = data.get('table_number')
    items = data.get('cart_items', [])
    if not items:
        return jsonify({'status': 'error', 'message': 'هیچ خواردنێک دیاری نەکراوە!'})

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT allow_ordering FROM table_permissions WHERE table_number = %s", (int(tbl),))
            perm_row = cur.fetchone()
            if perm_row and perm_row['allow_ordering'] == 0:
                conn.close()
                return jsonify({'status': 'error', 'message': 'ئەم مێزە لەسەر تەنها بینین دانراوە و ڕێگە بە ئۆردەر نادرێت!'})

            for it in items:
                fname = it.get('food_name')
                qty = int(it.get('qty', 1))
                price = float(it.get('price', 0))
                cat = it.get('cat', 'گشتی')
                rice = it.get('rice_type', '')
                chicken = it.get('chicken_part', '')

                if cat in ['کوڵاو', 'پەلەوەر', 'کوردیەکان'] and rice:
                    fname += f" ({rice})"
                if cat == 'پەلەوەر' and chicken:
                    fname += f" ({chicken})"

                cur.execute("""
                    INSERT INTO froshtn (table_cabin, food_name, quantity, price, category, created_at, is_printed) 
                    VALUES (%s, %s, %s, %s, %s, NOW(), 1)
                """, (str(tbl), fname, qty, price, cat))

                cur.execute("""
                    INSERT INTO froshtn (table_cabin, food_name, quantity, price, category, created_at, is_printed) 
                    VALUES (%s, %s, %s, %s, %s, NOW(), 0)
                """, (str(tbl) + " [زیادکراو]", f"+ {fname}", qty, price, cat))

            conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as ex:
        if conn: conn.close()
        return jsonify({'status': 'error', 'message': str(ex)})

@app.route('/save_cart_order', methods=['POST'])
def save_cart_order():
    data = request.get_json()
    tbl = data.get('table_number')
    cart = data.get('cart_items', [])
    orig = data.get('original_items', [])

    def make_map(its):
        mp = {}
        for it in its:
            if it.get('is_divider'): continue
            name = it['food_name']
            cat = it.get('cat', '')
            rice = it.get('rice_type', '')
            chicken = it.get('chicken_part', '')
            if cat in ['کوڵاو', 'پەلەوەر', 'کوردیەکان'] and rice:
                name += f" ({rice})"
            if cat == 'پەلەوەر' and chicken:
                name += f" ({chicken})"
            mp[name] = {'qty': int(it['qty']), 'price': float(it['price']), 'cat': cat}
        return mp

    old_map = make_map(orig)
    new_map = make_map(cart)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM froshtn WHERE table_cabin = %s", (str(tbl),))
            for it in cart:
                if it.get('is_divider'):
                    fname = "--- قاپی نوێ ---"
                    qty = 1
                    price = 0
                    cat = 'مەتبەخ'
                else:
                    fname = it['food_name']
                    cat = it.get('cat', '')
                    rice = it.get('rice_type', '')
                    chicken = it.get('chicken_part', '')
                    if cat in ['کوڵاو', 'پەلەوەر', 'کوردیەکان'] and rice:
                        fname += f" ({rice})"
                    if cat == 'پەلەوەر' and chicken:
                        fname += f" ({chicken})"
                    qty = int(it['qty'])
                    price = float(it['price'])

                cur.execute("""
                    INSERT INTO froshtn (table_cabin, food_name, quantity, price, category, created_at, is_printed) 
                    VALUES (%s, %s, %s, %s, %s, NOW(), 1)
                """, (str(tbl), fname, qty, price, cat))

            for k in set(old_map.keys()).union(set(new_map.keys())):
                diff = new_map.get(k, {}).get('qty', 0) - old_map.get(k, {}).get('qty', 0)
                if diff > 0:
                    cur.execute("""
                        INSERT INTO froshtn (table_cabin, food_name, quantity, price, category, created_at, is_printed) 
                        VALUES (%s, %s, %s, %s, %s, NOW(), 0)
                    """, (str(tbl) + " [زیادکراو]", f"+ {k}", diff, new_map[k]['price'], new_map[k]['cat']))
                elif diff < 0:
                    cur.execute("""
                        INSERT INTO froshtn (table_cabin, food_name, quantity, price, category, created_at, is_printed) 
                        VALUES (%s, %s, %s, %s, %s, NOW(), 0)
                    """, (str(tbl) + " [سڕاوەتەوە]", f"سڕاوەتەوە: {k}", abs(diff), old_map[k]['price'], old_map[k]['cat']))
            conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as ex:
        if conn: conn.close()
        return jsonify({'status': 'error', 'message': str(ex)})

@app.route('/get_table_orders/<table_num>')
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
    tbl = request.get_json().get('table_number')
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM froshtn WHERE table_cabin = %s OR table_cabin LIKE %s", (str(tbl), f"{tbl} [%"))
        conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/change_table_number', methods=['POST'])
def change_table_number():
    if not session.get('authenticated'):
        return jsonify({'status': 'error', 'message': 'ڕێگەپێنەدراو'})
    data = request.get_json()
    old_tbl = str(data.get('old_table')).strip()
    new_tbl = str(data.get('new_table')).strip()
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE froshtn SET table_cabin = %s WHERE table_cabin = %s", (new_tbl, old_tbl))
            cursor.execute("""
                UPDATE froshtn 
                SET table_cabin = REPLACE(table_cabin, %s, %s) 
                WHERE table_cabin LIKE %s
            """, (f"{old_tbl} [", f"{new_tbl} [", f"{old_tbl} [%"))
            conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        if conn: conn.close()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/desktop/tables')
def desktop_tables():
    if not session.get('authenticated'): return redirect(url_for('login'))
    return render_template_string(DESKTOP_TABLES_TEMPLATE)

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
                c = f['category'].strip() if f['category'] else 'گشتی'
                categories.setdefault(c, []).append(f)
        conn.close()
    except: pass
    return render_template_string(DESKTOP_TEMPLATE, categories=categories, selected_table=tbl)

@app.route('/menu')
def menu():
    if not session.get('authenticated'): return redirect(url_for('login'))
    categories = {}
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT food_name, price, category, image_path FROM nse WHERE food_name != ''")
            for f in cur.fetchall():
                c = f['category'].strip() if f['category'] else 'گشتی'
                categories.setdefault(c, []).append(f)
        conn.close()
    except: pass
    return render_template_string(CUSTOMER_MENU_TEMPLATE, categories=categories, table_num=1, allow_ordering=True)

@app.route('/table/<int:table_num>')
def customer_table_view(table_num):
    categories = {}
    allow_ordering = False
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT allow_ordering FROM table_permissions WHERE table_number = %s", (table_num,))
            p_row = cur.fetchone()
            if p_row and p_row['allow_ordering'] == 1:
                allow_ordering = True

            cur.execute("SELECT food_name, price, category, image_path FROM nse WHERE food_name != ''")
            for f in cur.fetchall():
                c = f['category'].strip() if f['category'] else 'گشتی'
                categories.setdefault(c, []).append(f)
        conn.close()
    except: pass
    return render_template_string(CUSTOMER_MENU_TEMPLATE, table_num=table_num, categories=categories, allow_ordering=allow_ordering)

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

@app.route('/qr_manager')
def qr_manager():
    if not session.get('authenticated'): return redirect(url_for('login'))
    perm_dict = {}
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT table_number, allow_ordering FROM table_permissions")
            for r in cur.fetchall():
                perm_dict[r['table_number']] = r['allow_ordering']
        conn.close()
    except: pass
    return render_template_string(QR_MANAGER_TEMPLATE, perm_dict=perm_dict, base_url=request.host_url.rstrip('/'))

@app.route('/toggle_table_permission', methods=['POST'])
def toggle_table_permission():
    if not session.get('authenticated'): return jsonify({'status': 'error'})
    tbl = int(request.get_json().get('table_number'))
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT allow_ordering FROM table_permissions WHERE table_number = %s", (tbl,))
            row = cur.fetchone()
            new_val = 0 if (row and row['allow_ordering'] == 1) else 1
            cur.execute("INSERT INTO table_permissions (table_number, allow_ordering) VALUES (%s, %s) ON DUPLICATE KEY UPDATE allow_ordering = %s", (tbl, new_val, new_val))
            conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'allow_ordering': new_val})
    except Exception as ex:
        if conn: conn.close()
        return jsonify({'status': 'error', 'message': str(ex)})

@app.route('/set_all_table_permissions', methods=['POST'])
def set_all_table_permissions():
    if not session.get('authenticated'): return jsonify({'status': 'error'})
    allow = int(request.get_json().get('allow_ordering', 0))
    conn = get_db()
    try:
        with conn.cursor() as cur:
            for num in range(1, 91):
                cur.execute("INSERT INTO table_permissions (table_number, allow_ordering) VALUES (%s, %s) ON DUPLICATE KEY UPDATE allow_ordering = %s", (num, allow, allow))
            conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as ex:
        if conn: conn.close()
        return jsonify({'status': 'error', 'message': str(ex)})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
