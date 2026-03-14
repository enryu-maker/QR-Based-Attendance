from django.core.mail import get_connection, EmailMessage
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_custom_email(company, subject, body, recipient_list):
    """
    Sends an email using the company's custom SMTP settings.
    """
    if not company.smtp_host or not company.smtp_user or not company.smtp_password:
        logger.warning(f"SMTP settings not configured for company: {company.name}")
        return False

    try:
        # Create a connection using the company's SMTP settings
        connection = get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host=company.smtp_host,
            port=company.smtp_port,
            username=company.smtp_user,
            password=company.smtp_password,
            use_tls=company.smtp_use_tls,
            use_ssl=company.smtp_use_ssl,
            timeout=10
        )

        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=company.smtp_from_email or company.smtp_user,
            to=recipient_list,
            connection=connection
        )
        
        email.send()
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False
