from django.db import connection
import time

def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]

def clear_banks():
    cursor = connection.cursor()
    sql = "DELETE FROM sfr_bank"
    cursor.execute(sql)
    cursor.execute("COMMIT")

def add_bank(bank):
    cursor = connection.cursor()
    sql = "INSERT INTO sfr_bank (bank_name, sifra_banke, bank_tn, bic) VALUES(%s, %s, %s, %s)"
    bank[1] = "%02d" % int(bank[1])
    bank[2] = bank[2].replace("SI56", "").replace(" ", "")
    bank[3] = bank[3].replace(" ", "")
    cursor.execute(sql,bank)
    cursor.execute("COMMIT")


def get_payments_list(*args):
    
    cursor = connection.cursor()
    
    sql = "SELECT a.*, p.*, pr.name_project, b.bic, trr.id_trr "\
        + "FROM agreement_pay_installment as p, sfr_agreement as a, sfr_bank as b, sfr_project as pr "\
        + "JOIN sfr_project_trr as trr ON trr.id_vrstica = "\
        + "   (SELECT id_vrstica FROM sfr_project_trr WHERE id_project = pr.id_project LIMIT 1)  "\
        + "WHERE p.id_agreement = a.id_agreement AND p.pay_type='04' "\
        + "  AND pr.id_project = a.id_project AND trr.id_project = a.id_project "\
        + "  AND b.sifra_banke ILIKE a.sifra_banke || '%%' "\
        + "  AND (p.amount_payed IS NULL OR p.amount > p.amount_payed)"\
        + "  AND p.storno IS NULL"
    
    if len(args) == 1:
        sql += "  AND p.id_vrstica = %s "
        cursor.execute(sql  + "ORDER BY a.sifra_banke", args)
        return dictfetchall(cursor)
    else:
        sql += "  AND p.date_activate = %s AND a.id_project = %s "
    
    
    result = {"OOFF":[], "FRST":[], "RCUR":[], "FNAL": []}

    ooff = sql + "  AND 1 = (SELECT COUNT(*) FROM agreement_pay_installment WHERE id_agreement = a.id_agreement)  "
    cursor.execute(ooff + "ORDER BY a.sifra_banke", args)
    result["OOFF"] = dictfetchall(cursor)
    
    frst = sql + "  AND 1 < (SELECT COUNT(*) FROM agreement_pay_installment WHERE id_agreement = a.id_agreement)  "\
               + "  AND installment_nr = 1 "
    cursor.execute(frst + "ORDER BY a.sifra_banke", args)
    result["FRST"] = dictfetchall(cursor)
    
    rcur = sql + "  AND installment_nr < (SELECT COUNT(*) FROM agreement_pay_installment WHERE id_agreement = a.id_agreement)  "\
               + " AND installment_nr > 1 "
    cursor.execute(rcur + "ORDER BY a.sifra_banke", args)
    result["RCUR"] = dictfetchall(cursor)
    
    if args[0] == "2013-1-18":
        result["FRST"] += result["RCUR"]
        result["RCUR"] = []
    
    fnal = sql + "  AND installment_nr = (SELECT COUNT(*) FROM agreement_pay_installment WHERE id_agreement = a.id_agreement)  "\
               + "  AND 1 < (SELECT COUNT(*) FROM agreement_pay_installment WHERE id_agreement = a.id_agreement)"
    cursor.execute(fnal + "ORDER BY a.sifra_banke", args)
    result["FNAL"] = dictfetchall(cursor)
    
    cursor.execute(sql, args)
    return result
    
def get_available_approvals():
    cursor = connection.cursor()
    sql = "SELECT * FROM approvals WHERE available = TRUE"
    cursor.execute(sql)
    return [a['approval'] for a in dictfetchall(cursor)]

def generate_approvals(num):
    cursor = connection.cursor()
    approvals = []
    cursor.execute("BEGIN")
    for v in range(num):
        a = (time.strftime("%Y%m%d%H%M%S", time.localtime()) + ("%03d" % (v+1)))
        cursor.execute("INSERT INTO approvals (approval, available) VALUES (%s, TRUE)", (a,))
        approvals.append(a)
    cursor.execute("COMMIT")
    return approvals
