import requests
from django.contrib import auth
from django.db.models import F
from .models import Investor, WithdrawalRequest, Wallet
import json
from django.shortcuts import HttpResponse, render, redirect
import decimal
from django.utils.timezone import datetime as d


# Create your views here.

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

                        new_investor.save()
                        invest(new_investor)
                        return redirect('/login/')
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


def generate_address(id_):
    xpub = ''
    call_back_url = 'https://bitdouble.com?invoice_id=' + str(id_)
    key = ''
    gen = requests.request('GET',
                           'https://api.blockchain.info/v2/receive?xpub=' + xpub + '&callback=' + call_back_url + '&key=' + key)
    response = json.loads(gen.text).get('address')
    if response is None:
        return None
    else:
        return response


def invest(investor):
    if investor.deposit_address is None:
        address = generate_address(investor.id)
        if address is not None:
            investor.deposit_address = address
            investor.save()
            return True
        else:
            return False


def verify_payment(request):
    if request.method == 'GET':
        invoice_id = request.GET['invoice_id']
        transaction_hash = request.GET['transaction_hash']
        value_in_satoshi = request.GET['value']
        confirmation = request.GET['confirmations']
        if invoice_id and transaction_hash and value_in_satoshi and confirmation:
            value_in_btc = float(value_in_satoshi) / 100000000
            if int(confirmation) >= 4:
                investor = Investor.objects.get(id=invoice_id)
                if value_in_btc >= 0.001:
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
                            except IndexError:
                                pass
                        else:
                            referer.investment_count = F(referer.investment_count) + 1
                            if referer.investment_count % 2 or referer.investment_count > 2:
                                referer.balance = F(referer.balance) + 0.001
                            if referer.investment_count == 2:
                                referer.upgrade_investor()
                            referer.save()
            return HttpResponse('*ok*')


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
        return True
    else:
        return False


def pay_investor(address, amount):
    payer = Wallet.objects.get(id=1)
    try:
        pay = requests.request('GET',
                               'http://localhost:3000/merchant/' + payer.guid + '/payment?password='
                               + payer.password + '&to=' + address + '&amount=' + str((amount / 100000000)))
        response = json.loads(pay.text).get('message').split(' ')
        if response[0] == 'Sent' and (response[1] == amount) and (response[4] == address):
            return True
        else:
            return False
    except ConnectionRefusedError:
        return False
    except requests.ConnectionError:
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


def admin_withdrawal(request):
    list_ = WithdrawalRequest.objects.all().order_by('id').filter(serviced=False)
    if request.method == 'GET' and request.user.is_authenticated and request.user.is_staff:
        return render(request, 'wallet/admin_withdraw.html', {'the_list': list_})
    elif request.method == 'POST' and request.user.is_authenticated and request.user.is_staff:
        id_ = request.POST.get('id_')
        service_withdrawal(id_)
        return redirect('/admin/withdrawals')
