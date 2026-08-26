from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session
import pymysql

app = Flask(__name__)
app.secret_key = 'shahoor_secret_key_super_secure'

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

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <title>چوونەژوورەوە - شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; }
        body { background-color: #0b0f19; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; padding: 16px; }
        .login-card { background: #151d30; border: 1px solid #334155; padding: 30px 24px; border-radius: 16px; width: 100%; max-width: 380px; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
        .logo { color: #f59e0b; font-size: 24px; font-weight: 800; margin-bottom: 8px; }
        .subtitle { color: #94a3b8; font-size: 13px; margin-bottom: 24px; }
        .pin-input { width: 100%; padding: 14px; background: #0f172a; border: 1.5px solid #334155; border-radius: 10px; color: #f59e0b; font-size: 20px; text-align: center; font-weight: 700; letter-spacing: 4px; outline: none; margin-bottom: 18px; }
        .pin-input:focus { border-color: #f59e0b; }
        .btn-submit { width: 100%; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: #0b0f19; border: none; padding: 14px; border-radius: 10px; font-size: 16px; font-weight: 800; cursor: pointer; }
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

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <title>مێنیوی شاهور</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; -webkit-tap-highlight-color: transparent; }
        body { background-color: #0b0f19; color: #f8fafc; padding-bottom: 120px; }

        .app-header {
            background: linear-gradient(180deg, #161f32 0%, #0b0f19 100%);
            padding: 14px 16px 8px;
            text-align: center;
            border-bottom: 1px solid rgba(245, 158, 11, 0.2);
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .restaurant-name { color: #f59e0b; font-size: 20px; font-weight: 800; }
        .tagline { color: #94a3b8; font-size: 11px; margin-top: 2px; }

        .table-bar {
            background: #1e293b;
            margin: 10px 16px;
            padding: 10px 12px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border: 1px solid #334155;
            gap: 8px;
        }
        .table-info { display: flex; align-items: center; gap: 6px; }
        .table-info label { font-weight: 700; font-size: 13px; color: #f8fafc; }
        .table-select {
            background: #0f172a;
            color: #f59e0b;
            border: 1.5px solid #f59e0b;
            padding: 6px 10px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 700;
            outline: none;
        }

        .table-actions { display: flex; align-items: center; gap: 6px; }
        .btn-action {
            border: none;
            padding: 7px 10px;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 700;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .btn-change-tbl { background: #0284c7; color: #ffffff; }
        .btn-clear-tbl { background: #ef4444; color: #ffffff; }

        .btn-add-plate {
            background: #8b5cf6;
            color: #ffffff;
            border: none;
            padding: 7px 10px;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 700;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .categories-scroll {
            display: flex;
            overflow-x: auto;
            gap: 8px;
            padding: 4px 16px 12px;
            scrollbar-width: none;
        }
        .categories-scroll::-webkit-scrollbar { display: none; }
        .cat-chip {
            background: #1e293b;
            color: #94a3b8;
            padding: 7px 16px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            white-space: nowrap;
            text-decoration: none;
            border: 1px solid #334155;
        }
        .cat-chip.active { background: #f59e0b; color: #0b0f19; font-weight: 800; border-color: #f59e0b; }

        .menu-container { padding: 0 16px; }
        .category-block { margin-bottom: 18px; }
        .category-title { color: #f59e0b; font-size: 15px; font-weight: 700; margin-bottom: 10px; display: flex; align-items: center; gap: 8px; }
        .category-title::after { content: ''; flex: 1; height: 1px; background: #334155; }

        .food-card {
            background: #151d30;
            border: 1px solid #243048;
            border-radius: 14px;
            padding: 10px;
            margin-bottom: 10px;
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .food-img { width: 68px; height: 68px; border-radius: 10px; object-fit: cover; background: #0b0f19; border: 1px solid #334155; flex-shrink: 0; }
        .food-details { flex: 1; min-width: 0; }
        .food-name { font-size: 14px; font-weight: 700; color: #ffffff; margin-bottom: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .food-price { font-size: 13px; font-weight: 700; color: #10b981; }

        .counter-group { display: flex; align-items: center; background: #0b0f19; border-radius: 8px; border: 1px solid #334155; padding: 2px; gap: 3px; }
        .btn-count { width: 30px; height: 30px; border-radius: 6px; border: none; background: #1e293b; color: #ffffff; font-size: 15px; font-weight: 700; cursor: pointer; }
        .btn-count.plus { background: #f59e0b; color: #0b0f19; }
        .qty-val { width: 26px; text-align: center; font-size: 14px; font-weight: 700; color: #ffffff; background: transparent; border: none; outline: none; }

        .bottom-cart-bar {
            position: fixed;
            bottom: 0; left: 0; right: 0;
            background: rgba(15, 23, 42, 0.98);
            backdrop-filter: blur(10px);
            border-top: 1px solid #334155;
            padding: 12px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            z-index: 200;
        }
        .cart-info-btn {
            display: flex;
            align-items: center;
            gap: 10px;
            background: #1e293b;
            padding: 8px 14px;
            border-radius: 10px;
            border: 1px solid #334155;
            cursor: pointer;
        }
        .cart-badge { background: #f59e0b; color: #0b0f19; font-size: 11px; font-weight: 800; padding: 2px 7px; border-radius: 10px; }
        .cart-total-txt { font-size: 14px; font-weight: 800; color: #10b981; }
        
        /* دوگمەی ناردن */
        .btn-send-main {
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            color: #0b0f19;
            border: none;
            padding: 10px 20px;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 800;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        /* ستایلی سەوز بۆ دوگمەی ناردن کاتێک سەرکەوتوو بوو */
        .btn-send-main.saved-success {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
            color: #ffffff !important;
        }

        .modal-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.75);
            z-index: 300;
            display: none;
            align-items: flex-end;
        }
        .modal-sheet {
            background: #151d30;
            width: 100%;
            max-height: 80vh;
            border-radius: 20px 20px 0 0;
            padding: 18px 16px;
            display: flex;
            flex-direction: column;
            border-top: 1px solid #334155;
        }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; border-bottom: 1px solid #334155; padding-bottom: 8px; }
        .modal-title { font-size: 16px; font-weight: 800; color: #f59e0b; }
        .close-btn { background: none; border: none; color: #ef4444; font-size: 18px; font-weight: 800; cursor: pointer; }
        .cart-items-list { overflow-y: auto; flex: 1; max-height: 50vh; margin-bottom: 14px; }
        .cart-item-row { display: flex; justify-content: space-between; align-items: center; background: #0f172a; padding: 10px; border-radius: 8px; margin-bottom: 8px; }
        .del-item-btn { color: #ef4444; background: #1e293b; border: 1px solid #334155; font-size: 14px; cursor: pointer; width: 30px; height: 30px; border-radius: 6px; display: flex; align-items: center; justify-content: center; }

        .plate-separator-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: #8b5cf6;
            color: #ffffff;
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 800;
            margin: 10px 0;
        }

        .modal-center-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.8);
            z-index: 400;
            display: none;
            align-items: center;
            justify-content: center;
            padding: 16px;
        }
        .modal-center-card {
            background: #151d30;
            border: 1px solid #334155;
            border-radius: 16px;
            padding: 20px;
            width: 100%;
            max-width: 360px;
            text-align: center;
        }
    </style>
</head>
<body>

    <header class="app-header">
        <div class="restaurant-name">✨ شاهور ڕێستۆرانت</div>
        <div class="tagline">سیستەمی داواکاری مۆبایل</div>
    </header>

    <div class="table-bar">
        <div class="table-info">
            <label>📍 مێزی:</label>
            <select id="tableSelect" class="table-select" onchange="onTableChanged(this.value)">
                {% for num in range(1, 91) %}
                    <option value="{{ num }}">{{ num }}</option>
                {% endfor %}
            </select>
        </div>

        <div class="table-actions">
            <button type="button" class="btn-add-plate" onclick="addNewPlateDivider()">➕ قاپی نوێ</button>
            <button type="button" class="btn-action btn-change-tbl" onclick="openChangeTableModal()">🔄 گۆڕین</button>
            <button type="button" class="btn-action btn-clear-tbl" onclick="clearCurrentTableOrders()">🗑 سڕینەوە</button>
        </div>
    </div>

    <div class="categories-scroll">
        <a href="javascript:void(0)" class="cat-chip active" onclick="filterCat('all', this)">هەموو</a>
        {% for cat in categories.keys() %}
            <a href="javascript:void(0)" class="cat-chip" onclick="filterCat('cat-{{ loop.index }}', this)">{{ cat }}</a>
        {% endfor %}
    </div>

    <div class="menu-container">
        {% for cat, items in categories.items() %}
        <div class="category-block" id="cat-{{ loop.index }}">
            <div class="category-title">{{ cat }}</div>
            {% for item in items %}
            <div class="food-card">
                <img src="{{ item.image_path if item.image_path and item.image_path.startswith('http') else 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=200' }}" class="food-img" onerror="this.src='https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=200'">

                <div class="food-details">
                    <div class="food-name">{{ item.food_name }}</div>
                    <div class="food-price">{{ "{:,.0f}".format(item.price) }} دینار</div>
                </div>

                <div class="counter-group">
                    <button type="button" class="btn-count" onclick="updateQty('{{ item.food_name }}', -1, {{ item.price }}, '{{ item.category }}')">-</button>
                    <input type="text" id="qty_{{ item.food_name }}" value="0" class="qty-val" readonly>
                    <button type="button" class="btn-count plus" onclick="updateQty('{{ item.food_name }}', 1, {{ item.price }}, '{{ item.category }}')">+</button>
                </div>
            </div>
            {% endfor %}
        </div>
        {% endfor %}
    </div>

    <div class="bottom-cart-bar">
        <div class="cart-info-btn" onclick="openCartModal()">
            <span style="font-size: 18px;">🛒</span>
            <span class="cart-badge" id="cartCount">0</span>
            <span class="cart-total-txt" id="cartTotalTxt">0 دینار</span>
        </div>
        <button type="button" id="btnSubmitMain" class="btn-send-main" onclick="submitFinalOrder()">ناردنی داواکاری ➔</button>
    </div>

    <!-- مۆداڵی سەبەتە -->
    <div class="modal-overlay" id="cartModal" onclick="closeCartModal(event)">
        <div class="modal-sheet" onclick="event.stopPropagation()">
            <div class="modal-header">
                <span class="modal-title">🛒 خواردنەکانی ناو سەبەتە</span>
                <button type="button" class="close-btn" onclick="toggleCartModal(false)">✕</button>
            </div>
            <div class="cart-items-list" id="cartItemsList"></div>
            <div style="display: flex; gap: 8px; margin-top: 8px;">
                <button type="button" class="btn-add-plate" style="flex: 1; padding: 12px; justify-content: center;" onclick="addNewPlateDivider()">➕ قاپی نوێ (هێڵ)</button>
                <button type="button" id="btnSubmitModal" class="btn-send-main" style="flex: 2; padding: 12px;" onclick="submitFinalOrder()">ناردن بۆ مەتبەخ</button>
            </div>
        </div>
    </div>

    <!-- مۆداڵی گۆڕینی ژمارەی مێز -->
    <div class="modal-center-overlay" id="changeTableModal" onclick="toggleChangeTableModal(false)">
        <div class="modal-center-card" onclick="event.stopPropagation()">
            <div class="modal-title" style="margin-bottom: 12px;">🔄 گواستنەوەی مێز</div>
            <p style="color: #94a3b8; font-size: 13px; margin-bottom: 16px;">ژمارەی ئەو مێزە دیاری بکە کە دەتەوێت ئۆردەرەکەی بۆ بگوازیتەوە:</p>
            
            <select id="newTableSelect" class="table-select" style="width: 100%; padding: 10px; font-size: 16px; margin-bottom: 18px;">
                {% for num in range(1, 91) %}
                    <option value="{{ num }}">مێزی {{ num }}</option>
                {% endfor %}
            </select>

            <div style="display: flex; gap: 8px;">
                <button type="button" class="btn-send-main" style="flex: 1; padding: 10px;" onclick="confirmChangeTable()">گواستنەوە</button>
                <button type="button" class="btn-action btn-clear-tbl" style="flex: 1; justify-content: center;" onclick="toggleChangeTableModal(false)">پاشگەزبوونەوە</button>
            </div>
        </div>
    </div>

    <script>
        let cartItems = []; 
        let hasUnsavedChanges = false;

        // ڕێکخستنەوەی ڕەنگی دوگمەکە بۆ دۆخی ئاسایی (پرتەقاڵی)
        function setButtonStateNormal() {
            hasUnsavedChanges = true;
            const btnMain = document.getElementById('btnSubmitMain');
            const btnModal = document.getElementById('btnSubmitModal');
            if (btnMain) {
                btnMain.classList.remove('saved-success');
                btnMain.innerHTML = 'ناردنی داواکاری ➔';
            }
            if (btnModal) {
                btnModal.classList.remove('saved-success');
                btnModal.innerHTML = 'ناردن بۆ مەتبەخ';
            }
        }

        // ڕێکخستنی ڕەنگی دوگمەکە بۆ سەوز دوای ناردنی سەرکەوتوو
        function setButtonStateSaved() {
            hasUnsavedChanges = false;
            const btnMain = document.getElementById('btnSubmitMain');
            const btnModal = document.getElementById('btnSubmitModal');
            if (btnMain) {
                btnMain.classList.add('saved-success');
                btnMain.innerHTML = '✅ نێردرا بۆ مەتبەخ';
            }
            if (btnModal) {
                btnModal.classList.add('saved-success');
                btnModal.innerHTML = '✅ نێردرا بۆ مەتبەخ';
            }
        }

        function resetInputs() {
            document.querySelectorAll('.qty-val').forEach(el => el.value = 0);
        }

        function addNewPlateDivider() {
            if (cartItems.length === 0 || cartItems[cartItems.length - 1].is_divider) {
                alert("تکایە سەرەتا خواردنێک دیاری بکە پاشان قاپی نوێ لێبدە!");
                return;
            }
            cartItems.push({
                is_divider: true,
                food_name: '--- قاپی نوێ / هێڵ ---',
                price: 0,
                qty: 1,
                cat: 'مەتبەخ'
            });
            setButtonStateNormal();
            renderCartSummary();
            if (document.getElementById('cartModal').style.display === 'flex') {
                renderCartModalList();
            }
        }

        function updateQty(foodName, change, price, cat) {
            setButtonStateNormal();
            let found = false;
            for (let i = cartItems.length - 1; i >= 0; i--) {
                if (cartItems[i].is_divider) break;
                if (cartItems[i].food_name === foodName) {
                    cartItems[i].qty += change;
                    if (cartItems[i].qty <= 0) {
                        cartItems.splice(i, 1);
                    }
                    found = true;
                    break;
                }
            }

            if (!found && change > 0) {
                cartItems.push({
                    is_divider: false,
                    food_name: foodName,
                    price: price,
                    qty: 1,
                    cat: cat || ''
                });
            }

            updateMenuCardInputs();
            renderCartSummary();
        }

        function updateMenuCardInputs() {
            resetInputs();
            cartItems.forEach(item => {
                if (!item.is_divider) {
                    const input = document.getElementById('qty_' + item.food_name);
                    if (input) {
                        input.value = (parseInt(input.value) || 0) + item.qty;
                    }
                }
            });
        }

        function removeCartIndex(index) {
            setButtonStateNormal();
            cartItems.splice(index, 1);
            updateMenuCardInputs();
            renderCartSummary();
            renderCartModalList();
        }

        function renderCartSummary() {
            let total = 0;
            let count = 0;
            cartItems.forEach(item => {
                if (!item.is_divider) {
                    total += (item.qty * item.price);
                    count += item.qty;
                }
            });
            document.getElementById('cartTotalTxt').innerText = total.toLocaleString() + ' دینار';
            document.getElementById('cartCount').innerText = count;
        }

        function openCartModal() {
            renderCartModalList();
            toggleCartModal(true);
        }

        function toggleCartModal(show) {
            document.getElementById('cartModal').style.display = show ? 'flex' : 'none';
        }

        function closeCartModal(e) {
            if (e.target.id === 'cartModal') toggleCartModal(false);
        }

        function renderCartModalList() {
            const list = document.getElementById('cartItemsList');
            list.innerHTML = '';

            if (cartItems.length === 0) {
                list.innerHTML = '<div style="text-align:center; color:#94a3b8; padding:20px;">سەبەتە بەتاڵە!</div>';
                return;
            }

            let plateNum = 1;
            const startHeader = document.createElement('div');
            startHeader.className = 'plate-separator-row';
            startHeader.innerHTML = `<span>🍽 قاپی ١</span>`;
            list.appendChild(startHeader);

            cartItems.forEach((item, index) => {
                if (item.is_divider) {
                    plateNum++;
                    const sep = document.createElement('div');
                    sep.className = 'plate-separator-row';
                    sep.innerHTML = `
                        <span>🍽 قاپی ${plateNum} (هێڵی مەتبەخ)</span>
                        <button type="button" class="del-item-btn" style="background:#ef4444; color:#fff;" onclick="removeCartIndex(${index})">✕</button>
                    `;
                    list.appendChild(sep);
                } else {
                    const row = document.createElement('div');
                    row.className = 'cart-item-row';
                    row.innerHTML = `
                        <div class="counter-group">
                            <button type="button" class="del-item-btn" onclick="removeCartIndex(${index})" title="سڕینەوە">🗑</button>
                            <button type="button" class="btn-count" onclick="modifyItemQty(${index}, -1)">-</button>
                            <span style="padding:0 8px; font-weight:700;">${item.qty}</span>
                            <button type="button" class="btn-count plus" onclick="modifyItemQty(${index}, 1)">+</button>
                        </div>
                        <div style="text-align: left;">
                            <div style="font-weight:700; font-size:13px; color:#fff;">${item.food_name}</div>
                            <div style="color:#10b981; font-size:11px;">${(item.qty * item.price).toLocaleString()} دینار</div>
                        </div>
                    `;
                    list.appendChild(row);
                }
            });
        }

        function modifyItemQty(index, change) {
            setButtonStateNormal();
            if (cartItems[index] && !cartItems[index].is_divider) {
                cartItems[index].qty += change;
                if (cartItems[index].qty <= 0) {
                    cartItems.splice(index, 1);
                }
                updateMenuCardInputs();
                renderCartSummary();
                renderCartModalList();
            }
        }

        function filterCat(catId, btn) {
            document.querySelectorAll('.cat-chip').forEach(c => c.classList.remove('active'));
            btn.classList.add('active');

            const blocks = document.querySelectorAll('.category-block');
            if (catId === 'all') {
                blocks.forEach(b => b.style.display = 'block');
            } else {
                blocks.forEach(b => b.style.display = (b.id === catId) ? 'block' : 'none');
            }
        }

        // کاتێک مێز دەگۆڕدرێت لە ڕێگەی Select
        function onTableChanged(newTableNum) {
            fetchTableOrders(newTableNum);
        }

        // هێنانی داواکارییە تۆمارکراوەکانی مێزەکە لە داتابەیس
        function fetchTableOrders(tableNum) {
            fetch('/get_table_orders/' + tableNum)
                .then(res => res.json())
                .then(data => {
                    cartItems = [];
                    resetInputs();

                    if (data.length > 0) {
                        data.forEach(item => {
                            const isDiv = (item.food_name.includes('قاپی نوێ') || item.category === 'مەتبەخ');
                            cartItems.push({
                                is_divider: isDiv,
                                food_name: item.food_name,
                                qty: parseInt(item.quantity),
                                price: parseFloat(item.price),
                                cat: item.category || ''
                            });
                        });
                        setButtonStateSaved();
                    } else {
                        setButtonStateNormal();
                    }
                    updateMenuCardInputs();
                    renderCartSummary();
                    if (document.getElementById('cartModal').style.display === 'flex') {
                        renderCartModalList();
                    }
                })
                .catch(() => {});
        }

        function submitFinalOrder() {
            const tableNum = document.getElementById('tableSelect').value;
            if (cartItems.length === 0) {
                alert("تکایە سەرەتا خواردن دیاری بکە!");
                return;
            }

            fetch('/save_cart_order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ table_number: tableNum, cart_items: cartItems })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    toggleCartModal(false);
                    setButtonStateSaved();
                    alert('داواکارییەکە بە سەرکەوتوویی بۆ مەتبەخ و کاشێر تۆمارکرا!');
                } else {
                    alert('هەڵە لە ناردن: ' + data.message);
                }
            })
            .catch(err => alert("کێشە لە پەیوەندی سێرڤەر!"));
        }

        function clearCurrentTableOrders() {
            const currentTbl = document.getElementById('tableSelect').value;
            if (confirm("ئایا دڵنیایت لە سڕینەوە و بەتاڵکردنی تەواوی مێزی " + currentTbl + "؟")) {
                fetch('/clear_table_orders', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ table_number: currentTbl })
                })
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') {
                        alert("مێزی " + currentTbl + " بە سەرکەوتوویی بەتاڵکرایەوە!");
                        fetchTableOrders(currentTbl);
                    } else {
                        alert("هەڵە لە سڕینەوە: " + data.message);
                    }
                });
            }
        }

        function openChangeTableModal() {
            const currentTbl = document.getElementById('tableSelect').value;
            document.getElementById('newTableSelect').value = currentTbl;
            toggleChangeTableModal(true);
        }

        function toggleChangeTableModal(show) {
            document.getElementById('changeTableModal').style.display = show ? 'flex' : 'none';
        }

        function confirmChangeTable() {
            const oldTbl = document.getElementById('tableSelect').value;
            const newTbl = document.getElementById('newTableSelect').value;

            if (oldTbl === newTbl) {
                alert("تکایە ژمارەیەکی جیاواز دیاری بکە!");
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
                    alert("داواکارییەکان بە سەرکەوتوویی گوازرانەوە بۆ مێزی " + newTbl);
                    document.getElementById('tableSelect').value = newTbl;
                    fetchTableOrders(newTbl);
                } else {
                    alert("هەڵە لە گواستنەوە: " + data.message);
                }
            });
        }

        window.onload = function() {
            fetchTableOrders(document.getElementById('tableSelect').value);
        };
    </script>
</body>
</html>
"""

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        pin = request.form.get('pin')
        if pin == '345678' or pin == '٣٤٥٦٧٨':
            session['authenticated'] = True
            return redirect(url_for('menu'))
        else:
            return render_template_string(LOGIN_TEMPLATE, error='وشەی نهێنی هەڵەیە!')
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/')
def menu():
    if not session.get('authenticated'):
        return redirect(url_for('login'))

    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("SELECT food_name, price, category, image_path FROM nse WHERE food_name IS NOT NULL AND food_name != ''")
            foods = cursor.fetchall()
        conn.close()

        categories = {}
        for food in foods:
            cat = food['category'] if food['category'] else 'گشتی'
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(food)

        return render_template_string(HTML_TEMPLATE, categories=categories)
    except Exception as e:
        return f"<h3 style='color:red; text-align:center;'>کێشەی داتابەیس: {str(e)}</h3>"

@app.route('/get_table_orders/<table_num>')
def get_table_orders(table_num):
    if not session.get('authenticated'):
        return jsonify([])

    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, food_name, price, category, quantity 
                FROM froshtn 
                WHERE table_cabin = %s 
                ORDER BY id ASC
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

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM froshtn WHERE table_cabin = %s", (str(table_num),))

            for item in cart_items:
                food_name = item.get('food_name')
                qty = int(item.get('qty', 1))
                price = float(item.get('price', 0))
                cat = item.get('cat', '')

                cursor.execute("""
                    INSERT INTO froshtn (table_cabin, food_name, quantity, price, category, created_at, is_printed)
                    VALUES (%s, %s, %s, %s, %s, NOW(), 0)
                """, (str(table_num), food_name, qty, price, cat))

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
            cursor.execute("DELETE FROM froshtn WHERE table_cabin = %s", (str(table_num),))
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
    old_tbl = data.get('old_table')
    new_tbl = data.get('new_table')

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE froshtn SET table_cabin = %s WHERE table_cabin = %s", (str(new_tbl), str(old_tbl)))
            conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        if conn: conn.close()
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
