from django.conf.urls.defaults import *
from website import views
from settings import STATIC_DOC_ROOT


urlpatterns = patterns('',
    (r'^static/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': STATIC_DOC_ROOT}),
    url(r'^approvals_show', views.approvals_show, name='approvals_show'),
    url(r'^approvals', views.approvals, name='approvals'),
    url(r'^export', views.export, name='export'),
    url(r'^update_banks', views.update_banks, name='update_banks'),
    url(r'^invoices/export', views.invoices_export, name='invoices_export'),
    url(r'^invoices', views.invoices, name='invoices'),
    url(r'^$', views.index, name='index'),
    
)
