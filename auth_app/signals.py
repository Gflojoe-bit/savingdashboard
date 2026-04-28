from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Space, SpaceMembership


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_personal_space(sender, instance, created, **kwargs):
    """Auto-create a Personal Space + membership for every new User.

    The Space schema is the auth subsystem's contract; this hook keeps the
    invariant "every User has exactly one Personal Space" enforced for any
    user-creation path (admin, createsuperuser, future invite flow).
    """
    if not created:
        return
    space = Space.objects.create(
        name=f"{instance.get_username()}'s Space",
        owner=instance,
        is_personal=True,
    )
    SpaceMembership.objects.create(space=space, user=instance)
