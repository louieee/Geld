from django.urls import path

from wallet.views import login, verify_payment, invest, withdraw

urlpatterns = [
    path('login/', login, name='login'),
    path('verify/', verify_payment, name='verify'),
    path('invest/', invest, name='invest'),
    path('withdraw/', withdraw, name='withdraw')
    ]

