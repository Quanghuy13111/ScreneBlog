from django import template
from django.forms.boundfield import BoundField
import re

register = template.Library()

@register.filter(name='attr')
def attr(field, attribute_string):
    if isinstance(field, BoundField):
        attrs = {}
        # A robust regex to parse attributes. It looks for a key followed by a colon,
        # then captures everything until it hits the next key (or the end of the string).
        # This correctly handles values with colons, like in the 'style' attribute.
        for key, value in re.findall(r'(\w+):((?:(?! \w+:).)*)', attribute_string):
            attrs[key] = value.strip()
        return field.as_widget(attrs=attrs)
    else:
        # If it's not a BoundField, return the original field value to prevent AttributeError
        return field
