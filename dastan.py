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
# بەشی قاسە (۲٤ کاتژمێر)
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
# بەشی مەسرووفات
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
# بەشی شاگردەکان
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
# بەڕێوەبردنی مێنۆی خواردنەکان
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
# بەڕێوەبردنی کیوئاڕ کۆد (QR Manager)
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
        body { background-color: #03261d; color: #f8fafc; padding: 20px; }
        .top-nav { display: flex; justify-content: space-between; align-items: center; background: #064032; padding: 14px 20px; border-radius: 12px; border: 1px solid #0b5e4a; margin-bottom: 20px; }
        .top-title { font-size: 18px; font-weight: 800; color: #10b981; }
        .nav-btns { display: flex; gap: 10px; }
        .btn { background: #3b82f6; color: #fff; border: none; padding: 8px 16px; border-radius: 8px; font-weight: 700; text-decoration: none; cursor: pointer; font-size: 13px; }
        .btn-green { background: #10b981; }
        .btn-red { background: #ef4444; }
        .btn-gold { background: #f59e0b; color: #0b0f19; font-weight: 800; }
        
        .tables-perm-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
        .table-perm-card { background: #064032; border: 1.5px solid #0b5e4a; border-radius: 10px; padding: 12px; display: flex; flex-direction: column; gap: 8px; }
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
        {% set is_allowed = perm_dict.get(num, 1) == 1 %}
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
# پەڕەی موشتەری و مۆبایل بە برنج و مریشکەوە
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

        .options-group { width: 100%; display: flex; flex-direction: column; gap: 4px; margin-bottom: 6px; }
        .select-sub-opt { width: 100%; padding: 4px; border-radius: 6px; border: 1px solid #cbd5e1; background: #f8fafc; font-size: 11px; font-weight: 700; color: #03261d; outline: none; }

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
                            <option value="">جۆری برنج</option>
                            <option value="برنجی درێژ">برنجی درێژ</option>
                            <option value="برنجی خڕ">برنجی خڕ</option>
                            <option value="برنجی کوردی">برنجی کوردی</option>
                            <option value="برنج بە سرکە">برنج بە سرکە</option>
                        </select>
                        {% endif %}
                        {% if show_chicken %}
                        <select class="select-sub-opt" id="opt_chicken_{{ item_id_safe }}">
                            <option value="">بەشی مریشک</option>
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
# ڕێڕەوەکانی سیستەم (Routes)
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
        return f"<h3 style='color:red; text-align:center;'>کێشە لە پەڕەی مێز</h3>"

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
