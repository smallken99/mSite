"""
資料庫遷移腳本 - 建立商品規格 (ProductVariant) 支援
=====================================================
功能：
1. 使用 Flask app context 建立所有缺失的資料表 (db.create_all)
2. 檢查並新增缺失的欄位 (price_max, variant_id, variant_name)
3. 為每個現有 ShopProduct 建立一筆「預設」規格 (若尚未有)
4. 同步主品項的 price / price_max / stock

使用方式：
    python migrate_add_variants.py              (連線正式資料庫)
    python migrate_add_variants.py --test       (使用本地 SQLite 測試庫)
"""

import sys
import os

# 設定 UTF-8 輸出
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 判斷是否為測試模式
use_test = '--test' in sys.argv

if use_test:
    from mSite.config import TestConfig
    config_class = TestConfig
    print("[INFO] 使用測試資料庫 (SQLite)")
else:
    from mSite.config import Config
    config_class = Config
    print("[INFO] 使用正式資料庫 (MySQL)")

from mSite import create_app, db
from mSite.models import ShopProduct, ProductVariant

app = create_app(config_class)

with app.app_context():
    print("[INFO] 開始資料庫遷移...")
    print(f"[INFO] 資料庫 URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

    # Step 1: 建立所有缺失的資料表
    print("[STEP 1] 建立缺失的資料表 (db.create_all)...")
    db.create_all()
    print("  [OK] 資料表建立/確認完成")

    # Step 2: 檢查是否需要新增 price_max 欄位 (若表已存在但欄位缺失)
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)

    if inspector.has_table('shop_product'):
        shop_product_columns = [col['name'] for col in inspector.get_columns('shop_product')]

        if 'price_max' not in shop_product_columns:
            print("[STEP 2] 新增 shop_product.price_max 欄位...")
            db.session.execute(text("ALTER TABLE shop_product ADD COLUMN price_max FLOAT NOT NULL DEFAULT 0.0"))
            db.session.execute(text("UPDATE shop_product SET price_max = price"))
            db.session.commit()
            print("  [OK] price_max 欄位已新增並初始化")
        else:
            print("[STEP 2] shop_product.price_max 欄位已存在，跳過")
    else:
        print("[STEP 2] shop_product 表剛由 db.create_all 建立，已包含所有欄位")

    # Step 3: 檢查 shop_order_item 是否需要新增 variant 欄位
    if inspector.has_table('shop_order_item'):
        order_item_columns = [col['name'] for col in inspector.get_columns('shop_order_item')]

        if 'variant_id' not in order_item_columns:
            print("[STEP 3a] 新增 shop_order_item.variant_id 欄位...")
            db.session.execute(text("ALTER TABLE shop_order_item ADD COLUMN variant_id INTEGER"))
            db.session.commit()
            print("  [OK] variant_id 欄位已新增")
        else:
            print("[STEP 3a] shop_order_item.variant_id 欄位已存在，跳過")

        if 'variant_name' not in order_item_columns:
            print("[STEP 3b] 新增 shop_order_item.variant_name 欄位...")
            db.session.execute(text("ALTER TABLE shop_order_item ADD COLUMN variant_name VARCHAR(200) DEFAULT ''"))
            db.session.commit()
            print("  [OK] variant_name 欄位已新增")
        else:
            print("[STEP 3b] shop_order_item.variant_name 欄位已存在，跳過")
    else:
        print("[STEP 3] shop_order_item 表剛由 db.create_all 建立，已包含所有欄位")

    # Step 4: 為現有商品建立「預設」規格
    products = ShopProduct.query.all()
    if products:
        created_count = 0
        for p in products:
            if len(p.variants) == 0:
                variant = ProductVariant(
                    product_id=p.id,
                    name='預設',
                    price=p.price,
                    stock=p.stock,
                    image_file='',
                    is_active=True,
                    sort_order=0
                )
                db.session.add(variant)
                created_count += 1
                print(f"  [OK] 商品 [{p.name}] (ID: {p.id}) -> 建立預設規格 (價格: {p.price}, 庫存: {p.stock})")

        if created_count > 0:
            db.session.commit()
            print(f"[STEP 4] 已為 {created_count} 個商品建立預設規格")
        else:
            print("[STEP 4] 所有商品已有規格，跳過")
    else:
        print("[STEP 4] 目前無商品資料，不需建立預設規格")

    # Step 5: 同步主品項 price / price_max / stock
    print("[STEP 5] 同步主品項 price / price_max / stock...")
    products = ShopProduct.query.all()
    for p in products:
        p.sync_price_stock()
    db.session.commit()
    print("  [OK] 同步完成")

    # Step 6: 確認管理者通知信箱設定
    from mSite.models import ShopSetting
    admin_email_setting = ShopSetting.query.filter_by(key='admin_email').first()
    if not admin_email_setting:
        db.session.add(ShopSetting(key='admin_email', value='oioi7211@gmail.com'))
        db.session.commit()
        print("  [OK] 建立預設管理者通知信箱: oioi7211@gmail.com")
    elif not admin_email_setting.value or admin_email_setting.value == 'smallken@gmail.com':
        admin_email_setting.value = 'oioi7211@gmail.com'
        db.session.commit()
        print("  [OK] 更新管理者通知信箱為: oioi7211@gmail.com")

    print("\n[DONE] 遷移完成！所有變更已成功套用。")
