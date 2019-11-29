from django.views.generic.base import TemplateView


class TCPClientView(TemplateView):
    template_name = 'core/tcp_client.html'
