from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class CustomLoginView(LoginView):
    template_name = 'core/login.html'
    redirect_authenticated_user = True

class DashboardView(TemplateView):
    template_name = 'core/dashboard.html'
    # login_url = '/login/'
    # mixin LoginRequiredMixin later when auth is fully working
