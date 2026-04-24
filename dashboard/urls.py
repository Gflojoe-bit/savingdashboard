from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('accounts/', views.accounts, name='accounts'),
    path('accounts/<int:account_id>/', views.account_detail, name='account_detail'),
    path('settings/', views.settings_view, name='settings'),
]
