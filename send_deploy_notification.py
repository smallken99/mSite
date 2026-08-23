import sys
import subprocess
from datetime import datetime, timezone, timedelta
from flask_mail import Message
from mSite import create_app, mail

TW_TZ = timezone(timedelta(hours=8))
RECIPIENTS = ['smallken@gmail.com', 'oioi7211@gmail.com']


def get_git_info():
    """取得當前最新 Commit 資訊"""
    try:
        commit_hash = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('utf-8').strip()
        commit_msg = subprocess.check_output(['git', 'log', '-1', '--pretty=%B']).decode('utf-8').strip()
        author_name = subprocess.check_output(['git', 'log', '-1', '--pretty=%an']).decode('utf-8').strip()
        changed_files = subprocess.check_output(['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD']).decode('utf-8').strip().splitlines()
        return {
            'hash': commit_hash,
            'message': commit_msg,
            'author': author_name,
            'files': changed_files
        }
    except Exception as e:
        return {
            'hash': 'unknown',
            'message': '最新版本上線更新',
            'author': 'Deployment Agent',
            'files': []
        }


def send_deploy_email(custom_msg=None):
    app = create_app()
    with app.app_context():
        git_info = get_git_info()
        now_str = datetime.now(TW_TZ).strftime('%Y/%m/%d %H:%M:%S')
        feat_text = custom_msg or git_info['message']
        commit_hash = git_info['hash']
        author = git_info['author']
        files = git_info['files']

        files_html = "".join([f"<li style='margin-bottom: 4px; font-family: monospace;'>{f}</li>" for f in files]) if files else "<li>無檔案異動紀錄</li>"

        subject = f"🚀 [mSite 部署通知] {feat_text.splitlines()[0] if feat_text else '新版本上線成功'}"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Microsoft JhengHei', sans-serif; background-color: #f1f5f9; margin: 0; padding: 24px;">
            <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.08); border: 1px solid #e2e8f0;">
                
                <!-- 頂部 Header -->
                <div style="background: linear-gradient(135deg, #1e293b 0%, #334155 100%); color: #ffffff; padding: 24px; text-align: center;">
                    <h2 style="margin: 0; font-size: 22px; letter-spacing: 0.5px;">🚀 mSite 服務部署成功通知</h2>
                    <div style="font-size: 13px; color: #94a3b8; margin-top: 6px;">正式環境 (vultr2) 服務已順利重啟並上線生效</div>
                </div>

                <!-- 內容區塊 -->
                <div style="padding: 24px;">
                    
                    <!-- 更新摘要卡片 -->
                    <div style="background-color: #f8fafc; border-left: 4px solid #2563eb; padding: 14px 18px; border-radius: 6px; margin-bottom: 20px;">
                        <div style="font-size: 12px; font-weight: bold; color: #64748b; text-transform: uppercase; margin-bottom: 6px;">本次更新功能 (Feat)</div>
                        <div style="font-size: 16px; font-weight: 700; color: #0f172a; line-height: 1.5; white-space: pre-wrap;">{feat_text}</div>
                    </div>

                    <!-- 版本與環境資訊 -->
                    <table style="width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 20px;">
                        <tr style="border-bottom: 1px solid #f1f5f9;">
                            <td style="padding: 10px 0; color: #64748b; width: 110px;">📅 部署時間</td>
                            <td style="padding: 10px 0; color: #1e293b; font-weight: 600;">{now_str} (台灣時間 UTC+8)</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #f1f5f9;">
                            <td style="padding: 10px 0; color: #64748b;">🔖 Commit 標籤</td>
                            <td style="padding: 10px 0; color: #2563eb; font-weight: bold; font-family: monospace;">{commit_hash}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #f1f5f9;">
                            <td style="padding: 10px 0; color: #64748b;">👤 提交人員</td>
                            <td style="padding: 10px 0; color: #1e293b;">{author}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; color: #64748b;">🌐 線上站點</td>
                            <td style="padding: 10px 0;"><a href="https://store.smallken.site/shop" style="color: #2563eb; text-decoration: none; font-weight: bold;">https://store.smallken.site/shop</a></td>
                        </tr>
                    </table>

                    <!-- 異動檔案列表 -->
                    <div style="margin-bottom: 12px;">
                        <div style="font-size: 13px; font-weight: 600; color: #475569; margin-bottom: 8px;">📁 本次異動檔案清單：</div>
                        <ul style="background: #f8fafc; padding: 12px 12px 12px 28px; border-radius: 6px; font-size: 13px; color: #334155; margin: 0; line-height: 1.6; border: 1px solid #e2e8f0;">
                            {files_html}
                        </ul>
                    </div>

                    <!-- 底部提示 -->
                    <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #e2e8f0; text-align: center; color: #94a3b8; font-size: 12px;">
                        此郵件由 mSite 自動化部署流程發送至 <strong>{', '.join(RECIPIENTS)}</strong>
                    </div>

                </div>
            </div>
        </body>
        </html>
        """

        msg = Message(
            subject=subject,
            recipients=RECIPIENTS,
            html=html_body
        )

        try:
            mail.send(msg)
            print(f"✅ 部署通知信已成功發送至: {', '.join(RECIPIENTS)}")
            return True
        except Exception as e:
            print(f"❌ 部署通知信發送失敗: {str(e)}")
            return False


if __name__ == '__main__':
    custom_message = sys.argv[1] if len(sys.argv) > 1 else None
    send_deploy_email(custom_message)
