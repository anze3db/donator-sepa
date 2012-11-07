'''
Created on Nov 2, 2012

@author: smotko
'''

from lxml.etree import tostring 
from lxml.builder import E
import psycopg2

if __name__ == '__main__':
    
    
    DSN = 'dbname=donator user=postgres host=192.168.56.101 port=5432' # dbname=donator;host=127.0.0.1;port=5432;
    
    print "Opening connection using dns:", DSN
    conn1 = psycopg2.connect(DSN)
    curs1 = conn1.cursor()
    
    curs1.execute("SELECT * FROM sfr_agreement LIMIT 10;")
    rows = curs1.fetchall()
    for r in rows:
        print r
    print tostring(E.results(E.country(name='neki')), pretty_print = True, xml_declaration=True, encoding='UTF-8')