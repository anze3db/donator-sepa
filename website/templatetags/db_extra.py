from django import template

register = template.Library()

def pretty_name(value):
    if value == "FRST":
        return "Prvi obrok"
    elif value == "LAST":
        return "Zadnji obrok"
    elif value == "RCUR":
        return "Vmesni obrok"
    elif value == "OOFF":
        return "Edini obrok"
    
    
register.filter('pretty_name', pretty_name)
