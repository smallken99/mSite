"""
本機測試啟動腳本 — 使用 SQLite 測試環境，不影響線上 MySQL。
"""
import os
import sys

# 確保 Windows 主控台支援 UTF-8 輸出
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
from mSite import create_app, db, bcrypt
from mSite.config import TestConfig
from mSite.models import User, ShopProduct, ProductVariant, ShopSetting

# 建立使用 TestConfig 的 Flask 應用實例
app = create_app(config_class=TestConfig)

with app.app_context():
    # 建立所有資料表
    db.create_all()

    # 1. 插入預設設定（若尚未存在或更新）
    shop_name_setting = ShopSetting.query.filter_by(key='shop_name').first()
    if not shop_name_setting:
        db.session.add(ShopSetting(key='shop_name', value='棋新商城'))
    
    admin_email_setting = ShopSetting.query.filter_by(key='admin_email').first()
    if not admin_email_setting:
        db.session.add(ShopSetting(key='admin_email', value='smallken@gmail.com'))
    else:
        admin_email_setting.value = 'smallken@gmail.com'
    db.session.commit()

    # 2. 建立測試管理員帳號 (若尚未存在)
    test_user = User.query.filter_by(email='admin@test.com').first()
    if not test_user:
        hashed_pwd = bcrypt.generate_password_hash('admin123').decode('utf-8')
        test_user = User(
            username='admin',
            email='admin@test.com',
            password=hashed_pwd,
            is_verified='Y'
        )
        db.session.add(test_user)
        db.session.commit()
        print('✅ 測試管理者帳號已建立: admin@test.com / admin123')

    # 3. 若無商品，建立幾筆示範商品 + 規格供快速體驗
    if ShopProduct.query.count() == 0:
        # 商品 1：白鐵六角螺絲 (多規格)
        p1 = ShopProduct(
            name='白鐵六角螺絲',
            description='SUS304 不鏽鋼材質，標準牙距',
            sort_order=1,
            is_active=True,
            image_file='sample_bolt.jpg'
        )
        p1.variants.append(ProductVariant(name='M6x20', price=35.0, stock=100, image_file='var_bolt_m6.jpg', sort_order=0))
        p1.variants.append(ProductVariant(name='M8x30', price=50.0, stock=80, image_file='var_bolt_m8.jpg', sort_order=1))
        p1.variants.append(ProductVariant(name='M10x40', price=75.0, stock=60, image_file='var_bolt_m10.jpg', sort_order=2))
        p1.sync_price_stock()

        # 商品 2：不鏽鋼平華司 (多規格)
        p2 = ShopProduct(
            name='不鏽鋼平華司 (10入)',
            description='高強度防腐蝕墊片',
            sort_order=2,
            is_active=True,
            image_file='sample_flat_washer.jpg'
        )
        p2.variants.append(ProductVariant(name='M6', price=60.0, stock=200, image_file='var_washer_m6.jpg', sort_order=0))
        p2.variants.append(ProductVariant(name='M8', price=70.0, stock=150, image_file='var_washer_m8.jpg', sort_order=1))
        p2.variants.append(ProductVariant(name='M10', price=80.0, stock=120, image_file='var_washer_m10.jpg', sort_order=2))
        p2.sync_price_stock()

        # 商品 3：彈簧墊圈 (單規格)
        p3 = ShopProduct(
            name='彈簧墊圈 M6 (20入)',
            description='防鬆脫彈簧華司',
            sort_order=3,
            is_active=True,
            image_file='sample_spring_washer.jpg'
        )
        p3.variants.append(ProductVariant(name='預設', price=40.0, stock=150, image_file='var_spring_m6.jpg', sort_order=0))
        p3.sync_price_stock()

        db.session.add_all([p1, p2, p3])
        db.session.commit()
        print('✅ 已建立 3 筆範例商品（含規格變體）')

    print('====================================================')
    print('  🎉 mSite 本機測試環境準備完成！')
    print(f'  📁 資料庫：{app.config["SQLALCHEMY_DATABASE_URI"]}')
    print('  🛒 前台商城：http://localhost:5000/shop')
    print('  ⚙️  後台管理：http://localhost:5000/shop/admin/products')
    print('  🔑 登入帳號：admin@test.com / admin123')
    print('====================================================')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
