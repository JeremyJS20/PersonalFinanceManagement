from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from .forms import CustomUserCreationForm
from .models import CategoryGroup, Category

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        groups = CategoryGroup.objects.filter(user=self.request.user).prefetch_related('categories')
        context['expenses_groups'] = groups.filter(transaction_type='expenses')
        context['income_groups'] = groups.filter(transaction_type='income')
        
        # Determine active tab: Query Param > Cookie > Default (expenses)
        active_tab = self.request.GET.get('tab')
        if not active_tab:
            active_tab = self.request.COOKIES.get('pfm_last_category_tab', 'expenses')
            
        context['active_tab'] = active_tab

        # Calculate statistics
        total_categories = Category.objects.filter(group__user=self.request.user).count()
        context['total_categories'] = total_categories
        
        # Calculate progress percentage (arbitrary limit of 50 for visual representation)
        limit = 50
        context['categories_progress'] = min((total_categories / limit) * 100, 100) if limit > 0 else 0
        
        return context

class CategoryGroupCreateView(LoginRequiredMixin, CreateView):
    model = CategoryGroup
    fields = ['name', 'icon', 'transaction_type', 'description']
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        self.object = form.save()
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'group': {
                    'id': self.object.id,
                    'name': self.object.name,
                    'icon': self.object.icon,
                    'transaction_type': self.object.transaction_type,
                }
            })
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('categories')

class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    fields = ['group', 'name', 'icon', 'description']

    def form_valid(self, form):
        # Ensure the group belongs to the user
        if form.instance.group.user != self.request.user:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
        
        self.object = form.save()
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'category': {
                    'id': self.object.id,
                    'name': self.object.name,
                    'icon': self.object.icon,
                    'group_id': self.object.group.id,
                }
            })
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('categories')
