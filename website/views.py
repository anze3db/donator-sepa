# Create your views here.
from django.http import HttpResponse
from lxml.etree import tostring 
from lxml.builder import E
from django.db import connection
from django.shortcuts import render_to_response
from django.utils.datetime_safe import datetime
from datetime import date
from django.template.context import RequestContext
from website.models import get_payments_list

def index(request):

    cursor = connection.cursor()
    stuff = []
    #, sfr_project as pr, sfr_project_trr as trr "\
    if request.POST:
        
#        "SELECT  ".
#                   "a.zap_st_dolznika, a.sifra_banke, a.stara_pogodba ".
#                   "FROM agreement_pay_installment as p, sfr_agreement as a ".
#                   "WHERE p.id_vrstica= ? AND a.id_agreement = p.id_agreement ".
#                   "ORDER BY a.sifra_banke"
        
        
        
        
        

    # Data retrieval operation - no commit required
        date = '-'.join([request.POST['year'], request.POST['month'], request.POST['day']])
        stuff = get_payments_list(date, request.POST['project'])

    cursor.execute("SELECT * FROM sfr_project;")
    rows = cursor.fetchall()
    
    project = []
    for r in rows:
        project.append({'id': r[0], 'project':r[1].strip()})
        
    
    
    month = [{"month": i, "current":i==int(datetime.now().strftime("%m"))} for i in range(1,13)]
    y = int(datetime.now().strftime("%Y"))
    year   = [{"year": i, "current":i==y} for i in range(2010,y+4,1)]
    
    
    
    
    return render_to_response('index.html', {'date': datetime.now(), 'month': month, 'year':year, 'project':project, 'stuff': stuff},
                              context_instance=RequestContext(request))
    
def export(request):
    if request.POST:
        
        print request.POST.getlist('id_payement')
        
        xml = tostring(E.results(E.country(name='neki')), pretty_print = True, xml_declaration=True, encoding='UTF-8')
        
        return HttpResponse(xml, 'xml')
    