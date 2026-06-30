from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


# Create your models here.
class User(AbstractUser):
    """
    Custom user models that extends the user model provided by Django. This allows for additional fields and customization of the user model.
    """
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    nin = models.CharField(max_length=11, null=False, blank=False, unique=True)
    is_dealer = models.BooleanField(default=False)
    dealer_verified = models.BooleanField(default=False)
    credits = models.IntegerField(default=0)

    class Meta:
        db_table = 'auth_user'

    def __str__(self):
        return self.username


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    saved_vehicles = models.ManyToManyField('vehicles.Vehicle', related_name='saved_by_users', blank=True)
    bio = models.TextField(max_length=200, null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    watchlist = models.ManyToManyField('vehicles.Vehicle',  related_name='watched_by', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()