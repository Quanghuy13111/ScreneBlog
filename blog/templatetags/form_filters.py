from django import template

register = template.Library()

@register.filter(name='attr')
def attr(field, css):
    attrs = {}
    for pair in css.split('|'):
        key, value = pair.split(':', 1)
        attrs[key.strip()] = value.strip()
    return field.as_widget(attrs=attrs)
