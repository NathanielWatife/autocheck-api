from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.user_profile, name='user_profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('change-password/', views.change_password, name='change_password'),

    # password reset
    path('password-reset/', views.password_reset_request, name='password_reset_request'),
    path('password-reset-confirm/', views.password_reset_confirm, name='password_reset_confirm'),

    #  garage
    path('garage/', views.list_garage, name='garage_list'),
    path('garage/save/<str:vin>/', views.save_vehicle, name='save_vehicle'),
    path('garage/remove/<str:vin>/', views.unsave_vehicle, name='unsave_vehicle'),
]