from datetime import date
from django.db import connection
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.datetime_safe import datetime
from lxml.builder import E
from lxml.etree import tostring
from website.models import get_payments_list, get_available_approvals, generate_approvals
import time

def index(request):

    cursor = connection.cursor()
    installments = []
    #, sfr_project as pr, sfr_project_trr as trr "\
    if request.POST:
        date = '-'.join([request.POST['year'], request.POST['month'], request.POST['day']])
        installments = get_payments_list(date, request.POST['project'])
        print installments

    cursor.execute("SELECT * FROM sfr_project;")
    rows = cursor.fetchall()
    
    project = []
    for r in rows:
        project.append({'id': r[0], 'project':r[1].strip()})
        
    
    
    month = [{"month": i, "current":i==int(datetime.now().strftime("%m"))} for i in range(1,13)]
    y = int(datetime.now().strftime("%Y"))
    year   = [{"year": i, "current":i==y} for i in range(2010,y+4,1)]
    
    num_approvals = len(get_available_approvals())
    
    return render_to_response('index.html', {
                                   'date': datetime.now(), 
                                   'month': month, 
                                   'year':year, 
                                   'project':project, 
                                   'installments': installments,
                                   'num_approvals': num_approvals,
                               }, context_instance=RequestContext(request))

def export(request):
    if request.POST:
        
        pay = [get_payments_list(p)[0] for p in request.POST.getlist('id_payement')]
        
        # Strip strings:
        for i in range(len(pay)):
            for j in pay[i].keys():
                if isinstance(pay[i][j], basestring):
                    pay[i][j] = pay[i][j].strip()
        
        nbOfTxs, CtrlSum = (str(len(pay)), str(sum([p['amount'] for p in pay])))
        rf = time.strftime("%Y%m%d%H%M%S", time.localtime()) + str(nbOfTxs)
        ctrl = "%02d" % (98-(int(rf + "271500") % 97))
        hd = "RF"+ctrl+rf
        header = E.GrpHdr(E.MsgId(hd),
                          
            E.CreDtTm(time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())),
            E.NbOfTxs(nbOfTxs),
            E.CtrlSum(CtrlSum),
            E.InitgPty(
                E.Nm(pay[0]['name_project']),
                #  VID= SI83ZZZ79740111 Fundacija= SI60ZZZ85420263
                E.Id(E.OrgId(E.Othr(E.Id("SI60ZZZ85420263" if pay[0]['id_project'] == 2 else "SI83ZZZ79740111"))))
                )
        )
        
        payment = E.PmtInf(
            E.PmtInfId("PAK"+rf),
            E.PmtMtd("DD"),
            E.BtchBookg("FALSE"),
            E.NbOfTxs(nbOfTxs),
            E.CtrlSum(CtrlSum),
            E.PmtTpInf(E.SvcLvl(E.Cd("SEPA")), E.LclInstrm(E.Cd("CORE")), E.SeqTp("FRST")), # TODO: FRST- RCUR - FNAL????
            E.ReqdColltnDt(pay[0]['date_activate'].strftime("%Y-%m-%d")),
            E.Cdtr(E.Nm(pay[0]['name_project']), E.PstlAdr(
                E.Ctry("SI"),
                E.AddrLine("Planina 3"),
                E.AddrLine("4000 Kranj")
            )),
            E.CdtrAcct(E.Id(E.IBAN("SI56"+pay[0]["id_trr"].replace("-", "")))), # TODO :(
            E.CdtrAgt(E.FinInstnId(E.BIC("???"))),
            E.UltmtCdtr(E.Nm(pay[0]['name_project']), E.BICOrBEI("???"), E.Othr(E.Id("???"))), # TODO: AAAA
            E.ChrgBr("SLEV"),
            E.CdtrSchmeId(), # TODO: BBBB
        )
        for p in pay:
            TxInf = E.DrctDbtTxInf(
                E.PmtId(E.PmtId(E.EndToEndId(p['id_agreement']))),
                E.InstdAmt(str(p['amount']), Ccy="EUR"),
                E.ChrgBr("SLEV"),
                E.DrctDbtTx(E.MndtRltdInf(
                    E.MndtId(str(p['approval'])),
                    E.DtOfSgntr(p['approval_date'].strftime("%Y-%m-%d")),
                    E.AmdmntInd("false"),  
                )),
                E.DbtrAgt(E.FinInstnId(E.BIC(p['bic']))), # TODO: BIC?
                E.Dbtr(
                    E.Nm(p['first_name'] + " " +p['scnd_name']),
                    E.PstlAdr(
                        E.Ctry("SI"),
                        E.AdrLine(p['street'] + " " + p['street_number']),
                        E.AdrLine(p['post_name'])
                    ),
                    E.Id(E.Othr(str(p['id_donor']))) # TODO: Is this OK?
                ),
                E.DbtrAcct(E.Id(E.IBAN(p['bank_account2']))),
                #E.UltmtDbtr(), # TODO: Is this necissary
                E.Purp(E.Cd("CHAR")),
                E.RmtInf() # TODO: WTF?
            )
            payment.append(TxInf)
        
        x = E.Document(E.CstmrDrctDbtInitn(header, payment))
        xml = tostring(x, pretty_print = True, xml_declaration=True, encoding='UTF-8')
        
        
        response =  HttpResponse(xml, 'xml')
        response['Content-Disposition'] = 'attachment; filename="db%s.xml"' % time.strftime("%Y-%m-%d", time.localtime())
        return response
    
def approvals(request):
    if request.POST:
        a = generate_approvals(int(request.POST['num_approvals']))
        response = HttpResponse("\n".join(a), 'text')
        response['Content-Disposition'] = 'attachment; filename="sog%s.txt"' % time.strftime("%Y-%m-%d", time.localtime())
        return response
    
def approvals_show(request):
    return HttpResponse("\n".join(get_available_approvals()), 'text')


