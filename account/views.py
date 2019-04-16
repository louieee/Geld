from django.shortcuts import HttpResponse
from django.core.mail import EmailMultiAlternatives
from django.core import mail
from django.contrib.auth.models import User
from django.contrib import auth
from .models import Client, Level1, Level2, Level3, Level4, Level5, Level6, Wallet
from blockchain import createwallet, wallet
from django.utils.timezone import datetime as date
from django.contrib.auth.decorators import login_required
import json
import decimal
import requests

# Create your views here.
Api_code = ""
service_url = 'http://27.0.0.1:8000/'
mail_conn = mail.get_connection()


def signup(request):
    global user, refer, ma_ref
    if request.method == 'POST':
        first_password = str(request.POST.get('password1', False))
        second_password = str(request.POST.get('password2', False))
        email = str(request.POST.get('email', False))
        referer = str(request.POST.get('referer', False))
        username = str(request.POST.get('username', False))
        if first_password == second_password:
            try:
                error = 'Username has already been taken'
                user = User.objects.get(username=username)
                return HttpResponse(json.dumps({'error': error}))
            except user.DoesNotExist:
                try:
                    error = 'Email is already in use'
                    user = User.objects.get(email=email)
                    return HttpResponse(json.dumps({'error': error}))
                except user.DoesNotExist:
                    user = User.objects.create_user(username=username, password=first_password, email=email)
                    client = Client()
                    client.user = user
                    try:
                        refer = Level1.objects.get(user__username=client.referer)
                        client.referer = referer
                    except refer.DoesNotExist:
                        assert isinstance(ma_ref, Level1)
                        try:
                            ma_ref = Level1.objects.order_by('date_joined').filter(no_received__lt=2)[:1].get()
                            client.referer = ma_ref.user.username
                        except ma_ref.DoesNotExist:
                            client.referer = '0'
                    client.save()
                    wallet_ = createwallet.create_wallet(password=first_password, api_code=Api_code, email=email,
                                                         service_url=service_url)
                    my_wallet = Wallet()
                    my_wallet.user = client.user
                    my_wallet.guid = wallet_.identifier
                    my_wallet.password = client.user.password
                    my_wallet.address = wallet_.address
                    my_wallet.label = wallet_.label
                    return HttpResponse(json.dumps({'Message': 'Sign up successful'}))
        else:
            error = 'Passwords must match'
            return HttpResponse(json.dumps({'Message': error}))
    else:
        pass


def login(request):
    if request.method == 'POST':
        username = str(request.POST.get('username', False))
        password = str(request.POST.get('password', False))
        user_ = auth.authenticate(username=username, password=password)
        if user_ is not None:
            auth.login(request, user_)
            d_client = Client.objects.get(user__username=username, user__password=password)
            return HttpResponse(json.dumps({'Message': "You are Logged in", 'Level': d_client.level}))

        else:
            error = 'Username or Password is Incorrect'
            return HttpResponse(json.dumps({'Message': error}))


def logout(request):
    auth.logout(request)
    return HttpResponse(json.dumps({'Message': 'You are currently logged out'}))


@login_required(login_url="/")
def payment(request, username):
    if request.method == 'POST':
        amount_ = int(request.POST.get('amount', False))
        geld_wallet = Wallet.objects.get(user__username='Louisane')
        address_ = wallet.Wallet(identifier=geld_wallet.guid, password=geld_wallet.password, service_url=service_url,
                                 api_code=Api_code).new_address(label=geld_wallet.label)
        wallet__ = Wallet.objects.get(user__username=username)
        bit_wallet = wallet.Wallet(identifier=wallet__.guid, password=wallet__.password, service_url=service_url,
                                   api_code=Api_code)
        prev_bal = bit_wallet.get_balance()
        wallet__.previous_balance = prev_bal
        trans_ = wallet.Wallet(identifier=wallet__.guid, password=wallet__.password,
                               service_url=service_url, api_code=Api_code).send(to=address_, amount=amount_)
        curr_bal = bit_wallet.get_balance()
        wallet__.balance = curr_bal
        wallet__.save()
        if str(trans_.notice).__contains__('sent'):
            return HttpResponse(json.dumps({'Message': trans_.message, 'Notice': trans_.notice,
                                            'previous_balance': prev_bal}))
        else:
            return HttpResponse(json.dumps({'Message': 'Error Making Payment'}))


@login_required(login_url="/")
def verify(request, username):
    global d_level
    a_wallet = Wallet.objects.get(user__username=username)
    r = requests.get(url='https://blockchain.info/q/getsentbyaddress/' + a_wallet.address + '?confirmations=6')
    value = decimal.Decimal(r.text) / 1000000
    if value >= decimal.Decimal(0.0025):
        d_client = Client().objects.get(user__username=username)
        d_client.paid = True
        try:
            d_level = Level1.objects.get(user__username=d_client.referer)
            if d_level.no_received < 2:
                d_level.no_received += 1
                d_level.save()
                d_ref = Client.objects.get(user__username=d_client.referer)
                d_ref.balance += decimal.Decimal(0.0025)
                d_ref.save()
        except d_level.DoesNotExist:
            d_level = Level1().objects.filter(no_received__lt=2).first()
            d_level.no_received += 1
            d_level.save()
            d_ref = Client.objects.get(user__username=d_client.referer)
            d_ref.balance += decimal.Decimal(0.0025)
            d_ref.save()
        d_client.level = Level1.name
        some_level = Level1()
        some_level.user = d_client.user
        some_level.date_joined = date.now()
        some_level.save()
        return HttpResponse(json.dumps({'Message': 'Verified'}))
    else:
        return HttpResponse(json.dumps({'Message': 'Not Verified'}))


@login_required(login_url="/")
def account(request, username):
    the_client = Client.objects.get(user__username=username)
    the_level = the_client.level
    global per_cent
    global la_level
    if the_level == Level1.name:
        la_level = Level1.objects.get(user__username=username)
        per_cent = (la_level.no_received / 2) * 100
    elif the_level == Level2.name:
        la_level = Level2.objects.get(user__username=username)
        per_cent = (la_level.no_received / 4) * 100
    elif the_level == Level3.name:
        la_level = Level3.objects.get(user__username=username)
        per_cent = (la_level.no_received / 8) * 100
    elif the_level == Level4.name:
        la_level = Level4.objects.get(user__username=username)
        per_cent = (la_level.no_received / 16) * 100
    elif the_level == Level5.name:
        la_level = Level5.objects.get(user__username=username)
        per_cent = (la_level.no_received / 32) * 100
    elif the_level == Level6.name:
        la_level = Level6.objects.get(user__username=username)
        per_cent = (la_level.no_received / 64) * 100
    return HttpResponse(json.dumps({"username": the_client.user.username, "email": the_client.user.email,
                                    'level': la_level.name, "percentage": per_cent,
                                    'Balance': str(the_client.balance)}))


@login_required(login_url="/")
def new_account(request, username):
    the_client = Client.objects.get(user__username=username)
    return HttpResponse(json.dumps({'username': the_client.user.username, 'email': the_client.user.email,
                                    'level': the_client.level, 'status': the_client.paid}))


@login_required(login_url="/")
def upgrade(request, username):
    global smone
    the_client = Client.objects.get(user__username=username)
    ma_level = the_client.level
    if ma_level == Level1.name:
        if Level1.objects.get(user__username=username).no_received == 2:
            try:
                smone = Level2.objects.order_by('date_joined').filter(no_received__lt=4)[:1].get()
                smone.no_received += 1
                smone.save()
                d_ref = Client.objects.get(user__username=smone.user.username)
                d_ref.balance += decimal.Decimal(0.004)
                d_ref.save()
            except smone.DoesNotExist:
                pass
            the_client.balance -= decimal.Decimal(0.004)
            the_client.save()
            Level1.objects.get(user__username=username).delete()
            ma_level_ = Level2()
            ma_level_.user = User.objects.get(username=username)
            ma_level_.date_joined = date.now()
            ma_level_.save()
            the_client.level = Level2.name
            the_client.save()
        else:
            return HttpResponse(json.dumps({'Message': 'You have not reached the limit'}))
    elif ma_level == Level2.name:
        if Level2.objects.get(user__username=username).no_received == 4:
            try:
                smone = Level3.objects.order_by('date_joined').filter(no_received__lt=8)[:1].get()
                smone.no_received += 1
                smone.save()
                d_ref = Client.objects.get(user__username=smone.user.username)
                d_ref.balance += decimal.Decimal(0.006)
                d_ref.save()
            except smone.DoesNotExist:
                pass
            the_client.balance -= decimal.Decimal(0.006)
            the_client.save()
            Level2.objects.get(user__username=username).delete()
            ma_level_ = Level3()
            ma_level_.user = User.objects.get(username=username)
            ma_level_.date_joined = date.now()
            ma_level_.save()
            the_client.level = Level3.name
            the_client.save()
        else:
            return HttpResponse(json.dumps({'Message': 'You have not reached the limit'}))
    elif ma_level == Level3.name:
        if Level3.objects.get(user__username=username).no_received == 8:
            try:
                smone = Level4.objects.order_by('date_joined').filter(no_received__lt=16)[:1].get()
                smone.no_received += 1
                smone.save()
                d_ref = Client.objects.get(user__username=smone.user.username)
                d_ref.balance += decimal.Decimal(0.018)
                d_ref.save()
            except smone.DoesNotExist:
                pass
            the_client.balance -= decimal.Decimal(0.018)
            the_client.save()
            Level3.objects.get(user__username=username).delete()
            ma_level_ = Level4()
            ma_level_.user = User.objects.get(username=username)
            ma_level_.date_joined = date.now()
            ma_level_.save()
            the_client.level = Level4.name
            the_client.save()
        else:
            return HttpResponse(json.dumps({'Message': 'You have not reached the limit'}))
    elif ma_level == Level4.name:
        if Level4.objects.get(user__username=username).no_received == 16:
            try:
                smone = Level5.objects.order_by('date_joined').filter(no_received__lt=32)[:1].get()
                smone.no_received += 1
                smone.save()
                d_ref = Client.objects.get(user__username=smone.user.username)
                d_ref.balance += decimal.Decimal(0.088)
                d_ref.save()
            except smone.DoesNotExist:
                pass
            the_client.balance -= decimal.Decimal(0.088)
            the_client.save()
            Level4.objects.get(user__username=username).delete()
            ma_level_ = Level5()
            ma_level_.user = User.objects.get(username=username)
            ma_level_.date_joined = date.now()
            ma_level_.save()
            the_client.level = Level5.name
            the_client.save()
        else:
            return HttpResponse(json.dumps({'Message': 'You have not reached the limit'}))
    elif ma_level == Level5.name:
        if Level5.objects.get(user__username=username).no_received == 32:
            try:
                smone = Level6.objects.order_by('date_joined').filter(no_received__lt=64)[:1].get()
                smone.no_received += 1
                smone.save()
                d_ref = Client.objects.get(user__username=smone.user.username)
                d_ref.balance += decimal.Decimal(0.816)
                d_ref.save()
            except smone.DoesNotExist:
                pass
            the_client.balance -= decimal.Decimal(0.816)
            the_client.save()
            Level5.objects.get(user__username=username).delete()
            ma_level_ = Level6()
            ma_level_.user = User.objects.get(username=username)
            ma_level_.date_joined = date.now()
            ma_level_.save()
            the_client.level = Level6.name
            the_client.save()
        else:
            return HttpResponse(json.dumps({'Message': 'You have not reached the limit'}))
    elif ma_level == Level6.name:
        if Level6.objects.get(user__username=username).no_received == 64:
            the_wallet = Wallet.objects.get(user__username=username)
            body = '<html>Wallet Address: ' + the_wallet.address + '<br/>' + 'Wallet Email:' + the_wallet.user.email + '<br/>' \
                   + 'Wallet Password' + the_wallet.password + '<br/><br/>' + 'The wallet details above was sent to you' \
                   + 'because you have finished the final level in Geld and your account has been deleted'
            msg = EmailMultiAlternatives(subject='Geld Wallet Details', from_email='info@geld.com</html>',
                                         to=[the_client.user.email], connection=mail_conn, body=body)
            msg.attach_alternative(body, "text/html")
            msg.content_subtype = "html"
            msg.send()
            the_wallet.delete()
            Level6.objects.get(user__username=username).delete()
            User.objects.get(username=username).delete()
        else:
            return HttpResponse(json.dumps({'Message': 'You have not reached the limit'}))

    return HttpResponse(json.dumps({'Message': 'Successful'}))


@login_required(login_url="/")
def cash_out(request, username):
    the_client = Client.objects.get(user__username=username)
    the_wallet = Wallet.objects.get(user__username=username)
    geld_wallet = Wallet.objects.get(user__username='Louisane')
    global message
    level = the_client.level
    if level == Level1.name:
        if the_client.balance > decimal.Decimal(0.001 + 0.004):
            amount = the_client.balance - decimal.Decimal(0.005)
            if amount >= decimal.Decimal(0.001):
                trans = wallet.Wallet(geld_wallet.guid, geld_wallet.password, service_url, api_code=Api_code) \
                    .send(to=the_wallet.address, amount=amount)
                if str(trans.message).__contains__('sent'):
                    the_client.balance -= amount
                    the_client.save()
                    message = trans.message
                else:
                    message = trans.message
            else:
                message = 'Insufficient Funds'
        else:
            message = 'Insufficient Funds'
    elif level == Level2.name:
        if the_client.balance > decimal.Decimal(0.001 + 0.006):
            amount = the_client.balance - decimal.Decimal(0.007)
            if amount >= decimal.Decimal(0.005):
                trans = wallet.Wallet(geld_wallet.guid, geld_wallet.password, service_url, api_code=Api_code) \
                    .send(to=the_wallet.address, amount=amount)
                if str(trans.message).__contains__('sent'):
                    the_client.balance -= amount
                    the_client.save()
                    message = trans.message
                else:
                    message = trans.message
            else:
                message = 'Insufficient Funds'
        else:
            message = 'Insufficient Funds'
    elif level == Level3.name:
        if the_client.balance > decimal.Decimal(0.001 + 0.018):
            amount = the_client.balance - decimal.Decimal(0.019)
            if amount >= decimal.Decimal(0.007):
                trans = wallet.Wallet(geld_wallet.guid, geld_wallet.password, service_url, api_code=Api_code) \
                    .send(to=the_wallet.address, amount=amount)
                if str(trans.message).__contains__('sent'):
                    the_client.balance -= amount
                    the_client.save()
                    message = trans.message
                else:
                    message = trans.message
            else:
                message = 'Insufficient Funds'
        else:
            message = 'Insufficient Funds'
    elif level == Level4.name:
        if the_client.balance > decimal.Decimal(0.001 + 0.088):
            amount = the_client.balance - decimal.Decimal(0.089)
            if amount >= decimal.Decimal(0.019):
                trans = wallet.Wallet(geld_wallet.guid, geld_wallet.password, service_url, api_code=Api_code) \
                    .send(to=the_wallet.address, amount=amount)
                if str(trans.message).__contains__('sent'):
                    the_client.balance -= amount
                    the_client.save()
                    message = trans.message
                else:
                    message = trans.message
            else:
                message = 'Insufficient Funds'
        else:
            message = 'Insufficient Funds'
    elif level == Level5.name:
        if the_client.balance > decimal.Decimal(0.001 + 0.816):
            amount = the_client.balance - decimal.Decimal(0.817)
            if amount >= decimal.Decimal(0.089):
                trans = wallet.Wallet(geld_wallet.guid, geld_wallet.password, service_url, api_code=Api_code) \
                    .send(to=the_wallet.address, amount=amount)
                if str(trans.message).__contains__('sent'):
                    the_client.balance -= amount
                    the_client.save()
                    message = trans.message
                else:
                    message = trans.message
            else:
                message = 'Insufficient Funds'
        else:
            message = 'Insufficient Funds'
    elif level == Level6.name:
        if the_client.balance > decimal.Decimal(0.001 + 2.224):
            amount = the_client.balance - decimal.Decimal(2.225)
            if amount >= decimal.Decimal(0.817):
                trans = wallet.Wallet(geld_wallet.guid, geld_wallet.password, service_url, api_code=Api_code) \
                    .send(to=the_wallet.address, amount=amount)
                if str(trans.message).__contains__('sent'):
                    the_client.balance -= amount
                    the_client.save()
                    message = trans.message
                else:
                    message = trans.message
            else:
                message = 'Insufficient Funds'
        else:
            message = 'Insufficient Funds'

    return HttpResponse(json.dumps({'Message': message}))


def home(request):
    return HttpResponse(json.dumps({'Message': "You are currently Logged out"}))


@login_required(login_url="/")
def client_wallet(request, username):
    d_wallet = Wallet.objects.get(user__username=username)
    b = wallet.Wallet(identifier=d_wallet.guid, password=d_wallet.password, service_url=service_url)
    d_wallet.balance = b.get_balance() / 100000000
    d_wallet.save()
    return HttpResponse(json.dumps({'address': d_wallet.address, 'balance': d_wallet.balance,
                                    'email': d_wallet.user.email}))
