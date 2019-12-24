import re
from decimal import Decimal

from django import template
from django.conf import settings
from django.contrib.humanize.templatetags.humanize import intcomma
from django.template.defaultfilters import floatformat
from django.urls import NoReverseMatch, reverse

register = template.Library()


@register.inclusion_tag('core/item_widget.html', takes_context=True)
def item_widget(context):
    return {'item': context['item']}


@register.simple_tag(takes_context=True)
def active_url(context, url):
    try:
        pattern = f'^{reverse(url)}'
    except NoReverseMatch:
        pattern = url

    path = context['request'].path
    return "active" if re.search(pattern, path) else ""


@register.filter(name='money')
def money(value):
    try:
        value = Decimal(value)
    except (TypeError, ValueError):
        return 'N/A'
    minus = value < 0
    if minus:
        value = -value
    value = floatformat(value, arg=2)
    value = intcomma(value)
    if minus:
        return f'-${value}'
    return f'${value}'


@register.filter(name='bidding_strategy')
def humanize_bidding_strategy(value):
    return {
        'increment': 'Increment',
        'decrement': 'Decrement',
        'highest_contribution': 'Highest Contribution',
    }.get(value, 'Invalid')


@register.filter(name='item_image')
def item_image(value):
    static_url = settings.STATIC_URL
    media_url = settings.MEDIA_URL
    if not value:
        return f"{static_url}images/question.jpg"
    return f"{media_url}{value}"
