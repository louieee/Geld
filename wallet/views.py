import requests
from django.contrib import auth
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.urls import reverse
from wallet.extra import account_activation_token, get_phrase
from django.shortcuts import HttpResponse, render, redirect
import decimal
from django.utils.timezone import datetime as d
from blockchain.v2.receive import receive
from blockchain.wallet import Wallet
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
    if request.method == 'POST':
        username = str(request.POST['username'])
        password1 = str(request.POST['password1'])
        password2 = str(request.POST['password2'])
        email = str(request.POST['email'])
        if username and password1 and password2 and email:
            request.session['username'] = username
            request.session['email'] = email

            if password1 != password2:
                request.session['message'] = 'The two passwords do not match'
                request.session['status'] = 'danger'
                return redirect('home')
            else:
                try:
                    Investor.objects.get(username=username)
                    request.session['message'] = 'This username is already in use'
                    request.session['status'] = 'danger'
                    return redirect('home')
                except Investor.DoesNotExist:
                    try:
                        Investor.objects.get(email=email)
                        request.session['message'] = 'This email address is already in use'
                        request.session['status'] = 'danger'
                        return redirect('home')
                    except Investor.DoesNotExist:
                        new_investor = Investor.objects.create_user(username, email, password1)
                        if request.session['ref_id'] is not None:
                            ref_id = 1000 - int(request.session['ref_id'])
                            del request.session['ref_id']
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
                        new_investor.pass_phrase = get_phrase()
                        new_investor.save()
                        invest(new_investor)
                        current_site = get_current_site(request)
                        mail_subject = 'Activate your Geld account.'
                        message = render_to_string('registration/activate_email.html', {
                            'user': new_investor.username,
                            'domain': current_site.domain,
                            'uid': urlsafe_base64_encode(force_bytes(new_investor.id)),
                            'token': account_activation_token.make_token(new_investor),
                        })
                        message_ = Mail(from_email=settings.EMAIL,
                                        to_emails=new_investor.email,
                                        subject=mail_subject, html_content=message)
                        try:
                            current_site = get_current_site(request)
                            send_message(message_)
                            new_investor.save()
                            new_investor.referral_url = current_site.domain + '/?ref_id=' + (
                                        1000 + int(new_investor.id))
                            new_investor.save()
                            request.session['message'] = 'check your e-mail inbox or spam folder for the email ' \
                                                         'verification '
                            request.session['status'] = 'info'
                            return redirect('home')
                        except Exception as e:
                            print(e.__str__())
                            request.session['message'] = 'Connection Failed'
                            request.session['status'] = 'danger'
                            return redirect('home')

        else:
            return render(request, 'wallet/home.html',
                          {'message': 'All Fields Must Be Filled', 'status': 'danger'})
    else:
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


def login(request):
    if request.method == 'POST':
        username = str(request.POST.get('username'))
        password = str(request.POST.get('password'))
        phrase = str(request.POST.get('phrase'))
        if username and password and phrase:
            try:
                inv_ = Investor.objects.get(username=username)
                check_timer(inv_)
                if not inv_.is_active:
                    request.session['message'] = 'Your Account has been deactivated. '
                    request.session['status'] = 'info'
                    return redirect('home')
                if inv_.timer_on:
                    request.session['message'] = 'You can login after ' + \
                                                 str(int((
                                                                 inv_.timer.timestamp() - d.now().timestamp()) / 60) - 60) + ' minutes'
                    request.session['status'] = 'info'
                    return redirect('/login')
                else:
                    investor = auth.authenticate(username=username, password=password)
                    if investor is not None:
                        if inv_.pass_phrase == phrase:
                            auth.login(request, investor)
                            reset_parameters(inv_)
                            return redirect('/dashboard/')
                        else:
                            activate_security(inv_)
                            request.session['message'] = 'Wrong Passphrase'
                            request.session['status'] = 'danger'
                            request.session['username'] = username
                            request.session['passphrase'] = phrase
                            return redirect('/login')
                    else:
                        activate_security(inv_)
                        request.session['message'] = 'Incorrect Password'
                        request.session['status'] = 'danger'
                        request.session['username'] = username
                        request.session['passphrase'] = phrase
                        return redirect('/login')
            except Investor.DoesNotExist:
                request.session['message'] = 'This User does not exist'
                request.session['status'] = 'danger'
                request.session['username'] = username
                request.session['passphrase'] = phrase
                return redirect('/login')
        else:
            request.session['message'] = 'All fields must be filled'
            request.session['status'] = 'danger'
            request.session['username'] = username
            request.session['passphrase'] = phrase
            return redirect('login')
    else:
        if request.user.is_authenticated:
            return redirect('/dashboard/')
        else:
            try:
                message = request.session['message']
                status = request.session['status']
                del request.session['message']
                del request.session['status']
                try:
                    passphrase = request.session['passphrase']
                    username = request.session['username']
                    del request.session['passphrase']
                    del request.session['username']
                    return render(request, 'wallet/login.html',
                                  {'message': message, 'status': status, 'phrase': passphrase, 'username': username})
                except KeyError:
                    return render(request, 'wallet/login.html',
                                  {'message': message, 'status': status})
            except KeyError:
                try:
                    passphrase = request.session['passphrase']
                    username = request.session['username']
                    del request.session['passphrase']
                    del request.session['username']
                    return render(request, 'wallet/login.html',
                                  {'phrase': passphrase, 'username': username})
                except KeyError:
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
                    passphrase = request.session['passphrase']
                    amount = request.session['amount']
                    address = request.session['address']
                    del request.session['passphrase']
                    del request.session['amount']
                    del request.session['address']
                    return render(request, 'wallet/withdrawal.html',
                                  {'message': message, 'status': status, 'phrase': passphrase, 'amount': amount,
                                   'address': address, 'pending': investor.pending_withdrawals(),
                                   'serviced': investor.withdrawals()})
                except KeyError:
                    return render(request, 'wallet/withdrawal.html',
                                  {'message': message, 'status': status, 'pending': investor.pending_withdrawals(),
                                   'serviced': investor.withdrawals()})
            except KeyError:
                try:
                    passphrase = request.session['passphrase']
                    amount = request.session['amount']
                    address = request.session['address']
                    del request.session['passphrase']
                    del request.session['amount']
                    del request.session['address']
                    return render(request, 'wallet/withdrawal.html',
                                  {'phrase': passphrase, 'amount': amount,
                                   'address': address, 'pending': investor.pending_withdrawals(),
                                   'serviced': investor.withdrawals()})
                except KeyError:
                    return render(request, 'wallet/withdrawal.html',
                                  {'pending': investor.pending_withdrawals(),
                                   'serviced': investor.withdrawals()})
    elif request.method == 'POST':
        amount = decimal.Decimal(request.POST.get('amount'))
        address = str(request.POST['address'])
        password = str(request.POST['password'])
        passphrase = str(request.POST.get('phrase'))
        if request.user.is_authenticated:
            investor = Investor.objects.get(id=request.user.id)
            user = auth.authenticate(username=investor.username, password=password)
            if user is not None and user.pass_phrase == passphrase:
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
                        request.session['passphrase'] = passphrase

                        return redirect('withdraw')

                else:
                    request.session['message'] = 'All Fields Must Be Filled'
                    request.session['status'] = 'danger'
                    request.session['amount'] = str(amount)
                    request.session['address'] = address
                    request.session['passphrase'] = passphrase

                    return redirect('withdraw')
            else:
                request.session['message'] = 'Withdrawal Authentication Failed '
                request.session['status'] = 'danger'
                return redirect('logout')
        else:
            request.session['message'] = 'You Need to be Logged In'
            request.session['status'] = 'info'
            return redirect('login')


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
        pay = Wallet(settings.BLOCKCHAIN_GUID,settings.BLOCKCHAIN_PASSWORD, 'http://geldbaum.herokuapp.com').send(
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
                         'deposit_address': investor_.deposit_address,  'ref_url': investor_.referral_url
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



def activate(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        print('UID: ' + str(uid))
        user = Investor.objects.get(id=int(uid))
        print('Username: ' + str(user.username))
        if account_activation_token.check_token(user, token):
            user.is_active = True
            user.save()
            current_site = get_current_site(request)
            mail_subject = 'Your Geld Account Details.'
            message = render_to_string('registration/activate_email.html', {
                'user': user.username,
                'passphrase': user.pass_phrase,
                'Wallet_address': user.deposit_address
            })
            message_ = Mail(from_email=settings.EMAIL,
                            to_emails=user.email,
                            subject=mail_subject, html_content=message)
            try:
                send_message(message_)
                user.save()
                request.session['message'] = 'Your pass phrase is "' + str(
                    user.pass_phrase) + '". Please kindly save it somewhere'
                request.session['status'] = 'info'
                return redirect('login')
            except Exception as e:
                request.session['message'] = 'Your pass phrase is ' + str(
                    user.pass_phrase) + '. Please kindly save it somewhere.'
                request.session['status'] = 'info'
                return redirect('login')

        else:
            if user.is_active is False:
                user.delete()
                return render(request, 'wallet/home.html',
                              {'message': 'Your Email was invalid, Therefore Your Account Has '
                                          'been deleted', 'status': 'danger'})
            else:
                request.session['message'] = 'Your pass phrase is "' + str(
                    user.pass_phrase) + '". Please kindly save it somewhere.'
                request.session['status'] = 'info'
                return redirect('login')
    except Investor.DoesNotExist:
        return render(request, 'wallet/home.html', {'message': 'User Does Not Exist', 'status': 'danger'})


