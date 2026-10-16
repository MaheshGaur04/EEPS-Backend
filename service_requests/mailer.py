from django.conf import settings
from django.core.mail import send_mail


def send_status_email(to_email: str, name: str | None, service, new_status: str):
    if not settings.EMAIL_HOST or not settings.EMAIL_HOST_USER:
        return

    subject = f'Service request {service.subject} - {new_status}'
    body = (
        f"Hi {name or 'Customer'},\n\n"
        f"Your service request {service.subject} (ID: {service.pk}) has been updated to {new_status}.\n\n"
        f"Details:\n{service.description}\n\n"
        f"If you have questions, please reply to this email or contact support.\n\n"
        f"Thanks,\n{settings.COMPANY_NAME}"
    )
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to_email], fail_silently=True)
    except Exception as exc:  # pragma: no cover
        print(f'Failed to send status email: {exc}')
