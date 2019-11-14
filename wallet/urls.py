from django.urls import path

from wallet.views import login, verify_payment, invest, withdraw, dashboard

urlpatterns = [
    path('login/', login, name='login'),
    path('verify/', verify_payment, name='verify'),
    path('invest/', invest, name='invest'),
    path('withdraw/', withdraw, name='withdraw'),
    path('dashboard/', dashboard, name='dashboard'),
    ]

