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

def normalize_digits(text):
    if not text:
        return ""
    text = str(text).strip()
    eastern_digits = '٠١٢٣٤٥٦٧٨٩'
    western_digits = '0123456789'
    trans_table = str.maketrans(eastern_digits, western_digits)
    return text.translate(trans_table)

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
    <title>مێنیوی شاهور - مۆبایل</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; -webkit-tap-highlight-color: transparent; }
        body { background-color: #0b0f19; color: #f8fafc; padding-bottom: 120px; }
        .app-header { background: linear-gradient(180deg, #161f32 0%, #0b0f19 100%); padding: 14px 16px 8px; text-align: center; border-bottom: 1px solid rgba(245, 158, 11, 0.2); position: sticky; top: 0; z-index: 100; }
        .restaurant-name { color: #f59e0b; font-size: 20px; font-weight: 800; }
        .tagline { color: #94a3b8; font-size: 11px; margin-top: 2px; }
        .table-bar { background: #1e293b; margin: 10px 16px; padding: 10px 12px; border-radius: 12px; display: flex; align-items: center; justify-content: space-between; border: 1px solid #334155; gap: 8px; }
        .table-info { display: flex; align-items: center; gap: 6px; }
        .table-info label { font-weight: 700; font-size: 13px; color: #f8fafc; }
        .table-select { background: #0f172a; color: #f59e0b; border: 1.5px solid #f59e0b; padding: 6px 10px; border-radius: 8px; font-size: 14px; font-weight: 700; outline: none; }
        .table-actions { display: flex; align-items: center; gap: 6px; }
        .btn-action { border: none; padding: 7px 10px; border-radius: 8px; font-size: 11px; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 4px; }
        .btn-change-tbl { background: #0284c7; color: #ffffff; }
        .btn-clear-tbl { background: #ef4444; color: #ffffff; }
        .btn-add-plate { background: #8b5cf6; color: #ffffff; border: none; padding: 7px 10px; border-radius: 8px; font-size: 11px; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 4px; }
        .categories-scroll { display: flex; overflow-x: auto; gap: 8px; padding: 4px 16px 12px; scrollbar-width: none; }
        .categories-scroll::-webkit-scrollbar { display: none; }
        .cat-chip { background: #1e293b; color: #94a3b8; padding: 7px 16px; border-radius: 20px; font-size: 12px; font-weight: 600; white-space: nowrap; text-decoration: none; border: 1px solid #334155; }
        .cat-chip.active { background: #f59e0b; color: #0b0f19; font-weight: 800; border-color: #f59e0b; }
        .menu-container { padding: 0 16px; }
        .category-block { margin-bottom: 18px; }
        .category-title { color: #f59e0b; font-size: 15px; font-weight: 700; margin-bottom: 10px; display: flex; align-items: center; gap: 8px; }
        .category-title::after { content: ''; flex: 1; height: 1px; background: #334155; }
        .food-card { background: #151d30; border: 1px solid #243048; border-radius: 14px; padding: 10px; margin-bottom: 10px; display: flex; gap: 10px; align-items: center; }
        .food-img { width: 68px; height: 68px; border-radius: 10px; object-fit: cover; background: #0b0f19; border: 1px solid #334155; flex-shrink: 0; }
        .food-details { flex: 1; min-width: 0; }
        .food-name { font-size: 14px; font-weight: 700; color: #ffffff; margin-bottom: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .food-price { font-size: 13px; font-weight: 700; color: #10b981; }
        .counter-group { display: flex; align-items: center; background: #0b0f19; border-radius: 8px; border: 1px solid #334155; padding: 2px; gap: 3px; }
        .btn-count { width: 30px; height: 30px; border-radius: 6px; border: none; background: #1e293b; color: #ffffff; font-size: 15px; font-weight: 700; cursor: pointer; }
        .btn-count.plus { background: #f59e0b; color: #0b0f19; }
        .qty-val { width: 26px; text-align: center; font-size: 14px; font-weight: 700; color: #ffffff; background: transparent; border: none; outline: none; }
        .bottom-cart-bar { position: fixed; bottom: 0; left: 0; right: 0; background: rgba(15, 23, 42, 0.98); backdrop-filter: blur(10px); border-top: 1px solid #334155; padding: 12px 16px; display: flex; align-items: center; justify-content: space-between; z-index: 200; }
        .cart-info-btn { display: flex; align-items: center; gap: 10px; background: #1e293b; padding: 8px 14px; border-radius: 10px; border: 1px solid #334155; cursor: pointer; }
        .cart-badge { background: #f59e0b; color: #0b0f19; font-size: 11px; font-weight: 800; padding: 2px 7px; border-radius: 10px; }
        .cart-total-txt { font-size: 14px; font-weight: 800; color: #10b981; }
        .btn-send-main { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: #0b0f19; border: none; padding: 10px 18px; border-radius: 10px; font-size: 13px; font-weight: 800; cursor: pointer; transition: all 0.25s ease; }
        .btn-send-main.saved-success { background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important; color: #ffffff !important; }
        .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.75); z-index: 300; display: none; align-items: flex-end; }
        .modal-sheet { background: #151d30; width: 100%; max-height: 85vh; border-radius: 20px 20px 0 0; padding: 18px 16px; display: flex; flex-direction: column; border-top: 1px solid #334155; }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; border-bottom: 1px solid #334155; padding-bottom: 8px; }
        .modal-title { font-size: 16px; font-weight: 800; color: #f59e0b; }
        .close-btn { background: none; border: none; color: #ef4444; font-size: 18px; font-weight: 800; cursor: pointer; }
        .cart-items-list { overflow-y: auto; flex: 1; max-height: 60vh; margin-bottom: 10px; }
        .cart-item-row { display: flex; flex-direction: column; background: #0f172a; padding: 10px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #334155; gap: 6px; }
        .cart-item-top { display: flex; justify-content: space-between; align-items: center; width: 100%; }
        .item-options-box { display: flex; gap: 6px; width: 100%; margin-top: 4px; }
        .item-rice-select, .item-chicken-select { flex: 1; background: #1e293b; color: #f59e0b; border: 1px solid #334155; padding: 6px; border-radius: 6px; font-size: 11px; font-weight: 700; outline: none; }
        .del-item-btn { color: #ef4444; background: #1e293b; border: 1px solid #334155; font-size: 14px; cursor: pointer; width: 30px; height: 30px; border-radius: 6px; display: flex; align-items: center; justify-content: center; }
        .plate-separator-row { display: flex; align-items: center; justify-content: space-between; background: #8b5cf6; color: #ffffff; padding: 8px 12px; border-radius: 8px; font-size: 12px; font-weight: 800; margin: 12px 0 6px 0; }
        .modal-center-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); z-index: 400; display: none; align-items: center; justify-content: center; padding: 16px; }
        .modal-center-card { background: #151d30; border: 1px solid #334155; border-radius: 16px; padding: 20px; width: 100%; max-width: 360px; text-align: center; }
        #toastMsg { position: fixed; top: 70px; left: 50%; transform: translateX(-50%); background: #10b981; color: #ffffff; padding: 10px 22px; border-radius: 30px; font-size: 13px; font-weight: 700; z-index: 1000; box-shadow: 0 4px 15px rgba(0,0,0,0.4); display: none; opacity: 0; transition: opacity 0.3s ease; }
    </style>
</head>
<body>
    <div id="toastMsg">✅ بە سەرکەوتوویی بۆ مەتبەخ نێردرا</div>
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
            <button type="button" class="btn-add-plate" onclick="addNewPlateDivider()" id="btnAddPlate" style="display:none;">➕ قاپی نوێ</button>
            <button type="button" class="btn-action btn-change-tbl" onclick="openChangeTableModal()">🔄 گۆڕین</button>
            <button type="button" class="btn-action btn-clear-tbl" onclick="clearCurrentTableOrders()">🗑 سڕینەوە</button>
        </div>
    </div>

    <div class="categories-scroll">
        <a href="javascript:void(0)" class="cat-chip active" onclick="filterCat('all', this)">هەموو</a>
        {% for cat in categories.keys() %}
            <a href="javascript:void(0)" class="cat-chip" onclick="filterCat('cat-group-{{ loop.index }}', this)">{{ cat }}</a>
        {% endfor %}
    </div>

    <div class="menu-container">
        {% for cat, items in categories.items() %}
        <div class="category-block category-group-item" id="cat-group-{{ loop.index }}" data-cat-name="{{ cat }}">
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
        <button type="button" id="btnSubmitMain" class="btn-send-main" onclick="submitFinalOrder()">ناردن بۆ مەتبەخ ➔</button>
    </div>

    <div class="modal-overlay" id="cartModal" onclick="closeCartModal(event)">
        <div class="modal-sheet" onclick="event.stopPropagation()">
            <div class="modal-header">
                <span class="modal-title">🛒 خواردنەکانی ناو سەبەتە</span>
                <button type="button" class="close-btn" onclick="toggleCartModal(false)">✕</button>
            </div>
            <div class="cart-items-list" id="cartItemsList"></div>
            <div style="display: flex; gap: 8px; margin-top: 4px;">
                <button type="button" class="btn-add-plate" style="flex: 1; padding: 12px; justify-content: center; display:none;" id="btnModalAddPlate" onclick="addNewPlateDivider()">➕ قاپی نوێ (هێڵ)</button>
                <button type="button" id="btnSubmitModal" class="btn-send-main" style="flex: 2; padding: 12px;" onclick="submitFinalOrder()">ناردن بۆ مەتبەخ</button>
            </div>
        </div>
    </div>

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
        function checkHasGrill() {
            let hasGrill = cartItems.some(i => !i.is_divider && i.cat === 'برژاو');
            document.getElementById('btnAddPlate').style.display = hasGrill ? 'flex' : 'none';
            document.getElementById('btnModalAddPlate').style.display = hasGrill ? 'flex' : 'none';
        }
        function showToast(text, isError = false) {
            const toast = document.getElementById('toastMsg');
            toast.innerText = text;
            toast.style.background = isError ? '#ef4444' : '#10b981';
            toast.style.display = 'block';
            setTimeout(() => { toast.style.opacity = '1'; }, 10);
            setTimeout(() => {
                toast.style.opacity = '0';
                setTimeout(() => { toast.style.display = 'none'; }, 300);
            }, 2500);
        }
        function setButtonStateNormal() {
            const btnMain = document.getElementById('btnSubmitMain');
            const btnModal = document.getElementById('btnSubmitModal');
            if (btnMain) { btnMain.classList.remove('saved-success'); btnMain.innerHTML = 'ناردن بۆ مەتبەخ ➔'; }
            if (btnModal) { btnModal.classList.remove('saved-success'); btnModal.innerHTML = 'ناردن بۆ مەتبەخ'; }
        }
        function setButtonStateSaved() {
            const btnMain = document.getElementById('btnSubmitMain');
            const btnModal = document.getElementById('btnSubmitModal');
            if (btnMain) { btnMain.classList.add('saved-success'); btnMain.innerHTML = '✅ نێردرا بۆ مەتبەخ'; }
            if (btnModal) { btnModal.classList.add('saved-success'); btnModal.innerHTML = '✅ نێردرا بۆ مەتبەخ'; }
        }
        function resetInputs() { document.querySelectorAll('.qty-val').forEach(el => el.value = 0); }
        function addNewPlateDivider() {
            if (cartItems.length === 0 || cartItems[cartItems.length - 1].is_divider) {
                showToast("تکایە سەرەتا خواردنێک دیاری بکە!", true);
                return;
            }
            cartItems.push({ is_divider: true, food_name: '--- قاپی نوێ ---', price: 0, qty: 1, cat: 'مەتبەخ' });
            setButtonStateNormal();
            checkHasGrill();
            renderCartSummary();
            if (document.getElementById('cartModal').style.display === 'flex') { renderCartModalList(); }
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
            updateMenuCardInputs();
            checkHasGrill();
            renderCartSummary();
        }
        function updateMenuCardInputs() {
            resetInputs();
            cartItems.forEach(item => {
                if (!item.is_divider) {
                    const input = document.getElementById('qty_' + item.food_name);
                    if (input) { input.value = (parseInt(input.value) || 0) + item.qty; }
                }
            });
        }
        function removeCartIndex(index) {
            setButtonStateNormal();
            cartItems.splice(index, 1);
            updateMenuCardInputs();
            checkHasGrill();
            renderCartSummary();
            renderCartModalList();
        }
        function updateItemRice(index, val) { setButtonStateNormal(); cartItems[index].rice_type = val; }
        function updateItemChicken(index, val) { setButtonStateNormal(); cartItems[index].chicken_part = val; }
        function renderCartSummary() {
            let total = 0, count = 0;
            cartItems.forEach(item => {
                if (!item.is_divider) { total += (item.qty * item.price); count += item.qty; }
            });
            document.getElementById('cartTotalTxt').innerText = total.toLocaleString() + ' دینار';
            document.getElementById('cartCount').innerText = count;
        }
        function openCartModal() { renderCartModalList(); toggleCartModal(true); }
        function toggleCartModal(show) { document.getElementById('cartModal').style.display = show ? 'flex' : 'none'; }
        function closeCartModal(e) { if (e.target.id === 'cartModal') toggleCartModal(false); }
        function renderCartModalList() {
            const list = document.getElementById('cartItemsList');
            list.innerHTML = '';
            if (cartItems.length === 0) {
                list.innerHTML = '<div style="text-align:center; color:#94a3b8; padding:20px;">سەبەتە بەتاڵە!</div>';
                return;
            }
            let plateNum = 1;
            cartItems.forEach((item, index) => {
                if (item.is_divider) {
                    plateNum++;
                    const sep = document.createElement('div');
                    sep.className = 'plate-separator-row';
                    sep.innerHTML = `<span>🍽 قاپی ${plateNum}</span> <button type="button" class="del-item-btn" style="background:#ef4444; color:#fff; width:24px; height:24px; font-size:11px;" onclick="removeCartIndex(${index})">✕</button>`;
                    list.appendChild(sep);
                } else {
                    let showRice = ['کوڵاو', 'پەلەوەر', 'کوردیەکان'].includes(item.cat);
                    let showChicken = (item.cat === 'پەلەوەر');
                    let optionsHtml = '';
                    if (showRice || showChicken) {
                        optionsHtml += `<div class="item-options-box">`;
                        if (showRice) {
                            let rVal = item.rice_type || '';
                            optionsHtml += `
                                <select class="item-rice-select" onchange="updateItemRice(${index}, this.value)">
                                    <option value="">جۆری برنج دیاریبکە</option>
                                    <option value="برنجی درێژ" ${rVal === 'برنجی درێژ' ? 'selected' : ''}>برنجی درێژ</option>
                                    <option value="برنجی خڕ" ${rVal === 'برنجی خڕ' ? 'selected' : ''}>برنجی خڕ</option>
                                    <option value="برنجی کوردی" ${rVal === 'برنجی کوردی' ? 'selected' : ''}>برنجی کوردی</option>
                                    <option value="برنج بە سرکە" ${rVal === 'برنج بە سرکە' ? 'selected' : ''}>برنج بە سرکە</option>
                                </select>`;
                        }
                        if (showChicken) {
                            let cVal = item.chicken_part || '';
                            optionsHtml += `
                                <select class="item-chicken-select" onchange="updateItemChicken(${index}, this.value)">
                                    <option value="">بەشی مریشک</option>
                                    <option value="سینگ" ${cVal === 'سینگ' ? 'selected' : ''}>سینگ</option>
                                    <option value="ڕان" ${cVal === 'ڕان' ? 'selected' : ''}>ڕان</option>
                                </select>`;
                        }
                        optionsHtml += `</div>`;
                    }
                    const row = document.createElement('div');
                    row.className = 'cart-item-row';
                    row.innerHTML = `
                        <div class="cart-item-top">
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
                        </div>
                        ${optionsHtml}`;
                    list.appendChild(row);
                }
            });
        }
        function modifyItemQty(index, change) {
            setButtonStateNormal();
            if (cartItems[index] && !cartItems[index].is_divider) {
                cartItems[index].qty += change;
                if (cartItems[index].qty <= 0) { cartItems.splice(index, 1); }
                updateMenuCardInputs();
                checkHasGrill();
                renderCartSummary();
                renderCartModalList();
            }
        }
        function filterCat(catId, btn) {
            document.querySelectorAll('.cat-chip').forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            const blocks = document.querySelectorAll('.category-group-item');
            if (catId === 'all') { blocks.forEach(b => b.style.display = 'block'); }
            else { blocks.forEach(b => b.style.display = (b.id === catId) ? 'block' : 'none'); }
        }
        function onTableChanged(newTableNum) { fetchTableOrders(newTableNum); }
        function fetchTableOrders(tableNum) {
            fetch('/get_table_orders/' + tableNum)
                .then(res => res.json())
                .then(data => {
                    cartItems = [];
                    resetInputs();
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
                            if (isDiv) {
                                cartItems.push({ is_divider: true, food_name: fName, price: 0, qty: 1, cat: 'مەتبەخ' });
                            } else {
                                cartItems.push({ is_divider: false, food_name: fName, qty: parseInt(item.quantity), price: parseFloat(item.price), cat: item.category || '', rice_type: rType, chicken_part: cPart });
                            }
                        });
                        setButtonStateSaved();
                    } else { setButtonStateNormal(); }
                    updateMenuCardInputs();
                    checkHasGrill();
                    renderCartSummary();
                    if (document.getElementById('cartModal').style.display === 'flex') { renderCartModalList(); }
                }).catch(() => {});
        }
        function submitFinalOrder() {
            const tableNum = document.getElementById('tableSelect').value;
            if (cartItems.length === 0) { showToast("تکایە سەرەتا خواردن دیاری بکە!", true); return; }
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
                    showToast("✅ داواکارییەکە بۆ مەتبەخ نێردرا");
                } else { showToast('هەڵە لە ناردن: ' + data.message, true); }
            }).catch(() => showToast("کێشە لە پەیوەندی سێرڤەر!", true));
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
                        showToast("مێزی " + currentTbl + " بەتاڵکرایەوە");
                        fetchTableOrders(currentTbl);
                    } else { showToast("هەڵە: " + data.message, true); }
                });
            }
        }
        function openChangeTableModal() {
            const currentTbl = document.getElementById('tableSelect').value;
            document.getElementById('newTableSelect').value = currentTbl;
            toggleChangeTableModal(true);
        }
        function toggleChangeTableModal(show) { document.getElementById('changeTableModal').style.display = show ? 'flex' : 'none'; }
        function confirmChangeTable() {
            const oldTbl = document.getElementById('tableSelect').value;
            const newTbl = document.getElementById('newTableSelect').value;
            if (oldTbl === newTbl) { showToast("تکایە ژمارەیەکی جیاواز دیاری بکە!", true); return; }
            fetch('/change_table_number', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ old_table: oldTbl, new_table: newTbl })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    toggleChangeTableModal(false);
                    showToast("داواکارییەکان گوازرانەوە بۆ مێزی " + newTbl);
                    document.getElementById('tableSelect').value = newTbl;
                    fetchTableOrders(newTbl);
                } else { showToast("هەڵە لە گواستنەوە: " + data.message, true); }
            });
        }
        window.onload = function() { fetchTableOrders(document.getElementById('tableSelect').value); };
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
    <title>مێنیوی شاهور - بەشی کۆمپیوتەر / ئایپاد</title>
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
        .desktop-header { background: linear-gradient(180deg, #161f32 0%, var(--bg-main) 100%); padding: 12px 24px; border-bottom: 1px solid rgba(245, 158, 11, 0.3); display: flex; align-items: center; justify-content: space-between; height: 70px; }
        .brand-box { display: flex; align-items: center; gap: 12px; }
        .brand-logo { color: var(--gold); font-size: 22px; font-weight: 800; text-shadow: 0 2px 10px rgba(245,158,11,0.2); }
        .table-control-bar { display: flex; align-items: center; gap: 14px; background: var(--bg-card); padding: 8px 16px; border-radius: 12px; border: 1px solid var(--border-color); }
        .table-control-bar label { font-weight: 700; font-size: 14px; color: var(--cream); }
        .table-dropdown { background: var(--bg-main); color: var(--gold); border: 1.5px solid var(--gold); padding: 6px 14px; border-radius: 8px; font-size: 16px; font-weight: 800; outline: none; }
        .btn-top-action { background: #1e293b; color: var(--text-main); border: 1px solid var(--border-color); padding: 6px 12px; border-radius: 8px; font-size: 12px; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 6px; }
        .btn-top-action.danger { color: var(--danger); border-color: rgba(239,68,68,0.4); }
        .desktop-main-layout { display: grid; grid-template-columns: 1fr 380px; flex: 1; overflow: hidden; }
        .menu-section { display: flex; flex-direction: column; padding: 16px 24px; overflow-y: auto; }
        .categories-tabs { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .tab-btn { background: var(--bg-card); color: var(--text-muted); border: 1px solid var(--border-color); padding: 8px 18px; border-radius: 20px; font-size: 13px; font-weight: 700; cursor: pointer; transition: all 0.2s; }
        .tab-btn.active { background: linear-gradient(135deg, var(--gold) 0%, var(--gold-dark) 100%); color: var(--bg-main); border-color: var(--gold); box-shadow: 0 4px 12px rgba(245,158,11,0.25); }
        .category-desktop-group { margin-bottom: 24px; }
        .category-desktop-title { color: var(--gold); font-size: 16px; font-weight: 800; margin-bottom: 12px; display: flex; align-items: center; gap: 10px; border-bottom: 1px solid var(--border-color); padding-bottom: 6px; }
        .food-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 16px; padding-bottom: 10px; }
        .desktop-food-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 14px; padding: 12px; display: flex; flex-direction: column; gap: 10px; transition: transform 0.2s, border-color 0.2s; }
        .desktop-food-card:hover { border-color: var(--gold); transform: translateY(-2px); }
        .desktop-food-img { width: 100%; height: 120px; border-radius: 10px; object-fit: cover; background: var(--bg-main); border: 1px solid var(--border-color); }
        .desktop-food-info { display: flex; flex-direction: column; gap: 4px; flex: 1; }
        .desktop-food-name { font-size: 14px; font-weight: 700; color: var(--text-main); }
        .desktop-food-price { font-size: 13px; font-weight: 700; color: var(--success); }
        .desktop-counter-group { display: flex; align-items: center; justify-content: space-between; background: var(--bg-main); border-radius: 8px; border: 1px solid var(--border-color); padding: 3px; }
        .desktop-btn-count { width: 32px; height: 32px; border-radius: 6px; border: none; background: #1e293b; color: var(--text-main); font-size: 16px; font-weight: 700; cursor: pointer; }
        .desktop-btn-count.plus { background: var(--gold); color: var(--bg-main); }
        .desktop-qty-val { width: 35px; text-align: center; font-size: 15px; font-weight: 800; color: var(--text-main); background: transparent; border: none; outline: none; }
        
        /* تێبینی ٣: زیادکردنی سکڕۆڵ بۆ بەشی دەستی ڕاست (سەبەتە) */
        .cart-sidebar { background: var(--bg-sidebar); border-right: 1px solid var(--border-color); display: flex; flex-direction: column; padding: 16px; height: 100%; overflow: hidden; }
        .cart-sidebar-header { font-size: 16px; font-weight: 800; color: var(--gold); margin-bottom: 14px; padding-bottom: 8px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; flex-shrink: 0; }
        .cart-items-container { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; padding-right: 4px; scrollbar-width: thin; }
        .cart-items-container::-webkit-scrollbar { width: 5px; }
        .cart-items-container::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 4px; }

        .desktop-cart-row { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; padding: 10px; display: flex; flex-direction: column; gap: 6px; }
        .desktop-cart-top { display: flex; justify-content: space-between; align-items: center; }
        .desktop-cart-options { display: flex; gap: 6px; width: 100%; }
        .desktop-select-opt { flex: 1; background: var(--bg-main); color: var(--gold); border: 1px solid var(--border-color); padding: 5px; border-radius: 6px; font-size: 11px; font-weight: 700; outline: none; }
        .plate-sep-desktop { background: #8b5cf6; color: #ffffff; padding: 6px 10px; border-radius: 6px; font-size: 12px; font-weight: 800; display: flex; justify-content: space-between; align-items: center; margin: 8px 0; }
        .cart-sidebar-footer { border-top: 1px solid var(--border-color); padding-top: 12px; display: flex; flex-direction: column; gap: 10px; flex-shrink: 0; }
        .cart-total-box { display: flex; justify-content: space-between; align-items: center; font-size: 15px; font-weight: 800; }
        .cart-total-val { color: var(--success); font-size: 18px; }
        .btn-send-desktop { background: linear-gradient(135deg, var(--gold) 0%, var(--gold-dark) 100%); color: var(--bg-main); border: none; padding: 12px; border-radius: 10px; font-size: 15px; font-weight: 800; cursor: pointer; transition: all 0.2s; text-align: center; }
        .btn-send-desktop.saved-success { background: linear-gradient(135deg, var(--success) 0%, #059669 100%) !important; color: #ffffff !important; }
        .btn-add-plate-desktop { background: #8b5cf6; color: #ffffff; border: none; padding: 8px; border-radius: 8px; font-size: 12px; font-weight: 700; cursor: pointer; display: none; flex-shrink: 0; margin-bottom: 8px; }
        #toastMsg { position: fixed; top: 20px; left: 50%; transform: translateX(-50%); background: var(--success); color: #ffffff; padding: 10px 24px; border-radius: 30px; font-size: 14px; font-weight: 700; z-index: 1000; box-shadow: 0 4px 20px rgba(0,0,0,0.5); display: none; opacity: 0; transition: opacity 0.3s ease; }
    </style>
</head>
<body>
    <div id="toastMsg">✅ بە سەرکەوتوویی بۆ مەتبەخ نێردرا</div>
    <header class="desktop-header">
        <div class="brand-box">
            <div class="brand-logo">✨ شاهور ڕێستۆرانت (بەشی کۆمپیوتەر / ئایپاد)</div>
        </div>
        <div class="table-control-bar">
            <label>📍 مێزی:</label>
            <select id="tableSelect" class="table-dropdown" onchange="onTableChanged(this.value)">
                {% for num in range(1, 91) %}
                    <option value="{{ num }}">مێزی {{ num }}</option>
                {% endfor %}
            </select>
            <button type="button" class="btn-top-action" onclick="openChangeTableModal()">🔄 گواستنەوەی مێز</button>
            <button type="button" class="btn-top-action danger" onclick="clearCurrentTableOrders()">🗑 سڕینەوەی مێز</button>
        </div>
    </header>

    <div class="desktop-main-layout">
        <div class="menu-section">
            <div class="categories-tabs" id="categoriesTabs">
                <button type="button" class="tab-btn active" onclick="filterCat('all', this)">هەموو</button>
                {% for cat in categories.keys() %}
                    <button type="button" class="tab-btn" onclick="filterCat('cat-group-{{ loop.index }}', this)">{{ cat }}</button>
                {% endfor %}
            </div>
            
            <div class="menu-container-desktop">
                {% for cat, items in categories.items() %}
                <div class="category-desktop-group category-group-item" id="cat-group-{{ loop.index }}" data-cat-name="{{ cat }}">
                    <div class="category-desktop-title">{{ cat }}</div>
                    <div class="food-grid">
                        {% for item in items %}
                        <div class="desktop-food-card">
                            <img src="{{ item.image_path if item.image_path and item.image_path.startswith('http') else 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=200' }}" class="desktop-food-img" onerror="this.src='https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=200'">
                            <div class="desktop-food-info">
                                <div class="desktop-food-name">{{ item.food_name }}</div>
                                <div class="desktop-food-price">{{ "{:,.0f}".format(item.price) }} دینار</div>
                            </div>
                            <div class="desktop-counter-group">
                                <button type="button" class="desktop-btn-count" onclick="updateQty('{{ item.food_name }}', -1, {{ item.price }}, '{{ item.category }}')">-</button>
                                <input type="text" id="qty_{{ item.food_name }}" value="0" class="desktop-qty-val" readonly>
                                <button type="button" class="desktop-btn-count plus" onclick="updateQty('{{ item.food_name }}', 1, {{ item.price }}, '{{ item.category }}')">+</button>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <div class="cart-sidebar">
            <div class="cart-sidebar-header">
                <span>🛒 داواکارییەکانی مێز</span>
                <span id="cartCountBadge" style="background: var(--gold); color: var(--bg-main); padding: 2px 8px; border-radius: 12px; font-size: 12px;">0</span>
            </div>
            <button type="button" id="btnAddPlateDesktop" class="btn-add-plate-desktop" onclick="addNewPlateDivider()">➕ قاپی نوێ (بۆ برژاو)</button>
            <div class="cart-items-container" id="cartItemsList">
                <div style="text-align: center; color: var(--text-muted); padding: 40px 0;">سەبەتە بەتاڵە</div>
            </div>
            <div class="cart-sidebar-footer">
                <div class="cart-total-box">
                    <span>کۆی گشتی:</span>
                    <span class="cart-total-val" id="cartTotalTxt">0 دینار</span>
                </div>
                <button type="button" id="btnSubmitDesktop" class="btn-send-desktop" onclick="submitFinalOrder()">ناردن بۆ مەتبەخ ➔</button>
            </div>
        </div>
    </div>

    <div id="changeTableModal" style="position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.8); z-index:500; display:none; align-items:center; justify-content:center;">
        <div style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 16px; padding: 24px; width: 100%; max-width: 380px; text-align: center;">
            <div style="font-size: 18px; font-weight: 800; color: var(--gold); margin-bottom: 12px;">🔄 گواستنەوەی مێز</div>
            <p style="color: var(--text-muted); font-size: 13px; margin-bottom: 16px;">ژمارەی ئەو مێزە نوێیە دیاری بکە:</p>
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
        let originalTableOrders = []; // بۆ بەراوردکردن و ناردنی تەنها شتە زیادکراو یان سڕدراوەکان

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
        function resetInputs() { document.querySelectorAll('.desktop-qty-val').forEach(el => el.value = 0); }
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
            updateMenuCardInputs();
            checkHasGrill();
            renderCart();
        }
        function updateMenuCardInputs() {
            resetInputs();
            cartItems.forEach(item => {
                if (!item.is_divider) {
                    const input = document.getElementById('qty_' + item.food_name);
                    if (input) { input.value = (parseInt(input.value) || 0) + item.qty; }
                }
            });
        }
        function removeCartIndex(index) {
            setButtonStateNormal();
            cartItems.splice(index, 1);
            updateMenuCardInputs();
            checkHasGrill();
            renderCart();
        }
        function modifyItemQty(index, change) {
            setButtonStateNormal();
            if (cartItems[index] && !cartItems[index].is_divider) {
                cartItems[index].qty += change;
                if (cartItems[index].qty <= 0) { cartItems.splice(index, 1); }
                updateMenuCardInputs();
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
                    sep.innerHTML = `<span>🍽 قاپی ${plateNum}</span> <button type="button" style="background:var(--danger); color:#fff; border:none; width:22px; height:22px; border-radius:4px; cursor:pointer; font-size:10px;" onclick="removeCartIndex(${index})">✕</button>`;
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
                            <div class="desktop-counter-group" style="padding: 1px;">
                                <button type="button" style="background:var(--danger); color:#fff; border:none; width:24px; height:24px; border-radius:4px; cursor:pointer;" onclick="removeCartIndex(${index})" title="سڕینەوە">🗑</button>
                                <button type="button" class="desktop-btn-count" style="width:26px; height:26px; font-size:13px;" onclick="modifyItemQty(${index}, -1)">-</button>
                                <span style="padding:0 8px; font-weight:800; font-size:13px;">${item.qty}</span>
                                <button type="button" class="desktop-btn-count plus" style="width:26px; height:26px; font-size:13px;" onclick="modifyItemQty(${index}, 1)">+</button>
                            </div>
                            <div style="text-align: left;">
                                <div style="font-weight:700; font-size:13px; color:#fff;">${item.food_name}</div>
                                <div style="color:var(--success); font-size:11px;">${(item.qty * item.price).toLocaleString()} دینار</div>
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
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const groups = document.querySelectorAll('.category-group-item');
            groups.forEach(group => {
                if (catId === 'all') { group.style.display = 'block'; }
                else { group.style.display = (group.id === catId) ? 'block' : 'none'; }
            });
        }
        function onTableChanged(tableNum) { fetchTableOrders(tableNum); }
        function fetchTableOrders(tableNum) {
            fetch('/get_table_orders/' + tableNum)
                .then(res => res.json())
                .then(data => {
                    cartItems = [];
                    originalTableOrders = [];
                    resetInputs();
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
                    updateMenuCardInputs();
                    checkHasGrill();
                    renderCart();
                }).catch(() => {});
        }
        function submitFinalOrder() {
            const tableNum = document.getElementById('tableSelect').value;
            if (cartItems.length === 0) { showToast("تکایە سەرەتا خواردن دیاری بکە!", true); return; }
            
            fetch('/save_cart_order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ table_number: tableNum, cart_items: cartItems, original_items: originalTableOrders })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    setButtonStateSaved();
                    originalTableOrders = JSON.parse(JSON.stringify(cartItems));
                    showToast("✅ داواکارییەکە بۆ مەتبەخ نێردرا");
                } else { showToast('هەڵە لە ناردن: ' + data.message, true); }
            }).catch(() => showToast("کێشە لە پەیوەندی سێرڤەر!", true));
        }
        function clearCurrentTableOrders() {
            const currentTbl = document.getElementById('tableSelect').value;
            if (confirm("ئایا دڵنیایت لە سڕینەوەی تەواوی مێزی " + currentTbl + "؟")) {
                fetch('/clear_table_orders', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ table_number: currentTbl })
                })
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') {
                        showToast("مێزی " + currentTbl + " بەتاڵکرایەوە");
                        fetchTableOrders(currentTbl);
                    }
                });
            }
        }
        function openChangeTableModal() {
            const currentTbl = document.getElementById('tableSelect').value;
            document.getElementById('newTableSelect').value = currentTbl;
            document.getElementById('changeTableModal').style.display = 'flex';
        }
        function toggleChangeTableModal(show) { document.getElementById('changeTableModal').style.display = show ? 'flex' : 'none'; }
        function confirmChangeTable() {
            const oldTbl = document.getElementById('tableSelect').value;
            const newTbl = document.getElementById('newTableSelect').value;
            if (oldTbl === newTbl) { showToast("تکایە ژمارەیەکی جیاواز دیاری بکە!", true); return; }
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
                    document.getElementById('tableSelect').value = newTbl;
                    fetchTableOrders(newTbl);
                }
            });
        }
        window.onload = function() { fetchTableOrders(document.getElementById('tableSelect').value); };
    </script>
</body>
</html>
"""

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        input_pin = normalize_digits(request.form.get('pin', ''))
        if input_pin in ['22', '٢٢']:
            session['authenticated'] = True
            return redirect(url_for('desktop_menu'))
        if input_pin in ['345678', '٣٤٥٦٧٨']:
            session['authenticated'] = True
            return redirect(url_for('menu'))

        db_pin = None
        try:
            conn = get_db()
            with conn.cursor() as cursor:
                cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'mobile_pin' LIMIT 1")
                row = cursor.fetchone()
                if row and row.get('setting_value'):
                    db_pin = normalize_digits(row['setting_value'])
            conn.close()
        except Exception as ex:
            print("Database Error in Login:", ex)

        if db_pin is not None and input_pin == db_pin:
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
            # تێبینی ٤: ڕیزکردنەکان بە هەمان داتابەیس و خشتەی nse
            cursor.execute("SELECT food_name, price, category, image_path FROM nse WHERE food_name IS NOT NULL AND food_name != ''")
            foods = cursor.fetchall()
        conn.close()

        categories = {}
        for food in foods:
            cat = food['category'].strip() if food['category'] and food['category'].strip() else 'گشتی'
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(food)

        return render_template_string(HTML_TEMPLATE, categories=categories)
    except Exception as e:
        return f"<h3 style='color:red; text-align:center;'>کێشەی داتابەیس: {str(e)}</h3>"

@app.route('/desktop')
def desktop_menu():
    if not session.get('authenticated'):
        return redirect(url_for('login'))
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            # تێبینی ٤: هێنانەوەی ڕیزبەندی ڕەسەنی nse
            cursor.execute("SELECT food_name, price, category, image_path FROM nse WHERE food_name IS NOT NULL AND food_name != ''")
            foods = cursor.fetchall()
        conn.close()

        categories = {}
        for food in foods:
            cat = food['category'].strip() if food['category'] and food['category'].strip() else 'گشتی'
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(food)

        return render_template_string(DESKTOP_TEMPLATE, categories=categories)
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

    # دروستکردنی دیکشێنەری کۆن و نوێ بۆ بەراوردکردن (تێبینی ١ و ٢)
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
            # ١. پاشەکەوتکردن یان نوێکردنەوەی تەواوی سەبەتە لە خشتەی froshtn
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
                    VALUES (%s, %s, %s, %s, %s, NOW(), 0)
                """, (str(table_num), food_name, qty, price, cat))

            # ٢. پشکنینی جیاوازی بۆ چاپکردنی تەنها ئەوەی زیادکراوە یان سڕدراوە بۆ مەتبەخ
            all_keys = set(old_map.keys()).union(set(new_map.keys()))
            for key in all_keys:
                old_qty = old_map.get(key, {}).get('qty', 0)
                new_qty = new_map.get(key, {}).get('qty', 0)
                diff = new_qty - old_qty
                
                if diff != '' and diff != 0 and key != "--- قاپی نوێ ---":
                    cat_val = new_map.get(key, {}).get('cat') or old_map.get(key, {}).get('cat', 'گشتی')
                    price_val = new_map.get(key, {}).get('price') or old_map.get(key, {}).get('price', 0)
                    
                    if diff > 0:
                        # زیادکردنی بڕی نوێ بۆ مەتبەخ (تێبینی ١)
                        cursor.execute("""
                            INSERT INTO froshtn (table_cabin, food_name, quantity, price, category, created_at, is_printed)
                            VALUES (%s, %s, %s, %s, %s, NOW(), 0)
                        """, (str(table_num) + " [زیادکراو]", key, diff, price_val, cat_val))
                    else:
                        # ئاماژەدان بە سڕینەوە بۆ مەتبەخ (تێبینی ٢)
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
        return jsonify({'status': 'error', 'system': 'ڕێگەپێنەدراو'})
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
