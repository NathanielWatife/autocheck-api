from django.contrib import admin
from django.contrib.auth.admin import UserAdmin 
from .models import *

# Register your models here.
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_dealer', 'dealer_verified', 'credits')
    fieldsets = UserAdmin.fieldsets + (
        ('Extra Info', {'fields': ('phone_number', 'nin', 'is_dealer', 'dealer_verified', 'credits')}),
    )


admin.site.register(User, CustomUserAdmin)
admin.site.register(UserProfile)