from celery import shared_task
from django.utils import timezone
from .models import CategoryOffer

@shared_task
def deactivate_expired_offers():
    """Deactivate CategoryOffers that have expired."""
    now = timezone.now().date()
    expired_offers = CategoryOffer.objects.filter(end_date__lt=now, is_active=True)
    expired_offers.update(is_active=False)
    return f'{expired_offers.count()} expired offers deactivated.'
