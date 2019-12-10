from urllib.error import URLError
from decimal import Decimal
import django
from django.db import models
from django.conf import settings
from sendgrid import Mail, SendGridAPIClient
from django.utils.datetime_safe import datetime
from django.utils.timezone import timedelta as td
from .models import Investor, WithdrawalRequest


def reset_parameters(investor):
    investor.timer_no = 0
    investor.timer = None
    investor.login_retries = 0
    investor.save()


def increment_login_retries(investor):
    investor.login_retries = investor.login_retries + 1
    investor.save()


def activate_security(investor):
    if investor.login_retries == 3 and (investor.timer_no < 6 or investor.timer_no == 0):
        investor.increment_timer()
    elif investor.login_retries < 3 and investor.timer_no == 0:
        investor.increment_login_retries()
    elif investor.timer_no == 6 and investor.login_retries == 3:
        investor.login_retries = 0
        investor.timer_no = 0
        investor.is_active = False
        investor.save()


def check_timer(investor):
    try:
        if (int((investor.timer.timestamp() - datetime.now().timestamp()) / 60) - 60) <= 0:
            investor.timer_on = False
            investor.save()
    except AttributeError:
        pass


def set_timer(investor, number):
    investor.timer = datetime.now() + td(minutes=int(number))
    investor.timer_on = True
    investor.save()


def increment_timer(investor):
    investor.timer_no = investor.timer_no + 1
    investor.set_timer(int(investor.timer_no * 10))


def upgrade_investor(investor):
    def level1():

        def message_investor():
            try:
                message = Mail(from_email=settings.EMAIL, to_emails=investor.email,
                               subject='Successful wallet Funding', plain_text_content='Dear ' +
                                                                                       investor.username + ', You have successfully funded your wallet with 0.001 Btc')
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
                upgrade_investor(referer_)
                referer_.save()
            else:
                pass

        def get_tree_referer():
            global prev
            global next_
            try:
                curr = Investor.objects.get(id=investor.referer_id, level__gt=0)
            except Investor.DoesNotExist:
                curr = None
                prev = None
            except Investor.MultipleObjectsReturned:
                curr = Investor.objects.all().order_by('id').filter(id=investor.referer_id, level__gt=0)[0]

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

        if investor.referer is None:
            upgrade_due_person(get_random_referer())
            investor.save()
            message_investor()
        else:
            referer = Investor.objects.get(id=investor.referer_id)
            if referer.level > 1:
                upgrade_due_person(get_tree_referer())
            else:
                upgrade_due_person(referer)
            investor.save()
            message_investor()

    def level2():
        try:
            referer = Investor.objects.get(id=Investor.objects.get(id=investor.referer_id).referer_id)
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
            (id=investor.referer_id).referer_id).referer_id)
            referer.investment_count = referer.investment_count + 1
            referer.save()
            if referer.investment_count % 2 == 0 or referer.investment_count > 8:
                referer.balance = referer.balance + Decimal(0.002)
            if referer.investment_count == 8:
                upgrade_investor(referer)

            referer.save()

        except Investor.DoesNotExist:
            pass

    def level4():
        try:
            referer = Investor.objects.get(
                id=Investor.objects.get(id=Investor.objects.get(id=Investor.objects.get
                (id=investor.referer_id).referer_id).referer_id).referer_id)
            referer.investment_count = referer.investment_count + 1
            referer.save()
            if referer.investment_count % 2 == 0 or referer.investment_count > 12:
                referer.balance = referer.balance + Decimal(0.006)
            if referer.investment_count == 16:
                upgrade_investor(referer)

            referer.save()

        except Investor.DoesNotExist:
            pass

    def level5():
        try:
            referer = Investor.objects.get(id=
                                           Investor.objects.get(
                                               id=Investor.objects.get(
                                                   id=Investor.objects.get(id=Investor.objects.get(
                                                       id=investor.referer_id).referer_id).referer_id).
                                                   referer_id).referer_id)
            referer.investment_count = referer.investment_count + 1
            referer.save()
            if referer.investment_count % 2 == 0 or referer.investment_count > 16:
                referer.balance = referer.balance + Decimal(0.024)
            if referer.investment_count == 32:
                upgrade_investor(referer)

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
                                                                                   id=investor.referer_id).
                                                                                   referer_id).referer_id).
                                                                           referer_id).referer_id).referer_id)
            referer.investment_count = referer.investment_count + 1
            referer.save()
            if referer.investment_count % 2 == 0 or referer.investment_count > 28:
                referer.balance = referer.balance + Decimal(0.168)
            if referer.investment_count == 64:
                upgrade_investor(referer)
            referer.save()

        except Investor.DoesNotExist:
            pass

    def out():
        try:
            last_withdrawal = WithdrawalRequest()
            last_withdrawal.investor = investor
            last_withdrawal.amount = investor.balance - Decimal(0.752)
            last_withdrawal.final = True
            last_withdrawal.save()
            return 'final'
        except django.db.utils.IntegrityError:
            pass

    upgrade = {'0-0': 1, '2-1': 2, '4-2': 3, '8-3': 4, '16-4': 5, '32-5': 6, '64-6': 7}
    previous_level = investor.level
    try:
        investor.level = upgrade[str(investor.investment_count) + '-' + str(investor.level)]
        investor.save()
        investor.investment_count = 0
        investor.save()
        if investor.level == 1:
            level1()
        elif investor.level == 2:
            level2()
        elif investor.level == 3:
            level3()
        elif investor.level == 4:
            level4()
        elif investor.level == 5:
            level5()
        elif investor.level == 6:
            level6()
        elif investor.level == 7:
            out()
    except KeyError:
        investor.level = previous_level
    investor.save()
