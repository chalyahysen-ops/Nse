from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session
from datetime import timedelta
import pymysql

app = Flask(__name__)
app.secret_key = 'shahoor_secret_key_super_secure'

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=20)

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

def ensure_qr_table_exists():
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS table_permissions (
                    table_number INT PRIMARY KEY,
                    allow_ordering TINYINT DEFAULT 0
                );
            """)
        conn.commit()
        conn.close()
    except Exception as ex:
        print("Table permissions setup error:", ex)

ensure_qr_table_exists()

# 🛡️ پاراستنی ئاسایش: هەر کاتێک ئینتەر لە ناونیشانی سێرچ بکرێت دەچێتەوە لۆگین
@app.before_request
def enforce_login_on_direct_url():
    exempt_endpoints = ['login', 'customer_table_view', 'save_customer_order', 'static']
    if request.endpoint in exempt_endpoints:
        return

    is_api = request.path.startswith(('/get_', '/save_', '/clear_', '/change_', '/set_', '/toggle_'))
    if is_api:
        return

    referer = request.headers.get('Referer')
    if not referer and request.endpoint != 'login':
        session.clear()
        return redirect(url_for('login'))

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>چوونەژوورەوە - شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background-color: #03261d; color: #f8fafc; display: flex; align-items: center; justify-content: center; min-height: 100vh; padding: 16px; }
        .login-card { background: #064032; border: 1px solid #0b5e4a; padding: 30px 24px; border-radius: 16px; width: 100%; max-width: 380px; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
        .logo { color: #f59e0b; font-size: 24px; font-weight: 800; margin-bottom: 8px; }
        .subtitle { color: #94a3b8; font-size: 13px; margin-bottom: 24px; }
        .pin-input { width: 100%; padding: 14px; background: #03261d; border: 1.5px solid #0b5e4a; border-radius: 10px; color: #f59e0b; font-size: 20px; text-align: center; font-weight: 700; letter-spacing: 4px; outline: none; margin-bottom: 18px; }
        .pin-input:focus { border-color: #10b981; }
        .btn-submit { width: 100%; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #ffffff; border: none; padding: 14px; border-radius: 10px; font-size: 16px; font-weight: 800; cursor: pointer; }
        .error-msg { color: #ef4444; font-size: 13px; margin-top: 14px; }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="logo">✨ شاهور ڕێستۆرانت</div>
        <div class="subtitle">تکایە وشەی نهێنی بنووسە بۆ چوونەژوورەوە</div>
        <form method="POST" action="/login">
            <input type="password" name="pin" class="pin-input" placeholder="••••••" inputmode="numeric" required autofocus>
            <button type="submit" class="btn-submit">چوونەژوورەوە</button>
        </form>
        {% if error %}
            <div class="error-msg">{{ error }}</div>
        {% endif %}
    </div>
</body>
</html>
"""

DESKTOP_TABLES_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>هەڵبژاردنی مێز - شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; -webkit-tap-highlight-color: transparent; }
        html, body { 
            background-color: #03261d; 
            color: #ffffff; 
            min-height: 100%;
            height: auto;
            overflow-x: hidden;
            overflow-y: scroll;
            -webkit-overflow-scrolling: touch; 
        }
        .header-bar { 
            background-color: #064032; 
            padding: 14px 24px; 
            display: flex; 
            align-items: center; 
            justify-content: space-between; 
            border-bottom: 2px solid #0b5e4a; 
            position: sticky;
            top: 0;
            z-index: 1000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        .header-title { font-size: 17px; font-weight: 800; color: #ffffff; text-align: center; flex: 1; }
        .header-actions { display: flex; gap: 8px; align-items: center; }
        .btn-qr-mgr { background-color: #3b82f6; color: #ffffff; border: none; padding: 8px 14px; border-radius: 8px; font-size: 13px; font-weight: 800; text-decoration: none; cursor: pointer; }
        .btn-exit { background-color: #ef4444; color: #ffffff; border: none; padding: 8px 18px; border-radius: 8px; font-size: 14px; font-weight: 800; text-decoration: none; cursor: pointer; }
        
        .tables-grid-wrapper { 
            padding: 18px 20px 80px 20px; 
            width: 100%;
            max-width: 1500px;
            margin: 0 auto;
        }
        .tables-grid { 
            display: grid; 
            grid-template-columns: repeat(10, 1fr); 
            gap: 12px; 
            width: 100%; 
        }
        .table-box { 
            background-color: #ffffff; 
            border: 2px solid #e2e8f0; 
            border-radius: 10px; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            font-size: 28px; 
            font-weight: 800; 
            font-family: 'Segoe UI', Arial, sans-serif; 
            color: #03261d; 
            text-decoration: none; 
            height: 90px;
            box-shadow: 0 3px 6px rgba(0,0,0,0.2);
            transition: all 0.15s ease;
            cursor: pointer; 
            user-select: none; 
        }
        .table-box:hover, .table-box:active { 
            transform: translateY(-2px); 
            border-color: #10b981;
            box-shadow: 0 6px 14px rgba(0,0,0,0.3); 
        }
        .table-box.active-occupied { 
            background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important; 
            color: #ffffff !important; 
            border-color: #047857 !important; 
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.45) !important;
        }

        @media (max-width: 900px) {
            .tables-grid { grid-template-columns: repeat(8, 1fr); gap: 10px; }
            .table-box { height: 80px; font-size: 24px; }
        }
    </style>
</head>
<body>
    <div class="header-bar">
        <a href="/logout" class="btn-exit">✕ دەرچوون</a>
        <div class="header-title">تکایە بۆ ئۆردەرکردنی خواردن و خواردنەوە مێزێک دیاری بکە!</div>
        <div class="header-actions">
            <a href="/qr_manager" class="btn-qr-mgr">📱 بەڕێوەبردنی QR</a>
        </div>
    </div>

    <div class="tables-grid-wrapper">
        <div class="tables-grid" id="tablesGrid">
            {% for num in range(1, 91) %}
                <a href="/desktop?table={{ num }}" class="table-box" id="tbl-box-{{ num }}">
                    {{ num }}
                </a>
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

# فۆڕمی دیسکتۆپ و ئایپاد بە چاککردنی دەرکەوتنی وێنەکانی سەرەوە و لابردنی جیاکەرەوەکانی ناوەڕۆک
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
        :root {
            --bg-main: #0b0f19;
            --bg-card: #151d30;
            --bg-sidebar: #101726;
            --gold: #f59e0b;
            --gold-dark: #d97706;
            --cream: #fef3c7;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border-color: #334155;
            --success: #10b981;
            --danger: #ef4444;
        }
        body { background-color: var(--bg-main); color: var(--text-main); height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
        .desktop-main-layout { display: grid; grid-template-columns: 1fr 480px; flex: 1; overflow: hidden; }
        .menu-section { display: flex; flex-direction: column; padding: 16px 20px; overflow-y: auto; -webkit-overflow-scrolling: touch; }
        
        /* شریتی کارتی جۆرەکان لە سەرەوە بە بەرزی و ڕوونی تەواو تا وێنە و ناوەکان نەبڕدرێن */
        .categories-visual-bar { 
            display: flex; 
            gap: 12px; 
            margin-bottom: 22px; 
            overflow-x: auto; 
            padding: 6px 4px 10px 4px;
            scrollbar-width: thin;
            flex-shrink: 0;
        }
        .categories-visual-bar::-webkit-scrollbar { height: 6px; }
        .categories-visual-bar::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
        
        .cat-visual-btn { 
            background: #151d30; 
            border: 2px solid #334155; 
            border-radius: 14px; 
            padding: 8px 10px; 
            display: flex; 
            flex-direction: column; 
            align-items: center; 
            justify-content: center;
            min-width: 90px; 
            cursor: pointer; 
            transition: all 0.2s ease; 
            user-select: none;
            flex-shrink: 0;
        }
        .cat-visual-btn:hover { border-color: var(--gold); transform: translateY(-2px); }
        .cat-visual-btn.active { 
            background: #1e293b; 
            border-color: var(--gold); 
            box-shadow: 0 4px 14px rgba(245,158,11,0.35); 
        }
        .cat-visual-btn.active .cat-visual-title { color: var(--gold); font-weight: 800; }

        .cat-visual-img { 
            width: 60px; 
            height: 60px; 
            border-radius: 10px; 
            object-fit: cover; 
            background: #0b0f19;
            margin-bottom: 6px;
        }
        .cat-visual-title { 
            font-size: 13px; 
            font-weight: 700; 
            color: #f8fafc; 
            white-space: nowrap; 
        }

        /* تۆڕی یەکدەستی خواردنەکان (بەبێ سەردێڕ و جیاکەرەوە) */
        .food-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); 
            gap: 14px; 
            padding-bottom: 20px; 
        }
        .desktop-food-card { 
            background: var(--bg-card); 
            border: 1px solid var(--border-color); 
            border-radius: 12px; 
            padding: 10px; 
            display: flex; 
            flex-direction: column; 
            gap: 8px; 
            transition: transform 0.2s, border-color 0.2s;
            min-height: 215px;
            justify-content: space-between;
        }
        .desktop-food-card:hover { border-color: var(--gold); transform: translateY(-2px); }
        
        .desktop-food-img { 
            width: 100%; 
            height: 125px; 
            border-radius: 8px; 
            object-fit: cover; 
            background: var(--bg-main); 
            border: 1px solid var(--border-color); 
            cursor: pointer; 
            transition: opacity 0.2s, transform 0.1s; 
        }
        .desktop-food-img:hover { opacity: 0.9; transform: scale(1.02); }
        .desktop-food-img:active { transform: scale(0.98); }

        .desktop-food-info { display: flex; flex-direction: column; gap: 3px; text-align: center; }
        .desktop-food-name { font-size: 13.5px; font-weight: 700; color: var(--text-main); white-space: normal; line-height: 1.3; min-height: 36px; display: flex; align-items: center; justify-content: center; }
        .desktop-food-price { font-size: 13px; font-weight: 800; color: var(--success); }

        .cart-sidebar { background: var(--bg-sidebar); border-right: 1px solid var(--border-color); display: flex; flex-direction: column; padding: 16px; height: 100%; overflow: hidden; }
        
        .cart-top-bar { display: flex; align-items: center; justify-content: space-between; background: var(--bg-card); padding: 8px 12px; border-radius: 10px; border: 1px solid var(--border-color); margin-bottom: 12px; flex-shrink: 0; gap: 6px; }
        .table-badge-header { background: var(--gold); color: var(--bg-main); padding: 5px 12px; border-radius: 6px; font-size: 15px; font-weight: 800; }
        .btn-top-action { background: #1e293b; color: var(--text-main); border: 1px solid var(--border-color); padding: 5px 10px; border-radius: 6px; font-size: 11px; font-weight: 700; cursor: pointer; text-decoration: none; }
        .btn-top-action.change { color: #38bdf8; border-color: rgba(56, 189, 248, 0.4); }
        .btn-top-action.danger { color: var(--danger); border-color: rgba(239,68,68,0.4); }

        .cart-sidebar-header { font-size: 16px; font-weight: 800; color: var(--gold); margin-bottom: 10px; padding-bottom: 6px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; flex-shrink: 0; }
        
        .cart-items-container { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; margin-bottom: 10px; padding-right: 4px; scrollbar-width: thin; -webkit-overflow-scrolling: touch; }
        .cart-items-container::-webkit-scrollbar { width: 6px; }
        .cart-items-container::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 4px; }

        .desktop-cart-row { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; padding: 10px; display: flex; flex-direction: column; gap: 6px; }
        .desktop-cart-top { display: flex; justify-content: space-between; align-items: center; width: 100%; }
        
        .desktop-counter-group { display: flex; align-items: center; background: var(--bg-main); border-radius: 6px; border: 1.5px solid var(--border-color); padding: 2px; gap: 4px; }
        .desktop-btn-count { width: 30px; height: 30px; border-radius: 6px; border: none; background: #1e293b; color: var(--text-main); font-size: 14px; font-weight: 800; cursor: pointer; display: flex; align-items: center; justify-content: center; }
        .desktop-btn-count.plus { background: var(--gold); color: var(--bg-main); }
        .desktop-cart-qty-val { width: 30px; text-align: center; font-size: 14px; font-weight: 800; color: var(--text-main); }
        .desktop-del-btn { background: var(--danger); color: #fff; border: none; width: 30px; height: 30px; border-radius: 6px; font-size: 13px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
        
        .desktop-cart-options { display: flex; gap: 6px; width: 100%; margin-top: 2px; }
        .desktop-select-opt { flex: 1; background: var(--bg-main); color: var(--gold); border: 1.5px solid var(--border-color); padding: 3px 6px; border-radius: 6px; font-size: 11px; font-weight: 700; outline: none; height: 26px; }
        
        .plate-sep-desktop { background: #8b5cf6; color: #ffffff; padding: 6px 10px; border-radius: 8px; font-size: 12px; font-weight: 800; display: flex; justify-content: space-between; align-items: center; margin: 6px 0; }
        
        .cart-sidebar-footer { border-top: 1px solid var(--border-color); padding-top: 10px; display: flex; flex-direction: column; gap: 8px; flex-shrink: 0; }
        .cart-total-box { display: flex; justify-content: space-between; align-items: center; font-size: 15px; font-weight: 800; }
        .cart-total-val { color: var(--success); font-size: 18px; }
        
        .cart-actions-bottom { display: flex; gap: 8px; width: 100%; }
        .btn-send-desktop { flex: 2; background: linear-gradient(135deg, var(--gold) 0%, var(--gold-dark) 100%); color: var(--bg-main); border: none; padding: 11px; border-radius: 8px; font-size: 14px; font-weight: 800; cursor: pointer; transition: all 0.2s; text-align: center; box-shadow: 0 4px 15px rgba(245,158,11,0.2); }
        .btn-send-desktop.saved-success { background: linear-gradient(135deg, var(--success) 0%, #059669 100%) !important; color: #ffffff !important; }
        .btn-add-plate-desktop { flex: 1; background: #8b5cf6; color: #ffffff; border: none; padding: 11px; border-radius: 8px; font-size: 12px; font-weight: 800; cursor: pointer; display: none; text-align: center; transition: opacity 0.2s; }
        
        #toastMsg { position: fixed; top: 20px; left: 50%; transform: translateX(-50%); background: var(--success); color: #ffffff; padding: 10px 24px; border-radius: 30px; font-size: 14px; font-weight: 700; z-index: 1000; box-shadow: 0 4px 20px rgba(0,0,0,0.5); display: none; opacity: 0; transition: opacity 0.3s ease; }
        .table-dropdown { background: var(--bg-main); color: var(--gold); border: 1.5px solid var(--gold); padding: 8px 12px; border-radius: 8px; font-size: 15px; font-weight: 800; outline: none; }
    </style>
</head>
<body>
    <div id="toastMsg">✅ بە سەرکەوتوویی بۆ مەتبەخ نێردرا</div>

    <div class="desktop-main-layout">
        <div class="menu-section">
            
            <!-- شریتی وێنەداری جۆرەکان بە قەبارەی تەواو و دیاریکراو -->
            <div class="categories-visual-bar" id="categoriesTabs">
                <div class="cat-visual-btn active" onclick="filterCat('all', this)">
                    <img src="https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=140" class="cat-visual-img" alt="هەموو">
                    <span class="cat-visual-title">هەموو</span>
                </div>
                {% for cat, items in categories.items() %}
                    <div class="cat-visual-btn" onclick="filterCat('cat-group-{{ loop.index }}', this)">
                        <img src="{{ items[0].image_path if items[0].image_path and items[0].image_path.startswith('http') else 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=140' }}" class="cat-visual-img" onerror="this.src='https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=140'">
                        <span class="cat-visual-title">{{ cat }}</span>
                    </div>
                {% endfor %}
            </div>
            
            <!-- کانتەینەری خواردنەکان بەبێ سەردێڕ و دەقی جیاکەرەوە -->
            <div class="menu-container-desktop">
                {% for cat, items in categories.items() %}
                <div class="category-desktop-group category-group-item" id="cat-group-{{ loop.index }}" data-cat-name="{{ cat }}">
                    <div class="food-grid">
                        {% for item in items %}
                        <div class="desktop-food-card">
                            <img src="{{ item.image_path if item.image_path and item.image_path.startswith('http') else 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=300' }}" 
                                   class="desktop-food-img" 
                                   onclick="updateQty('{{ item.food_name }}', 1, {{ item.price }}, '{{ item.category }}')"
                                   onerror="this.src='https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=300'"
                                   title="کلیک بکە بۆ زیادکردن">
                            
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
                <div style="display:flex; align-items:center; gap:6px;">
                    <div class="table-badge-header">📍 مێزی {{ selected_table }}</div>
                    <input type="hidden" id="currentTableNum" value="{{ selected_table }}">
                </div>
                <div style="display:flex; gap:4px;">
                    <button type="button" class="btn-top-action change" onclick="openChangeTableModal()">🔄 گۆڕین</button>
                    <a href="/desktop/tables" class="btn-top-action">⬅️ مێزەکان</a>
                    <button type="button" class="btn-top-action danger" onclick="clearCurrentTableOrders()">🗑 سڕینەوە</button>
                </div>
            </div>

            <div class="cart-sidebar-header">
                <span>🛒 داواکارییەکانی مێز</span>
                <span id="cartCountBadge" style="background: var(--gold); color: var(--bg-main); padding: 2px 8px; border-radius: 10px; font-size: 12px;">0</span>
            </div>
            
            <div class="cart-items-container" id="cartItemsList">
                <div style="text-align: center; color: var(--text-muted); padding: 40px 0;">سەبەتە بەتاڵە</div>
            </div>
            
            <div class="cart-sidebar-footer">
                <div class="cart-total-box">
                    <span>کۆی گشتی:</span>
                    <span class="cart-total-val" id="cartTotalTxt">0 دینار</span>
                </div>
                <div class="cart-actions-bottom">
                    <button type="button" id="btnAddPlateDesktop" class="btn-add-plate-desktop" onclick="addNewPlateDivider()">➕ قاپی نوێ</button>
                    <button type="button" id="btnSubmitDesktop" class="btn-send-desktop" onclick="submitFinalOrder()">ناردن بۆ مەتبەخ ➔</button>
                </div>
            </div>
        </div>
    </div>

    <div id="changeTableModal" style="position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.8); z-index:500; display:none; align-items:center; justify-content:center;">
        <div style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 16px; padding: 24px; width: 100%; max-width: 380px; text-align: center;">
            <div style="font-size: 18px; font-weight: 800; color: var(--gold); margin-bottom: 12px;">🔄 گواستنەوەی مێز</div>
            <p style="color: var(--text-muted); font-size: 13px; margin-bottom: 16px;">ژمارەی ئەو مێزە نوێیە دیاری بکە کە ئۆردەرەکەی بۆ دەگوازیتەوە:</p>
            <select id="newTableSelect" class="table-dropdown" style="width: 100%; padding: 10px; margin-bottom: 18px;">
                {% for num in range(1, 91) %}
                    <option value="{{ num }}">مێزی {{ num }}</option>
                {% endfor %}
            </select>
            <div style="display: flex; gap: 8px;">
                <button type="button" class="btn-send-desktop" style="flex: 1; padding: 10px;" onclick="confirmChangeTable()">گواستنەوە</button>
                <button type="button" class="btn-top-action" style="flex: 1; justify-content: center;" onclick="toggleChangeTableModal(false)">پاشگەزبوونەوە</button>
            </div>
        </div>
    </div>

    <script>
        let cartItems = [];
        let originalTableOrders = [];
        const tableNum = document.getElementById('currentTableNum').value;

        function showToast(text, isError = false) {
            const toast = document.getElementById('toastMsg');
            toast.innerText = text;
            toast.style.background = isError ? 'var(--danger)' : 'var(--success)';
            toast.style.display = 'block';
            setTimeout(() => { toast.style.opacity = '1'; }, 10);
            setTimeout(() => {
                toast.style.opacity = '0';
                setTimeout(() => { toast.style.display = 'none'; }, 300);
            }, 2500);
        }
        function setButtonStateNormal() {
            const btn = document.getElementById('btnSubmitDesktop');
            if (btn) { btn.classList.remove('saved-success'); btn.innerHTML = 'ناردن بۆ مەتبەخ ➔'; }
        }
        function setButtonStateSaved() {
            const btn = document.getElementById('btnSubmitDesktop');
            if (btn) { btn.classList.add('saved-success'); btn.innerHTML = '✅ نێردرا بۆ مەتبەخ'; }
        }
        function checkHasGrill() {
            let hasGrill = cartItems.some(i => !i.is_divider && i.cat === 'برژاو');
            document.getElementById('btnAddPlateDesktop').style.display = hasGrill ? 'block' : 'none';
        }
        function addNewPlateDivider() {
            if (cartItems.length === 0 || cartItems[cartItems.length - 1].is_divider) {
                showToast("تکایە سەرەتا خواردنێک دیاری بکە!", true);
                return;
            }
            cartItems.push({ is_divider: true, food_name: '--- قاپی نوێ ---', price: 0, qty: 1, cat: 'مەتبەخ' });
            setButtonStateNormal();
            checkHasGrill();
            renderCart();
            showToast("قاپی نوێ زیادکرا");
        }
        function updateQty(foodName, change, price, cat) {
            setButtonStateNormal();
            let found = false;
            for (let i = cartItems.length - 1; i >= 0; i--) {
                if (cartItems[i].is_divider) break;
                if (cartItems[i].food_name === foodName) {
                    cartItems[i].qty += change;
                    if (cartItems[i].qty <= 0) { cartItems.splice(i, 1); }
                    found = true;
                    break;
                }
            }
            if (!found && change > 0) {
                cartItems.push({ is_divider: false, food_name: foodName, price: price, qty: 1, cat: cat || '', rice_type: '', chicken_part: '' });
            }
            checkHasGrill();
            renderCart();
        }
        function removeCartIndex(index) {
            setButtonStateNormal();
            cartItems.splice(index, 1);
            checkHasGrill();
            renderCart();
        }
        function modifyItemQty(index, change) {
            setButtonStateNormal();
            if (cartItems[index] && !cartItems[index].is_divider) {
                cartItems[index].qty += change;
                if (cartItems[index].qty <= 0) { cartItems.splice(index, 1); }
                checkHasGrill();
                renderCart();
            }
        }
        function updateItemRice(index, val) { setButtonStateNormal(); cartItems[index].rice_type = val; }
        function updateItemChicken(index, val) { setButtonStateNormal(); cartItems[index].chicken_part = val; }
        
        function renderCart() {
            const list = document.getElementById('cartItemsList');
            list.innerHTML = '';
            if (cartItems.length === 0) {
                list.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 40px 0;">سەبەتە بەتاڵە</div>';
                document.getElementById('cartTotalTxt').innerText = '0 دینار';
                document.getElementById('cartCountBadge').innerText = '0';
                return;
            }
            let total = 0, count = 0, plateNum = 1;
            cartItems.forEach((item, index) => {
                if (item.is_divider) {
                    plateNum++;
                    const sep = document.createElement('div');
                    sep.className = 'plate-sep-desktop';
                    sep.innerHTML = `<span>🍽 قاپی ${plateNum}</span> <button type="button" style="background:var(--danger); color:#fff; border:none; width:22px; height:22px; border-radius:6px; cursor:pointer; font-size:11px; display:flex; align-items:center; justify-content:center;" onclick="removeCartIndex(${index})">✕</button>`;
                    list.appendChild(sep);
                } else {
                    total += (item.qty * item.price);
                    count += item.qty;
                    let showRice = ['کوڵاو', 'پەلەوەر', 'کوردیەکان'].includes(item.cat);
                    let showChicken = (item.cat === 'پەلەوەر');
                    let optionsHtml = '';
                    if (showRice || showChicken) {
                        optionsHtml += `<div class="desktop-cart-options">`;
                        if (showRice) {
                            let rVal = item.rice_type || '';
                            optionsHtml += `
                                <select class="desktop-select-opt" onchange="updateItemRice(${index}, this.value)">
                                    <option value="">جۆری برنج</option>
                                    <option value="برنجی درێژ" ${rVal === 'برنجی درێژ' ? 'selected' : ''}>برنجی درێژ</option>
                                    <option value="برنجی خڕ" ${rVal === 'برنجی خڕ' ? 'selected' : ''}>برنجی خڕ</option>
                                    <option value="برنجی کوردی" ${rVal === 'برنجی کوردی' ? 'selected' : ''}>برنجی کوردی</option>
                                    <option value="برنج بە سرکە" ${rVal === 'برنج بە سرکە' ? 'selected' : ''}>برنج بە سرکە</option>
                                </select>`;
                        }
                        if (showChicken) {
                            let cVal = item.chicken_part || '';
                            optionsHtml += `
                                <select class="desktop-select-opt" onchange="updateItemChicken(${index}, this.value)">
                                    <option value="">بەشی مریشک</option>
                                    <option value="سینگ" ${cVal === 'سینگ' ? 'selected' : ''}>سینگ</option>
                                    <option value="ڕان" ${cVal === 'ڕان' ? 'selected' : ''}>ڕان</option>
                                </select>`;
                        }
                        optionsHtml += `</div>`;
                    }
                    const row = document.createElement('div');
                    row.className = 'desktop-cart-row';
                    row.innerHTML = `
                        <div class="desktop-cart-top">
                            <div class="desktop-counter-group">
                                <button type="button" class="desktop-del-btn" onclick="removeCartIndex(${index})" title="سڕینەوە">🗑</button>
                                <button type="button" class="desktop-btn-count" onclick="modifyItemQty(${index}, -1)">-</button>
                                <span class="desktop-cart-qty-val">${item.qty}</span>
                                <button type="button" class="desktop-btn-count plus" onclick="modifyItemQty(${index}, 1)">+</button>
                            </div>
                            <div style="text-align: left;">
                                <div style="font-weight:800; font-size:13px; color:#fff;">${item.food_name}</div>
                                <div style="color:var(--success); font-size:11px; font-weight:700;">${(item.qty * item.price).toLocaleString()} دینار</div>
                            </div>
                        </div>
                        ${optionsHtml}`;
                    list.appendChild(row);
                }
            });
            document.getElementById('cartTotalTxt').innerText = total.toLocaleString() + ' دینار';
            document.getElementById('cartCountBadge').innerText = count;
        }

        function filterCat(catId, btn) {
            document.querySelectorAll('.cat-visual-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const groups = document.querySelectorAll('.category-group-item');
            groups.forEach(group => {
                if (catId === 'all') { group.style.display = 'block'; }
                else { group.style.display = (group.id === catId) ? 'block' : 'none'; }
            });
        }

        function fetchTableOrders() {
            fetch('/get_table_orders/' + tableNum)
                .then(res => res.json())
                .then(data => {
                    cartItems = [];
                    originalTableOrders = [];
                    if (data && data.length > 0) {
                        data.forEach(item => {
                            const isDiv = (item.food_name.includes('قاپی نوێ') || item.category === 'مەتبەخ');
                            let fName = item.food_name, rType = '', cPart = '';
                            ['برنجی درێژ', 'برنجی خڕ', 'برنجی کوردی', 'برنج بە سرکە'].forEach(r => {
                                if (fName.includes(`(${r})`)) { rType = r; fName = fName.replace(` (${r})`, '').trim(); }
                            });
                            ['سینگ', 'ڕان'].forEach(c => {
                                if (fName.includes(`(${c})`)) { cPart = c; fName = fName.replace(` (${c})`, '').trim(); }
                            });
                            
                            let parsedItem = { is_divider: isDiv, food_name: fName, qty: parseInt(item.quantity), price: parseFloat(item.price), cat: item.category || '', rice_type: rType, chicken_part: cPart };
                            cartItems.push(parsedItem);
                            originalTableOrders.push(JSON.parse(JSON.stringify(parsedItem)));
                        });
                        setButtonStateSaved();
                    } else { setButtonStateNormal(); }
                    checkHasGrill();
                    renderCart();
                }).catch(() => {});
        }
        function submitFinalOrder() {
            if (cartItems.length === 0) { showToast("تکایە سەرەتا خواردن دیاری بکە!", true); return; }
            
            fetch('/save_cart_order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ table_number: tableNum, cart_items: cartItems, original_items: originalTableOrders })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    showToast("✅ داواکارییەکە بۆ مەتبەخ نێردرا");
                    setTimeout(() => {
                        window.location.href = '/desktop/tables';
                    }, 800);
                } else { showToast('هەڵە لە ناردن: ' + data.message, true); }
            }).catch(() => showToast("کێشە لە پەیوەندی سێرڤەر!", true));
        }
        function clearCurrentTableOrders() {
            if (confirm("ئایا دڵنیایت لە سڕینەوە و بەتاڵکردنی تەواوی مێزی " + tableNum + "؟")) {
                fetch('/clear_table_orders', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ table_number: tableNum })
                })
                .then(res => res.json())
                .then(data => {
                    if (data.success || data.status === 'success') {
                        showToast("مێزی " + tableNum + " بەتاڵکرایەوە");
                        fetchTableOrders();
                    }
                });
            }
        }

        function openChangeTableModal() {
            document.getElementById('newTableSelect').value = tableNum;
            toggleChangeTableModal(true);
        }
        function toggleChangeTableModal(show) {
            document.getElementById('changeTableModal').style.display = show ? 'flex' : 'none';
        }
        function confirmChangeTable() {
            const oldTbl = tableNum;
            const newTbl = document.getElementById('newTableSelect').value;
            if (oldTbl === newTbl) {
                showToast("تکایە ژمارەیەکی جیاواز دیاری بکە!", true);
                return;
            }
            fetch('/change_table_number', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ old_table: oldTbl, new_table: newTbl })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    toggleChangeTableModal(false);
                    showToast("گوازرایەوە بۆ مێزی " + newTbl);
                    setTimeout(() => {
                        window.location.href = '/desktop?table=' + newTbl;
                    }, 600);
                } else {
                    showToast("هەڵە لە گواستنەوە: " + data.message, true);
                }
            }).catch(() => showToast("کێشە لە پەیوەندی سێرڤەر!", true));
        }

        window.onload = function() { fetchTableOrders(); };
    </script>
</body>
</html>
"""

# فۆڕمی نوێی موشتەری و مۆبایل ڕێک بەپێی وێنەکەت
CUSTOMER_MENU_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>مێنیوی شاهور - مێزی {{ table_num }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; -webkit-tap-highlight-color: transparent; }
        body { 
            background-color: #03261d; 
            color: #ffffff; 
            padding-bottom: {{ '115px' if allow_ordering else '30px' }}; 
            min-height: 100vh;
        }
        
        .top-header-bar {
            background-color: #03261d;
            padding: 10px 14px 6px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .header-brand {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 17px;
            font-weight: 800;
            color: #ffffff;
        }
        .table-pill {
            background-color: #059669;
            color: #ffffff;
            font-size: 12px;
            font-weight: 800;
            padding: 4px 12px;
            border-radius: 20px;
        }

        .categories-carousel {
            display: flex;
            overflow-x: auto;
            gap: 10px;
            padding: 10px 12px 14px;
            scrollbar-width: none;
        }
        .categories-carousel::-webkit-scrollbar { display: none; }
        
        .cat-card-item {
            background: #064032;
            border: 2px solid transparent;
            border-radius: 12px;
            padding: 5px;
            display: flex;
            flex-direction: column;
            align-items: center;
            width: 76px;
            flex-shrink: 0;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.2s;
        }
        .cat-card-item.active {
            border-color: #ef4444;
            background: #085341;
        }
        .cat-img-box {
            width: 62px;
            height: 62px;
            border-radius: 10px;
            overflow: hidden;
            background: #021a14;
            margin-bottom: 5px;
        }
        .cat-img-box img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .cat-title-text {
            font-size: 11px;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 5px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            width: 100%;
            text-align: center;
        }
        .cat-plus-pill {
            background: #10b981;
            color: #03261d;
            width: 100%;
            height: 20px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            font-weight: 900;
        }

        .foods-container {
            padding: 0 12px;
        }
        .food-grid-2col {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
        }
        .food-card-white {
            background: #ffffff;
            border-radius: 14px;
            padding: 8px;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.25);
            position: relative;
        }
        .food-img-hero {
            width: 100%;
            height: 120px;
            border-radius: 10px;
            object-fit: cover;
            margin-bottom: 8px;
            background: #f1f5f9;
        }
        .food-title-main {
            font-size: 14px;
            font-weight: 800;
            color: #0f172a;
            margin-bottom: 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            width: 100%;
        }
        .food-price-red {
            font-size: 14px;
            font-weight: 800;
            color: #e11d48;
            margin-bottom: 6px;
        }

        .mini-stepper {
            display: flex;
            align-items: center;
            background: #f1f5f9;
            border-radius: 8px;
            padding: 2px;
            gap: 4px;
            width: 100%;
            justify-content: space-between;
        }
        .btn-step {
            width: 32px;
            height: 32px;
            border-radius: 6px;
            border: none;
            background: #e2e8f0;
            color: #0f172a;
            font-size: 16px;
            font-weight: 800;
            cursor: pointer;
        }
        .btn-step.add {
            background: #10b981;
            color: #ffffff;
        }
        .qty-val-display {
            font-size: 14px;
            font-weight: 800;
            color: #0f172a;
        }

        .bottom-checkout-bar {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(3, 38, 29, 0.95);
            backdrop-filter: blur(10px);
            border-top: 1px solid #0b5e4a;
            padding: 12px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            z-index: 200;
        }
        .cart-bubble-btn {
            display: flex;
            align-items: center;
            gap: 8px;
            background: #064032;
            padding: 8px 14px;
            border-radius: 10px;
            cursor: pointer;
        }
        .cart-counter-pill {
            background: #10b981;
            color: #03261d;
            font-size: 12px;
            font-weight: 800;
            padding: 2px 8px;
            border-radius: 12px;
        }
        .cart-sum-txt {
            color: #ffffff;
            font-weight: 800;
            font-size: 13.5px;
        }
        .btn-submit-order {
            background: #10b981;
            color: #ffffff;
            border: none;
            padding: 10px 20px;
            border-radius: 10px;
            font-size: 13.5px;
            font-weight: 800;
            cursor: pointer;
        }

        .modal-shade {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.75);
            z-index: 300;
            display: none;
            align-items: flex-end;
        }
        .modal-bottom-box {
            background: #064032;
            width: 100%;
            max-height: 80vh;
            border-radius: 20px 20px 0 0;
            padding: 18px 16px;
            display: flex;
            flex-direction: column;
            border-top: 2px solid #10b981;
        }
        .modal-items-scroller {
            overflow-y: auto;
            flex: 1;
            margin: 12px 0;
        }
        .cart-row-item {
            background: #03261d;
            padding: 10px 12px;
            border-radius: 10px;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        #toastBox {
            position: fixed;
            top: 65px;
            left: 50%;
            transform: translateX(-50%);
            background: #10b981;
            color: #ffffff;
            padding: 9px 20px;
            border-radius: 30px;
            font-size: 13px;
            font-weight: 700;
            z-index: 1000;
            box-shadow: 0 4px 15px rgba(0,0,0,0.4);
            display: none;
            opacity: 0;
            transition: opacity 0.3s ease;
        }
    </style>
</head>
<body>
    <div id="toastBox">✅ بە سەرکەوتوویی نێردرا</div>

    <header class="top-header-bar">
        <div class="header-brand">
            <span>✨ شاهور ڕێستۆرانت</span>
        </div>
        <div class="table-pill">مێزی {{ table_num }}</div>
    </header>

    {% if not allow_ordering %}
    <div style="background:#064032; color:#a7f3d0; font-size:11px; text-align:center; padding:6px; border-bottom:1px solid #0b5e4a;">
        ℹ️ تەنها بینینی مێنیوە. بۆ داواکردن پەیوەندی بە کارمەند بکەن.
    </div>
    {% endif %}

    <div class="categories-carousel">
        <div class="cat-card-item active" onclick="filterMenu('all', this)">
            <div class="cat-img-box">
                <img src="https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=150" alt="هەموو">
            </div>
            <div class="cat-title-text">هەموو</div>
            <div class="cat-plus-pill">+</div>
        </div>

        {% for cat, items in categories.items() %}
        <div class="cat-card-item" onclick="filterMenu('group-{{ loop.index }}', this)">
            <div class="cat-img-box">
                <img src="{{ items[0].image_path if items[0].image_path and items[0].image_path.startswith('http') else 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=150' }}" onerror="this.src='https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=150'">
            </div>
            <div class="cat-title-text">{{ cat }}</div>
            <div class="cat-plus-pill">+</div>
        </div>
        {% endfor %}
    </div>

    <div class="foods-container">
        {% for cat, items in categories.items() %}
        <div class="category-block-wrapper" id="group-{{ loop.index }}" style="margin-bottom: 16px;">
            <div class="food-grid-2col">
                {% for item in items %}
                <div class="food-card-white">
                    <img src="{{ item.image_path if item.image_path and item.image_path.startswith('http') else 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=300' }}" 
                         class="food-img-hero" 
                         onerror="this.src='https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=300'">
                    
                    <div class="food-title-main">{{ item.food_name }}</div>
                    <div class="food-price-red">{{ "{:,.0f}".format(item.price) }} د.ع</div>

                    {% if allow_ordering %}
                    <div class="mini-stepper">
                        <button type="button" class="btn-step" onclick="changeQty('{{ item.food_name }}', -1, {{ item.price }}, '{{ item.category }}')">-</button>
                        <span class="qty-val-display" id="count_{{ item.food_name }}">0</span>
                        <button type="button" class="btn-step add" onclick="changeQty('{{ item.food_name }}', 1, {{ item.price }}, '{{ item.category }}')">+</button>
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
            setTimeout(() => { toast.style.opacity = '1'; }, 10);
            setTimeout(() => {
                toast.style.opacity = '0';
                setTimeout(() => { toast.style.display = 'none'; }, 300);
            }, 2500);
        }

        function filterMenu(groupId, el) {
            document.querySelectorAll('.cat-card-item').forEach(c => c.classList.remove('active'));
            el.classList.add('active');
            
            const groups = document.querySelectorAll('.category-block-wrapper');
            groups.forEach(g => {
                if (groupId === 'all') { g.style.display = 'block'; }
                else { g.style.display = (g.id === groupId) ? 'block' : 'none'; }
            });
        }

        function changeQty(name, delta, price, cat) {
            let found = false;
            for (let i = myCart.length - 1; i >= 0; i--) {
                if (myCart[i].food_name === name) {
                    myCart[i].qty += delta;
                    if (myCart[i].qty <= 0) { myCart.splice(i, 1); }
                    found = true;
                    break;
                }
            }
            if (!found && delta > 0) {
                myCart.push({ food_name: name, price: price, qty: 1, cat: cat || '' });
            }
            refreshCounterDisplays();
            renderCartUI();
        }

        function refreshCounterDisplays() {
            document.querySelectorAll('.qty-val-display').forEach(d => d.innerText = '0');
            myCart.forEach(item => {
                const el = document.getElementById('count_' + item.food_name);
                if (el) el.innerText = item.qty;
            });
        }

        function renderCartUI() {
            let total = 0, count = 0;
            const scroller = document.getElementById('cartScrollerList');
            if (scroller) scroller.innerHTML = '';

            myCart.forEach(item => {
                total += (item.qty * item.price);
                count += item.qty;

                if (scroller) {
                    const row = document.createElement('div');
                    row.className = 'cart-row-item';
                    row.innerHTML = `
                        <div style="text-align: right;">
                            <div style="font-weight:700; font-size:13.5px; color:#fff;">${item.food_name}</div>
                            <div style="color:#10b981; font-size:12px; font-weight:700;">${(item.qty * item.price).toLocaleString()} د.ع</div>
                        </div>
                        <span style="background:#064032; border:1px solid #10b981; padding:3px 10px; border-radius:6px; font-weight:800;">${item.qty}</span>
                    `;
                    scroller.appendChild(row);
                }
            });

            if (document.getElementById('cartBadgeCount')) {
                document.getElementById('cartBadgeCount').innerText = count;
                document.getElementById('cartTotalDisplay').innerText = total.toLocaleString() + ' د.ع';
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
                } else {
                    showNotification(data.message || 'هەڵە لە ناردن', true);
                }
            }).catch(() => showNotification("کێشە لە پەیوەندی سێرڤەر!", true));
        }
    </script>
</body>
</html>
"""

HTML_TEMPLATE = CUSTOMER_MENU_TEMPLATE

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
            <a href="/desktop/tables" class="btn">⬅️ مێزەکان</a>
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
                    if (data.status === 'success') {
                        location.reload();
                    }
                });
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    session.clear()
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        input_pin = normalize_digits(request.form.get('pin', ''))
        
        db_mobile_pin = None
        db_desktop_pin = None
        try:
            conn = get_db()
            with conn.cursor() as cursor:
                cursor.execute("SELECT setting_key, setting_value FROM system_settings WHERE setting_key IN ('mobile_pin', 'desktop_pin')")
                rows = cursor.fetchall()
                for row in rows:
                    if row['setting_key'] == 'mobile_pin' and row.get('setting_value'):
                        db_mobile_pin = normalize_digits(row['setting_value'])
                    elif row['setting_key'] == 'desktop_pin' and row.get('setting_value'):
                        db_desktop_pin = normalize_digits(row['setting_value'])
            conn.close()
        except Exception as ex:
            print("Database Error in Login:", ex)

        if (db_desktop_pin and input_pin == db_desktop_pin) or input_pin in ['22', '٢٢']:
            session.permanent = True
            session['authenticated'] = True
            return redirect(url_for('desktop_tables'))

        if (db_mobile_pin and input_pin == db_mobile_pin) or input_pin in ['345678', '٣٤٥٦٧٨']:
            session.permanent = True
            session['authenticated'] = True
            return redirect(url_for('menu'))

        return render_template_string(LOGIN_TEMPLATE, error='وشەی نهێنی هەڵەیە!')

    return render_template_string(LOGIN_TEMPLATE)

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
            cursor.execute("""
                SELECT DISTINCT table_cabin 
                FROM froshtn 
                WHERE table_cabin NOT LIKE '%%[%%' 
                  AND table_cabin IS NOT NULL 
                  AND table_cabin != ''
            """)
            rows = cursor.fetchall()
        conn.close()
        
        active_list = [str(r['table_cabin']).strip() for r in rows if str(r['table_cabin']).strip()]
        return jsonify(active_list)
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
            if cat not in categories:
                categories[cat] = []
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
            if cat not in categories:
                categories[cat] = []
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
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(food)

        return render_template_string(CUSTOMER_MENU_TEMPLATE, 
                                      table_num=table_num, 
                                      categories=categories, 
                                      allow_ordering=allow_ordering)
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
    if not session.get('authenticated'):
        return jsonify({'status': 'error', 'message': 'Unauthorized'})
    
    data = request.get_json()
    table_num = int(data.get('table_number'))

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT allow_ordering FROM table_permissions WHERE table_number = %s", (table_num,))
            row = cursor.fetchone()
            new_val = 0 if (row and row['allow_ordering']) else 1

            cursor.execute("""
                INSERT INTO table_permissions (table_number, allow_ordering) 
                VALUES (%s, %s) 
                ON DUPLICATE KEY UPDATE allow_ordering = %s
            """, (table_num, new_val, new_val))
            conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'allow_ordering': new_val})
    except Exception as e:
        if conn: conn.close()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/set_all_table_permissions', methods=['POST'])
def set_all_table_permissions():
    if not session.get('authenticated'):
        return jsonify({'status': 'error', 'message': 'Unauthorized'})
    
    data = request.get_json()
    allow = int(data.get('allow_ordering', 0))

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            for num in range(1, 91):
                cursor.execute("""
                    INSERT INTO table_permissions (table_number, allow_ordering) 
                    VALUES (%s, %s) 
                    ON DUPLICATE KEY UPDATE allow_ordering = %s
                """, (num, allow, allow))
            conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        if conn: conn.close()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/get_table_orders/<table_num>')
def get_table_orders(table_num):
    if not session.get('authenticated'):
        return jsonify([])
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT food_name, price, category, quantity 
                FROM froshtn 
                WHERE table_cabin = %s
            """, (str(table_num),))
            orders = cursor.fetchall()
        conn.close()
        return jsonify(orders)
    except:
        return jsonify([])

@app.route('/save_cart_order', methods=['POST'])
def save_cart_order():
    if not session.get('authenticated'):
        return jsonify({'status': 'error', 'message': 'ڕێگەپێنەدراو'})

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
                if cat in ['کوڵاو', 'پەلەوەر', 'کوردیەکان'] and rice:
                    full_name += f" ({rice})"
                if cat == 'پەلەوەر' and chicken:
                    full_name += f" ({chicken})"
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
                    
                    if cat in ['کوڵاو', 'پەلەوەر', 'کوردیەکان'] and rice_type:
                        food_name += f" ({rice_type})"
                    if cat == 'پەلەوەر' and chicken_part:
                        food_name += f" ({chicken_part})"

                    qty = int(item.get('qty', 1))
                    price = float(item.get('price', 0))

                cursor.execute("""
                    INSERT INTO froshtn (table_cabin, food_name, quantity, price, category, created_at, is_printed)
                    VALUES (%s, %s, %s, %s, %s, NOW(), 1)
                """, (str(table_num), food_name, qty, price, cat))

            all_keys = set(old_map.keys()).union(set(new_map.keys()))
            for key in all_keys:
                old_qty = old_map.get(key, {}).get('qty', 0)
                new_qty = new_map.get(key, {}).get('qty', 0)
                diff = new_qty - old_qty
                
                if diff != 0 and key != "--- قاپی نوێ ---":
                    cat_val = new_map.get(key, {}).get('cat') or old_map.get(key, {}).get('cat', 'گشتی')
                    price_val = new_map.get(key, {}).get('price') or old_map.get(key, {}).get('price', 0)
                    
                    if diff > 0:
                        cursor.execute("""
                            INSERT INTO froshtn (table_cabin, food_name, quantity, price, category, created_at, is_printed)
                            VALUES (%s, %s, %s, %s, %s, NOW(), 0)
                        """, (str(table_num) + " [زیادکراو]", f"+ {key}", diff, price_val, cat_val))
                    else:
                        cursor.execute("""
                            INSERT INTO froshtn (table_cabin, food_name, quantity, price, category, created_at, is_printed)
                            VALUES (%s, %s, %s, %s, %s, NOW(), 0)
                        """, (str(table_num) + " [سڕاوەتەوە]", f"سڕاوەتەوە: {key}", abs(diff), price_val, cat_val))

            conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        if conn: conn.close()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/clear_table_orders', methods=['POST'])
def clear_table_orders():
    if not session.get('authenticated'):
        return jsonify({'status': 'error', 'message': 'ڕێگەپێنەدراو'})
    data = request.get_json()
    table_num = data.get('table_number')
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                DELETE FROM froshtn 
                WHERE table_cabin = %s 
                   OR table_cabin LIKE %s
            """, (str(table_num), f"{table_num} [%"))
            conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        if conn: conn.close()
        return jsonify({'status': 'error', 'message': str(e)})

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

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
