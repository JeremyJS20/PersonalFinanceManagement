from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from .forms import CustomUserCreationForm, TransactionForm
from .models import CategoryGroup, Category, Transaction, Account
from django.db.models import Sum, Q
from django.utils import timezone

class CustomLoginView(LoginView):
    template_name = 'core/login.html'
    redirect_authenticated_user = True

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

class AccountsContextMixin:
    """Mixin to provide shared context for accounts-related views."""
    def get_accounts_context(self, user, active_filter=None):
        accounts = Account.objects.filter(user=user)
        
        # Determine active filter if not provided: Query Param > Cookie > Default
        if not active_filter:
            active_filter = self.request.GET.get('filter')
            if not active_filter:
                active_filter = self.request.COOKIES.get('pfm_last_account_filter', 'all')

        # Categorize accounts
        assets_types = ['checking', 'savings', 'bank', 'brokerage', 'cash', 'real_estate', 'crypto']
        liabilities_types = ['credit', 'loan', 'mortgage', 'line_of_credit']
        
        banking_accounts = accounts.filter(type__in=['checking', 'savings', 'bank', 'cash'])
        investment_accounts = accounts.filter(type__in=['brokerage', 'crypto', 'real_estate'])
        liability_accounts = accounts.filter(type__in=liabilities_types)
        
        # Calculate totals
        total_assets = accounts.filter(type__in=assets_types, include_in_total=True).aggregate(total=Sum('balance'))['total'] or 0
        total_liabilities_sum = accounts.filter(type__in=liabilities_types, include_in_total=True).aggregate(total=Sum('balance'))['total'] or 0
        
        # liabilities are stored as negative numbers, so assets + liabilities = net worth
        total_balance = total_assets + total_liabilities_sum
        
        balance_percentage = 0
        if total_assets > 0:
            balance_percentage = (total_balance / total_assets) * 100
        
        return {
            'banking_accounts': banking_accounts,
            'investment_accounts': investment_accounts,
            'liability_accounts': liability_accounts,
            'total_assets': total_assets,
            'total_liabilities': abs(total_liabilities_sum),
            'total_balance': total_balance,
            'balance_percentage': balance_percentage,
            'active_filter': active_filter,
            'accounts': accounts,
        }

class DashboardView(LoginRequiredMixin, AccountsContextMixin, TemplateView):
    template_name = 'core/dashboard.html'
    login_url = '/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Use mixin for financial data
        context.update(self.get_accounts_context(self.request.user))
        
        # Add transactions
        context['recent_transactions'] = Transaction.objects.filter(
            user=self.request.user
        ).select_related('category', 'account').order_by('-date', '-created_at')[:5]
        
        # Add form
        context['transaction_form'] = TransactionForm(user=self.request.user)
        
        # Calculate budget summary (placeholder for now, can be sophisticated later)
        # For now, let's sum expenses for the current month
        now = timezone.now()
        monthly_expenses = Transaction.objects.filter(
            user=self.request.user,
            category__group__transaction_type='expenses',
            date__year=now.year,
            date__month=now.month
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        context['monthly_expenses'] = monthly_expenses
        context['budget_limit'] = 2500 # Hardcoded for now
        context['budget_percentage'] = min((monthly_expenses / 2500) * 100, 100) if 2500 > 0 else 0
        
        context['categories'] = Category.objects.filter(group__user=self.request.user)
        context['today'] = timezone.now()
        
        return context

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'core/signup.html'


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


class AccountsView(LoginRequiredMixin, AccountsContextMixin, TemplateView):
    template_name = 'core/accounts.html'
    login_url = reverse_lazy('login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_accounts_context(self.request.user))
        return context

class AccountCreateView(LoginRequiredMixin, AccountsContextMixin, CreateView):
    model = Account
    fields = ['name', 'type', 'balance', 'include_in_total', 'icon']
    template_name = 'core/accounts.html'
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        self.object = form.save()
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('accounts')

class AccountUpdateView(LoginRequiredMixin, AccountsContextMixin, UpdateView):
    model = Account
    fields = ['name', 'type', 'balance', 'include_in_total', 'icon']
    template_name = 'core/accounts.html'
    
    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)
    
    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('accounts')

class AccountDeleteView(LoginRequiredMixin, DeleteView):
    model = Account
    
    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        return JsonResponse({'status': 'success'})

    def get_success_url(self):
        return reverse_lazy('accounts')

class TransactionListView(LoginRequiredMixin, TemplateView):
    template_name = 'core/transactions.html'
    login_url = reverse_lazy('login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        transactions = Transaction.objects.filter(user=self.request.user).select_related('category', 'category__group', 'account')
        
        # Simple filtering logic
        search_query = self.request.GET.get('search')
        if search_query:
            transactions = transactions.filter(description__icontains=search_query)
        
        category_id = self.request.GET.get('category')
        if category_id:
            transactions = transactions.filter(category_id=category_id)

        account_id = self.request.GET.get('account')
        if account_id:
            transactions = transactions.filter(account_id=account_id)

        start_date = self.request.GET.get('start_date')
        if start_date:
            transactions = transactions.filter(date__gte=start_date)

        end_date = self.request.GET.get('end_date')
        if end_date:
            transactions = transactions.filter(date__lte=end_date)

        context['transactions'] = transactions
        context['has_filters'] = any([search_query, category_id, account_id, start_date, end_date])
        
        # Summary calculations (applying the same filters)
        summary_base = Transaction.objects.filter(user=self.request.user)
        if search_query:
            summary_base = summary_base.filter(description__icontains=search_query)
        if category_id:
            summary_base = summary_base.filter(category_id=category_id)
        if account_id:
            summary_base = summary_base.filter(account_id=account_id)
        if start_date:
            summary_base = summary_base.filter(date__gte=start_date)
        if end_date:
            summary_base = summary_base.filter(date__lte=end_date)

        total_income = summary_base.filter(
            category__group__transaction_type='income'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        total_expenses = summary_base.filter(
            category__group__transaction_type='expenses'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        context['total_income'] = total_income
        context['total_expenses'] = total_expenses
        context['net_flow'] = total_income - total_expenses

        categories = list(Category.objects.filter(group__user=self.request.user))
        for cat in categories:
            cat.is_selected = str(cat.id) == category_id
            
        context['categories'] = categories
        
        accounts = list(Account.objects.filter(user=self.request.user))
        for acc in accounts:
            acc.is_selected = str(acc.id) == account_id
            
        context['accounts'] = accounts
        context['transaction_form'] = TransactionForm(user=self.request.user)
        context['today'] = timezone.now()
        
        return context

class TransactionCreateView(LoginRequiredMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        self.object = form.save()
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'transaction': {
                    'id': self.object.id,
                    'description': self.object.description,
                    'amount': str(self.object.amount),
                    'date': self.object.date.strftime('%Y-%m-%d'),
                    'category': self.object.category.name,
                }
            })
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('dashboard')
