from django.contrib import admin
from .models import Investor, WithdrawalRequest, Wallet

# Register your models here.
admin.site.register(Investor)
admin.site.register(WithdrawalRequest)
admin.site.register(Wallet)
