import requests
from django.contrib import auth
from django.db.models import F

from .models import Investor, WithdrawalRequest, Wallet
import json
from django.shortcuts import HttpResponse
import decimal
from django.utils.timezone import datetime as d


# Create your views here.

def signup(request):
    if request.method == 'POST':
        username = str(request.POST['username'])
        password1 = str(request.POST['password'])
        password2 = str(request.POST['password'])
        email = str(request.POST['email'])
        if username and password1 and password2 and email:
            if password1 == password2:
                return HttpResponse(json.dumps({'error': 'The two passwords do not match'}))
            else:
                try:
                    Investor.objects.get(username=username, email=email)
                    return HttpResponse(json.dumps({'error': 'This user already exists'}))
                except Investor.DoesNotExist:
                    new_investor = Investor.objects.create_user(username, email, password1)
                    if request.GET['ref_id']:
                        ref_id = int(request.GET['ref_id'])
                        try:
                            referer = Investor.objects.get(id=ref_id)
                            new_investor.referer = referer
                        except Investor.DoesNotExist:
                            referer = Investor.objects.all().order_by('date_joined').filter(level=1)[:1]
                            new_investor.referer = referer
                    else:
                        referer = Investor.objects.all().order_by('date_joined').filter(level=1)[:1]
                        new_investor.referer = referer
                    new_investor.save()
                    return HttpResponse(json.dumps({'message': 'Sign Up is successful.'}))
        else:
            return HttpResponse(json.dumps({'error': 'All fields must be filled'}))
    elif request.method == 'GET':
        return HttpResponse(json.dumps({'message': 'Welcome to the signup page'}))


def login(request):
    if request.method == 'GET':
        return HttpResponse(json.dumps({'message': 'welcome to the login page'}))
    elif request.method == 'POST':
        username = str(request.GET['username'])
        password = str(request.GET['password'])
        if username and password:
            investor = auth.authenticate(username=username, password=password)
            if investor is not None:
                auth.login(request, investor)
                return HttpResponse(json.dumps({'message': username + ' logged in successfully', 'id': investor.id}))
            else:
                return HttpResponse(json.dumps({'error': 'authentication failed'}))
        else:
            return HttpResponse(json.dumps({'error': 'All fields must be filled'}))


def dashboard(request):
    if request.user.is_authenticated:
        investor_id = request.user.id
        investor = Investor.objects.get(id=investor_id)
        referer = Investor.objects.get(id=investor.referer_id)
        return HttpResponse(json.dumps({'id': investor.id, 'username': investor.username, 'level': investor.level,
                                        'percentage': investor.percentage, 'balance': investor.balance,
                                        'payment_count': investor.investment_count,
                                        'upliner': {'username': referer.username, 'level': referer.level},
                                        'downliners': investor.direct_downliners(),
                                        'pending withdrawal': investor.pending_withdrawals(),
                                        'serviced withdrawals': investor.withdrawals()}))


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


def invest(request):
    if request.user.is_authenticated:
        id_ = request.user.id
        investor = Investor.objects.get(id=id_)
        if investor.deposit_address is None:
            address = generate_address(id_)
            if address is not None:
                investor.deposit_address = address
                investor.save()
                return HttpResponse(json.dumps({'message': investor.deposit_address}))
            else:
                return HttpResponse(json.dumps({'error': 'Could not generate an address. Try again'}))
        else:
            return HttpResponse(json.dumps({'message': investor.deposit_address}))
    else:
        return HttpResponse(json.dumps({'error': 'Login Required', 'position': 'dashboard'}))


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
                    referer = Investor.objects.get(id=investor.referer_id)
                    referer.investment_count = F(referer.investment_count) + 1
                    if referer.investment_count % 2 or referer.investment_count > 2:
                        referer.balance = F(referer.balance) + 0.001
                    if referer.investment_count == 2:
                        referer.upgrade_investor()
                    referer.save()
            return HttpResponse('*ok*')


def withdraw(request):
    amount = decimal.Decimal(request.POST['amount'])
    address = str(request.POST['address'])
    if request.user.is_authenticated:
        investor = Investor.objects.get(id=request.user.id)
        if amount and address:
            fee = amount * (2 / 100)
            total_amount = amount + fee
            if investor.balance > total_amount:
                withdrawal_request = WithdrawalRequest()
                withdrawal_request.investor = investor
                withdrawal_request.amount = amount
                withdrawal_request.address = address
                withdrawal_request.date_of_request = d.now()
                withdrawal_request.save()
                return HttpResponse(
                    json.dumps({'message': 'Your withdrawal request will be serviced within the next 24 hrs'}))
            else:
                return HttpResponse(json.dumps({'error': 'Insufficient Balance'}))
        else:
            return HttpResponse(json.dumps({'error': 'all fields must be filled'}))
    else:
        return HttpResponse(json.dumps({'error': 'Login Required', 'position': 'withdrawal'}))


def fetch_withdrawals(request):
    all_list = WithdrawalRequest.objects.all().order_by('-date_of_request').filter(serviced=False)
    return_list = []
    for item in all_list:
        details = {'id': item.id, 'investor': item.investor.username, 'email': item.investor.email,
                   'amount': item.amount,
                   'address': item.address, 'date': item.date_of_request.date(), 'time': item.date_of_request.time(),
                   'level': item.investor.level, 'final': item.final}
        return_list.append(details)
    return return_list


def service_withdrawal(request):
    id_ = request.GET['id']
    withdrawal = WithdrawalRequest.objects.get(id=id_)
    if pay_investor(withdrawal.address, withdrawal.amount) is True:
        withdrawal.serviced = True
    withdrawal.save()

    return HttpResponse(json.dumps({'message': 'successful'}))


def pay_investor(address, amount):
    payer = Wallet.objects.get(id=1)
    pay = requests.request('GET',
                           'http://localhost:3000/merchant/' + payer.guid + '/payment?password='
                           + payer.password + '&to=' + address + '&amount=' + (amount / 100000000))
    response = json.loads(pay.text).get('message').split(' ')
    if response[0] == 'Sent' and (response[1] == amount) and (response[4] == address):
        return True
    else:
        return False
