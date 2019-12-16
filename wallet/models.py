from decimal import Decimal
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class Wallet(models.Model):
    guid = models.CharField(max_length=255)
    api_key = models.CharField(max_length=255)
    password = models.CharField(max_length=50)
    xpub = models.CharField(max_length=255, default=None, null=True)


class Investor(AbstractUser):
    level = models.IntegerField(default=0)
    balance = models.DecimalField(max_digits=6, decimal_places=4, default=0.0000)
    deposit_address = models.CharField(max_length=50, default=None, null=True)
    investment_count = models.IntegerField(default=0)
    referer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING, null=True)
    pass_number = models.CharField(max_length=4, default='')
    timer = models.DateTimeField(default=None, null=True)
    referral_url = models.CharField(max_length=150, default='')

    def pending_withdrawals(self):
        return WithdrawalRequest.objects.all().order_by('-date_of_request').filter(investor_id=self.id).filter \
            (serviced=False)

    def withdrawals(self):
        return WithdrawalRequest.objects.all().order_by('-date_of_request').filter(investor_id=self.id).filter \
            (serviced=True)

    def direct_downliners(self):
        return Investor.objects.all().filter(referer_id=self.id)

    def level_details(self):
        level_data = {0: 'Novice', 1: 'Newbie', 2: 'Intermediate', 3: 'Senior', 4: 'Professional', 5: 'Veteran',
                      6: 'Master', 7: 'Grand Master'}
        return level_data[self.level]

    def percentage(self):
        try:
            return (self.investment_count / (pow(2, self.level))) * 100
        except ZeroDivisionError:
            return 0


class WithdrawalRequest(models.Model):
    amount = models.DecimalField(max_digits=9, decimal_places=6, default=0.0000)
    date_of_request = models.DateTimeField()
    final = models.BooleanField(default=False)
    investor = models.ForeignKey(Investor, on_delete=models.CASCADE)
    address = models.CharField(max_length=50, default=None, null=True)
    serviced = models.BooleanField(default=False)

    def withdrawal_fee(self):
        return self.amount * Decimal(2 / 100)

    def total_amount(self):
        return self.amount + self.withdrawal_fee()
