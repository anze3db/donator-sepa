from django.conf.urls.defaults import *
from website import views


urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
)
