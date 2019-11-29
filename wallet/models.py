from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
# Create your models here.
from django.db.models import F
from sendgrid import Mail, SendGridAPIClient
from django.utils.datetime_safe import datetime


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
    login_retries = models.IntegerField(default=0)
    otp_sent = models.BooleanField(default=True)

    def level_details(self):
        level_data = {0: 'Novice', 1: 'Newbie', 2: 'Intermediate', 3: 'Senior', 4: 'Professional', 5: 'Veteran',
                      6: 'Master', 7: 'Grand Master'}
        return level_data[self.level]

    def percentage(self):
        try:
            return self.investment_count / (pow(self.level, 2))
        except ZeroDivisionError:
            return 0

    def direct_downliners(self):
        return Investor.objects.all().filter(referer_id=self.id)

    def upgrade_investor(self):
        upgrade = {[0, 0]: 1, [2, 1]: 2, [4, 2]: 3, [8.3]: 4, [16, 4]: 5, [32, 5]: 6, [64, 6]: 7}
        previous_level = self.level
        self.level = upgrade[[self.investment_count, self.level]]
        if self.level is None:
            self.level = previous_level
        else:
            self.investment_count = 0
        self.save()

        def level1():
            def message_investor():
                message = Mail(from_email=settings.EMAIL, to_emails=self.email,
                               subject='Successful wallet Funding', plain_text_content='Dear ' +
                                                                                       self.username + ', You have successfully funded your wallet with 0.001 Btc')
                sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
                response = sg.send(message)

            def get_random_referer():
                return Investor.objects.all().filter(level=1).order_by('id')[0]

            def upgrade_due_person(referer):
                referer.investment_count = F(referer.investment_count) + 1
                if referer.investment_count % 2 == 0 or referer.investment_count > 2:
                    referer.balance = F(referer.balance) + 0.001
                if referer.investment_count == 2:
                    pass
                referer.save()
                referer.upgrade_investor()
                referer.save()

            def get_tree_referer():
                global prev
                global next_
                curr = Investor.objects.get(id=self.referer_id)
                while curr is not None:
                    if curr.level > 1:
                        try:
                            next_ = Investor.objects.get(referer_id=curr.id)
                        except Investor.DoesNotExist:
                            next_ = None
                        prev = curr
                        curr = next_
                    elif curr.level == 1:
                        prev = curr
                        curr = None
                return prev

            if self.referer is None:
                upgrade_due_person(get_random_referer())
                message_investor()
                self.save()
            else:
                upgrade_due_person(get_tree_referer())
                message_investor()
                self.save()
            return True

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

        upgrade = {0: level1(), 1: level2(), 2: level3(), 3: level4(), 4: level5(), 5: level6(), 6: out()}
        result = upgrade[self.level]
        return result

    def pending_withdrawals(self):
        return WithdrawalRequest.objects.all().order_by('-date_of_request').filter(investor_id=self.id).filter \
            (serviced=False)

    def withdrawals(self):
        return WithdrawalRequest.objects.all().order_by('-date_of_request').filter(investor_id=self.id).filter \
            (serviced=True)


class WithdrawalRequest(models.Model):
    amount = models.DecimalField(max_digits=9, decimal_places=6, default=0.0000)
    date_of_request = models.DateTimeField()
    final = models.BooleanField(default=False)
    investor = models.ForeignKey(Investor, on_delete=models.CASCADE)
    address = models.CharField(max_length=50, default=None, null=True)
    serviced = models.BooleanField(default=False)

    def withdrawal_fee(self):
        return self.amount * (2 / 100)
