# Create your views here.
from django.http import HttpResponse
from lxml.etree import tostring 
from lxml.builder import E
from django.db import connection
from django.shortcuts import render_to_response

def index(request):

    cursor = connection.cursor()

    # Data retrieval operation - no commit required
    cursor.execute("SELECT * FROM sfr_agreement LIMIT 10;")
    rows = cursor.fetchall()
    for r in rows:
        print r
    return render_to_response('index.html', {'hello': "aaa",})
