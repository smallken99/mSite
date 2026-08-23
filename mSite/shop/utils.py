import os
import secrets
from datetime import datetime
from PIL import Image, ImageOps
from flask import current_app
from flask_mail import Message
from mSite import db, mail
from mSite.models import ShopOrder, ShopSetting, get_tw_now


def get_shop_setting(key, default=''):
    """取得商城設定值"""
    setting = ShopSetting.query.filter_by(key=key).first()
    if setting and setting.value:
        return setting.value
    return default


def generate_order_no():
    """產生唯一訂單編號，格式：SH + YYYYMMDD + 3 位流水號 (例: SH20260821001)"""
    today_str = get_tw_now().strftime('%Y%m%d')
    prefix = f'SH{today_str}'

    latest_order = (ShopOrder.query
                    .filter(ShopOrder.order_no.like(f'{prefix}%'))
                    .order_by(ShopOrder.order_no.desc())
                    .first())

    if latest_order:
        try:
            last_seq = int(latest_order.order_no[-3:])
            seq = last_seq + 1
        except ValueError:
            seq = 1
    else:
        seq = 1

    return f'{prefix}{seq:03d}'


def save_product_image(form_picture):
    """儲存上傳之商品圖片並回傳隨機檔名（統一轉為高品質 JPEG 格式）"""
    random_hex = secrets.token_hex(8)
    picture_fn = f"{random_hex}.jpg"
    
    upload_dir = os.path.join(current_app.root_path, 'static', 'shop', 'products')
    try:
        os.makedirs(upload_dir, exist_ok=True)
    except Exception as e:
        current_app.logger.warning(f"建立圖片目錄警告: {e}")

    picture_path = os.path.join(upload_dir, picture_fn)

    # 縮圖至 800x800 以內保持比例
    output_size = (800, 800)
    i = Image.open(form_picture)

    # 自動修正 EXIF 方向（如手機直拍）
    try:
        i = ImageOps.exif_transpose(i)
    except Exception:
        pass

    # 確保轉換為 RGB 模式
    if i.mode != 'RGB':
        i = i.convert('RGB')

    # 高品質縮圖
    resample_filter = getattr(Image, 'Resampling', Image).LANCZOS if hasattr(Image, 'Resampling') else Image.ANTIALIAS
    i.thumbnail(output_size, resample_filter)
    i.save(picture_path, format='JPEG', quality=85, optimize=True)

    return picture_fn


def save_announcement_image(form_picture):
    """儲存上傳之公告圖片並回傳隨機檔名（統一轉為高品質 JPEG 格式）"""
    random_hex = secrets.token_hex(8)
    picture_fn = f"{random_hex}.jpg"

    upload_dir = os.path.join(current_app.root_path, 'static', 'shop', 'announcements')
    try:
        os.makedirs(upload_dir, exist_ok=True)
    except Exception as e:
        current_app.logger.warning(f"建立公告圖片目錄警告: {e}")

    picture_path = os.path.join(upload_dir, picture_fn)

    # 縮圖至 1200x1200 以內保持比例（公告圖保留更多細節）
    output_size = (1200, 1200)
    i = Image.open(form_picture)

    # 自動修正 EXIF 方向
    try:
        i = ImageOps.exif_transpose(i)
    except Exception:
        pass

    if i.mode != 'RGB':
        i = i.convert('RGB')

    resample_filter = getattr(Image, 'Resampling', Image).LANCZOS if hasattr(Image, 'Resampling') else Image.ANTIALIAS
    i.thumbnail(output_size, resample_filter)
    i.save(picture_path, format='JPEG', quality=90, optimize=True)

    return picture_fn


def build_order_summary_text(order, items, shop_name=None):
    """組裝純文字訂單摘要（供客戶複製貼到 LINE）"""
    if not shop_name:
        shop_name = get_shop_setting('shop_name', '棋新商城')
    
    created_time_str = order.created_at.strftime('%Y/%m/%d %H:%M') if order.created_at else get_tw_now().strftime('%Y/%m/%d %H:%M')

    lines = [
        f"📋 {shop_name} — 訂單通知",
        "━━━━━━━━━━━━━━━━━━",
        f"訂單編號：{order.order_no}",
        f"訂單日期：{created_time_str}",
    ]

    if order.customer_note and order.customer_note.strip():
        lines.append(f"🚚 寄送方式：{order.customer_note.strip()}")

    lines.append("")
    lines.append("──── 訂單明細 ────")
    for item in items:
        display_name = item.variant_name if (hasattr(item, 'variant_name') and item.variant_name) else item.product_name
        price_str = f"{int(item.subtotal):,}" if item.subtotal.is_integer() else f"{item.subtotal:,.2f}"
        lines.append(f"• {display_name}  x{item.quantity}   NT$ {price_str}")

    total_str = f"{int(order.total_amount):,}" if order.total_amount.is_integer() else f"{order.total_amount:,.2f}"
    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append(f"合計金額（不含運費）：NT$ {total_str}")

    return "\n".join(lines)


def build_order_email_html(order, items, shop_name=None):
    """組裝管理者通知 Email HTML"""
    if not shop_name:
        shop_name = get_shop_setting('shop_name', '棋新商城')
    
    created_time_str = order.created_at.strftime('%Y/%m/%d %H:%M') if order.created_at else get_tw_now().strftime('%Y/%m/%d %H:%M')
    total_str = f"{int(order.total_amount):,}" if order.total_amount.is_integer() else f"{order.total_amount:,.2f}"

    item_rows = ""
    for item in items:
        display_name = item.variant_name if (hasattr(item, 'variant_name') and item.variant_name) else item.product_name
        unit_p = f"{int(item.unit_price):,}" if item.unit_price.is_integer() else f"{item.unit_price:,.2f}"
        sub_p = f"{int(item.subtotal):,}" if item.subtotal.is_integer() else f"{item.subtotal:,.2f}"
        item_rows += f"""
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 10px 8px;">{display_name}</td>
            <td style="padding: 10px 8px; text-align: center;">{item.quantity}</td>
            <td style="padding: 10px 8px; text-align: right;">NT$ {unit_p}</td>
            <td style="padding: 10px 8px; text-align: right; font-weight: bold;">NT$ {sub_p}</td>
        </tr>
        """

    note_html = ""
    if order.customer_note and order.customer_note.strip():
        note_html = f"""
        <p style="margin: 6px 0; color: #555;"><strong>🚚 寄送方式：</strong>{order.customer_note.strip()}</p>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: Arial, 'Microsoft JhengHei', sans-serif; background-color: #f4f6f8; margin: 0; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
            <div style="background-color: #5f788a; color: #ffffff; padding: 18px 24px;">
                <h2 style="margin: 0; font-size: 20px;">🛒 [{shop_name}] 新訂單成立通知</h2>
            </div>
            <div style="padding: 24px;">
                <div style="background-color: #f8fafc; border-left: 4px solid #5f788a; padding: 12px 16px; margin-bottom: 20px;">
                    <p style="margin: 4px 0;"><strong>訂單編號：</strong><span style="font-size: 16px; color: #1e293b; font-weight: bold;">{order.order_no}</span></p>
                    <p style="margin: 4px 0; color: #555;"><strong>成立時間：</strong>{created_time_str}</p>
                    {note_html}
                </div>

                <h3 style="margin: 16px 0 8px 0; font-size: 16px; color: #333;">📦 訂購明細</h3>
                <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                    <thead>
                        <tr style="background-color: #f1f5f9; text-align: left; color: #475569;">
                            <th style="padding: 8px;">品名</th>
                            <th style="padding: 8px; text-align: center;">數量</th>
                            <th style="padding: 8px; text-align: right;">單價</th>
                            <th style="padding: 8px; text-align: right;">小計</th>
                        </tr>
                    </thead>
                    <tbody>
                        {item_rows}
                    </tbody>
                    <tfoot>
                        <tr>
                            <td colspan="3" style="padding: 14px 8px; text-align: right; font-weight: bold; font-size: 16px;">總計金額（不含運費）：</td>
                            <td style="padding: 14px 8px; text-align: right; font-weight: bold; font-size: 18px; color: #e11d48;">NT$ {total_str}</td>
                        </tr>
                    </tfoot>
                </table>

                <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #e2e8f0; color: #64748b; font-size: 13px; text-align: center;">
                    此為系統自動發送通知，請至管理後台確認訂單狀態。
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html


def send_order_notification(order, items):
    """發送訂單通知信件給管理者"""
    admin_email = get_shop_setting('admin_email')
    if not admin_email or not admin_email.strip():
        current_app.logger.warning("未設定管理者 Email (admin_email)，跳過訂單郵件通知")
        return False, "未設定管理者 Email"

    shop_name = get_shop_setting('shop_name', '棋新商城')
    subject = f"[{shop_name}] 新訂單通知 — {order.order_no}"
    html_content = build_order_email_html(order, items, shop_name)
    plain_summary = build_order_summary_text(order, items, shop_name)
    sender = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME') or 'noreply@demo.com'

    try:
        msg = Message(
            subject=subject,
            sender=sender,
            recipients=[admin_email.strip()]
        )
        msg.body = plain_summary
        msg.html = html_content
        mail.send(msg)
        current_app.logger.info(f"訂單 {order.order_no} 通知信已成功發送至 {admin_email.strip()}")
        return True, "發送成功"
    except Exception as e:
        err_msg = f"發送訂單 Email 失敗: {str(e)}"
        current_app.logger.error(err_msg)
        return False, err_msg


def send_test_email(recipient=None):
    """發送測試信件以檢查郵件設定"""
    if not recipient:
        recipient = get_shop_setting('admin_email')
    if not recipient or not recipient.strip():
        return False, "未設定收件者 Email"

    shop_name = get_shop_setting('shop_name', '棋新商城')
    sender = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME') or 'noreply@demo.com'

    msg = Message(
        subject=f"[{shop_name}] 商城郵件發送測試",
        sender=sender,
        recipients=[recipient.strip()]
    )
    msg.body = f"這是一封來自「{shop_name}」的測試郵件。\n若您收到此信，代表郵件通知功能運作正常！\n發送時間：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}"
    msg.html = f"""
    <div style="font-family: sans-serif; padding: 20px; background-color: #f8fafc; border-radius: 8px;">
        <h2 style="color: #5f788a;">🛒 {shop_name} — 郵件發送測試成功</h2>
        <p>若您收到此信件，代表系統的 SMTP 郵件通知服務已正確配置並可正常寄送！</p>
        <p style="color: #64748b; font-size: 13px;">發送時間：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}</p>
    </div>
    """
    try:
        mail.send(msg)
        return True, f"測試郵件已成功寄送至 {recipient.strip()}！"
    except Exception as e:
        return False, f"郵件發送失敗: {str(e)}"
