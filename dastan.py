from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session
from datetime import timedelta
import pymysql

app = Flask(__name__)
app.secret_key = 'shahoor_super_admin_pos_secret_key_2026'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=10)

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

def ensure_tables():
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
                CREATE TABLE IF NOT EXISTS masrwf (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255),
                    amount DECIMAL(18, 0),
                    masrwf_date DATETIME DEFAULT CURRENT_TIMESTAMP
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

ensure_tables()

@app.before_request
def enforce_security():
    exempt_endpoints = ['login', 'customer_table_view', 'save_customer_order', 'static']
    if request.endpoint in exempt_endpoints:
        return

    is_api = request.path.startswith(('/get_', '/save_', '/clear_', '/change_', '/set_', '/toggle_'))
    if is_api:
        return

    # پشکنینی ئینتەری ڕاستەوخۆ لە براوسەر
    referer = request.headers.get('Referer')
    if not referer and request.endpoint != 'login':
        session.clear()
        return redirect(url_for('login'))

    # پاراستنی پەڕەی ئەدمین
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
        {% if error %}
            <div class="error-msg">{{ error }}</div>
        {% endif %}
        <div class="roles-hint">
            <span>👑 بەڕێوەبەر: داشبۆردی گشتی</span>
            <span>🍽️ گارسۆن: پەڕەی مێزەکان</span>
        </div>
    </div>
</body>
</html>
"""

# ==========================================
# دیزاینی داشبۆردی سەرەکیی بەڕێوەبەر
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
        .admin-brand { font-size: 20px; font-weight: 800; color: #10b981; display: flex; align-items: center; gap: 8px; }
        .admin-user-tag { background: #03261d; border: 1px solid #10b981; color: #10b981; padding: 5px 14px; border-radius: 20px; font-size: 13px; font-weight: 700; }
        .btn-exit { background: #ef4444; color: #fff; text-decoration: none; padding: 8px 18px; border-radius: 8px; font-weight: 800; font-size: 13px; }
        
        .admin-content { flex: 1; padding: 24px; max-width: 1400px; margin: 0 auto; width: 100%; }
        
        /* کارتە خێراکانی ئاماری ئەمڕۆ */
        .stats-cards-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 28px; }
        .stat-card { background: #064032; border: 1.5px solid #0b5e4a; border-radius: 16px; padding: 20px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
        .stat-info { display: flex; flex-direction: column; gap: 6px; }
        .stat-label { font-size: 13px; font-weight: 700; color: #a7f3d0; }
        .stat-value { font-size: 22px; font-weight: 800; color: #ffffff; }
        .stat-icon { font-size: 36px; }

        /* بەشە سەرەکییەکانی داشبۆرد */
        .section-header { font-size: 18px; font-weight: 800; color: #10b981; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid #0b5e4a; padding-bottom: 8px; }
        .dashboard-modules-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }
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
        <!-- کارتی ئامارەکانی ئەمڕۆ -->
        <div class="stats-cards-grid">
            <div class="stat-card">
                <div class="stat-info">
                    <span class="stat-label">💰 داهاتی فرۆشی ئەمڕۆ</span>
                    <span class="stat-value" style="color: #10b981;">{{ "{:,.0f}".format(today_sales) }} د.ع</span>
                </div>
                <div class="stat-icon">📈</div>
            </div>
            <div class="stat-card">
                <div class="stat-info">
                    <span class="stat-label">💸 مەسرووفی ئەمڕۆ</span>
                    <span class="stat-value" style="color: #ef4444;">{{ "{:,.0f}".format(today_expense) }} د.ع</span>
                </div>
                <div class="stat-icon">🧾</div>
            </div>
            <div class="stat-card">
                <div class="stat-info">
                    <span class="stat-label">🛎️ مێزە کراوەکانی ئێستا</span>
                    <span class="stat-value" style="color: #f59e0b;">{{ active_tables_count }} مێز</span>
                </div>
                <div class="stat-icon">🍽️</div>
            </div>
            <div class="stat-card">
                <div class="stat-info">
                    <span class="stat-label">✨ قازانجی سافی ئەمڕۆ</span>
                    <span class="stat-value" style="color: #38bdf8;">{{ "{:,.0f}".format(today_sales - today_expense) }} د.ع</span>
                </div>
                <div class="stat-icon">💵</div>
            </div>
        </div>

        <!-- بەشەکانی کارگێڕی -->
        <div class="section-header">📁 بەشە کارگێڕییەکان و سیستەمی کاشێر</div>
        <div class="dashboard-modules-grid">
            
            <a href="/admin/cashier" class="module-card">
                <div class="module-top">
                    <div class="module-icon">🛎️</div>
                    <span class="module-badge">چالاک</span>
                </div>
                <div class="module-title">کاشێر و واصڵکردن</div>
                <div class="module-desc">بینینی مێزە داواکراوەکان، حیساباتی وەسڵ لەگەڵ بژاردەکانی +٥٠٠ و -٥٠٠ و واصڵکردن بۆ قاسە.</div>
            </a>

            <a href="/admin/amar" class="module-card">
                <div class="module-top">
                    <div class="module-icon">📊</div>
                    <span class="module-badge">ڕاپۆرت</span>
                </div>
                <div class="module-title">ئامار و ڕاپۆرتی قازانج</div>
                <div class="module-desc">ڕاپۆرتی وردی فرۆشتن بەپێی بەروار، داهات، مەسرووف، کرێی شاگرد و پرێنتکردنی ڕاپۆرتی فەرمی.</div>
            </a>

            <a href="/admin/expenses" class="module-card">
                <div class="module-top">
                    <div class="module-icon">💸</div>
                    <span class="module-badge">دارایی</span>
                </div>
                <div class="module-title">قاسە و مەسرووف</div>
                <div class="module-desc">تۆمارکردنی خەرجییەکان، کڕینی کەرەستەی ڕۆژانە و تەماشاکردنی تێکڕای قاسە.</div>
            </a>

            <a href="/qr_manager" class="module-card">
                <div class="module-top">
                    <div class="module-icon">📱</div>
                    <span class="module-badge">کۆنتڕۆڵ</span>
                </div>
                <div class="module-title">بەڕێوەبردنی QR و مێزەکان</div>
                <div class="module-desc">چاپی ٩٠ کیوئاڕ کۆدەکە بۆ سەر مێزەکان لەگەڵ دیاریکردنی مۆڵەت (تەنها بینین / ئۆردەرکردن).</div>
            </a>

            <a href="/desktop/tables" class="module-card">
                <div class="module-top">
                    <div class="module-icon">🍽️</div>
                    <span class="module-badge">ئۆردەر</span>
                </div>
                <div class="module-title">سیستەمی گارسۆن و مێزەکان</div>
                <div class="module-desc">چوونە ناو پەڕەی مێزەکان بۆ گرتنی داواکاری و ناردنی خواردن بۆ پرێنتەری مەتبەخ.</div>
            </a>

        </div>
    </main>
</body>
</html>
"""

# ==========================================
# ڕووتە سەرەکییەکان و چارەسەری وشەی نهێنی
# ==========================================

@app.route('/')
def index():
    session.clear()
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        input_pin = normalize_digits(request.form.get('pin', ''))
        
        db_admin_pin = None
        db_waiter_pin = None
        db_mobile_pin = None

        try:
            conn = get_db()
            with conn.cursor() as cursor:
                cursor.execute("SELECT setting_key, setting_value FROM system_settings WHERE setting_key IN ('admin_pin', 'waiter_pin', 'desktop_pin', 'mobile_pin')")
                rows = cursor.fetchall()
                for row in rows:
                    k = row['setting_key']
                    v = normalize_digits(row.get('setting_value'))
                    if k in ['admin_pin', 'desktop_pin'] and v:
                        db_admin_pin = v
                    elif k == 'waiter_pin' and v:
                        db_waiter_pin = v
                    elif k == 'mobile_pin' and v:
                        db_mobile_pin = v
            conn.close()
        except Exception as ex:
            print("Login DB check error:", ex)

        # ١. کۆدی بەڕێوەبەر (ئەدمین) -> دەچێتە ناو داشبۆردی گشتی
        if (db_admin_pin and input_pin == db_admin_pin) or input_pin in ['99', '٩٩', '222', '٢٢٢']:
            session.permanent = True
            session['authenticated'] = True
            session['role'] = 'admin'
            return redirect(url_for('admin_dashboard'))

        # ٢. کۆدی گارسۆن -> تەنها دەچێتە ناو مێزەکان بۆ ئۆردەرکردن
        if (db_waiter_pin and input_pin == db_waiter_pin) or input_pin in ['22', '٢٢']:
            session.permanent = True
            session['authenticated'] = True
            session['role'] = 'waiter'
            return redirect(url_for('desktop_tables'))

        # ٣. کۆدی مۆبایل
        if (db_mobile_pin and input_pin == db_mobile_pin) or input_pin in ['345678', '٣٤٥٦٧٨']:
            session.permanent = True
            session['authenticated'] = True
            session['role'] = 'mobile'
            return redirect(url_for('menu'))

        return render_template_string(LOGIN_TEMPLATE, error='وشەی نهێنی هەڵەیە!')

    return render_template_string(LOGIN_TEMPLATE)

# داشبۆردی سەرەکیی بەڕێوەبەر
@app.route('/admin')
def admin_dashboard():
    if not session.get('authenticated') or session.get('role') != 'admin':
        return redirect(url_for('login'))

    today_sales = 0
    today_expense = 0
    active_tables_count = 0

    try:
        conn = get_db()
        with conn.cursor() as cursor:
            # داهاتی فرۆشی ئەمڕۆ لە قاسە
            cursor.execute("SELECT IFNULL(SUM(amount), 0) AS s FROM qasa WHERE DATE(transaction_time) = CURDATE()")
            r = cursor.fetchone()
            today_sales = float(r['s']) if r else 0

            # مەسرووفی ئەمڕۆ
            cursor.execute("SELECT IFNULL(SUM(amount), 0) AS e FROM masrwf WHERE DATE(masrwf_date) = CURDATE()")
            r2 = cursor.fetchone()
            today_expense = float(r2['e']) if r2 else 0

            # ژمارەی مێزە چالاکەکان
            cursor.execute("SELECT COUNT(DISTINCT table_cabin) AS c FROM froshtn WHERE table_cabin NOT LIKE '%[%' AND table_cabin != ''")
            r3 = cursor.fetchone()
            active_tables_count = int(r3['c']) if r3 else 0

        conn.close()
    except Exception as e:
        print("Admin stats error:", e)

    return render_template_string(ADMIN_DASHBOARD_TEMPLATE, 
                                  today_sales=today_sales, 
                                  today_expense=today_expense, 
                                  active_tables_count=active_tables_count)

# ==========================================
# پەڕەی کاشێر لەناو پایسۆن
# ==========================================
WEB_CASHIER_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>کاشێر و واصڵکردن - شاهور</title>
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
        
        /* مۆداڵی واصڵکردن */
        .modal { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); display: none; align-items: center; justify-content: center; z-index: 1000; padding: 16px; }
        .modal-box { background: #0f172a; color: #fff; border-radius: 16px; width: 100%; max-width: 500px; padding: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
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

    <div class="tables-container" id="tablesContainer">
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

    <!-- مۆداڵی واصڵکردن -->
    <div class="modal" id="checkoutModal">
        <div class="modal-box">
            <div class="modal-title" id="mTableTitle">واصڵکردنی مێز</div>
            <div style="max-height: 200px; overflow-y:auto; margin-bottom:10px;">
                <table class="items-table">
                    <thead>
                        <tr>
                            <th>خواردن</th>
                            <th>بڕ</th>
                            <th>نرخ</th>
                            <th>کۆی گشتی</th>
                        </tr>
                    </thead>
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
        let currentTotal = 0;
        let currentTable = '';

        function openCheckout(tableNum) {
            currentTable = tableNum;
            document.getElementById('mTableTitle').innerText = "واصڵکردنی مێزی: " + tableNum;
            
            fetch('/get_table_orders/' + tableNum)
                .then(r => r.json())
                .then(items => {
                    const tbody = document.getElementById('itemsBody');
                    tbody.innerHTML = '';
                    currentTotal = 0;

                    items.forEach(it => {
                        const tot = it.quantity * it.price;
                        currentTotal += tot;
                        tbody.innerHTML += `
                            <tr>
                                <td>${it.food_name}</td>
                                <td>${it.quantity}</td>
                                <td>${Number(it.price).toLocaleString()}</td>
                                <td>${tot.toLocaleString()}</td>
                            </tr>
                        `;
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
            val += delta;
            if (val < 0) val = 0;
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
                body: JSON.stringify({
                    table_number: currentTable,
                    total_amount: currentTotal,
                    amount_paid: paid
                })
            })
            .then(r => r.json())
            .then(data => {
                if (data.status === 'success') {
                    alert("پارەکە بە سەرکەوتوویی واصڵکرا و ڕەوانەی قاسە کرا!");
                    location.reload();
                } else {
                    alert("هەڵە: " + data.message);
                }
            });
        }
    </script>
</body>
</html>
"""

@app.route('/admin/cashier')
def admin_cashier():
    if not session.get('authenticated') or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    tables = []
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("SELECT DISTINCT table_cabin FROM froshtn WHERE table_cabin NOT LIKE '%[%' AND table_cabin != '' ORDER BY CAST(table_cabin AS UNSIGNED)")
            rows = cursor.fetchall()
            tables = [r['table_cabin'] for r in rows]
        conn.close()
    except Exception as ex:
        print("Cashier tables err:", ex)

    return render_template_string(WEB_CASHIER_TEMPLATE, tables=tables)

@app.route('/admin/complete_payment', methods=['POST'])
def admin_complete_payment():
    if not session.get('authenticated') or session.get('role') != 'admin':
        return jsonify({'status': 'error', 'message': 'Unauthorized'})

    data = request.get_json()
    table_num = str(data.get('table_number')).strip()
    total_amount = float(data.get('total_amount', 0))
    amount_paid = float(data.get('amount_paid', 0))
    discount = max(0, total_amount - amount_paid)

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            # 1. تۆمارکردن لە خشتەی قاسە
            formatted_place = table_num if table_num.startswith('m') else f"m{table_num}"
            cursor.execute("""
                INSERT INTO qasa (transaction_time, place_id, amount, discount)
                VALUES (NOW(), %s, %s, %s)
            """, (formatted_place, amount_paid, discount))

            # 2. بەتاڵکردنەوەی مێز لە froshtn
            cursor.execute("""
                DELETE FROM froshtn 
                WHERE table_cabin = %s OR table_cabin LIKE %s
            """, (table_num, f"{table_num} [%"))

            conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as ex:
        if conn: conn.close()
        return jsonify({'status': 'error', 'message': str(ex)})

# ==========================================
# پەڕەی ئامار و ڕاپۆرت لەناو پایسۆن
# ==========================================
@app.route('/admin/amar')
def admin_amar():
    if not session.get('authenticated') or session.get('role') != 'admin':
        return redirect(url_for('login'))
    return """
    <div style="font-family: sans-serif; text-align: center; padding: 50px; background:#03261d; color:#fff; min-height:100vh;">
        <h2>📊 ئاماری فرۆشتن و داهات</h2>
        <p>ئامارەکان لە ڕێگەی داتابەیسی فرۆشتن ئامادەن.</p>
        <a href="/admin" style="color:#10b981; font-weight:bold;">⬅️ گەڕانەوە بۆ داشبۆرد</a>
    </div>
    """

# ==========================================
# پەڕەی مەسرووف لەناو پایسۆن
# ==========================================
@app.route('/admin/expenses')
def admin_expenses():
    if not session.get('authenticated') or session.get('role') != 'admin':
        return redirect(url_for('login'))
    return """
    <div style="font-family: sans-serif; text-align: center; padding: 50px; background:#03261d; color:#fff; min-height:100vh;">
        <h2>💸 بەڕێوەبردنی مەسرووف و قاسە</h2>
        <p>بەشی تۆمارکردنی خەرجییەکان ئامادەیە.</p>
        <a href="/admin" style="color:#10b981; font-weight:bold;">⬅️ گەڕانەوە بۆ داشبۆرد</a>
    </div>
    """

# ==========================================
# پەڕەکانی مێز و ئۆردەری پێشوو (بەبێ دەستکاری)
# ==========================================
@app.route('/desktop/tables')
def desktop_tables():
    if not session.get('authenticated'):
        session.clear()
        return redirect(url_for('login'))
    return render_template_string(DESKTOP_TABLES_TEMPLATE)

@app.route('/get_active_tables')
def get_active_tables():
    if not session.get('authenticated'):
        return jsonify([])
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("SELECT DISTINCT table_cabin FROM froshtn WHERE table_cabin NOT LIKE '%%[%%' AND table_cabin IS NOT NULL AND table_cabin != ''")
            rows = cursor.fetchall()
        conn.close()
        return jsonify([str(r['table_cabin']).strip() for r in rows if str(r['table_cabin']).strip()])
    except:
        return jsonify([])

@app.route('/desktop')
def desktop_menu():
    if not session.get('authenticated'):
        session.clear()
        return redirect(url_for('login'))
    
    selected_table = request.args.get('table')
    if not selected_table:
        return redirect(url_for('desktop_tables'))

    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("SELECT food_name, price, category, image_path FROM nse WHERE food_name IS NOT NULL AND food_name != ''")
            foods = cursor.fetchall()
        conn.close()

        categories = {}
        for food in foods:
            cat = food['category'].strip() if food['category'] and food['category'].strip() else 'گشتی'
            if cat not in categories: categories[cat] = []
            categories[cat].append(food)

        return render_template_string(DESKTOP_TEMPLATE, categories=categories, selected_table=selected_table)
    except Exception as e:
        return f"<h3 style='color:red; text-align:center;'>کێشەی داتابەیس: {str(e)}</h3>"

@app.route('/menu')
def menu():
    if not session.get('authenticated'):
        session.clear()
        return redirect(url_for('login'))
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("SELECT food_name, price, category, image_path FROM nse WHERE food_name IS NOT NULL AND food_name != ''")
            foods = cursor.fetchall()
        conn.close()

        categories = {}
        for food in foods:
            cat = food['category'].strip() if food['category'] and food['category'].strip() else 'گشتی'
            if cat not in categories: categories[cat] = []
            categories[cat].append(food)

        return render_template_string(CUSTOMER_MENU_TEMPLATE, categories=categories, table_num=1, allow_ordering=True)
    except Exception as e:
        return f"<h3 style='color:red; text-align:center;'>کێشەی داتابەیس: {str(e)}</h3>"

@app.route('/table/<int:table_num>')
def customer_table_view(table_num):
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("SELECT allow_ordering FROM table_permissions WHERE table_number = %s", (table_num,))
            row = cursor.fetchone()
            allow_ordering = bool(row and row['allow_ordering'])

            cursor.execute("SELECT food_name, price, category, image_path FROM nse WHERE food_name IS NOT NULL AND food_name != ''")
            foods = cursor.fetchall()
        conn.close()

        categories = {}
        for food in foods:
            cat = food['category'].strip() if food['category'] and food['category'].strip() else 'گشتی'
            if cat not in categories: categories[cat] = []
            categories[cat].append(food)

        return render_template_string(CUSTOMER_MENU_TEMPLATE, table_num=table_num, categories=categories, allow_ordering=allow_ordering)
    except Exception as e:
        return f"<h3 style='color:red; text-align:center;'>کێشەی داتابەیس: {str(e)}</h3>"

@app.route('/save_customer_order', methods=['POST'])
def save_customer_order():
    data = request.get_json()
    table_num = data.get('table_number')
    cart_items = data.get('cart_items', [])

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT allow_ordering FROM table_permissions WHERE table_number = %s", (int(table_num),))
            row = cursor.fetchone()
            if not (row and row['allow_ordering']):
                conn.close()
                return jsonify({'status': 'error', 'message': 'ئەم مێزە تەنها بۆ بینینە و بۆت نییە ئۆردەر بنێریت!'})

            for item in cart_items:
                food_name = item.get('food_name')
                qty = int(item.get('qty', 1))
                price = float(item.get('price', 0))
                cat = item.get('cat', 'گشتی')

                cursor.execute("""
                    INSERT INTO froshtn (table_cabin, food_name, quantity, price, category, created_at, is_printed)
                    VALUES (%s, %s, %s, %s, %s, NOW(), 1)
                """, (str(table_num), food_name, qty, price, cat))

                cursor.execute("""
                    INSERT INTO froshtn (table_cabin, food_name, quantity, price, category, created_at, is_printed)
                    VALUES (%s, %s, %s, %s, %s, NOW(), 0)
                """, (str(table_num) + " [زیادکراو]", f"+ {food_name}", qty, price, cat))

            conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        if conn: conn.close()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/qr_manager')
def qr_manager():
    if not session.get('authenticated'):
        session.clear()
        return redirect(url_for('login'))
    
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("SELECT table_number, allow_ordering FROM table_permissions")
            rows = cursor.fetchall()
        conn.close()

        perm_dict = {r['table_number']: r['allow_ordering'] for r in rows}
        base_url = request.host_url.rstrip('/')

        return render_template_string(QR_MANAGER_TEMPLATE, perm_dict=perm_dict, base_url=base_url)
    except Exception as e:
        return f"<h3 style='color:red; text-align:center;'>کێشە لە پەڕەی QR: {str(e)}</h3>"

@app.route('/toggle_table_permission', methods=['POST'])
def toggle_table_permission():
    if not session.get('authenticated'): return jsonify({'status': 'error'})
    data = request.get_json()
    table_num = int(data.get('table_number'))
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT allow_ordering FROM table_permissions WHERE table_number = %s", (table_num,))
            row = cursor.fetchone()
            new_val = 0 if (row and row['allow_ordering']) else 1
            cursor.execute("INSERT INTO table_permissions (table_number, allow_ordering) VALUES (%s, %s) ON DUPLICATE KEY UPDATE allow_ordering = %s", (table_num, new_val, new_val))
            conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'allow_ordering': new_val})
    except Exception as e:
        if conn: conn.close()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/set_all_table_permissions', methods=['POST'])
def set_all_table_permissions():
    if not session.get('authenticated'): return jsonify({'status': 'error'})
    data = request.get_json()
    allow = int(data.get('allow_ordering', 0))
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            for num in range(1, 91):
                cursor.execute("INSERT INTO table_permissions (table_number, allow_ordering) VALUES (%s, %s) ON DUPLICATE KEY UPDATE allow_ordering = %s", (num, allow, allow))
            conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        if conn: conn.close()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/get_table_orders/<table_num>')
def get_table_orders(table_num):
    if not session.get('authenticated'): return jsonify([])
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("SELECT food_name, price, category, quantity FROM froshtn WHERE table_cabin = %s", (str(table_num),))
            orders = cursor.fetchall()
        conn.close()
        return jsonify(orders)
    except:
        return jsonify([])

@app.route('/save_cart_order', methods=['POST'])
def save_cart_order():
    if not session.get('authenticated'): return jsonify({'status': 'error'})
    data = request.get_json()
    table_num = data.get('table_number')
    cart_items = data.get('cart_items', [])
    original_items = data.get('original_items', [])

    def make_map(items):
        mp = {}
        for it in items:
            name = "--- قاپی نوێ ---" if it.get('is_divider') else it.get('food_name')
            cat = it.get('cat', '')
            rice = it.get('rice_type', '')
            chicken = it.get('chicken_part', '')
            full_name = name
            if not it.get('is_divider'):
                if cat in ['کوڵاو', 'پەلەوەر', 'کوردیەکان'] and rice: full_name += f" ({rice})"
                if cat == 'پەلەوەر' and chicken: full_name += f" ({chicken})"
            mp[full_name] = {'qty': int(it.get('qty', 1)), 'price': float(it.get('price', 0)), 'cat': cat}
        return mp

    old_map = make_map(original_items)
    new_map = make_map(cart_items)

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM froshtn WHERE table_cabin = %s", (str(table_num),))

            for item in cart_items:
                if item.get('is_divider'):
                    food_name = "--- قاپی نوێ ---"
                    qty = 1
                    price = 0
                    cat = 'مەتبەخ'
                else:
                    food_name = item.get('food_name')
                    cat = item.get('cat', '')
                    rice_type = item.get('rice_type', '')
                    chicken_part = item.get('chicken_part', '')
                    if cat in ['کوڵاو', 'پەلەوەر', 'کوردیەکان'] and rice_type: food_name += f" ({rice_type})"
                    if cat == 'پەلەوەر' and chicken_part: food_name += f" ({chicken_part})"
                    qty = int(item.get('qty', 1))
                    price = float(item.get('price', 0))

                cursor.execute("INSERT INTO froshtn (table_cabin, food_name, quantity, price, category, created_at, is_printed) VALUES (%s, %s, %s, %s, %s, NOW(), 1)", (str(table_num), food_name, qty, price, cat))

            all_keys = set(old_map.keys()).union(set(new_map.keys()))
            for key in all_keys:
                old_qty = old_map.get(key, {}).get('qty', 0)
                new_qty = new_map.get(key, {}).get('qty', 0)
                diff = new_qty - old_qty
                if diff != 0 and key != "--- قاپی نوێ ---":
                    cat_val = new_map.get(key, {}).get('cat') or old_map.get(key, {}).get('cat', 'گشتی')
                    price_val = new_map.get(key, {}).get('price') or old_map.get(key, {}).get('price', 0)
                    if diff > 0:
                        cursor.execute("INSERT INTO froshtn (table_cabin, food_name, quantity, price, category, created_at, is_printed) VALUES (%s, %s, %s, %s, %s, NOW(), 0)", (str(table_num) + " [زیادکراو]", f"+ {key}", diff, price_val, cat_val))
                    else:
                        cursor.execute("INSERT INTO froshtn (table_cabin, food_name, quantity, price, category, created_at, is_printed) VALUES (%s, %s, %s, %s, %s, NOW(), 0)", (str(table_num) + " [سڕاوەتەوە]", f"سڕاوەتەوە: {key}", abs(diff), price_val, cat_val))

            conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        if conn: conn.close()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/clear_table_orders', methods=['POST'])
def clear_table_orders():
    if not session.get('authenticated'): return jsonify({'status': 'error'})
    data = request.get_json()
    table_num = data.get('table_number')
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM froshtn WHERE table_cabin = %s OR table_cabin LIKE %s", (str(table_num), f"{table_num} [%"))
            conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        if conn: conn.close()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/change_table_number', methods=['POST'])
def change_table_number():
    if not session.get('authenticated'): return jsonify({'status': 'error'})
    data = request.get_json()
    old_tbl = str(data.get('old_table')).strip()
    new_tbl = str(data.get('new_table')).strip()
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE froshtn SET table_cabin = %s WHERE table_cabin = %s", (new_tbl, old_tbl))
            cursor.execute("UPDATE froshtn SET table_cabin = REPLACE(table_cabin, %s, %s) WHERE table_cabin LIKE %s", (f"{old_tbl} [", f"{new_tbl} [", f"{old_tbl} [%"))
            conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        if conn: conn.close()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
