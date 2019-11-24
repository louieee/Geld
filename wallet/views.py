import urllib

from django.contrib import auth
from django.contrib.sites.shortcuts import get_current_site
from django.db.models import F
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from wallet.extra import account_activation_token
from .models import Investor, WithdrawalRequest
import json
from django.shortcuts import HttpResponse, render, redirect
import decimal
from django.utils.timezone import datetime as d
from coinpayments import CoinPaymentsAPI
from django.core.mail import send_mail, BadHeaderError
from django.conf import settings
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

api = CoinPaymentsAPI(public_key=settings.PUBLIC_KEY,
                      private_key=settings.PRIVATE_KEY)


def signup(request):
    if request.method == 'POST':
        username = str(request.POST['username'])
        password1 = str(request.POST['password1'])
        password2 = str(request.POST['password2'])
        email = str(request.POST['email'])
        if username and password1 and password2 and email:
            if password1 != password2:
                return render(request, 'wallet/home.html',
                              {'message': 'The two passwords do not match', 'status': 'danger'})
            else:
                try:
                    Investor.objects.get(username=username)
                    return render(request, 'wallet/home.html',
                                  {'message': 'This username is already in use', 'status': 'danger'})
                except Investor.DoesNotExist:
                    try:
                        Investor.objects.get(email=email)
                        return render(request, 'wallet/home.html',
                                      {'message': 'This email is already in use', 'status': 'danger'})
                    except Investor.DoesNotExist:
                        new_investor = Investor.objects.create_user(username, email, password1)
                        if request.GET.get('ref_id') is not None:
                            ref_id = int(request.GET['ref_id'])
                            try:
                                referer = Investor.objects.get(id=ref_id)
                                new_investor.referer = referer
                            except Investor.DoesNotExist:
                                try:
                                    referer = Investor.objects.all().order_by('id').filter(level=1)[0]
                                    new_investor.referer = referer
                                except IndexError:
                                    pass
                        else:
                            try:
                                referer = Investor.objects.all().order_by('id').filter(level=1)[0]
                                new_investor.referer = referer
                            except IndexError:
                                pass
                        new_investor.is_active = False

                        current_site = get_current_site(request)
                        mail_subject = 'Activate your Geld account.'
                        message = render_to_string('registration/activate_email.html', {
                            'user': new_investor.username,
                            'domain': current_site.domain,
                            'uid': urlsafe_base64_encode(force_bytes(new_investor.id)),
                            'token': account_activation_token.make_token(new_investor),
                        })
                        message_ = Mail(from_email=settings.EMAIL_HOST_USER,
                                        to_emails=new_investor.email,
                                        subject=mail_subject, html_content=message)
                        try:
                            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
                            response = sg.send(message_)
                            new_investor.save()
                            return render(request, 'wallet/home.html', {'message': 'check your e-mail '
                                                                                   'inbox or spam folder for the email '
                                                                                   'verification', 'status': 'info'})
                        except Exception as e:
                            print(e.__str__())
                            return redirect('/')

        else:
            return render(request, 'wallet/home.html',
                          {'message': 'All Fields Must Be Filled', 'status': 'danger'})
    else:
        if request.user.is_authenticated:
            return redirect('/dashboard/')
        else:
            return render(request, 'wallet/home.html')


def login(request):
    if request.method == 'POST':
        username = str(request.POST.get('username'))
        password = str(request.POST.get('password'))
        if username and password:
            investor = auth.authenticate(username=username, password=password)
            if investor is not None:
                auth.login(request, investor)
                return redirect('/dashboard/')
            else:
                return render(request, 'wallet/login.html', {'message': 'authentication failed', 'status': 'danger'})
        else:
            return render(request, 'wallet/login.html', {'message': 'All fields must be filled', 'status': 'danger'})
    else:
        if request.user.is_authenticated:
            return redirect('/dashboard/')
        else:
            return render(request, 'wallet/login.html')


def generate_address(username):
    the_api = api.get_callback_address(label=username)
    try:
        response = json.dumps(the_api['result']['address'])
        return response
    except TypeError:
        response = None
        return response


def invest(investor):
    if investor.deposit_address is None:
        address = generate_address(investor.username)
        if address is not None:
            investor.deposit_address = address
            investor.save()
            return True
        else:
            return False


def verify_payment(request):
    if request.method == 'POST':
        my_merchant_id = ''
        my_ipn_secret = ''
        if request.POST['ipn_mode'] == 'hmac':
            if request.POST['merchant'] == my_merchant_id:
                address = request.POST['address']
                currency = request.POST['currency']
                total_amount = request.POST['amount']
                deduct_fee = request.POST['fee']
                confirmation = request.POST['status']
                if api.check_signature(request.headers['HTTP_HMAC'], my_ipn_secret):
                    if currency == 'NGN':
                        if decimal.Decimal(total_amount) - decimal.Decimal(deduct_fee) >= 0.001:
                            if confirmation >= 100 or confirmation == 2:
                                try:
                                    investor = Investor.objects.get(deposit_address=address, level=0)
                                    investor.level = 1
                                    investor.save()
                                    if investor.referer is None:
                                        try:
                                            referer = Investor.objects.all().order_by('id').filter(level=1)[0]
                                            referer.investment_count = F(referer.investment_count) + 1
                                            if referer.investment_count % 2 or referer.investment_count > 2:
                                                referer.balance = F(referer.balance) + 0.001
                                            if referer.investment_count == 2:
                                                referer.upgrade_investor()
                                                message = Mail(from_email=settings.EMAIL_HOST_USER,
                                                               to_emails=investor.email,
                                                               subject='Successful wallet Funding',
                                                               plain_text_content='Dear ' + investor.username + ', You '
                                                                                                                'have '
                                                                                                                'successfully funded your wallet '
                                                                                                                'with 0.001 Btc'
                                                               )
                                                sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
                                                response = sg.send(message)
                                            referer.save()
                                        except IndexError:
                                            pass
                                    else:
                                        referer = Investor.objects.get(id=investor.referer_id)
                                        if referer.level > 1:
                                            try:
                                                referer = Investor.objects.all().order_by('id').filter(level=1)[0]
                                                referer.investment_count = F(referer.investment_count) + 1
                                                if referer.investment_count % 2 or referer.investment_count > 2:
                                                    referer.balance = F(referer.balance) + 0.001
                                                if referer.investment_count == 2:
                                                    referer.upgrade_investor()
                                                referer.save()
                                                message = Mail(from_email=settings.EMAIL_HOST_USER,
                                                               to_emails=investor.email,
                                                               subject='Successful wallet Funding',
                                                               plain_text_content='Dear ' + investor.username + ', You '
                                                                                                                'have '
                                                                                                                'successfully funded your wallet '
                                                                                                                'with 0.001 Btc'
                                                               )
                                                sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
                                                response = sg.send(message)
                                            except IndexError:
                                                pass
                                        else:
                                            referer.investment_count = F(referer.investment_count) + 1
                                            if referer.investment_count % 2 or referer.investment_count > 2:
                                                referer.balance = F(referer.balance) + 0.001
                                            if referer.investment_count == 2:
                                                referer.upgrade_investor()
                                            referer.save()
                                            Message = Mail(from_email=settings.EMAIL_HOST_USER,
                                                           to_emails=investor.email,
                                                           subject='Successful wallet Funding',
                                                           plain_text_content='Dear ' + investor.username + ', You '
                                                                                                            'have '
                                                                                                            'successfully funded your wallet '
                                                                                                            'with 0.001 Btc'
                                                           )
                                            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
                                            response = sg.send(Message)
                                    return HttpResponse('*IPN OK*')
                                except Investor.DoesNotExist:
                                    pass


def withdraw(request):
    if request.method == 'GET':
        investor = Investor.objects.get(id=request.user.id)
        the_data = {'pending': investor.pending_withdrawals(), 'serviced': investor.withdrawals()}
        return render(request, 'wallet/withdrawal.html', the_data)
    elif request.method == 'POST':
        amount = decimal.Decimal(request.POST['amount'])
        address = str(request.POST['address'])
        password = str(request.POST['password'])
        if request.user.is_authenticated:
            investor = Investor.objects.get(id=request.user.id)
            user = auth.authenticate(username=investor.username, password=password)
            if user is not None:
                if amount and address:
                    fee = amount * decimal.Decimal(2 / 100)
                    total_amount = amount + fee
                    if investor.balance > total_amount:
                        withdrawal_request = WithdrawalRequest()
                        withdrawal_request.investor = investor
                        withdrawal_request.amount = amount
                        withdrawal_request.address = address
                        withdrawal_request.date_of_request = d.now()
                        withdrawal_request.save()
                        message = Mail(from_email=settings.EMAIL_HOST_USER,
                                       to_emails=investor.email, subject='Withdrawal request',
                                       plain_text_content='Dear ' + investor.username + ', You '
                                                                                        'just requested to withdraw '
                                                          + withdrawal_request.amount +
                                                          'BTC to this address: ' + withdrawal_request.address)
                        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
                        response = sg.send(message)
                        return redirect('http://127.0.0.1:8000/withdraw/')
                    else:
                        return render(request, 'wallet/withdrawal.html',
                                      {'message': 'Insufficient Balance', 'status': 'danger',
                                       'pending': investor.pending_withdrawals(), 'serviced': investor.withdrawals()})
                else:
                    return render(request, 'wallet/withdrawal.html',
                                  {'message': 'All Fields Must Be Filled', 'status': 'danger',
                                   'pending': investor.pending_withdrawals(), 'serviced': investor.withdrawals()})
            else:
                return render(request, 'wallet/withdrawal.html',
                              {'message': 'Your Password Is Incorrect', 'status': 'danger',
                               'pending': investor.pending_withdrawals(), 'serviced': investor.withdrawals()})
        else:
            return render(request, 'wallet/login.html',
                          {'message': 'Authentication Failed', 'status': 'danger'})


def service_withdrawal(id_):
    withdrawal = WithdrawalRequest.objects.get(id=id_)
    if pay_investor(withdrawal.address, withdrawal.amount) is True:
        withdrawal.serviced = True
        withdrawal.save()
        message = Mail(from_email=settings.EMAIL_HOST_USER,
                       to_emails=withdrawal.investor.email, subject='Successful Withdrawal',
                       plain_text_content='Dear ' + withdrawal.investor.username + ', ' + withdrawal.amount +
                                          'BTC has been paid to the address you specified : ' +
                                          withdrawal.address + ', Thank you for working with us')
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        return True
    else:
        return False


def pay_investor(address, amount):
    pay = api.create_withdrawal(amount=amount, currency='BTC', address=address)
    response = json.loads(pay).get('error')
    if response == 'ok':
        return True
    else:
        return False


def dashboard(request):
    if request.method == 'GET' and request.user.is_authenticated:
        investor_ = Investor.objects.get(id=request.user.id)
        referer = Investor.objects.get(id=investor_.referer_id)
        user_data = {'id': investor_.id, 'level': investor_.level_details(), 'username': investor_.username,
                     'email': investor_.email,
                     'balance': investor_.balance, 'percentage': investor_.percentage(),
                     'downliners': investor_.direct_downliners(),
                     'u_username': referer.username, 'u_level': referer.level_details(),
                     'u_percentage': referer.percentage(), 'u_email': referer.email,
                     'deposit_address': investor_.deposit_address
                     }
        return render(request, 'wallet/dashboard.html', user_data)
    else:
        return redirect('/')


def admin_withdrawal(request):
    list_ = WithdrawalRequest.objects.all().order_by('id').filter(serviced=False)
    if request.method == 'GET' and request.user.is_authenticated and request.user.is_staff:
        return render(request, 'wallet/admin_withdraw.html', {'the_list': list_})
    elif request.method == 'POST' and request.user.is_authenticated and request.user.is_staff:
        id_ = request.POST.get('id_')
        service_withdrawal(id_)
        return redirect('/admin/withdrawals')


def contact_us(request):
    if request.method == 'GET':
        return render(request, 'wallet/contact_us.html')
    elif request.method == 'POST':
        subject = request.POST.get('subject')
        body = request.POST.get('body')
        message = Mail(to_emails=settings.EMAIL_HOST_USER,
                       from_email=request.user.email, subject=subject,
                       plain_text_content=body)
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        if response._status_code == 202:
            redirect('/contact')
            return render(request, 'wallet/contact_us.html', {'message': 'message was sent successfully',
                                                              'status': 'success'})
        else:
            redirect('/contact')
            return render(request, 'wallet/contact_us.html', {'message': 'message was not sent',
                                                              'status': 'danger'})


def activate(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        print('UID: ' + str(uid))
        user = Investor.objects.get(id=int(uid))
        print('Username: ' + str(user.username))
        if account_activation_token.check_token(user, token):
            user.is_active = True
            user.save()
            invest(user)
            return redirect('/login')
        else:
            if user.is_active is False:
                user.delete()
            return render(request, 'wallet/home.html', {'message': 'Your Email was invalid, Therefore Your Account Has '
                                                                   'been deleted', 'status': 'danger'})
    except Investor.DoesNotExist:
        return render(request, 'wallet/home.html', {'message': 'User Does Not Exist', 'status': 'danger'})
