from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

# Create your models here.
from django.db.models import F


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
    def percentage(self):
        return self.investment_count / (pow(self.level, 2))

    def direct_downliners(self):
        downliners = Investor.objects.all().filter(referer_id=self.id)
        its_list = []
        for investor in downliners:
            detail = {'username': investor.username, 'level': investor.level, 'email': investor.email}
            its_list.append(detail)
        return its_list

    def upgrade_investor(self):
        upgrade = {[2, 1]: 2, [4, 2]: 3, [8.3]: 4, [16, 4]: 5, [32, 5]: 6, [64, 6]: 7}
        previous_level = self.level
        self.level = upgrade[[self.investment_count, self.level]]
        if self.level is None:
            self.level = previous_level
        else:
            self.investment_count = 0
        self.save()

        def level2():
            try:
                referer = Investor.objects.get(id=Investor.objects.get(id=self.referer_id).referer_id)
                referer.investment_count = F(referer.investment_count) + 1
                if referer.investment_count % 2 == 0 or referer.investment_count > 4:
                    referer.balance = F(referer.balance) + 0.001
                if referer.investment_count == 4:
                    referer.upgrade_investor()
                referer.save()
                return True
            except Investor.DoesNotExist:
                return False

        def level3():
            try:
                referer = Investor.objects.get(id=Investor.objects.get(id=Investor.objects.get
                (id=self.referer_id).referer_id).referer_id)
                referer.investment_count = F(referer.investment_count) + 1
                if referer.investment_count % 2 == 0 or referer.investment_count > 8:
                    referer.balance = F(referer.balance) + 0.002
                if referer.investment_count == 8:
                    referer.upgrade_investor()

                referer.save()
                return True
            except Investor.DoesNotExist:
                return False

        def level4():
            try:
                referer = Investor.objects.get(
                    id=Investor.objects.get(id=Investor.objects.get(id=Investor.objects.get
                    (id=self.referer_id).referer_id).referer_id).referer_id)
                referer.investment_count = F(referer.investment_count) + 1
                if referer.investment_count % 2 == 0 or referer.investment_count > 12:
                    referer.balance = F(referer.balance) + 0.006
                if referer.investment_count == 16:
                    referer.upgrade_investor()

                referer.save()
                return True
            except Investor.DoesNotExist:
                return False

        def level5():
            try:
                referer = Investor.objects.get(id=
                                               Investor.objects.get(
                                                   id=Investor.objects.get(
                                                       id=Investor.objects.get(id=Investor.objects.get(
                                                           id=self.referer_id).referer_id).referer_id).
                                                       referer_id).referer_id)
                referer.investment_count = F(referer.investment_count) + 1
                if referer.investment_count % 2 == 0 or referer.investment_count > 16:
                    referer.balance = F(referer.balance) + 0.024
                if referer.investment_count == 32:
                    referer.upgrade_investor()

                referer.save()
                return True
            except Investor.DoesNotExist:
                return False

        def level6():
            try:
                referer = Investor.objects.get(id=Investor.objects.get(id=
                                                                       Investor.objects.get(
                                                                           id=Investor.objects.get(
                                                                               id=Investor.objects.get(
                                                                                   id=Investor.objects.get(
                                                                                       id=self.referer_id).
                                                                                       referer_id).referer_id).
                                                                               referer_id).referer_id).referer_id)
                referer.investment_count = F(referer.investment_count) + 1
                if referer.investment_count % 2 == 0 or referer.investment_count > 28:
                    referer.balance = F(referer.balance) + 0.168
                if referer.investment_count == 64:
                    referer.upgrade_investor()
                referer.save()
                return True
            except Investor.DoesNotExist:
                return False

        def out():
            last_withdrawal = WithdrawalRequest()
            last_withdrawal.investor = self
            last_withdrawal.amount = self.balance - 0.752
            last_withdrawal.final = True
            last_withdrawal.save()
            return 'final'

        upgrade = {1: level2(), 2: level3(), 3: level4(), 4: level5(), 5: level6(), 6: out()}
        result = upgrade[self.level]
        return result

    def pending_withdrawals(self):
        all_withdrawals = []
        for item in WithdrawalRequest.objects.all().order_by('-date_of_request').filter(investor_id=self.id).filter \
                    (serviced=False):
            detail = {'id': item.id, 'amount': item.amount, 'date': item.date_of_request.date(),
                      'time': item.date_of_request.time(), 'address': item.address}
            all_withdrawals.append(detail)
        return all_withdrawals

    def withdrawals(self):
        all_withdrawals = []
        for item in WithdrawalRequest.objects.all().order_by('-date_of_request').filter(investor_id=self.id).filter \
                    (serviced=True):
            detail = {'id': item.id, 'amount': item.amount, 'date': item.date_of_request.date(),
                      'time': item.date_of_request.time(), 'address': item.address}
            all_withdrawals.append(detail)
        return all_withdrawals


class WithdrawalRequest(models.Model):
    amount = models.DecimalField(max_digits=6, decimal_places=4, default=0.0000)
    date_of_request = models.DateTimeField()
    final = models.BooleanField(default=False)
    investor = models.ForeignKey(Investor, on_delete=models.CASCADE)
    address = models.CharField(max_length=50, default=None, null=True)
    serviced = models.BooleanField(default=False)

    def withdrawal_fee(self):
        return self.amount * (2 / 100)
