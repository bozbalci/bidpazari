from django.views.generic.base import TemplateView


class WSClientView(TemplateView):
    template_name = 'core/ws_client.html'

    def get_context_data(self, **kwargs):
        return {'props': {'test': 42}}
