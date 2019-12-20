import re

from django import template
from django.urls import NoReverseMatch, reverse

register = template.Library()


@register.inclusion_tag('core/item_widget.html', takes_context=True)
def item_widget(context):
    return {'item': context['item']}


@register.simple_tag(takes_context=True)
def active_url(context, url):
    try:
        pattern = f'^{reverse(url)}$'
    except NoReverseMatch:
        pattern = url

    path = context['request'].path
    return "active" if re.search(pattern, path) else ""
