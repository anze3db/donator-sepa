from django.conf.urls.defaults import *
from website import views
from settings import STATIC_DOC_ROOT


urlpatterns = patterns('',
    (r'^static/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': STATIC_DOC_ROOT}),
    url(r'^export', views.export, name='export'),
    url(r'^$', views.index, name='index'),
)
