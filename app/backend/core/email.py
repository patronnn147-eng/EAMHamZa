"""
Email Service for sending notifications
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP"""
    
    def __init__(self):
        self.smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_username = os.environ.get("SMTP_USERNAME", "")
        self.smtp_password = os.environ.get("SMTP_PASSWORD", "")
        self.from_email = os.environ.get("FROM_EMAIL", self.smtp_username)
        self.from_name = os.environ.get("FROM_NAME", "Asset Management System")
        
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str = None
    ) -> bool:
        """
        Send an email
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content (optional, falls back to HTML)
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Add text and HTML parts
            if text_content:
                part1 = MIMEText(text_content, 'plain', 'utf-8')
                msg.attach(part1)
            
            part2 = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(part2)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    def send_registration_pending_email(self, user_email: str, user_name: str) -> bool:
        """Send email notification that registration is pending approval"""
        subject = "Inscription en attente d'approbation"
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2563eb;">Bienvenue {user_name}!</h2>
                    <p>Votre inscription a été reçue avec succès.</p>
                    <p>Votre compte est actuellement <strong>en attente d'approbation</strong> par un administrateur.</p>
                    <p>Vous recevrez un email de confirmation dès que votre compte sera approuvé.</p>
                    <div style="margin-top: 30px; padding: 15px; background-color: #f3f4f6; border-radius: 5px;">
                        <p style="margin: 0;"><strong>Note:</strong> Ce processus peut prendre quelques heures. Merci de votre patience.</p>
                    </div>
                    <p style="margin-top: 30px; color: #6b7280; font-size: 14px;">
                        Cordialement,<br>
                        L'équipe Asset Management
                    </p>
                </div>
            </body>
        </html>
        """
        
        text_content = f"""
        Bienvenue {user_name}!
        
        Votre inscription a été reçue avec succès.
        Votre compte est actuellement en attente d'approbation par un administrateur.
        Vous recevrez un email de confirmation dès que votre compte sera approuvé.
        
        Note: Ce processus peut prendre quelques heures. Merci de votre patience.
        
        Cordialement,
        L'équipe Asset Management
        """
        
        return self.send_email(user_email, subject, html_content, text_content)
    
    def send_approval_email(self, user_email: str, user_name: str) -> bool:
        """Send email notification that account has been approved"""
        subject = "Votre compte a été approuvé!"
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #10b981;">Félicitations {user_name}!</h2>
                    <p>Votre compte a été <strong style="color: #10b981;">approuvé</strong> par un administrateur.</p>
                    <p>Vous pouvez maintenant vous connecter et accéder à votre espace.</p>
                    <div style="margin-top: 30px;">
                        <a href="{os.environ.get('FRONTEND_URL', 'http://localhost:5173')}/login" 
                           style="display: inline-block; padding: 12px 24px; background-color: #2563eb; color: white; text-decoration: none; border-radius: 5px;">
                            Se connecter
                        </a>
                    </div>
                    <p style="margin-top: 30px; color: #6b7280; font-size: 14px;">
                        Cordialement,<br>
                        L'équipe Asset Management
                    </p>
                </div>
            </body>
        </html>
        """
        
        text_content = f"""
        Félicitations {user_name}!
        
        Votre compte a été approuvé par un administrateur.
        Vous pouvez maintenant vous connecter et accéder à votre espace.
        
        Lien de connexion: {os.environ.get('FRONTEND_URL', 'http://localhost:5173')}/login
        
        Cordialement,
        L'équipe Asset Management
        """
        
        return self.send_email(user_email, subject, html_content, text_content)
    
    def send_rejection_email(self, user_email: str, user_name: str, reason: str = None) -> bool:
        """Send email notification that account has been rejected"""
        subject = "Votre inscription n'a pas été approuvée"
        
        reason_text = f"<p><strong>Raison:</strong> {reason}</p>" if reason else ""
        reason_plain = f"\nRaison: {reason}\n" if reason else ""
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #ef4444;">Bonjour {user_name},</h2>
                    <p>Nous regrettons de vous informer que votre inscription n'a pas été approuvée.</p>
                    {reason_text}
                    <p>Si vous pensez qu'il s'agit d'une erreur, vous pouvez vous réinscrire ou contacter un administrateur.</p>
                    <div style="margin-top: 30px;">
                        <a href="{os.environ.get('FRONTEND_URL', 'http://localhost:5173')}/login" 
                           style="display: inline-block; padding: 12px 24px; background-color: #2563eb; color: white; text-decoration: none; border-radius: 5px;">
                            Réessayer l'inscription
                        </a>
                    </div>
                    <p style="margin-top: 30px; color: #6b7280; font-size: 14px;">
                        Cordialement,<br>
                        L'équipe Asset Management
                    </p>
                </div>
            </body>
        </html>
        """
        
        text_content = f"""
        Bonjour {user_name},
        
        Nous regrettons de vous informer que votre inscription n'a pas été approuvée.
        {reason_plain}
        Si vous pensez qu'il s'agit d'une erreur, vous pouvez vous réinscrire ou contacter un administrateur.
        
        Lien d'inscription: {os.environ.get('FRONTEND_URL', 'http://localhost:5173')}/login
        
        Cordialement,
        L'équipe Asset Management
        """
        
        return self.send_email(user_email, subject, html_content, text_content)


# Global email service instance
email_service = EmailService()