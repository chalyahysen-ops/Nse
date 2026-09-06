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
# پەڕەی دیسکتۆپ و ئایپاد (بەبێ سەردێڕی ناوەڕۆک)
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
        .desktop-food-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; padding: 10px; display: flex; flex-direction: column; gap: 8px; min-height: 215px; justify-content: space-between; }
        .desktop-food-img { width: 100%; height: 125px; border-radius: 8px; object-fit: cover; cursor: pointer; }
        .desktop-food-info { display: flex; flex-direction: column; gap: 3px; text-align: center; }
        .desktop-food-name { font-size: 13.5px; font-weight: 700; min-height: 36px; display: flex; align-items: center; justify-content: center; }
        .desktop-food-price { font-size: 13px; font-weight: 800; color: var(--success); }

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
                        <img src="{{ items[0].image_path if items[0].image_path and items[0].image_path.startswith('http') else 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=140' }}" class="cat-visual-img" onerror="this.src='https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=140'">
                        <span class="cat-visual-title">{{ cat }}</span>
                    </div>
                {% endfor %}
            </div>
            
            <div class="menu-container-desktop">
                {% for cat, items in categories.items() %}
                <div class="category-desktop-group category-group-item" id="cat-group-{{ loop.index }}">
                    <div class="food-grid">
                        {% for item in items %}
                        <div class="desktop-food-card">
                            <img src="{{ item.image_path if item.image_path and item.image_path.startswith('http') else 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=300' }}" class="desktop-food-img" onclick="updateQty('{{ item.food_name }}', 1, {{ item.price }}, '{{ item.category }}')" onerror="this.src='https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=300'">
                            <div class="desktop-food-info">
                                <div class="desktop-food-name">{{ item.food_name }}</div>
                                <div class="desktop-food-price">{{ "{:,.0f}".format(item.price) }} دینار</div>
                            </div>
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
            if (!found && change > 0) cartItems.push({ is_divider: false, food_name: foodName, price: price, qty: 1, cat: cat || '', rice_type: '', chicken_part: '' });
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
# چارەسەری ناردنی ئۆردەر (API ئۆردەر)
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
            for it in items:
                fname = it.get('food_name')
                qty = int(it.get('qty', 1))
                price = float(it.get('price', 0))
                cat = it.get('cat', 'گشتی')

                # تۆمارکردنی سەرەکی لەسەر مێزەکە
                cur.execute("""
                    INSERT INTO froshtn (table_cabin, food_name, quantity, price, category, created_at, is_printed) 
                    VALUES (%s, %s, %s, %s, %s, NOW(), 1)
                """, (str(tbl), fname, qty, price, cat))

                # تۆمارکردنی کاتی بۆ ئەوەی پرێنتەری مەتبەخ چاپی بکات (is_printed = 0)
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
    return render_template_string(CUSTOMER_MENU_TEMPLATE, table_num=table_num, categories=categories, allow_ordering=True)

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
    return render_template_string(QR_MANAGER_TEMPLATE, base_url=request.host_url.rstrip('/'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
