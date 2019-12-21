import decimal
import requests
from blockchain.v2.receive import receive
from blockchain.wallet import Wallet
from django.shortcuts import HttpResponse, render, redirect
from django.urls import reverse
from django.utils.timezone import datetime as d
from .investor import *


def send_message(message):
    sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
    return sg.send(message)


def generate_address(id_):
    url = 'http://geldbaum.herokuapp.com/' + reverse('verify', args=[id_])
    gen = receive(settings.BLOCKCHAIN_XPUB, url, settings.BLOCKCHAIN_API_KEY)
    response = gen.address
    if response is None:
        return None
    else:
        return response


def signup(request):
    if request.GET.get('ref_id'):
        request.session['ref_id'] = int(request.GET.get('ref_id'))
        return redirect('/')

    if request.user.is_authenticated:
        return redirect('/dashboard/')
    else:
        try:
            message = request.session['message']
            status = request.session['status']
            del request.session['message']
            del request.session['status']
            try:
                email = request.session['email']
                username = request.session['username']
                del request.session['email']
                del request.session['username']
                return render(request, 'wallet/home.html',
                              {'message': message, 'status': status, 'email': email, 'username': username})
            except KeyError:
                return render(request, 'wallet/home.html',
                              {'message': message, 'status': status})
        except KeyError:
            try:
                email = request.session['email']
                username = request.session['username']
                del request.session['email']
                del request.session['username']
                return render(request, 'wallet/home.html',
                              {'email': email, 'username': username})
            except KeyError:
                return render(request, 'wallet/home.html')


def home(request):
    if request.user.is_authenticated:
        investor = Investor.objects.get(id=request.user.id)
        if investor.pass_number == '':
            return redirect('pass_number')
        else:
            return redirect('dashboard')
    else:
        return redirect('home')


def pass_number(request):
    if request.method == 'GET':
        try:
            message = request.session['message']
            status = request.session['status']
            del request.session['message']
            del request.session['status']
            return render(request, 'wallet/pass.html', {'message': message, 'status': status})
        except KeyError:
            return render(request, 'wallet/pass.html')
    elif request.method == 'POST':
        digits = request.POST.get('digits')
        if digits:
            investor = Investor.objects.get(id=request.user.id)
            investor.pass_number = str(digits)
            investor.deposit_address = generate_address(investor.id)
            investor.save()
            investor.referral_url = 'http://www.geldbaum.tk/?ref_id='+str(1000+int(investor.id))
            investor.save()
            try:
                investor.referer_id = 1000 - request.session['ref_id']
                investor.save()
                del request.session['ref_id']
            except KeyError:
                try:
                    ref = Investor.objects.all().order_by('id').filter(level=1, investment_count__lt=2)[0]
                    if ref.id == investor.id:
                        investor.referer = None
                    else:
                        investor.referer = ref
                    investor.save()
                except IndexError:
                    pass
            request.session['message'] = 'Sign Up Successful !'
            request.session['status'] = 'success'
            return redirect('dashboard')
        else:
            request.session['message'] = 'No Digit Found !'
            request.session['status'] = 'danger'
            return redirect('pass_number')


def login(request):
    return render(request, 'wallet/login.html')


def invest(investor):
    if investor.deposit_address is None:
        address = generate_address(investor.id)
        if address is not None:
            investor.deposit_address = address
            investor.save()
            return True
        else:
            return False


def verify_payment(request, id_):
    if request.method == 'GET':
        try:
            investor = Investor.objects.get(id=id_, level=0)
            invoice_id = request.GET['invoice_id']
            transaction_hash = request.GET['transaction_hash']
            value_in_satoshi = request.GET['value']
            confirmation = request.GET['confirmations']
            if invoice_id and transaction_hash and value_in_satoshi and confirmation:
                value_in_btc = float(value_in_satoshi) / 100000000
                if int(confirmation) >= 4 and value_in_btc >= 0.001:
                    if investor.id == invoice_id:
                        upgrade_investor(investor)
                        investor.save()
                        return HttpResponse('*OK*')
                    else:
                        return HttpResponse('Wrong id')
                else:
                    return HttpResponse('Confirmation and amount not enough')
            else:
                return HttpResponse('No values')
        except Investor.DoesNotExist:
            return HttpResponse('Wrong Callback url')


def withdraw(request):
    if request.method == 'GET':
        if request.user.is_authenticated:
            investor = Investor.objects.get(id=request.user.id)
            try:
                message = request.session['message']
                status = request.session['status']
                del request.session['message']
                del request.session['status']
                try:
                    amount = request.session['amount']
                    address = request.session['address']
                    del request.session['amount']
                    del request.session['address']
                    return render(request, 'wallet/withdrawal.html',
                                  {'message': message, 'status': status, 'amount': amount,
                                   'address': address, 'pending': investor.pending_withdrawals(),
                                   'serviced': investor.withdrawals()})
                except KeyError:
                    return render(request, 'wallet/withdrawal.html',
                                  {'message': message, 'status': status, 'pending': investor.pending_withdrawals(),
                                   'serviced': investor.withdrawals()})
            except KeyError:
                try:
                    amount = request.session['amount']
                    address = request.session['address']
                    del request.session['amount']
                    del request.session['address']
                    return render(request, 'wallet/withdrawal.html',
                                  {'amount': amount,
                                   'address': address, 'pending': investor.pending_withdrawals(),
                                   'serviced': investor.withdrawals()})
                except KeyError:
                    return render(request, 'wallet/withdrawal.html',
                                  {'pending': investor.pending_withdrawals(),
                                   'serviced': investor.withdrawals()})
        else:
            return redirect('home')
    elif request.method == 'POST':
        amount = decimal.Decimal(request.POST.get('amount'))
        address = str(request.POST['address'])
        digits = str(request.POST['digits'])
        investor = Investor.objects.get(id=request.user.id)
        if investor.pass_number == digits:
            if amount and address:
                fee = amount * decimal.Decimal(2 / 100)
                total_amount = amount + fee
                if investor.balance > total_amount and amount > 0.001:
                    withdrawal_request = WithdrawalRequest()
                    withdrawal_request.investor = investor
                    withdrawal_request.amount = amount
                    withdrawal_request.address = address
                    withdrawal_request.date_of_request = d.now()
                    withdrawal_request.save()
                    message = Mail(from_email=settings.EMAIL,
                                   to_emails=investor.email, subject='Withdrawal request',
                                   plain_text_content='Dear ' + investor.username + ', You '
                                                                                    'just requested to withdraw '
                                                      + str(withdrawal_request.amount) +
                                                      'BTC to this address: ' + withdrawal_request.address)
                    send_message(message)
                    request.session['message'] = 'Your Withdrawal request has been sent Successfully'
                    request.session['status'] = 'success'
                    return redirect('/withdraw/')
                else:
                    request.session['message'] = 'Your Balance is Insufficient'
                    request.session['status'] = 'danger'
                    request.session['amount'] = str(amount)
                    request.session['address'] = address
                    return redirect('withdraw')

            else:
                request.session['message'] = 'All Fields Must Be Filled'
                request.session['status'] = 'danger'
                request.session['amount'] = str(amount)
                request.session['address'] = address

                return redirect('withdraw')
        else:
            request.session['message'] = 'Withdrawal Authentication Failed '
            request.session['status'] = 'danger'
            return redirect('logout')


def service_withdrawal(id_):
    withdrawal = WithdrawalRequest.objects.get(id=int(id_))
    if pay_investor(withdrawal.address, withdrawal.amount) is True:
        withdrawal.serviced = True
        withdrawal.save()
        investor = Investor.objects.get(id=withdrawal.investor_id)
        investor.balance = investor.balance - withdrawal.total_amount()
        investor.save()
        message = Mail(from_email=settings.EMAIL,
                       to_emails=withdrawal.investor.email, subject='Successful Withdrawal',
                       plain_text_content='Dear ' + withdrawal.investor.username + ', ' + withdrawal.amount +
                                          'BTC has been paid to the address you specified : ' +
                                          withdrawal.address + ', Thank you for working with us')
        send_message(message)
        return True
    else:
        return False


def pay_investor(address, amount):
    try:
        pay = Wallet(settings.BLOCKCHAIN_GUID, settings.BLOCKCHAIN_PASSWORD, 'http://geldbaum.herokuapp.com').send(
            address, amount)

        response = str(pay.message).split(' ')
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
        try:
            referer = Investor.objects.get(id=investor_.referer_id)
            user_data = {'id': investor_.id, 'level': investor_.level_details(), 'username': investor_.username,
                         'email': investor_.email,
                         'balance': investor_.balance, 'percentage': investor_.percentage(),
                         'downliners': investor_.direct_downliners(),
                         'u_username': referer.username, 'u_level': referer.level_details(),
                         'u_percentage': referer.percentage(), 'u_email': referer.email,
                         'deposit_address': investor_.deposit_address, 'ref_url': investor_.referral_url
                         }
        except Investor.DoesNotExist:
            user_data = {'id': investor_.id, 'level': investor_.level_details(), 'username': investor_.username,
                         'email': investor_.email,
                         'balance': investor_.balance, 'percentage': investor_.percentage(),
                         'downliners': investor_.direct_downliners(),
                         'deposit_address': investor_.deposit_address, 'ref_url': investor_.referral_url
                         }
        return render(request, 'wallet/dashboard.html', user_data)
    else:
        return redirect('/')


def admin_withdrawal(request):
    list_ = WithdrawalRequest.objects.all().order_by('id').filter(serviced=False)
    if request.method == 'GET' and request.user.is_authenticated and request.user.is_staff:
        try:
            message = request.session['message']
            status = request.session['status']
            del request.session['message']
            del request.session['status']
            return render(request, 'wallet/admin_withdraw.html',
                          {'the_list': list_, 'message': message, 'status': status})
        except KeyError:
            return render(request, 'wallet/admin_withdraw.html', {'the_list': list_})
    elif request.method == 'POST' and request.user.is_authenticated and request.user.is_staff:
        id_ = request.POST.get('id_')
        stat = service_withdrawal(id_)
        if stat is True:
            request.session['message'] = 'Payout Successful'
            request.session['status'] = 'success'
        else:
            request.session['message'] = 'Payout was not Successful'
            request.session['status'] = 'danger'
        return redirect('/admin/withdrawals')


def contact_us(request):
    if request.method == 'GET':
        try:
            message = request.session['message']
            status = request.session['status']
            del request.session['message']
            del request.session['status']
            return render(request, 'wallet/contact_us.html', {'message': message, 'status': status})
        except KeyError:
            return render(request, 'wallet/contact_us.html')
    elif request.method == 'POST':
        subject = request.POST.get('subject')
        body = request.POST.get('body')
        message = Mail(to_emails=settings.EMAIL,
                       from_email=request.user.email, subject=subject,
                       plain_text_content=body)
        response = send_message(message)
        if response._status_code == 202:
            request.session['message'] = 'We have received your message. We will get back to you'
            request.session['status'] = 'success'
            return redirect('/contact')
        else:
            request.session['message'] = 'Your Message was not sent.'
            request.session['status'] = 'danger'
            redirect('/contact')
