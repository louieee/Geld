from django.urls import path

from wallet.views import login, verify_payment, invest, withdraw, dashboard, contact_us, login2

urlpatterns = [
    path('login/', login, name='login'),
    path('login/<code>/', login2, name='login2'),
    path('verify/', verify_payment, name='verify'),
    path('invest/', invest, name='invest'),
    path('withdraw/', withdraw, name='withdraw'),
    path('dashboard/', dashboard, name='dashboard'),
    path('contact/', contact_us, name='email')
    ]

