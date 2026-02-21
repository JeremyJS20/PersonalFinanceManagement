from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView, CreateView, UpdateView, DeleteView
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

class CategoriesContextMixin:
    """Mixin to provide shared context for categories-related views."""
    def get_categories_context(self, user, active_tab=None):
        groups = CategoryGroup.objects.filter(user=user).prefetch_related('categories')
        
        # Determine active tab if not provided: Query Param > Cookie > Default
        if not active_tab:
            active_tab = self.request.GET.get('tab')
            if not active_tab:
                active_tab = self.request.COOKIES.get('pfm_last_category_tab', 'expenses')

        # Calculate statistics
        total_categories = Category.objects.filter(group__user=user).count()
        limit = 50
        categories_progress = min((total_categories / limit) * 100, 100) if limit > 0 else 0

        return {
            'expenses_groups': groups.filter(transaction_type='expenses'),
            'income_groups': groups.filter(transaction_type='income'),
            'active_tab': active_tab,
            'total_categories': total_categories,
            'categories_progress': categories_progress,
        }

class CategoriesView(LoginRequiredMixin, CategoriesContextMixin, TemplateView):
    template_name = 'core/categories.html'
    login_url = reverse_lazy('login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_categories_context(self.request.user))
        return context

class CategoryGroupCreateView(LoginRequiredMixin, CategoriesContextMixin, CreateView):
    model = CategoryGroup
    fields = ['name', 'icon', 'transaction_type', 'description']
    template_name = 'core/categories.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_categories_context(self.request.user))
        return context

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

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('categories')

class CategoryGroupUpdateView(LoginRequiredMixin, CategoriesContextMixin, UpdateView):
    model = CategoryGroup
    fields = ['name', 'icon', 'transaction_type', 'description']
    template_name = 'core/categories.html'
    
    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_categories_context(self.request.user))
        return context

    def form_valid(self, form):
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

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('categories')

class CategoryCreateView(LoginRequiredMixin, CategoriesContextMixin, CreateView):
    model = Category
    fields = ['group', 'name', 'icon', 'description']
    template_name = 'core/categories.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_categories_context(self.request.user))
        return context

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

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('categories')

class CategoryUpdateView(LoginRequiredMixin, CategoriesContextMixin, UpdateView):
    model = Category
    fields = ['group', 'name', 'icon', 'description']
    template_name = 'core/categories.html'
    
    def get_queryset(self):
        # Ensure user can only update their own categories
        return super().get_queryset().filter(group__user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_categories_context(self.request.user))
        return context

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

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('categories')

class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Category
    
    def get_queryset(self):
        # Ensure user can only delete their own categories
        return super().get_queryset().filter(group__user=self.request.user)

    def post(self, request, *args, **kwargs):
        """Handle POST request for deletion, often used by AJAX/fetch."""
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            self.object = self.get_object()
            self.object.delete()
            return JsonResponse({'status': 'success'})
        return self.delete(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """Standard DELETE method handling."""
        response = super().delete(request, *args, **kwargs)
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        return response

    def get_success_url(self):
        return reverse_lazy('categories')

class AccountsView(LoginRequiredMixin, TemplateView):
    template_name = 'core/accounts.html'
    login_url = reverse_lazy('login')
