'''
Created on Nov 2, 2012

@author: smotko
'''

from lxml.etree import tostring 
from lxml.builder import E

if __name__ == '__main__':
    print tostring(E.results(E.country(name='neki')), pretty_print = True, xml_declaration=True, encoding='UTF-8')