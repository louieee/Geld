from django.contrib import admin

from .models import Client, Wallet, Level6, Level5, Level4, Level3, Level2, Level1

# Register your models here.
admin.site.register(Client)
admin.site.register(Wallet)
admin.site.register(Level6)
admin.site.register(Level1)
admin.site.register(Level2)
admin.site.register(Level3)
admin.site.register(Level4)
admin.site.register(Level5)
