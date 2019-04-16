from django.db import models
from django.contrib.auth.models import User


# Create your models here.

class Client(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    level = models.CharField(max_length=255, default="Newbie")
    referer = models.CharField(max_length=255, default='0')
    paid = models.BooleanField(default=False)
    balance = models.DecimalField(default=0.0, decimal_places=6, max_digits=255)


class Level1(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    no_received = models.IntegerField(default=0)
    date_joined = models.DateTimeField()
    name = "Beginner"


class Level2(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    no_received = models.IntegerField(default=0)
    date_joined = models.DateTimeField()
    name = "Amateur"


class Level3(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    no_received = models.IntegerField(default=0)
    date_joined = models.DateTimeField()
    name = "Intermediate"


class Level4(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    no_received = models.IntegerField(default=0)
    date_joined = models.DateTimeField()
    name = "Professional"


class Level5(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    no_received = models.IntegerField(default=0)
    date_joined = models.DateTimeField()
    name = "Master"


class Level6(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    no_received = models.IntegerField(default=0,)
    date_joined = models.DateTimeField()
    name = "Grand Master"


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    address = models.CharField(max_length=255)
    guid = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    balance = models.DecimalField(default=0.0, decimal_places=6, max_digits=255)
    label = models.CharField(max_length=255)
    previous_balance = models.DecimalField(default=0.0, decimal_places=6, max_digits=255)