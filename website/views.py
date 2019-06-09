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

from docxtpl import DocxTemplate
from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from httplib2 import Http
import io
from apiclient.http import MediaIoBaseDownload, MediaFileUpload


def _get_projects():
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM sfr_project order by id_project;")
    rows = cursor.fetchall()
    
    project = []
    for r in rows:
        project.append({'id': r[0], 'project':r[1].strip()})

    return project

def _get_events():
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM sfr_events order by id_event;")
    rows = cursor.fetchall()
    
    project = []
    for r in rows:
        project.append({'id': r[0], 'event':r[1].strip()})

    return project

def index(request):

    cursor = connection.cursor()
    installments = []
    if request.POST:
        date = '-'.join([request.POST['year'], request.POST['month'], request.POST['day']])
        installments = get_payments_list(date, request.POST['project'])

    project = _get_projects()
        
    
    
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
    banks = open("/home/smotko/sepa-production/banks").readlines()

    clear_banks()

    for bank in banks:
        add_bank(bank.strip().split("    "))

    return HttpResponse("O", 'text')

def invoices(request):
    data = {
        'years': range(datetime.now().year, 2006, -1),
        'projects': _get_projects(),
        'events': _get_events(),
        'date': datetime.now().strftime('%Y-%m-%d')
    }
    if request.POST:
        cursor = connection.cursor()
        cursor.execute(
            """SELECT DISTINCT 
                    a.id_agreement,
                    api.id_vrstica,
                    a.name_company,
                    a.street,
                    a.street_number,
                    a.id_post,
                    a.post_name,
                    a.tax_number,
                    api.amount
                 FROM sfr_agreement AS a
                 JOIN agreement_pay_installment AS api ON api.id_agreement = a.id_agreement
                WHERE api.storno ISNULL 
                  AND api.amount > 0 
                  AND api.date_izpis ISNULL
                  AND api.debit_type = 'A1'
                  AND api.leto = %s
                  AND api.id_project = %s
                  AND a.id_event = %s
            """, (
                request.POST.get('year')[2:],
                request.POST.get('project'),
                request.POST.get('event')
            )
        )
        rows = cursor.fetchall()
        invoices = []
        for row in rows:
            invoice = {
                'id_agreement': row[0],
                'id_vrstica': row[1],
                'name_company': row[2],
                'street': row[3],
                'street_number': row[4],
                'id_post': row[5],
                'post_name': row[6],
                'tax_number': row[7],
                'amount': row[8],
            }
            invoices.append(invoice)
        data['invoices'] = invoices
        data['invoices_len'] = len(invoices)
        return render_to_response('invoices.html', data, context_instance=RequestContext(request))
    return render_to_response('invoices.html', data, context_instance=RequestContext(request))

def invoices_export(request):
    installments = request.POST.getlist("installments")
    is_store_date = request.POST.get("store_date") == 'on'
    store_date = datetime.strptime(request.POST.get("date"), "%Y-%m-%d")
    cursor = connection.cursor()
    
    cursor.execute(
        """SELECT DISTINCT 
                a.id_agreement,
                api.id_vrstica,
                a.name_company,
                a.street,
                a.street_number,
                a.id_post,
                a.post_name,
                a.tax_number,
                api.amount,
                a.date_agreement,
                api.date_activate
             FROM sfr_agreement AS a
             JOIN agreement_pay_installment AS api ON api.id_agreement = a.id_agreement
            WHERE api.id_vrstica IN ({}) 
        """.format(','.join('%s' for _ in installments)), installments)
    rows = cursor.fetchall()
    invoices = []
    for row in rows:
        invoice = {
            'id_pogodbe': row[0],
            'id_vrstica': row[1],
            'naziv_podjetja': row[2],
            'ulica': row[3].strip(),
            'ulicna_stevilka': row[4].strip(),
            'postna_stevilka': row[5],
            'posta': row[6],
            'davcna_stevilka': row[7],
            'celoten_znesek': row[8],
            'datum_pogodbe': row[9].strftime('%d. %m. %Y'),
            'datum_zapadlosti': row[10].strftime('%d. %m. %Y'),
            'datum_vnosa': store_date.strftime('%d. %m. %Y')
            
        }
        invoices.append(invoice)
    
    # AUTH DRIVE:
    scopes = ['https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('donator-1500c8e231aa.json', scopes)
    http_auth = credentials.authorize(Http())
    drive = build('drive', 'v3', http=http_auth)
    
    # FETCH TEMPLATE
    file_id = '1D2DyCUuUyqeGBA3tDZTa-pRZhBUfOPoPk64dCjG7UD8'
    drive_request = drive.files().export_media(fileId=file_id,
                                         mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, drive_request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()

    # GENERATE FILE
    filename = "{}-racun.docx".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print datetime.now()
    doc = DocxTemplate(fh)
    context = { 'racuni' : invoices }
    doc.render(context)
    doc.save(filename)

    # UPLOAD FILE
    file_metadata = {'name': filename, "parents" : ['11H0nuJ6YXSdxL9azPrppr56YVXL4LiPO']}

    media = MediaFileUpload(filename)
    file = drive.files().create(body=file_metadata,
                                media_body=media,
                                fields='id').execute()
    
    # STORE DATE
    if is_store_date:
        print "EXECUTE", [store_date] + installments
        cursor.execute("BEGIN")
        cursor.execute("""
            UPDATE agreement_pay_installment SET date_izpis = %s
            WHERE id_vrstica IN ({}) 
        """.format(','.join('%s' for _ in installments)), [store_date] + installments)
        cursor.execute("COMMIT")
    return render_to_response('invoices_done.html', {
        "file_id": file.get('id'),
        "file_name": filename
    }, context_instance=RequestContext(request))
