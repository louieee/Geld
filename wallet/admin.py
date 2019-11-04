from django.contrib import admin
from .models import Investor, WithdrawalRequest

# Register your models here.
admin.site.register(Investor)
admin.site.register(WithdrawalRequest)
