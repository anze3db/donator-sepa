from django.db import connection

def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]


def get_payments_list(date, project):
    
    cursor = connection.cursor()
    
    sql = "SELECT p.*, a.bank_account2, a.frequency, a.sifra_banke, a.id_agreement "\
        + "FROM agreement_pay_installment as p, sfr_agreement as a, sfr_project as pr "\
        + "JOIN sfr_project_trr as trr ON trr.id_vrstica = (SELECT id_vrstica FROM sfr_project_trr WHERE id_project = %s LIMIT 1)  "\
        + "WHERE p.id_agreement = a.id_agreement AND p.date_activate = %s AND p.pay_type='04' "\
        + "  AND a.id_project = %s AND pr.id_project = a.id_project AND trr.id_project = a.id_project "\
        + "ORDER BY a.sifra_banke"
        #+ "  AND a.id_project = CAST (pr.id_project AS integer) AND a.id_project = trr.id_project "\
    #"SELECT * FROM sfr_project as p, sfr_project_trr as trr WHERE p.id_project = ? AND trr.id_project = ?"
    # trr banke
    # "SELECT * FROM sfr_bank WHERE sifra_banke ILIKE '$sifraBanke%'";
    cursor.execute(sql, (project, date, project))
    return dictfetchall(cursor)
    
