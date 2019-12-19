from django import template

register = template.Library()


@register.inclusion_tag('core/legacy/item_widget.html', takes_context=True)
def item_widget(context):
    return {'item': context['item']}
