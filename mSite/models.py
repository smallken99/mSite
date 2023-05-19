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
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

    def __init__(self, order_no, buyer_name, product_name, quantity, unit_price_tax_included, subtotal_tax_included):
        self.order_no = order_no
        self.buyer_name = buyer_name
        self.product_name = product_name
        self.quantity = quantity
        self.unit_price_tax_included = unit_price_tax_included
        self.subtotal_tax_included = subtotal_tax_included

    def to_dict(self):
        return {
            'id': self.id,
            'order_no': self.order_no,
            'buyer_name': self.buyer_name,
            'product_name': self.product_name,
            'quantity': self.quantity,
            'unit_price_tax_included': self.unit_price_tax_included,
            'subtotal_tax_included': self.subtotal_tax_included,
            'created_at': self.created_at
        }
    # Query to check if an order_no exists
    def check_order_is_exists(order_no):
        order = OrderFormat.query.filter_by(order_no=order_no).first()
        return order 

    # Example code to save multiple OrderFormat records
    def save_multiple_orders(orders):
        db.session.add_all(orders)
        db.session.commit() 