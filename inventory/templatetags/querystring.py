from django import template
register = template.Library()

@register.simple_tag(takes_context=True)
def querystring(context, **kwargs):
    request = context['request']
    updated = request.GET.copy()
    for key, value in kwargs.items():
        updated[key] = value
    return '?' + updated.urlencode()