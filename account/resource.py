from tastypie.resources import ModelResource
from .models import Level2


class Level2p(ModelResource):
    class Meta:
        queryset = Level2.objects.order_by('date_joined').filter(no_received__lt=4)
        resource_name = 'amateurs'
