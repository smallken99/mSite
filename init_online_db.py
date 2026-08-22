"""
線上資料庫初始化腳本 — 在線上 MySQL 建立商城模組資料表與初始設定
使用方式：於伺服器部署完成後執行一次即可
python init_online_db.py
"""
import sys
from mSite import create_app, db
from mSite.config import Config
from mSite.models import ShopProduct, ProductVariant, ShopOrder, ShopOrderItem, ShopSetting

app = create_app(config_class=Config)

with app.app_context():
    print("==========================================")
    print("🚀 開始初始化線上 MySQL 商城資料表...")
    print(f"🔗 資料庫連線：{app.config['SQLALCHEMY_DATABASE_URI']}")
    print("==========================================")

    # 1. 建立商城資料表 (若已存在則自動略過)
    db.create_all()
    print("✅ 資料表建立/驗證完成 (shop_product, product_variant, shop_order, shop_order_item, shop_setting)")

    # 2. 插入預設設定
    shop_name_setting = ShopSetting.query.filter_by(key='shop_name').first()
    if not shop_name_setting:
        db.session.add(ShopSetting(key='shop_name', value='棋新商城'))
        print("✅ 建立預設商城名稱：棋新商城")

    admin_email_setting = ShopSetting.query.filter_by(key='admin_email').first()
    if not admin_email_setting:
        db.session.add(ShopSetting(key='admin_email', value='oioi7211@gmail.com'))
        print("✅ 建立預設通知信箱：oioi7211@gmail.com")
    elif not admin_email_setting.value or admin_email_setting.value == 'smallken@gmail.com':
        admin_email_setting.value = 'oioi7211@gmail.com'
        print("✅ 更新通知信箱：oioi7211@gmail.com")

    db.session.commit()
    print("==========================================")
    print("🎉 線上商城資料庫初始化成功！")
    print("==========================================")
