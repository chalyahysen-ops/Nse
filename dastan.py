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
    return text.translate(str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789'))

def ensure_all_tables():
    try:
        conn = get_db()
        with conn.cursor() as cursor:
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
        .login-card { background: #064032; border: 1.5px solid #0b5e4a; padding: 36px 28px; border-radius: 20px; width: 100%; max-width: 390px; text-align: center; box-shadow: 0 15px 35px rgba(0,0,0,0.5); }
        .brand-title { color: #10b981; font-size: 26px; font-weight: 800; margin-bottom: 6px; }
        .brand-sub { color: #a7f3d0; font-size: 13px; margin-bottom: 24px; }
        .pin-input { width: 100%; padding: 14px; background: #03261d; border: 2px solid #0b5e4a; border-radius: 12px; color: #10b981; font-size: 24px; text-align: center; font-weight: 800; letter-spacing: 6px; outline: none; margin-bottom: 20px; }
        .pin-input:focus { border-color: #10b981; }
        .btn-submit { width: 100%; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #ffffff; border: none; padding: 14px; border-radius: 12px; font-size: 16px; font-weight: 800; cursor: pointer; }
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
    <title>داشبۆردی سەرەکی - شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background-color: #03261d; color: #ffffff; min-height: 100vh; display: flex; flex-direction: column; }
        .admin-nav { background: #064032; padding: 14px 28px; display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #0b5e4a; }
        .admin-brand { font-size: 20px; font-weight: 800; color: #10b981; }
        .btn-exit { background: #ef4444; color: #fff; text-decoration: none; padding: 8px 18px; border-radius: 8px; font-weight: 800; font-size: 13px; }
        .admin-content { flex: 1; padding: 24px; max-width: 1400px; margin: 0 auto; width: 100%; }
        .stats-cards-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 28px; }
        .stat-card { background: #064032; border: 1.5px solid #0b5e4a; border-radius: 16px; padding: 20px; display: flex; align-items: center; justify-content: space-between; }
        .stat-info { display: flex; flex-direction: column; gap: 6px; }
        .stat-label { font-size: 13px; font-weight: 700; color: #a7f3d0; }
        .stat-value { font-size: 22px; font-weight: 800; }
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
            <span style="color:#a7f3d0; font-size:13px; font-weight:700;">👑 بەڕێوەبەر</span>
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

        <div class="section-header">📁 بەشە کارگێڕییەکانی سیستەم</div>
        <div class="dashboard-modules-grid">
            <a href="/admin/cashier" class="module-card">
                <div class="module-top"><div class="module-icon">🛎️</div><span class="module-badge">POS</span></div>
                <div class="module-title">کاشێر و واصڵکردن</div>
                <div class="module-desc">بینینی مێزە داواکراوەکان بە باگڕاوەندی زەرد، دوگمەی +٥٠٠ و -٥٠٠ و واصڵکردن.</div>
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
                <div class="module-desc">چوونە ناو شاشەی مێزەکان و ئۆردەرکردنی خواردن بۆ ئایپاد و دیسکتۆپ.</div>
            </a>

            <a href="/qr_manager" class="module-card">
                <div class="module-top"><div class="module-icon">📱</div><span class="module-badge">QR</span></div>
                <div class="module-title">بەڕێوەبردنی QR مێزەکان</div>
                <div class="module-desc">چاپی ٩٠ کیوئاڕ کۆدەکە لەگەڵ دیاریکردنی مۆڵەت بۆ موشتەری.</div>
            </a>
        </div>
    </main>
</body>
</html>
"""

# ==========================================
# پەڕەی بەڕێوەبردنی QR کۆدەکان (چارەسەری ئیرۆر)
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
# بەشی کاشێر
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
# پەڕەی قاسە
# ==========================================
WEB_QASA_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>قاسەی فرۆشتن - شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background: #03261d; color: #fff; padding: 20px; }
        .top-nav { display: flex; justify-content: space-between; align-items: center; background: #064032; padding: 14px 20px; border-radius: 12px; border: 1px solid #0b5e4a; margin-bottom: 20px; }
        .btn-back { background: #10b981; color: #03261d; padding: 8px 16px; border-radius: 8px; text-decoration: none; font-weight: 800; }
        .summary-banner { display: flex; gap: 20px; margin-bottom: 20px; }
        .sum-card { flex: 1; background: #064032; padding: 18px; border-radius: 12px; border: 1px solid #0b5e4a; }
        table { width: 100%; border-collapse: collapse; background: #064032; border-radius: 12px; overflow: hidden; }
        th, td { padding: 12px; text-align: center; border-bottom: 1px solid #0b5e4a; font-size: 13px; }
        th { background: #0b5e4a; color: #a7f3d0; }
    </style>
</head>
<body>
    <div class="top-nav">
        <h2 style="color:#10b981;">💵 قاسەی فرۆشتن (٢٤ کاتژمێری ڕابردوو)</h2>
        <a href="/admin" class="btn-back">⬅️ داشبۆرد</a>
    </div>
    <div class="summary-banner">
        <div class="sum-card">
            <div style="color:#a7f3d0; font-size:13px;">کۆی داهاتی وەرگیراو:</div>
            <div style="font-size:24px; font-weight:800; color:#10b981;">{{ "{:,.0f}".format(total_received) }} د.ع</div>
        </div>
        <div class="sum-card">
            <div style="color:#a7f3d0; font-size:13px;">کۆی داشکاندن:</div>
            <div style="font-size:24px; font-weight:800; color:#ef4444;">{{ "{:,.0f}".format(total_discount) }} د.ع</div>
        </div>
    </div>
    <table>
        <thead>
            <tr><th>#</th><th>شوێن / مێز</th><th>بڕی پارە</th><th>داشکاندن</th><th>کاتی وەسڵ</th></tr>
        </thead>
        <tbody>
            {% for r in qasa_rows %}
            <tr>
                <td>{{ loop.index }}</td>
                <td>{{ r.place_id }}</td>
                <td style="color:#10b981; font-weight:800;">{{ "{:,.0f}".format(r.amount) }} د.ع</td>
                <td style="color:#ef4444;">{{ "{:,.0f}".format(r.discount) }} د.ع</td>
                <td>{{ r.transaction_time }}</td>
            </tr>
            {% else %}
            <tr><td colspan="5">هیچ وەسڵێک تۆمار نەکراوە</td></tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
"""

# ==========================================
# پەڕەی مەسرووفات
# ==========================================
WEB_MASRWF_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>مەسرووفات - شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background: #03261d; color: #fff; padding: 20px; }
        .top-nav { display: flex; justify-content: space-between; align-items: center; background: #064032; padding: 14px 20px; border-radius: 12px; border: 1px solid #0b5e4a; margin-bottom: 20px; }
        .btn-back { background: #10b981; color: #03261d; padding: 8px 16px; border-radius: 8px; text-decoration: none; font-weight: 800; }
        .form-box { background: #064032; padding: 18px; border-radius: 12px; margin-bottom: 20px; display: flex; gap: 10px; flex-wrap: wrap; }
        input, select { padding: 10px; border-radius: 8px; border: 1px solid #0b5e4a; background: #03261d; color: #fff; font-size: 13px; }
        .btn-add { background: #10b981; color: #fff; border: none; padding: 10px 20px; border-radius: 8px; font-weight: 800; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; background: #064032; border-radius: 12px; }
        th, td { padding: 12px; text-align: center; border-bottom: 1px solid #0b5e4a; font-size: 13px; }
        th { background: #0b5e4a; color: #a7f3d0; }
    </style>
</head>
<body>
    <div class="top-nav">
        <h2 style="color:#10b981;">💸 مەسرووفات و خەرجی (کۆی گشتی: {{ "{:,.0f}".format(total_m) }} د.ع)</h2>
        <a href="/admin" class="btn-back">⬅️ داشبۆرد</a>
    </div>
    <form class="form-box" method="POST" action="/admin/save_masrwf">
        <input type="date" name="m_date" value="{{ today_date }}" required>
        <input type="text" name="m_type" placeholder="جۆری مەسرووف" required>
        <input type="text" name="spent_by" placeholder="کێ خەرجی کرد">
        <input type="number" step="any" name="amount" placeholder="بڕی پارە" required>
        <input type="text" name="notes" placeholder="تێبینی">
        <button type="submit" class="btn-add">➕ تۆمارکردن</button>
    </form>
    <table>
        <thead>
            <tr><th>#</th><th>بەروار</th><th>جۆر</th><th>کەسی خەرجکار</th><th>بڕی پارە</th><th>تێبینی</th><th>کردار</th></tr>
        </thead>
        <tbody>
            {% for r in rows %}
            <tr>
                <td>{{ loop.index }}</td>
                <td>{{ r.m_date }}</td>
                <td>{{ r.masrwf_type }}</td>
                <td>{{ r.spent_by }}</td>
                <td style="color:#ef4444; font-weight:800;">{{ "{:,.0f}".format(r.amount) }} د.ع</td>
                <td>{{ r.notes }}</td>
                <td><a href="/admin/delete_masrwf/{{ r.id }}" onclick="return confirm('دڵنیایت لە سڕینەوە؟')" style="color:#ef4444; text-decoration:none; font-weight:800;">سڕینەوە</a></td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
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
    <title>شاگردەکان - شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background: #03261d; color: #fff; padding: 20px; }
        .top-nav { display: flex; justify-content: space-between; align-items: center; background: #064032; padding: 14px 20px; border-radius: 12px; border: 1px solid #0b5e4a; margin-bottom: 20px; }
        .btn-back { background: #10b981; color: #03261d; padding: 8px 16px; border-radius: 8px; text-decoration: none; font-weight: 800; }
        .form-box { background: #064032; padding: 18px; border-radius: 12px; margin-bottom: 20px; display: flex; gap: 10px; }
        input { padding: 10px; border-radius: 8px; border: 1px solid #0b5e4a; background: #03261d; color: #fff; }
        .btn-add { background: #10b981; color: #fff; border: none; padding: 10px 20px; border-radius: 8px; font-weight: 800; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; background: #064032; border-radius: 12px; }
        th, td { padding: 12px; text-align: center; border-bottom: 1px solid #0b5e4a; font-size: 13px; }
        th { background: #0b5e4a; color: #a7f3d0; }
    </style>
</head>
<body>
    <div class="top-nav">
        <h2 style="color:#10b981;">👥 حیساباتی شاگردەکان</h2>
        <a href="/admin" class="btn-back">⬅️ داشبۆرد</a>
    </div>
    <form class="form-box" method="POST" action="/admin/add_worker">
        <input type="text" name="name" placeholder="ناوی شاگرد" required>
        <input type="text" name="phone" placeholder="ژمارەی مۆبایل">
        <input type="number" name="salary" placeholder="ڕۆژانە (دینار)" value="25000" required>
        <button type="submit" class="btn-add">➕ زیادکردنی شاگرد</button>
    </form>
    <table>
        <thead>
            <tr><th>#</th><th>ناو</th><th>مۆبایل</th><th>ڕۆژانە</th><th>ڕۆژی کارکردن</th><th>شایستە</th><th>بەخشش</th><th>کۆی گشتی شایستە</th><th>کردار</th></tr>
        </thead>
        <tbody>
            {% for r in wage_rows %}
            <tr>
                <td>{{ loop.index }}</td>
                <td style="font-weight:800;">{{ r.name }}</td>
                <td>{{ r.phone }}</td>
                <td>{{ "{:,.0f}".format(r.salary) }}</td>
                <td>{{ r.work_days }}</td>
                <td>{{ "{:,.0f}".format(r.total_salary) }}</td>
                <td style="color:#f59e0b;">{{ "{:,.0f}".format(r.total_bonus) }}</td>
                <td style="color:#10b981; font-weight:800;">{{ "{:,.0f}".format(r.total_due) }} د.ع</td>
                <td><a href="/admin/delete_worker/{{ r.id }}" onclick="return confirm('دڵنیایت لە سڕینەوەی ئەم شاگردە؟')" style="color:#ef4444; text-decoration:none; font-weight:800;">سڕینەوە</a></td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
"""

# ==========================================
# پەڕەی بەڕێوەبردنی مێنۆ
# ==========================================
WEB_MENU_MANAGER_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>بەڕێوەبردنی مێنۆ - شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background: #03261d; color: #fff; padding: 20px; }
        .top-nav { display: flex; justify-content: space-between; align-items: center; background: #064032; padding: 14px 20px; border-radius: 12px; border: 1px solid #0b5e4a; margin-bottom: 20px; }
        .btn-back { background: #10b981; color: #03261d; padding: 8px 16px; border-radius: 8px; text-decoration: none; font-weight: 800; }
        .form-box { background: #064032; padding: 18px; border-radius: 12px; margin-bottom: 20px; display: flex; gap: 10px; flex-wrap: wrap; }
        input { padding: 10px; border-radius: 8px; border: 1px solid #0b5e4a; background: #03261d; color: #fff; }
        .btn-add { background: #10b981; color: #fff; border: none; padding: 10px 20px; border-radius: 8px; font-weight: 800; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; background: #064032; border-radius: 12px; }
        th, td { padding: 12px; text-align: center; border-bottom: 1px solid #0b5e4a; font-size: 13px; }
        th { background: #0b5e4a; color: #a7f3d0; }
        .food-thumb { width: 50px; height: 50px; border-radius: 8px; object-fit: cover; }
    </style>
</head>
<body>
    <div class="top-nav">
        <h2 style="color:#10b981;">📖 بەڕێوەبردنی خواردنەکانی مێنۆ</h2>
        <a href="/admin" class="btn-back">⬅️ داشبۆرد</a>
    </div>
    <form class="form-box" method="POST" action="/admin/add_food">
        <input type="text" name="food_name" placeholder="ناوی خواردن" required>
        <input type="number" step="any" name="price" placeholder="نرخ (دینار)" required>
        <input type="text" name="category" placeholder="پۆل / بەش (بۆ نموونە: برژاو، کوڵاو)" required>
        <input type="text" name="image_path" placeholder="لینکی وێنە (URL)">
        <button type="submit" class="btn-add">➕ زیادکردنی خواردن</button>
    </form>
    <table>
        <thead>
            <tr><th>#</th><th>وێنە</th><th>ناوی خواردن</th><th>نرخ</th><th>بەش</th><th>کردار</th></tr>
        </thead>
        <tbody>
            {% for f in foods %}
            <tr>
                <td>{{ loop.index }}</td>
                <td><img src="{{ f.image_path }}" class="food-thumb" onerror="this.src='https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=100'"></td>
                <td style="font-weight:800;">{{ f.food_name }}</td>
                <td style="color:#10b981; font-weight:800;">{{ "{:,.0f}".format(f.price) }} د.ع</td>
                <td>{{ f.category }}</td>
                <td><a href="/admin/delete_food/{{ f.id }}" onclick="return confirm('دڵنیایت لە سڕینەوە؟')" style="color:#ef4444; text-decoration:none; font-weight:800;">سڕینەوە</a></td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
"""

# ==========================================
# پەڕەی مێزەکان
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
        .header-bar { background-color: #064032; padding: 14px 24px; display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #0b5e4a; position: sticky; top: 0; z-index: 1000; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
        .header-title { font-size: 17px; font-weight: 800; color: #ffffff; text-align: center; flex: 1; }
        .header-actions { display: flex; gap: 8px; align-items: center; }
        .btn-qr-mgr { background-color: #3b82f6; color: #ffffff; border: none; padding: 8px 14px; border-radius: 8px; font-size: 13px; font-weight: 800; text-decoration: none; cursor: pointer; }
        .btn-exit { background-color: #ef4444; color: #ffffff; border: none; padding: 8px 18px; border-radius: 8px; font-size: 14px; font-weight: 800; text-decoration: none; cursor: pointer; }
        .tables-grid-wrapper { padding: 18px 20px 80px 20px; width: 100%; max-width: 1500px; margin: 0 auto; }
        .tables-grid { display: grid; grid-template-columns: repeat(10, 1fr); gap: 12px; width: 100%; }
        .table-box { background-color: #ffffff; border: 2px solid #e2e8f0; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 28px; font-weight: 800; color: #03261d; text-decoration: none; height: 90px; box-shadow: 0 3px 6px rgba(0,0,0,0.2); cursor: pointer; }
        .table-box.active-occupied { background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important; color: #ffffff !important; border-color: #047857 !important; }
        @media (max-width: 900px) { .tables-grid { grid-template-columns: repeat(8, 1fr); gap: 10px; } .table-box { height: 80px; font-size: 24px; } }
    </style>
</head>
<body>
    <div class="header-bar">
        <a href="/logout" class="btn-exit">✕ دەرچوون</a>
        <div class="header-title">تکایە بۆ ئۆردەرکردنی خواردن و خواردنەوە مێزێک دیاری بکە!</div>
        <div class="header-actions">
            {% if session.get('role') == 'admin' %}
            <a href="/admin" class="btn-qr-mgr" style="background-color:#10b981;">👑 داشبۆرد</a>
            {% endif %}
            <a href="/qr_manager" class="btn-qr-mgr">📱 بەڕێوەبردنی QR</a>
        </div>
    </div>
    <div class="tables-grid-wrapper">
        <div class="tables-grid" id="tablesGrid">
            {% for num in range(1, 91) %}
                <a href="/desktop?table={{ num }}" class="table-box" id="tbl-box-{{ num }}">{{ num }}</a>
            {% endfor %}
        </div>
    </div>
    <script>
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

# ==========================================
# پەڕەی دیسکتۆپ
# ==========================================
DESKTOP_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مێنیوی شاهور - مێزی {{ selected_table }}</title>
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
        .table-badge-header { background: var(--gold); color: var(--bg-main); padding: 5px 12px; border-radius: 6px; font-size: 15px; font-weight: 800; }
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
    <div id="toastMsg">✅ بە سەرکەوتوویی بۆ مەتبەخ نێردرا</div>
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
                <div class="table-badge-header">📍 مێزی {{ selected_table }}</div>
                <input type="hidden" id="currentTableNum" value="{{ selected_table }}">
                <div style="display:flex; gap:4px;">
                    <a href="/desktop/tables" class="btn-top-action">⬅️ مێزەکان</a>
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
            fetch('/get_table_orders/' + tableNum).then(r => r.json()).then(data => {
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
            if (confirm("ئایا دڵنیایت لە سڕینەوەی تەواوی مێزی " + tableNum + "؟")) {
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
# پەڕەی موشتەری و مۆبایل
# ==========================================
CUSTOMER_MENU_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>مێنیوی شاهور - مێزی {{ table_num }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background-color: #03261d; color: #ffffff; padding-bottom: {{ '115px' if allow_ordering else '30px' }}; min-height: 100vh; }
        .top-header-bar { background-color: #03261d; padding: 10px 14px 6px; display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 100; }
        .header-brand { display: flex; align-items: center; gap: 6px; font-size: 17px; font-weight: 800; color: #ffffff; }
        .table-pill { background-color: #059669; color: #ffffff; font-size: 12px; font-weight: 800; padding: 4px 12px; border-radius: 20px; }

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
        <div class="table-pill">مێزی {{ table_num }}</div>
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
                <span style="font-size: 16px; font-weight: 800; color: #ffffff;">🛒 داواکارییەکانی مێزی {{ table_num }}</span>
                <button type="button" style="background:none; border:none; color:#ef4444; font-size:18px; font-weight:800;" onclick="toggleCartModal(false)">✕</button>
            </div>
            <div class="modal-items-scroller" id="cartScrollerList"></div>
            <button type="button" class="btn-submit-order" style="width: 100%; padding: 13px; font-size: 15px;" onclick="sendFinalOrder()">پشتڕاستکردنەوە و ناردن</button>
        </div>
    </div>
    {% endif %}

    <script>
        let myCart = [];
        const tableId = "{{ table_num }}";

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
# ڕێڕەوەکانی سیستەم
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
    except: pass

    return render_template_string(ADMIN_DASHBOARD_TEMPLATE, today_sales=today_sales, today_expense=today_expense, active_tables_count=active_tables, total_workers=total_workers)

@app.route('/admin/cashier')
def admin_cashier():
    if not session.get('authenticated') or session.get('role') != 'admin': return redirect(url_for('login'))
    tables = []
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT table_cabin FROM froshtn WHERE table_cabin NOT LIKE '%[%' AND table_cabin != '' ORDER BY CAST(table_cabin AS UNSIGNED)")
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

@app.route('/table/<int:table_num>')
def customer_table_view(table_num):
    allow_ordering = True
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT allow_ordering FROM table_permissions WHERE table_number = %s", (table_num,))
            row = cur.fetchone()
            if row:
                allow_ordering = bool(row['allow_ordering'])

            cur.execute("SELECT food_name, price, category, image_path FROM nse WHERE food_name != ''")
            foods = cur.fetchall()
        conn.close()

        categories = {}
        for f in foods:
            c = f['category'].strip() if f['category'] else 'گشتی'
            categories.setdefault(c, []).append(f)

        return render_template_string(CUSTOMER_MENU_TEMPLATE, table_num=table_num, categories=categories, allow_ordering=allow_ordering)
    except:
        return "<h3 style='color:red; text-align:center;'>کێشە لە پەڕەی مێز</h3>"

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
    return render_template_string(QR_MANAGER_TEMPLATE, base_url=request.host_url.rstrip('/'), perm_dict=perm_dict)

@app.route('/toggle_table_permission', methods=['POST'])
def toggle_table_permission():
    if not session.get('authenticated'): return jsonify({'status': 'error'})
    t_num = int(request.get_json().get('table_number'))
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT allow_ordering FROM table_permissions WHERE table_number = %s", (t_num,))
        row = cur.fetchone()
        new_val = 0 if (row and row['allow_ordering']) else 1
        cur.execute("INSERT INTO table_permissions (table_number, allow_ordering) VALUES (%s, %s) ON DUPLICATE KEY UPDATE allow_ordering = %s", (t_num, new_val, new_val))
        conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'allow_ordering': new_val})

@app.route('/set_all_table_permissions', methods=['POST'])
def set_all_table_permissions():
    if not session.get('authenticated'): return jsonify({'status': 'error'})
    allow = int(request.get_json().get('allow_ordering', 1))
    conn = get_db()
    with conn.cursor() as cur:
        for i in range(1, 91):
            cur.execute("INSERT INTO table_permissions (table_number, allow_ordering) VALUES (%s, %s) ON DUPLICATE KEY UPDATE allow_ordering = %s", (i, allow, allow))
        conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

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
            p_row = cur.fetchone()
            if p_row and not p_row['allow_ordering']:
                conn.close()
                return jsonify({'status': 'error', 'message': 'ئەم مێزە تەنها بۆ بینینە و ڕێگە بە ناردنی ئۆردەر نادرێت!'})

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
        return {it['food_name']: {'qty': int(it['qty']), 'price': float(it['price']), 'cat': it.get('cat', 'گشتی')} for it in its if not it.get('is_divider')}

    old_map = make_map(orig)
    new_map = make_map(cart)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM froshtn WHERE table_cabin = %s", (str(tbl),))
            for it in cart:
                fname = "--- قاپی نوێ ---" if it.get('is_divider') else it['food_name']
                cur.execute("""
                    INSERT INTO froshtn (table_cabin, food_name, quantity, price, category, created_at, is_printed) 
                    VALUES (%s, %s, %s, %s, %s, NOW(), 1)
                """, (str(tbl), fname, it['qty'], it['price'], it.get('cat', 'گشتی')))

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
