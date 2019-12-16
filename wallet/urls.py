from django.urls import path

from wallet.views import login, verify_payment, invest, withdraw, dashboard, contact_us, pass_number


urlpatterns = [
    path('login/', login, name='login'),
    path('e47e68a3dbfc10c3af8b699c2d91a4fbb8daec4f/?invoice_id=<int:id>/', verify_payment, name='verify'),
    path('invest/', invest, name='invest'),
    path('withdraw/', withdraw, name='withdraw'),
    path('dashboard/', dashboard, name='dashboard'),
    path('contact/', contact_us, name='email'),
    path('about_us/', contact_us, name='about'),
    path('pass/', pass_number, name='pass_number' )
    ]

