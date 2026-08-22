import os
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required
from mSite import db
from mSite.models import ShopProduct, ProductVariant, ShopOrder, ShopOrderItem, ShopSetting
from mSite.shop.utils import (
    generate_order_no,
    save_product_image,
    build_order_summary_text,
    send_order_notification,
    send_test_email,
    get_shop_setting
)

shop = Blueprint('shop', __name__)


# ==========================================
# 前台頁面與 API (免登入)
# ==========================================

@shop.route('/shop')
def shop_index():
    """商城前台首頁"""
    shop_name = get_shop_setting('shop_name', '棋新商城')
    return render_template('shop.html', shop_name=shop_name)


@shop.route('/shop/api/products', methods=['GET'])
def get_public_products():
    """取得上架商品列表（含規格資訊）"""
    products = (ShopProduct.query
                .filter_by(is_active=True)
                .order_by(ShopProduct.sort_order.asc(), ShopProduct.id.desc())
                .all())
    result = []
    for p in products:
        d = p.to_dict(include_variants=True)
        # 前台只回傳啟用中的規格
        d['variants'] = [v.to_dict() for v in p.variants if v.is_active]
        result.append(d)
    return jsonify(result)


@shop.route('/shop/api/products/<int:id>', methods=['GET'])
def get_product_detail(id):
    """取得單一商品詳情 + 規格列表"""
    product = ShopProduct.query.get_or_404(id)
    if not product.is_active:
        return jsonify({'success': False, 'message': '商品不存在或已下架'}), 404

    d = product.to_dict(include_variants=True)
    # 前台只回傳啟用中的規格
    d['variants'] = [v.to_dict() for v in product.variants if v.is_active]
    return jsonify(d)


@shop.route('/shop/api/checkout', methods=['POST'])
def checkout():
    """成立訂單 API（以 variant_id 為主，即時扣減庫存）"""
    data = request.get_json() or {}
    items_data = data.get('items', [])
    note = (data.get('note') or '').strip()

    if not items_data:
        return jsonify({'success': False, 'message': '購物車內無商品'}), 400

    # 驗證商品規格並計算小計
    order_items = []
    total_amount = 0.0
    variants_to_deduct = []  # 待扣庫存的規格

    for item in items_data:
        variant_id = item.get('variant_id')
        qty = int(item.get('quantity', 1))
        if qty <= 0:
            continue

        variant = ProductVariant.query.get(variant_id)
        if not variant or not variant.is_active:
            return jsonify({'success': False, 'message': f'商品規格 (ID: {variant_id}) 已下架或不存在'}), 400

        product = variant.product
        if not product or not product.is_active:
            return jsonify({'success': False, 'message': f'商品「{product.name if product else ""}」已下架'}), 400

        # 庫存檢查
        if variant.stock < qty:
            return jsonify({
                'success': False,
                'message': f'「{product.name} - {variant.name}」庫存不足（剩餘 {variant.stock}，需要 {qty}）'
            }), 400

        unit_price = float(variant.price)
        subtotal = unit_price * qty
        total_amount += subtotal

        order_item = ShopOrderItem(
            product_id=product.id,
            variant_id=variant.id,
            product_name=product.name,
            variant_name=variant.name,
            quantity=qty,
            unit_price=unit_price,
            subtotal=subtotal
        )
        order_items.append(order_item)
        variants_to_deduct.append((variant, qty))

    if not order_items:
        return jsonify({'success': False, 'message': '無有效商品'}), 400

    # 即時扣減庫存
    for variant, qty in variants_to_deduct:
        variant.stock -= qty

    # 同步主品項庫存
    affected_product_ids = set(v.product_id for v, _ in variants_to_deduct)
    for pid in affected_product_ids:
        product = ShopProduct.query.get(pid)
        if product:
            product.sync_price_stock()

    order_no = generate_order_no()
    order = ShopOrder(
        order_no=order_no,
        customer_note=note,
        total_amount=total_amount,
        status='pending'
    )
    order.items = order_items

    db.session.add(order)
    db.session.commit()

    shop_name = get_shop_setting('shop_name', '棋新商城')
    order_summary = build_order_summary_text(order, order_items, shop_name)

    # 嘗試寄送管理者 Email (若失敗不阻擋訂單成立)
    try:
        send_order_notification(order, order_items)
    except Exception as e:
        current_app.logger.error(f"Email 通知寄送失敗: {str(e)}")

    return jsonify({
        'success': True,
        'order_no': order_no,
        'order_summary': order_summary,
        'total_amount': total_amount
    })


# ==========================================
# 後台管理頁面與 API (需登入)
# ==========================================

@shop.route('/shop/admin/products')
@login_required
def admin_products():
    """後台商品管理頁面"""
    return render_template('shop_admin_products.html', title='商品管理')


@shop.route('/shop/admin/api/products', methods=['GET'])
@login_required
def admin_get_products():
    """取得所有商品列表（包含下架，含規格）"""
    products = ShopProduct.query.order_by(ShopProduct.sort_order.asc(), ShopProduct.id.desc()).all()
    return jsonify([p.to_dict(include_variants=True) for p in products])


@shop.route('/shop/admin/api/products', methods=['POST'])
@login_required
def admin_create_product():
    """新增商品（主品項 + 規格）"""
    name = request.form.get('name', '').strip()
    if not name:
        return jsonify({'success': False, 'message': '商品名稱不能為空'}), 400

    description = request.form.get('description', '')
    is_active = request.form.get('is_active', 'true').lower() in ('true', '1')
    sort_order = int(request.form.get('sort_order', 0))

    image_file = 'default.jpg'
    if 'image' in request.files and request.files['image'].filename:
        image_file = save_product_image(request.files['image'])

    product = ShopProduct(
        name=name,
        description=description,
        is_active=is_active,
        sort_order=sort_order,
        image_file=image_file
    )

    # 解析 variants JSON
    import json
    variants_json = request.form.get('variants', '[]')
    try:
        variants_data = json.loads(variants_json)
    except (json.JSONDecodeError, TypeError):
        variants_data = []

    if not variants_data:
        # 若未提供規格，建立「預設」規格
        default_price = float(request.form.get('price', 0))
        default_stock = int(request.form.get('stock', 0))
        variants_data = [{'name': '預設', 'price': default_price, 'stock': default_stock}]

    for idx, vd in enumerate(variants_data):
        variant = ProductVariant(
            name=vd.get('name', '預設').strip() or '預設',
            price=float(vd.get('price', 0)),
            stock=int(vd.get('stock', 0)),
            image_file=vd.get('image_file', ''),
            is_active=vd.get('is_active', True),
            sort_order=idx
        )
        product.variants.append(variant)

    product.sync_price_stock()
    db.session.add(product)
    db.session.commit()

    return jsonify({'success': True, 'product': product.to_dict(include_variants=True)})


@shop.route('/shop/admin/api/products/<int:id>', methods=['POST', 'PUT'])
@login_required
def admin_update_product(id):
    """更新商品（主品項資訊 + 規格同步）"""
    product = ShopProduct.query.get_or_404(id)

    # 支援 JSON 或 FormData
    if request.is_json:
        data = request.get_json()
        if 'name' in data:
            product.name = data['name'].strip()
        if 'description' in data:
            product.description = data['description']
        if 'is_active' in data:
            product.is_active = bool(data['is_active'])
        if 'sort_order' in data:
            product.sort_order = int(data['sort_order'])

        # 更新規格列表
        if 'variants' in data:
            _sync_variants(product, data['variants'])
    else:
        name = request.form.get('name')
        if name:
            product.name = name.strip()
        if 'description' in request.form:
            product.description = request.form.get('description')
        if 'is_active' in request.form:
            product.is_active = request.form.get('is_active').lower() in ('true', '1')
        if 'sort_order' in request.form:
            product.sort_order = int(request.form.get('sort_order'))

        if 'image' in request.files and request.files['image'].filename:
            product.image_file = save_product_image(request.files['image'])

        # FormData 也可帶 variants JSON
        import json
        variants_json = request.form.get('variants')
        if variants_json:
            try:
                variants_data = json.loads(variants_json)
                _sync_variants(product, variants_data)
            except (json.JSONDecodeError, TypeError):
                pass

    product.sync_price_stock()
    db.session.commit()
    return jsonify({'success': True, 'product': product.to_dict(include_variants=True)})


def _sync_variants(product, variants_data):
    """同步規格列表：更新已存在的、新增新的、刪除被移除的"""
    existing_ids = {v.id for v in product.variants}
    incoming_ids = set()

    for idx, vd in enumerate(variants_data):
        vid = vd.get('id')
        if vid and vid in existing_ids:
            # 更新已存在的規格
            variant = ProductVariant.query.get(vid)
            if variant and variant.product_id == product.id:
                variant.name = vd.get('name', variant.name).strip() or variant.name
                variant.price = float(vd.get('price', variant.price))
                variant.stock = int(vd.get('stock', variant.stock))
                variant.image_file = vd.get('image_file', variant.image_file)
                variant.is_active = vd.get('is_active', variant.is_active)
                variant.sort_order = idx
                incoming_ids.add(vid)
        else:
            # 新增規格
            variant = ProductVariant(
                name=vd.get('name', '預設').strip() or '預設',
                price=float(vd.get('price', 0)),
                stock=int(vd.get('stock', 0)),
                image_file=vd.get('image_file', ''),
                is_active=vd.get('is_active', True),
                sort_order=idx
            )
            product.variants.append(variant)

    # 刪除不在 incoming 的規格
    for variant in list(product.variants):
        if variant.id and variant.id not in incoming_ids and variant.id in existing_ids:
            db.session.delete(variant)


@shop.route('/shop/admin/api/products/<int:id>', methods=['DELETE'])
@login_required
def admin_delete_product(id):
    """刪除商品（含所有規格）"""
    product = ShopProduct.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({'success': True})


# --- 規格管理 API ---

@shop.route('/shop/admin/api/products/<int:product_id>/variants', methods=['POST'])
@login_required
def admin_add_variant(product_id):
    """新增規格"""
    product = ShopProduct.query.get_or_404(product_id)
    data = request.get_json() or {}

    variant = ProductVariant(
        product_id=product.id,
        name=data.get('name', '預設').strip() or '預設',
        price=float(data.get('price', 0)),
        stock=int(data.get('stock', 0)),
        image_file=data.get('image_file', ''),
        is_active=data.get('is_active', True),
        sort_order=data.get('sort_order', 0)
    )
    db.session.add(variant)

    product.sync_price_stock()
    db.session.commit()

    return jsonify({'success': True, 'variant': variant.to_dict()})


@shop.route('/shop/admin/api/variants/<int:id>', methods=['PUT'])
@login_required
def admin_update_variant(id):
    """更新規格"""
    variant = ProductVariant.query.get_or_404(id)
    data = request.get_json() or {}

    if 'name' in data:
        variant.name = data['name'].strip() or variant.name
    if 'price' in data:
        variant.price = float(data['price'])
    if 'stock' in data:
        variant.stock = int(data['stock'])
    if 'image_file' in data:
        variant.image_file = data['image_file']
    if 'is_active' in data:
        variant.is_active = bool(data['is_active'])
    if 'sort_order' in data:
        variant.sort_order = int(data['sort_order'])

    variant.product.sync_price_stock()
    db.session.commit()

    return jsonify({'success': True, 'variant': variant.to_dict()})


@shop.route('/shop/admin/api/variants/<int:id>', methods=['DELETE'])
@login_required
def admin_delete_variant(id):
    """刪除規格"""
    variant = ProductVariant.query.get_or_404(id)
    product = variant.product

    # 至少保留一個規格
    active_count = sum(1 for v in product.variants if v.id != variant.id)
    if active_count == 0:
        return jsonify({'success': False, 'message': '至少須保留一個規格'}), 400

    db.session.delete(variant)
    product.sync_price_stock()
    db.session.commit()

    return jsonify({'success': True})


# --- 訂單管理 ---

@shop.route('/shop/admin/orders')
@login_required
def admin_orders():
    """後台訂單管理頁面"""
    return render_template('shop_admin_orders.html', title='訂單管理')


@shop.route('/shop/admin/api/orders', methods=['GET'])
@login_required
def admin_get_orders():
    """取得訂單列表"""
    status = request.args.get('status', '').strip()
    query = ShopOrder.query

    if status:
        query = query.filter_by(status=status)

    orders = query.order_by(ShopOrder.id.desc()).all()
    return jsonify([o.to_dict() for o in orders])


@shop.route('/shop/admin/api/orders/<int:id>', methods=['GET'])
@login_required
def admin_get_order_detail(id):
    """取得訂單詳情（包含商品明細）"""
    order = ShopOrder.query.get_or_404(id)
    order_dict = order.to_dict()
    order_dict['items'] = [item.to_dict() for item in order.items]
    return jsonify(order_dict)


@shop.route('/shop/admin/api/orders/<int:id>/status', methods=['PUT'])
@login_required
def admin_update_order_status(id):
    """更新訂單狀態"""
    order = ShopOrder.query.get_or_404(id)
    data = request.get_json() or {}
    new_status = data.get('status')

    if new_status not in ('pending', 'confirmed', 'cancelled'):
        return jsonify({'success': False, 'message': '不合法的訂單狀態'}), 400

    order.status = new_status
    db.session.commit()
    return jsonify({'success': True, 'status': order.status})


# --- 商城設定 ---

@shop.route('/shop/admin/settings')
@login_required
def admin_settings():
    """後台商城設定頁面"""
    return render_template('shop_admin_settings.html', title='商城設定')


@shop.route('/shop/admin/api/settings', methods=['GET'])
@login_required
def admin_get_settings():
    """取得商城設定"""
    admin_email = get_shop_setting('admin_email', '')
    shop_name = get_shop_setting('shop_name', '棋新商城')
    return jsonify({
        'admin_email': admin_email,
        'shop_name': shop_name
    })


@shop.route('/shop/admin/api/settings', methods=['PUT'])
@login_required
def admin_update_settings():
    """更新商城設定"""
    data = request.get_json() or {}

    for key in ['admin_email', 'shop_name']:
        if key in data:
            setting = ShopSetting.query.filter_by(key=key).first()
            if not setting:
                setting = ShopSetting(key=key, value=str(data[key]).strip())
                db.session.add(setting)
            else:
                setting.value = str(data[key]).strip()

    db.session.commit()
    return jsonify({'success': True})


# --- 圖片上傳 API ---

@shop.route('/shop/admin/api/upload_image', methods=['POST'])
@login_required
def admin_upload_image():
    """上傳單張圖片（供商品主圖或規格圖使用）"""
    if 'image' not in request.files or not request.files['image'].filename:
        return jsonify({'success': False, 'message': '未選取圖片檔案'}), 400

    try:
        filename = save_product_image(request.files['image'])
        return jsonify({
            'success': True,
            'image_file': filename,
            'image_url': f'/static/shop/products/{filename}'
        })
    except Exception as e:
        current_app.logger.error(f"上傳圖片失敗: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'圖片處理失敗: {str(e)}'}), 500


# --- 測試 Email 發送 API ---

@shop.route('/shop/admin/api/test_email', methods=['POST'])
@login_required
def admin_test_email():
    """測試發送通知信"""
    data = request.get_json() or {}
    email = data.get('email')
    success, message = send_test_email(email)
    return jsonify({'success': success, 'message': message}), (200 if success else 400)

