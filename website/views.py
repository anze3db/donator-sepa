from datetime import date
from django.db import connection
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.datetime_safe import datetime
from lxml.builder import E
from lxml.etree import tostring
from website.models import get_payments_list, get_available_approvals, generate_approvals, clear_banks, add_bank
import time

def index(request):

    cursor = connection.cursor()
    installments = []
    if request.POST:
        date = '-'.join([request.POST['year'], request.POST['month'], request.POST['day']])
        installments = get_payments_list(date, request.POST['project'])

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
        
        
        cursor = connection.cursor()
        cursor.execute("BEGIN;")
        pay = [get_payments_list(p)[0] for p in request.POST.getlist('id_payement')]
        
        # Strip strings:
        for i in range(len(pay)):
            for j in pay[i].keys():
                if isinstance(pay[i][j], basestring):
                    pay[i][j] = pay[i][j].strip()
        
        nbOfTxs, CtrlSum = (str(len(pay)), str(sum([p['amount'] for p in pay])))
        rf = time.strftime("%Y%m%d%H%M%S", time.localtime()) + str(nbOfTxs)
        ctrl = "%02d" % (98-(int(rf + "271500") % 97))
        hd = ""+ctrl+rf
        #  VID= SI83ZZZ79740111 Fundacija= SI60ZZZ85420263
        theId = "SI60ZZZ85420263" if pay[0]['id_project'] == 2 else "SI83ZZZ79740111"
        
        
        
        header = E.GrpHdr(E.MsgId(hd),
                          
            E.CreDtTm(time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())),
            E.NbOfTxs(nbOfTxs),
            E.CtrlSum(CtrlSum),
            E.InitgPty(
                E.Nm(pay[0]['name_project']),
                E.Id(E.OrgId(E.Othr(E.Id(theId[7:]), E.SchmeNm(E.Prtry('SEPA')))))
                
                )
        )
        
        payment = E.PmtInf(
            E.PmtInfId(hd),
            E.PmtMtd("DD"),
            E.BtchBookg("false"),
            E.NbOfTxs(nbOfTxs),
            E.CtrlSum(CtrlSum),
            E.PmtTpInf(E.InstrPrty("NORM"), 
                       E.SvcLvl(E.Cd("SEPA")), 
                       E.LclInstrm(E.Cd("CORE")), 
                       E.SeqTp(request.POST['type'])),
            E.ReqdColltnDt(pay[0]['date_activate'].strftime("%Y-%m-%d")),
            E.Cdtr(E.Nm(pay[0]['name_project']), E.PstlAdr(
                E.Ctry("SI"),
                E.AdrLine("Planina 3"),
                E.AdrLine("4000 Kranj")
            )),
            E.CdtrAcct(E.Id(E.IBAN("SI56"+pay[0]["id_trr"].replace("-", ""))), E.Ccy('EUR')),
            E.CdtrAgt(E.FinInstnId(E.BIC("ABANSI2X"))),
            #E.UltmtCdtr(E.Nm(pay[0]['name_project']), E.Id(E.OrgId(E.Othr(E.Id(theId[7:]))))),
            E.ChrgBr("SLEV"),
            E.CdtrSchmeId(E.Id(E.PrvtId(E.Othr(E.Id(theId), E.SchmeNm(E.Prtry("SEPA")))))),
        )
        for p in pay:
            if 'record-transaction' in request.POST:
                sql = "UPDATE agreement_pay_installment "\
                    + "SET amount_payed=%s, id_packet_pp=%s, date_due=date_activate "\
                    + "WHERE id_vrstica = %s"
                
                cursor.execute(sql,[p['amount'], "0", p['id_vrstica']])
            
            
            TxInf = E.DrctDbtTxInf(
                E.PmtId(E.InstrId("SI00"+p['id_agreement'][:8] + "-" + p['id_agreement'][8:]),
                        E.EndToEndId("SI00"+p['id_agreement'][:8] + "-" + p['id_agreement'][8:])),
                E.InstdAmt(str(p['amount']), Ccy="EUR"),
                E.ChrgBr("SLEV"),
                E.DrctDbtTx(E.MndtRltdInf(
                    E.MndtId(str(p['approval'])),
                    E.DtOfSgntr(p['approval_date'].strftime("%Y-%m-%d")),
                    E.AmdmntInd("false"),  
                )),
                E.DbtrAgt(E.FinInstnId(E.BIC(p['bic']))),
                E.Dbtr(
                    E.Nm(p['first_name'] + " " +p['scnd_name']),
                    E.PstlAdr(
                        E.Ctry("SI"),
                        E.AdrLine(p['street'] + " " + p['street_number']),
                        E.AdrLine(p['post_name'])
                    ),
                    E.Id(E.PrvtId(E.Othr(E.Id(str(p['id_donor']))))) 
                ),
                E.DbtrAcct(E.Id(E.IBAN("SI56" + p['bank_account2'].replace(' ', '')))),
                E.UltmtDbtr(E.Nm(p['first_name'] + " " +p['scnd_name']), 
                            E.Id(E.PrvtId(E.Othr(E.Id(str(p['id_donor'])))))
                ),
                E.Purp(E.Cd("CHAR")),
                E.RmtInf(E.Ustrd("DONACIJA %s-%s" % (str(p['id_agreement']), str(p["id_vrstica"]))))
            )
            payment.append(TxInf)
        
        
        
        x = E.Document(E.CstmrDrctDbtInitn(header, payment), xmlns="urn:iso:std:iso:20022:tech:xsd:pain.008.001.02")
        x.set("xmlns__xsi", "http://www.w3.org/2001/XMLSchema-instance")
        xml = tostring(x, pretty_print = False, xml_declaration=True, encoding='UTF-8')
        xml = xml.replace('xmlns__xsi', 'xmlns:xsi') # I can't seem to set this attrib normaly
        
        filename = "db-%s-%s-%s.xml" % (time.strftime("%Y-%m-%d", time.localtime()), pay[0]['id_project'], request.POST['type'] )
        
        sql = "INSERT INTO datoteke_izvozene (filename, content) VALUES (%s, %s)"
        cursor.execute(sql, [filename, xml])
        
        
        cursor.execute("COMMIT;")
        response =  HttpResponse(xml, 'xml')
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        return response
    
def approvals(request):
    if request.POST:
        a = generate_approvals(int(request.POST['num_approvals']))
        response = HttpResponse("\n".join(a), 'text')
        response['Content-Disposition'] = 'attachment; filename="sog%s.txt"' % time.strftime("%Y-%m-%d", time.localtime())
        return response
    
def approvals_show(request):
    return HttpResponse("\n".join(get_available_approvals()), 'text')

def update_banks(request):
    banks = open("banks").readlines()

    clear_banks()

    for bank in banks:
        add_bank(bank.strip().split("    "))

    return HttpResponse("O", 'text')
