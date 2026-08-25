import streamlit as st
import pymysql
import json

# ڕێکخستنی شاشەی مۆبایل
st.set_page_config(page_title="مێنیوی شاهور", layout="wide", initial_sidebar_state="collapsed")

# شاردنەوەی سەرپەڕەی ستاندارد
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container {padding: 0 !important; margin: 0 !important;}
    </style>
""", unsafe_allow_html=True)

# زانیاری داتابەیسی سەرەکی
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

# هێنانی خواردنەکان لە داتابەیس
def fetch_foods():
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("SELECT food_name, price, category, image_path FROM nse WHERE food_name IS NOT NULL AND food_name != ''")
            foods = cursor.fetchall()
        conn.close()
        return foods
    except:
        return []

# هێنانی ئۆردەرەکانی ئێستای سەر مێزەکان
def fetch_all_active_orders():
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT table_cabin, food_name, price, category, SUM(quantity) as quantity, SUM(quantity * price) as total 
                FROM froshtn 
                WHERE table_cabin IS NOT NULL AND table_cabin != ''
                GROUP BY table_cabin, food_name, price, category
            """)
            orders = cursor.fetchall()
        conn.close()
        return orders
    except:
        return []

foods_data = fetch_foods()
active_orders_data = fetch_all_active_orders()

# داڕشتنی پۆلەکانی خواردن
categories = {}
for food in foods_data:
    cat = food['category'] if food.get('category') else 'گشتی'
    if cat not in categories:
        categories[cat] = []
    categories[cat].append({
        'name': food['food_name'],
        'price': float(food['price']),
        'cat': cat,
        'image': food['image_path'] if food.get('image_path') else 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=200'
    })

foods_json = json.dumps(categories, ensure_ascii=False)
orders_json = json.dumps(active_orders_data, ensure_ascii=False, default=str)

# پێکهاتەی وێبسایت بە تەواوی
HTML_CODE = f"""
<!DOCTYPE html>
<html lang="ckb" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Kufi Arabic', sans-serif; -webkit-tap-highlight-color: transparent; }}
        body {{ background-color: #0b0f19; color: #f8fafc; padding-bottom: 110px; }}
        
        .app-header {{
            background: linear-gradient(180deg, #161f32 0%, #0b0f19 100%);
            padding: 16px 16px 8px;
            text-align: center;
            border-bottom: 1px solid rgba(245, 158, 11, 0.2);
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        .restaurant-name {{ color: #f59e0b; font-size: 20px; font-weight: 800; }}
        .tagline {{ color: #94a3b8; font-size: 11px; margin-top: 2px; }}

        .table-bar {{
            background: #1e293b;
            margin: 12px 16px;
            padding: 10px 14px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border: 1px solid #334155;
        }}
        .table-bar label {{ font-weight: 700; font-size: 13px; color: #f8fafc; }}
        .table-select {{
            background: #0f172a;
            color: #f59e0b;
            border: 1.5px solid #f59e0b;
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 700;
            outline: none;
        }}

        .categories-scroll {{
            display: flex;
            overflow-x: auto;
            gap: 8px;
            padding: 4px 16px 12px;
            scrollbar-width: none;
        }}
        .categories-scroll::-webkit-scrollbar {{ display: none; }}
        .cat-chip {{
            background: #1e293b;
            color: #94a3b8;
            padding: 7px 16px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            white-space: nowrap;
            text-decoration: none;
            border: 1px solid #334155;
        }}
        .cat-chip.active {{ background: #f59e0b; color: #0b0f19; font-weight: 800; border-color: #f59e0b; }}

        .menu-container {{ padding: 0 16px; }}
        .category-block {{ margin-bottom: 18px; }}
        .category-title {{ color: #f59e0b; font-size: 15px; font-weight: 700; margin-bottom: 10px; display: flex; align-items: center; gap: 8px; }}
        .category-title::after {{ content: ''; flex: 1; height: 1px; background: #334155; }}
        
        .food-card {{
            background: #151d30;
            border: 1px solid #243048;
            border-radius: 14px;
            padding: 10px;
            margin-bottom: 10px;
            display: flex;
            gap: 10px;
            align-items: center;
        }}
        .food-img {{ width: 68px; height: 68px; border-radius: 10px; object-fit: cover; background: #0b0f19; border: 1px solid #334155; flex-shrink: 0; }}
        .food-details {{ flex: 1; min-width: 0; }}
        .food-name {{ font-size: 14px; font-weight: 700; color: #ffffff; margin-bottom: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .food-price {{ font-size: 13px; font-weight: 700; color: #10b981; }}
        
        .counter-group {{ display: flex; align-items: center; background: #0b0f19; border-radius: 8px; border: 1px solid #334155; padding: 2px; gap: 3px; }}
        .btn-count {{ width: 30px; height: 30px; border-radius: 6px; border: none; background: #1e293b; color: #ffffff; font-size: 15px; font-weight: 700; cursor: pointer; }}
        .btn-count.plus {{ background: #f59e0b; color: #0b0f19; }}
        .qty-val {{ width: 26px; text-align: center; font-size: 14px; font-weight: 700; color: #ffffff; background: transparent; border: none; outline: none; }}

        .bottom-cart-bar {{
            position: fixed;
            bottom: 0; left: 0; right: 0;
            background: rgba(15, 23, 42, 0.96);
            backdrop-filter: blur(10px);
            border-top: 1px solid #334155;
            padding: 10px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            z-index: 200;
        }}
        .cart-info-btn {{
            display: flex;
            align-items: center;
            gap: 10px;
            background: #1e293b;
            padding: 8px 14px;
            border-radius: 10px;
            border: 1px solid #334155;
            cursor: pointer;
        }}
        .cart-badge {{ background: #f59e0b; color: #0b0f19; font-size: 11px; font-weight: 800; padding: 2px 7px; border-radius: 10px; }}
        .cart-total-txt {{ font-size: 14px; font-weight: 800; color: #10b981; }}
        .btn-send-main {{
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            color: #0b0f19;
            border: none;
            padding: 10px 20px;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 800;
            cursor: pointer;
        }}

        .modal-overlay {{
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.7);
            z-index: 300;
            display: none;
            align-items: flex-end;
        }}
        .modal-sheet {{
            background: #151d30;
            width: 100%;
            max-height: 80vh;
            border-radius: 20px 20px 0 0;
            padding: 18px 16px;
            display: flex;
            flex-direction: column;
            border-top: 1px solid #334155;
        }}
        .modal-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; border-bottom: 1px solid #334155; padding-bottom: 8px; }}
        .modal-title {{ font-size: 16px; font-weight: 800; color: #f59e0b; }}
        .close-btn {{ background: none; border: none; color: #ef4444; font-size: 18px; font-weight: 800; cursor: pointer; }}
        .cart-items-list {{ overflow-y: auto; flex: 1; max-height: 50vh; margin-bottom: 14px; }}
        .cart-item-row {{ display: flex; justify-content: space-between; align-items: center; background: #0f172a; padding: 10px; border-radius: 8px; margin-bottom: 8px; }}
        .del-item-btn {{ color: #ef4444; background: none; border: none; font-size: 16px; cursor: pointer; margin-right: 8px; }}
    </style>
</head>
<body>

    <header class="app-header">
        <div class="restaurant-name">✨ شاهور ڕێستۆرانت</div>
        <div class="tagline">سیستەمی داواکاری مۆبایل</div>
    </header>

    <div class="table-bar">
        <label>📍 ژمارەی مێزەکەت:</label>
        <select id="tableSelect" class="table-select" onchange="onTableChanged(this.value)">
            <!-- دروستکردنی ٣٠ مێز -->
        </select>
    </div>

    <div class="categories-scroll" id="categoriesBar"></div>

    <div class="menu-container" id="menuContainer"></div>

    <div class="bottom-cart-bar">
        <div class="cart-info-btn" onclick="openCartModal()">
            <span style="font-size: 18px;">🛒</span>
            <span class="cart-badge" id="cartCount">0</span>
            <span class="cart-total-txt" id="cartTotalTxt">0 دینار</span>
        </div>
        <button type="button" class="btn-send-main" onclick="submitFinalOrder()">ناردنی داواکاری ➔</button>
    </div>

    <div class="modal-overlay" id="cartModal" onclick="closeCartModal(event)">
        <div class="modal-sheet" onclick="event.stopPropagation()">
            <div class="modal-header">
                <span class="modal-title">🛒 خواردنەکانی ناو سەبەتە</span>
                <button type="button" class="close-btn" onclick="toggleCartModal(false)">✕</button>
            </div>
            <div class="cart-items-list" id="cartItemsList"></div>
            <button type="button" class="btn-send-main" style="width: 100%; padding: 12px;" onclick="submitFinalOrder()">تۆمارکردن لە سیستەم</button>
        </div>
    </div>

    <script>
        const categoriesData = {foods_json};
        const allActiveOrders = {orders_json};
        let cart = {{}};

        function initApp() {{
            const select = document.getElementById('tableSelect');
            for (let i = 1; i <= 30; i++) {{
                let opt = document.createElement('option');
                opt.value = i;
                opt.innerText = "مێزی " + i;
                select.appendChild(opt);
            }}

            const catBar = document.getElementById('categoriesBar');
            catBar.innerHTML = `<a href="javascript:void(0)" class="cat-chip active" onclick="filterCat('all', this)">هەموو</a>`;
            
            const menuCont = document.getElementById('menuContainer');
            let idx = 1;
            for (let cat in categoriesData) {{
                catBar.innerHTML += `<a href="javascript:void(0)" class="cat-chip" onclick="filterCat('cat-${{idx}}', this)">${{cat}}</a>`;
                
                let block = document.createElement('div');
                block.className = 'category-block';
                block.id = `cat-${{idx}}`;
                block.innerHTML = `<div class="category-title">${{cat}}</div>`;
                
                categoriesData[cat].forEach(item => {{
                    block.innerHTML += `
                        <div class="food-card">
                            <img src="${{item.image}}" class="food-img" onerror="this.src='https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=200'">
                            <div class="food-details">
                                <div class="food-name">${{item.name}}</div>
                                <div class="food-price">${{item.price.toLocaleString()}} دینار</div>
                            </div>
                            <div class="counter-group">
                                <button type="button" class="btn-count" onclick="updateQty('${{item.name}}', -1, ${{item.price}}, '${{item.cat}}')">-</button>
                                <input type="text" id="qty_${{item.name}}" value="0" class="qty-val" readonly>
                                <button type="button" class="btn-count plus" onclick="updateQty('${{item.name}}', 1, ${{item.price}}, '${{item.cat}}')">+</button>
                            </div>
                        </div>
                    `;
                }});
                menuCont.appendChild(block);
                idx++;
            }}

            onTableChanged(select.value);
        }}

        function onTableChanged(tblNum) {{
            cart = {{}};
            document.querySelectorAll('.qty-val').forEach(el => el.value = 0);

            const tableOrders = allActiveOrders.filter(o => String(o.table_cabin) === String(tblNum));
            tableOrders.forEach(item => {{
                cart[item.food_name] = {{
                    qty: parseInt(item.quantity),
                    price: parseFloat(item.price),
                    cat: item.category || ''
                }};
                const input = document.getElementById('qty_' + item.food_name);
                if (input) input.value = item.quantity;
            }});

            renderCartSummary();
        }}

        function updateQty(foodName, change, price, cat) {{
            if (!cart[foodName]) {{
                cart[foodName] = {{ qty: 0, price: price, cat: cat || '' }};
            }}
            cart[foodName].qty += change;
            if (cart[foodName].qty <= 0) delete cart[foodName];

            const input = document.getElementById('qty_' + foodName);
            if (input) input.value = cart[foodName] ? cart[foodName].qty : 0;

            renderCartSummary();
        }}

        function removeFoodEntirely(foodName) {{
            delete cart[foodName];
            const input = document.getElementById('qty_' + foodName);
            if (input) input.value = 0;
            renderCartSummary();
            renderCartModalList();
        }}

        function renderCartSummary() {{
            let total = 0, count = 0;
            for (let name in cart) {{
                total += (cart[name].qty * cart[name].price);
                count += cart[name].qty;
            }}
            document.getElementById('cartTotalTxt').innerText = total.toLocaleString() + ' دینار';
            document.getElementById('cartCount').innerText = count;
        }}

        function openCartModal() {{
            renderCartModalList();
            toggleCartModal(true);
        }}

        function toggleCartModal(show) {{
            document.getElementById('cartModal').style.display = show ? 'flex' : 'none';
        }}

        function closeCartModal(e) {{
            if (e.target.id === 'cartModal') toggleCartModal(false);
        }}

        function renderCartModalList() {{
            const list = document.getElementById('cartItemsList');
            list.innerHTML = '';
            if (Object.keys(cart).length === 0) {{
                list.innerHTML = '<div style="text-align:center; color:#94a3b8; padding:20px;">سەبەتە بەتاڵە!</div>';
                return;
            }}
            for (let name in cart) {{
                const item = cart[name];
                list.innerHTML += `
                    <div class="cart-item-row">
                        <div style="display:flex; align-items:center;">
                            <button type="button" class="del-item-btn" onclick="removeFoodEntirely('${{name}}')">🗑</button>
                            <div>
                                <div style="font-weight:700; font-size:13px; color:#fff;">${{name}}</div>
                                <div style="color:#10b981; font-size:11px;">${{(item.qty * item.price).toLocaleString()}} دینار</div>
                            </div>
                        </div>
                        <div class="counter-group">
                            <button type="button" class="btn-count" onclick="updateQty('${{name}}', -1, ${{item.price}}, '${{item.cat}}'); renderCartModalList();">-</button>
                            <span style="padding:0 8px; font-weight:700;">${{item.qty}}</span>
                            <button type="button" class="btn-count plus" onclick="updateQty('${{name}}', 1, ${{item.price}}, '${{item.cat}}'); renderCartModalList();">+</button>
                        </div>
                    </div>
                `;
            }}
        }}

        function filterCat(catId, btn) {{
            document.querySelectorAll('.cat-chip').forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            const blocks = document.querySelectorAll('.category-block');
            blocks.forEach(b => {{
                b.style.display = (catId === 'all' || b.id === catId) ? 'block' : 'none';
            }});
        }}

        function submitFinalOrder() {{
            const tableNum = document.getElementById('tableSelect').value;
            const payload = JSON.stringify({{ table: tableNum, items: cart }});
            
            // ناردنی داتا بۆ داتابەیس بە پارامیتەر
            window.parent.postMessage({{ type: 'streamlit:setComponentValue', value: payload }}, '*');
            alert('داواکارییەکە بە سەرکەوتوویی تۆمارکرا!');
            toggleCartModal(false);
        }}

        window.onload = initApp;
    </script>
</body>
</html>
"""

# هەڵگرتن لە داتابەیس
from streamlit.components.v1 import html
order_payload = html(HTML_CODE, height=850, scrolling=True)

if order_payload:
    try:
        data = json.loads(order_payload)
        tbl = data.get('table')
        cart_items = data.get('items', {})
        
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM froshtn WHERE table_cabin = %s", (str(tbl),))
            for f_name, item in cart_items.items():
                qty = int(item['qty'])
                price = float(item['price'])
                cat = item.get('cat', '')
                if qty > 0:
                    cursor.execute("""
                        INSERT INTO froshtn (table_cabin, food_name, quantity, price, category, created_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                    """, (str(tbl), f_name, qty, price, cat))
            conn.commit()
        conn.close()
        st.rerun()
    except Exception as e:
        st.error(f"هەڵە: {e}")
