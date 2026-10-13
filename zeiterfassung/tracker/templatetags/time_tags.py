from django import template
from tracker.services import duration
register=template.Library()
@register.filter
def hm(value): return duration(value or 0)
@register.filter
def signed(value): return duration(value or 0,True)
@register.filter
def tone(value): return 'negative' if value is not None and value<0 else 'positive'
@register.filter
def days_label(values):
    names=['Mo','Di','Mi','Do','Fr','Sa','So']
    return ', '.join(names[int(v)] for v in values)
