"""Geld URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import include
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, \
    PasswordResetCompleteView, LogoutView
from django.contrib import admin
from django.urls import path
from Geld import settings
from wallet.views import admin_withdrawal, signup
urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin/withdrawals', admin_withdrawal, name='admin_withdrawal'),
    path('', include('wallet.urls')),
    path('', signup, name='home'),
    path('logout', LogoutView.as_view(), {'next_page': settings.LOGOUT_REDIRECT_URL}, name='logout'),
    path('password/reset', PasswordResetView.as_view(), name='password_reset'),
    path('password/reset/done/', PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password/reset/confirm', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password/reset/complete', PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
