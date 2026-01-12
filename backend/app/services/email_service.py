"""
邮件发送服务

支持通过SMTP发送价格提醒邮件
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)

# 邮件配置（从环境变量读取）
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", SMTP_USERNAME)
SENDER_NAME = os.getenv("SENDER_NAME", "Trade View 价格提醒")


class EmailService:
    """邮件发送服务"""
    
    def __init__(self):
        self.smtp_server = SMTP_SERVER
        self.smtp_port = SMTP_PORT
        self.username = SMTP_USERNAME
        self.password = SMTP_PASSWORD
        self.sender_email = SENDER_EMAIL
        self.sender_name = SENDER_NAME
    
    def is_configured(self) -> bool:
        """检查邮件服务是否已配置"""
        return bool(self.username and self.password)
    
    def send_price_alert(
        self,
        to_email: str,
        stock_code: str,
        stock_name: Optional[str],
        alert_type: str,  # 'stop_loss' 或 'take_profit'
        current_price: float,
        target_price: float
    ) -> bool:
        """
        发送价格提醒邮件
        
        Args:
            to_email: 收件人邮箱
            stock_code: 股票代码
            stock_name: 股票名称
            alert_type: 提醒类型
            current_price: 当前价格
            target_price: 目标价格
            
        Returns:
            是否发送成功
        """
        if not self.is_configured():
            logger.warning("邮件服务未配置，跳过发送")
            return False
        
        try:
            # 构造邮件内容
            alert_type_zh = "止盈提醒 🎉" if alert_type == "take_profit" else "止损提醒 ⚠️"
            stock_display = f"{stock_code} - {stock_name}" if stock_name else stock_code
            
            subject = f"【Trade View】{alert_type_zh} - {stock_code}"
            
            # HTML邮件正文（JOJO风格）
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{
                        font-family: 'Arial', sans-serif;
                        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                        color: #ffffff;
                        padding: 20px;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        background-color: #0f3460;
                        border: 4px solid #FFD700;
                        border-radius: 12px;
                        padding: 30px;
                        box-shadow: 0 8px 32px rgba(255, 215, 0, 0.3);
                    }}
                    .header {{
                        text-align: center;
                        font-size: 32px;
                        font-weight: bold;
                        color: #FFD700;
                        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
                        margin-bottom: 20px;
                    }}
                    .alert-box {{
                        background: {'rgba(16, 185, 129, 0.2)' if alert_type == 'take_profit' else 'rgba(239, 68, 68, 0.2)'};
                        border: 2px solid {'#10B981' if alert_type == 'take_profit' else '#EF4444'};
                        border-radius: 8px;
                        padding: 20px;
                        margin: 20px 0;
                    }}
                    .stock-name {{
                        font-size: 24px;
                        font-weight: bold;
                        color: #FFD700;
                        margin-bottom: 10px;
                    }}
                    .price-info {{
                        font-size: 18px;
                        margin: 10px 0;
                    }}
                    .price {{
                        font-size: 28px;
                        font-weight: bold;
                        color: {'#10B981' if alert_type == 'take_profit' else '#EF4444'};
                    }}
                    .footer {{
                        text-align: center;
                        font-size: 14px;
                        color: #9ca3af;
                        margin-top: 30px;
                        padding-top: 20px;
                        border-top: 1px solid #4b5563;
                    }}
                    .emoji {{
                        font-size: 48px;
                        text-align: center;
                        margin: 20px 0;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">⭐ TRADE VIEW ⭐</div>
                    <div class="emoji">{'🎉' if alert_type == 'take_profit' else '⚠️'}</div>
                    <div class="alert-box">
                        <div class="stock-name">{stock_display}</div>
                        <div class="price-info">
                            <strong>提醒类型：</strong>{alert_type_zh}
                        </div>
                        <div class="price-info">
                            <strong>当前价格：</strong>
                            <span class="price">¥{current_price:.2f}</span>
                        </div>
                        <div class="price-info">
                            <strong>目标价格：</strong>¥{target_price:.2f}
                        </div>
                    </div>
                    <div class="footer">
                        <p>这是一封自动发送的提醒邮件，请勿直接回复。</p>
                        <p>如需关闭邮箱提醒，请登录 Trade View 在用户设置中修改。</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # 创建邮件
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.sender_name} <{self.sender_email}>"
            message["To"] = to_email
            
            # 添加HTML正文
            html_part = MIMEText(html_body, "html", "utf-8")
            message.attach(html_part)
            
            # 发送邮件
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(message)
            
            logger.info(f"✅ 邮件发送成功: {to_email} - {stock_code} {alert_type}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 邮件发送失败: {to_email} - {stock_code} - {e}")
            return False


# 默认邮件服务实例
default_email_service = EmailService()
