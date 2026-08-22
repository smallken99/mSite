from datetime import datetime
#from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import TimedSerializer as Serializer
from flask import current_app
from mSite import db, login_manager
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    is_verified = db.Column(db.String(2))
    posts = db.relationship('Post', backref='author', lazy=True)

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"
    
    def to_dict(self):
            return {
                'id': self.id,
                'username': self.username,
                'email': self.email,
                'image_file': self.image_file
            }


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Post('{self.title}', '{self.date_posted}')"

class OrderFormat(db.Model):
    __tablename__ = 'orderformat'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_no = db.Column(db.String(20), nullable=False)
    buyer_name = db.Column(db.String(50), nullable=False)
    product_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price_tax_included = db.Column(db.Float, nullable=False)
    subtotal_tax_included = db.Column(db.Float, nullable=False)
    order_datetime = db.Column(db.DateTime, nullable=False)  #  訂單日期時間欄位
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

    def __init__(self, order_no, buyer_name, product_name, quantity, unit_price_tax_included, subtotal_tax_included, order_datetime):
        self.order_no = order_no
        self.buyer_name = buyer_name
        self.product_name = product_name
        self.quantity = quantity
        self.unit_price_tax_included = unit_price_tax_included
        self.subtotal_tax_included = subtotal_tax_included
        self.order_datetime = order_datetime

    def to_dict(self):
        return {
            'id': self.id,
            'order_no': self.order_no,
            'buyer_name': self.buyer_name,
            'product_name': self.product_name,
            'quantity': self.quantity,
            'unit_price_tax_included': self.unit_price_tax_included,
            'subtotal_tax_included': self.subtotal_tax_included,
            'created_at': self.created_at,
            'order_datetime': self.order_datetime
        }
    # Query to check if an order_no exists
    def check_order_is_exists(order_no):
        order = OrderFormat.query.filter_by(order_no=order_no).first()
        return order 

    # Example code to save multiple OrderFormat records
    def save_multiple_orders(orders):
        db.session.add_all(orders)
        db.session.commit()


class ShopProduct(db.Model):
    __tablename__ = 'shop_product'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    image_file = db.Column(db.String(200), default='default.jpg')
    price = db.Column(db.Float, nullable=False, default=0.0)        # 最低價（由 variants 同步）
    price_max = db.Column(db.Float, nullable=False, default=0.0)    # 最高價（由 variants 同步）
    stock = db.Column(db.Integer, nullable=False, default=0)        # 總庫存（各規格加總）
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    variants = db.relationship('ProductVariant', backref='product', lazy=True,
                               cascade="all, delete-orphan",
                               order_by='ProductVariant.sort_order')
    items = db.relationship('ShopOrderItem', backref='product', lazy=True)

    def sync_price_stock(self):
        """依據 variants 同步主品項的 price / price_max / stock"""
        active_variants = [v for v in self.variants if v.is_active]
        if active_variants:
            prices = [v.price for v in active_variants]
            self.price = min(prices)
            self.price_max = max(prices)
            self.stock = sum(v.stock for v in active_variants)
        else:
            self.price = 0.0
            self.price_max = 0.0
            self.stock = 0

    def to_dict(self, include_variants=False):
        d = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'image_file': self.image_file,
            'price': self.price,
            'price_max': self.price_max,
            'stock': self.stock,
            'is_active': self.is_active,
            'sort_order': self.sort_order,
            'created_at': self.created_at.strftime('%Y/%m/%d %H:%M') if self.created_at else '',
            'updated_at': self.updated_at.strftime('%Y/%m/%d %H:%M') if self.updated_at else ''
        }
        if include_variants:
            d['variants'] = [v.to_dict() for v in self.variants]
        return d


class ProductVariant(db.Model):
    __tablename__ = 'product_variant'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('shop_product.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)          # 規格名稱，如「黑色 XL」
    price = db.Column(db.Float, nullable=False, default=0.0)
    stock = db.Column(db.Integer, nullable=False, default=0)
    image_file = db.Column(db.String(200), default='')        # 規格專屬圖片（選填）
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=db.func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'name': self.name,
            'price': self.price,
            'stock': self.stock,
            'image_file': self.image_file,
            'is_active': self.is_active,
            'sort_order': self.sort_order
        }


class ShopOrder(db.Model):
    __tablename__ = 'shop_order'

    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(20), unique=True, nullable=False)
    customer_note = db.Column(db.Text, default='')
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=db.func.now())

    items = db.relationship('ShopOrderItem', backref='order', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'order_no': self.order_no,
            'customer_note': self.customer_note,
            'total_amount': self.total_amount,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y/%m/%d %H:%M') if self.created_at else '',
            'item_count': len(self.items)
        }


class ShopOrderItem(db.Model):
    __tablename__ = 'shop_order_item'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('shop_order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('shop_product.id'), nullable=True)
    variant_id = db.Column(db.Integer, db.ForeignKey('product_variant.id'), nullable=True)
    product_name = db.Column(db.String(200), nullable=False)
    variant_name = db.Column(db.String(200), default='')     # 規格名稱快照
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'variant_id': self.variant_id,
            'product_name': self.product_name,
            'variant_name': self.variant_name,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'subtotal': self.subtotal
        }


class ShopSetting(db.Model):
    __tablename__ = 'shop_setting'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(500), default='')

    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value
        }