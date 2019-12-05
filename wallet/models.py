import secrets
from urllib.error import URLError
from decimal import Decimal

import django
from django.contrib.sites.shortcuts import get_current_site
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
# Create your models here.
from django.db.models import F
from sendgrid import Mail, SendGridAPIClient
from django.utils.datetime_safe import datetime
from django.utils.timezone import timedelta as td, timezone as tz


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
    pass_phrase = models.CharField(max_length=255, default='')
    timer = models.DateTimeField(default=None, null=True)
    timer_no = models.IntegerField(default=0)
    timer_on = models.BooleanField(default=False)
    callback_id = models.CharField(max_length=150, default='')

    def get_call_back(self, request):
        id_ = hex(secrets.randbits(125))[2:]
        current = get_current_site(request)
        url = str(current) + '/wallet/' + id_ + '?invoice_id=' + str(self.id)
        self.callback_id = id_
        self.save()
        return url

    def reset_parameters(self):
        self.timer_no = 0
        self.timer = None
        self.login_retries = 0
        self.save()

    def increment_login_retries(self):
        self.login_retries = self.login_retries + 1
        self.save()

    def activate_security(self):
        if self.login_retries == 3 and self.timer_no < 6 and self.timer_no == 0:
            self.increment_timer()
        elif self.login_retries < 3 and self.timer_no == 0:
            self.increment_login_retries()
        elif self.timer_no == 6 and self.login_retries == 3:
            self.login_retries = 0
            self.timer_no = 0
            self.is_active = False

    def check_timer(self):
        try:
            if (int((self.timer.timestamp() - datetime.now().timestamp()) / 60) - 60) <= 0:
                self.timer_on = False
                self.save()
        except AttributeError:
            pass

    def set_timer(self, number):
        self.timer = datetime.now() + td(minutes=int(number))
        self.timer_on = True
        self.save()

    def increment_timer(self):
        self.timer_no = self.timer_no + 1
        self.set_timer(int(self.timer_no * 10))

    def level_details(self):
        level_data = {0: 'Novice', 1: 'Newbie', 2: 'Intermediate', 3: 'Senior', 4: 'Professional', 5: 'Veteran',
                      6: 'Master', 7: 'Grand Master'}
        return level_data[self.level]

    def percentage(self):
        try:
            return (self.investment_count / (pow(2, self.level))) * 100
        except ZeroDivisionError:
            return 0

    def direct_downliners(self):
        return Investor.objects.all().filter(referer_id=self.id)

    def upgrade_investor(self):

        def level1():

            def message_investor():
                try:
                    message = Mail(from_email=settings.EMAIL, to_emails=self.email,
                                   subject='Successful wallet Funding', plain_text_content='Dear ' +
                                                                                           self.username + ', You have successfully funded your wallet with 0.001 Btc')
                    sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
                    response = sg.send(message)
                except URLError:
                    pass

            def get_random_referer():
                try:
                    ref = Investor.objects.all().filter(level=1).order_by('id')[0]
                    return ref
                except IndexError:
                    return None

            def upgrade_due_person(referer_):
                if referer_ is not None:
                    referer_.investment_count = referer_.investment_count + 1
                    referer_.save()
                    if int(referer_.investment_count) % 2 == 0 or int(referer_.investment_count) > 2:
                        referer_.balance = referer_.balance + Decimal(0.001)
                    referer_.save()
                    referer_.upgrade_investor()
                    referer_.save()
                else:
                    pass

            def get_tree_referer():
                global prev
                global next_
                try:
                    curr = Investor.objects.get(id=self.referer_id, level__gt=0)
                except Investor.DoesNotExist:
                    curr = None
                    prev = None
                except Investor.MultipleObjectsReturned:
                    curr = Investor.objects.all().order_by('id').filter(id=self.referer_id, level__gt=0)[0]

                while curr is not None:
                    if curr.level > 1:
                        try:
                            next_ = Investor.objects.get(referer_id=curr.id, level__gt=0)
                        except Investor.DoesNotExist:
                            next_ = None
                        except Investor.MultipleObjectsReturned:
                            next_ = Investor.objects.all().order_by('id').filter(referer_id=curr.id, level__gt=0)[0]
                        prev = curr
                        curr = next_
                    elif curr.level == 1:
                        prev = curr
                        curr = None
                if prev is None:
                    return get_random_referer()
                else:
                    return prev

            if self.referer is None:
                upgrade_due_person(get_random_referer())
                self.save()
                message_investor()
            else:
                referer = Investor.objects.get(id=self.referer_id)
                if referer.level > 1:
                    upgrade_due_person(get_tree_referer())
                else:
                    upgrade_due_person(referer)
                self.save()
                message_investor()

        def level2():
            try:
                referer = Investor.objects.get(id=Investor.objects.get(id=self.referer_id).referer_id)
                referer.investment_count = referer.investment_count + 1
                referer.save()
                if referer.investment_count % 2 == 0 or referer.investment_count > 4:
                    referer.balance = referer.balance + Decimal(0.001)
                if referer.investment_count == 4:
                    referer.upgrade_investor()
                referer.save()

            except Investor.DoesNotExist:
                pass

        def level3():
            try:
                referer = Investor.objects.get(id=Investor.objects.get(id=Investor.objects.get
                (id=self.referer_id).referer_id).referer_id)
                referer.investment_count = referer.investment_count + 1
                referer.save()
                if referer.investment_count % 2 == 0 or referer.investment_count > 8:
                    referer.balance = referer.balance + Decimal(0.002)
                if referer.investment_count == 8:
                    referer.upgrade_investor()

                referer.save()

            except Investor.DoesNotExist:
                pass

        def level4():
            try:
                referer = Investor.objects.get(
                    id=Investor.objects.get(id=Investor.objects.get(id=Investor.objects.get
                    (id=self.referer_id).referer_id).referer_id).referer_id)
                referer.investment_count = referer.investment_count + 1
                referer.save()
                if referer.investment_count % 2 == 0 or referer.investment_count > 12:
                    referer.balance = referer.balance + Decimal(0.006)
                if referer.investment_count == 16:
                    referer.upgrade_investor()

                referer.save()

            except Investor.DoesNotExist:
                pass

        def level5():
            try:
                referer = Investor.objects.get(id=
                                               Investor.objects.get(
                                                   id=Investor.objects.get(
                                                       id=Investor.objects.get(id=Investor.objects.get(
                                                           id=self.referer_id).referer_id).referer_id).
                                                       referer_id).referer_id)
                referer.investment_count = referer.investment_count + 1
                referer.save()
                if referer.investment_count % 2 == 0 or referer.investment_count > 16:
                    referer.balance = referer.balance + Decimal(0.024)
                if referer.investment_count == 32:
                    referer.upgrade_investor()

                referer.save()

            except Investor.DoesNotExist:
                pass

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
                referer.investment_count = referer.investment_count + 1
                referer.save()
                if referer.investment_count % 2 == 0 or referer.investment_count > 28:
                    referer.balance = referer.balance + Decimal(0.168)
                if referer.investment_count == 64:
                    referer.upgrade_investor()
                referer.save()

            except Investor.DoesNotExist:
                pass

        def out():
            try:
                last_withdrawal = WithdrawalRequest()
                last_withdrawal.investor = self
                last_withdrawal.amount = self.balance - Decimal(0.752)
                last_withdrawal.final = True
                last_withdrawal.save()
                return 'final'
            except django.db.utils.IntegrityError:
                pass

        upgrade = {'0-0': 1, '2-1': 2, '4-2': 3, '8-3': 4, '16-4': 5, '32-5': 6, '64-6': 7}
        previous_level = self.level
        try:
            self.level = upgrade[str(self.investment_count) + '-' + str(self.level)]
            self.save()
            self.investment_count = 0
            self.save()
            if self.level == 1:
                level1()
            elif self.level == 2:
                level2()
            elif self.level == 3:
                level3()
            elif self.level == 4:
                level4()
            elif self.level == 5:
                level5()
            elif self.level == 6:
                level6()
            elif self.level == 7:
                out()
        except KeyError:
            self.level = previous_level
        self.save()

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
        return self.amount * Decimal(2 / 100)
    def total_amount(self):
        return self.amount + self.withdrawal_fee()
