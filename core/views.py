from django.views.generic import TemplateView

class HomeView(TemplateView):
    template_name = 'development.html'

class DevelopmentView(TemplateView):
    template_name = 'development.html'

class ChartsView(TemplateView):
    template_name = 'development.html'

class OverviewView(TemplateView):
    template_name = 'development.html'

class SensorsView(TemplateView):
    template_name = 'development.html'

class VPDView(TemplateView):
    template_name = 'development.html'

class GaugesView(TemplateView):
    template_name = 'development.html'