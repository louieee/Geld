from django.urls import path
import account.views as d_view

urlpatterns = [
    path('login/', d_view.login, name='login'),
    path('signup/', d_view.signup, name='signup'),
    path('payment/<username>/', d_view.payment, name='payment'),
    path('verify/<username>/', d_view.verify, name='verify'),
    path('account/<username>/', d_view.account, name='account'),
    path('new.account/<username>/', d_view.new_account, name='new account'),
    path('upgrade/<username>/', d_view.upgrade, name='upgrade'),
    path('cashout/<username>/', d_view.cash_out, name='cash out'),
    path('wallet/<username>/', d_view.client_wallet, name='wallet')


]
