from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy

from .forms import CustomUserCreationForm

class CustomLoginView(LoginView):
    template_name = 'core/login.html'
    redirect_authenticated_user = True

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'
    login_url = '/login/'

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'core/signup.html'

class CategoriesView(LoginRequiredMixin, TemplateView):
    template_name = 'core/categories.html'
    login_url = reverse_lazy('login')
