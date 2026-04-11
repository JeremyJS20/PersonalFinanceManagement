from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from .forms import CustomUserCreationForm, TransactionForm, CutoffReportForm, BudgetForm
from .models import CategoryGroup, Category, Transaction, Account, CutoffReport, Budget
from django.db.models import Sum, Q, F
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.generic import TemplateView, CreateView, UpdateView, DeleteView, ListView, DetailView
from django.views import View
from django.utils.translation import gettext as _

import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.legends import Legend
import decimal

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

        # Fetch current monthly budgets
        now = timezone.now()
        budgets = Budget.objects.filter(user=user, month=now.month, year=now.year)
        budget_map = {b.category_id: float(b.amount) for b in budgets}

        # Attach budgets to categories and calculate group totals
        # Convert to list first to ensure attached attributes persist after filtering
        groups_list = list(groups)
        for group in groups_list:
            group.group_budget_total = 0
            for cat in group.categories.all():
                cat.current_budget = budget_map.get(cat.id, 0)
                group.group_budget_total += cat.current_budget

        return {
            'expenses_groups': [g for g in groups_list if g.transaction_type == 'expenses'],
            'income_groups': [g for g in groups_list if g.transaction_type == 'income'],
            'active_tab': active_tab,
            'total_categories': total_categories,
            'categories_progress': categories_progress,
            'budget_map': budget_map,
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
        user = self.request.user
        context.update(self.get_accounts_context(user))
        
        # Add transactions
        context['recent_transactions'] = Transaction.objects.filter(
            user=user
        ).select_related('category', 'category__group', 'account').order_by('-date', '-created_at')[:5]
        
        # Forms
        context['transaction_form'] = TransactionForm(user=user)
        context['budget_form'] = BudgetForm(user=user)
        
        # Calculate budget summary based on Category Budgets
        now = timezone.now()
        budgets = Budget.objects.filter(user=user, month=now.month, year=now.year)
        
        total_budget_limit = budgets.aggregate(total=Sum('amount'))['total'] or 0
        
        # Calculate actual spending for categories with budgets
        actual_spending_on_budgeted = Transaction.objects.filter(
            user=user,
            date__year=now.year,
            date__month=now.month,
            category__in=budgets.values_list('category', flat=True)
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Total monthly expenses
        total_monthly_expenses = Transaction.objects.filter(
            user=user,
            category__group__transaction_type='expenses',
            date__year=now.year,
            date__month=now.month,
        ).aggregate(total=Sum('amount'))['total'] or 0

        context['monthly_expenses'] = total_monthly_expenses
        context['budget_limit'] = total_budget_limit
        
        if total_budget_limit > 0:
            context['budget_percentage'] = min((actual_spending_on_budgeted / total_budget_limit) * 100, 100)
        else:
            context['budget_percentage'] = 0
            
        context['categories'] = Category.objects.filter(group__user=user)
        context['category_budgets'] = budgets.select_related('category')
        context['today'] = timezone.now()
        
        return context

class DashboardChartsView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        user = request.user
        now = timezone.now()
        
        # 1. Income vs Expense (Last 6 months)
        months = []
        income_data = []
        expense_data = []
        
        for i in range(5, -1, -1):
            # Calculate month/year correctly to avoid day arithmetic issues
            m = now.month - i
            y = now.year
            while m <= 0:
                m += 12
                y -= 1
            
            from datetime import date
            month_label = date(y, m, 1).strftime('%b')
            months.append(month_label)
            
            inc = Transaction.objects.filter(user=user, date__year=y, date__month=m, category__group__transaction_type='income').aggregate(total=Sum('amount'))['total'] or 0
            exp = Transaction.objects.filter(user=user, date__year=y, date__month=m, category__group__transaction_type='expenses').aggregate(total=Sum('amount'))['total'] or 0
            
            income_data.append(float(inc))
            expense_data.append(float(exp))
            
        # 2. Category Breakdown (Current Month)
        categories = []
        spending = []
        cat_data = Transaction.objects.filter(
            user=user, 
            date__year=now.year, 
            date__month=now.month, 
            category__group__transaction_type='expenses'
        ).values('category__name').annotate(total=Sum('amount')).order_by('-total')
        
        for item in cat_data:
            categories.append(item['category__name'])
            spending.append(float(item['total']))

        # 3. Net Worth Trend (Simplified for now - balance of accounts over time is complex without snapshots)
        # We'll use a simulated growth based on income/expense history or just current distribution
        
        return JsonResponse({
            'months': months,
            'income': income_data,
            'expense': expense_data,
            'categories': categories,
            'spending': spending
        })

class SetBudgetView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        user = request.user
        now = timezone.now()
        category_id = request.POST.get('category')
        amount = request.POST.get('amount')
        
        if not category_id or not amount:
            return JsonResponse({'status': 'error', 'message': 'Missing data'}, status=400)
            
        category = get_object_or_404(Category, id=category_id, group__user=user)
        
        budget, created = Budget.objects.update_or_create(
            user=user,
            category=category,
            month=now.month,
            year=now.year,
            defaults={'amount': amount}
        )
        
        return JsonResponse({'status': 'success', 'created': created})

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

class ReportListView(LoginRequiredMixin, TemplateView):
    template_name = 'core/reports.html'
    login_url = reverse_lazy('login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['reports'] = CutoffReport.objects.filter(user=self.request.user).order_by('-end_date')
        context['report_form'] = CutoffReportForm()
        return context

class PerformCutoffView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = CutoffReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.user = request.user
            
            # Aggregate totals for the selected period
            txs = Transaction.objects.filter(
                user=request.user,
                date__gte=report.start_date,
                date__lte=report.end_date
            )
            
            report.income_total = txs.filter(
                category__group__transaction_type='income'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            report.expense_total = txs.filter(
                category__group__transaction_type='expenses'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Calculate starting balance (balance before start_date)
            # This is tricky with our current model because balance is stored on Account.
            # We'd need a snapshot mechanism. For now, we'll calculate it by subtracting
            # all transactions from the current balance back to the start date.
            
            current_total_balance = Account.objects.filter(
                user=request.user, 
                include_in_total=True
            ).aggregate(total=Sum('balance'))['total'] or 0
            
            # Sum of all transactions after end_date (to get balance AT end_date)
            later_txs = Transaction.objects.filter(
                user=request.user,
                account__include_in_total=True,
                date__gt=report.end_date
            )
            
            later_income = later_txs.filter(category__group__transaction_type='income').aggregate(total=Sum('amount'))['total'] or 0
            later_expense = later_txs.filter(category__group__transaction_type='expenses').aggregate(total=Sum('amount'))['total'] or 0
            
            # Balance at end_date = Current Balance - (Later Income - Later Expenses)
            report.ending_balance = current_total_balance - (later_income - later_expense)
            
            # Starting balance = Ending Balance - (Period Income - Period Expenses)
            report.starting_balance = report.ending_balance - (report.income_total - report.expense_total)
            
            report.save()
            return redirect('report_detail', pk=report.pk)
        
        return redirect('reports')

class ReportDetailView(LoginRequiredMixin, DetailView):
    model = CutoffReport
    template_name = 'core/report_detail.html'
    context_object_name = 'report'

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Category breakdown for the report period
        report = self.get_object()
        txs = Transaction.objects.filter(
            user=self.request.user,
            date__gte=report.start_date,
            date__lte=report.end_date
        ).select_related('category', 'category__group')
        
        expenses_breakdown = txs.filter(
            category__group__transaction_type='expenses'
        ).values('category__name').annotate(total=Sum('amount')).order_by('-total')
        
        income_breakdown = txs.filter(
            category__group__transaction_type='income'
        ).values('category__name').annotate(total=Sum('amount')).order_by('-total')
        
        context['expenses_breakdown'] = expenses_breakdown
        context['income_breakdown'] = income_breakdown
        context['transactions'] = txs.order_by('-date')
        return context

class ToggleReportLockView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        report = get_object_or_404(CutoffReport, pk=pk, user=request.user)
        report.is_locked = not report.is_locked
        report.save()
        return JsonResponse({
            'status': 'success',
            'is_locked': report.is_locked
        })

class DownloadReportPDFView(LoginRequiredMixin, View):
    def get(self, request, pk, *args, **kwargs):
        report = get_object_or_404(CutoffReport, pk=pk, user=request.user)
        
        # Color Palette
        PRIMARY_TEAL = HexColor('#0d9488')
        SECONDARY_TEAL = HexColor('#14b8a6')
        BG_MUTED = HexColor('#f8fafc')
        BORDER_COLOR = HexColor('#e2e8f0')
        TEXT_DARK = HexColor('#0f172a')
        TEXT_LIGHT = HexColor('#64748b')
        SUCCESS_GREEN = HexColor('#10b981')
        DANGER_RED = HexColor('#ef4444')

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, 
                               rightMargin=40, leftMargin=40, 
                               topMargin=40, bottomMargin=40)
        elements = []
        
        styles = getSampleStyleSheet()
        
        # Custom Styles
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=26,
            textColor=TEXT_DARK,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=TEXT_LIGHT,
            spaceAfter=24,
            textTransform='uppercase',
            letterSpacing=1
        )
        
        card_label_style = ParagraphStyle(
            'CardLabel',
            fontSize=8,
            textColor=TEXT_LIGHT,
            fontName='Helvetica-Bold',
            textTransform='uppercase',
            alignment=1 # Center
        )
        
        card_value_style = ParagraphStyle(
            'CardValue',
            fontSize=16,
            textColor=TEXT_DARK,
            fontName='Helvetica-Bold',
            alignment=1
        )
        
        section_header_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=TEXT_DARK,
            spaceBefore=20,
            spaceAfter=12,
            fontName='Helvetica-Bold'
        )

        # 1. Header Section
        elements.append(Paragraph(report.name or _("Cutoff Report"), title_style))
        elements.append(Paragraph(f"{report.start_date} — {report.end_date}", subtitle_style))
        
        # 2. Executive Summary Cards (Simulated with Table)
        savings = report.income_total - report.expense_total
        summary_data = [
            [
                Paragraph(_("total_income"), card_label_style),
                Paragraph(_("total_expenses"), card_label_style),
                Paragraph(_("net_savings"), card_label_style),
                Paragraph(_("ending_balance"), card_label_style)
            ],
            [
                Paragraph(f"+${report.income_total:,.2f}", ParagraphStyle('V1', parent=card_value_style, textColor=SUCCESS_GREEN)),
                Paragraph(f"-${report.expense_total:,.2f}", ParagraphStyle('V2', parent=card_value_style, textColor=DANGER_RED)),
                Paragraph(f"${savings:,.2f}", card_value_style),
                Paragraph(f"${report.ending_balance:,.2f}", card_value_style)
            ]
        ]
        
        summary_table = Table(summary_data, colWidths=[135, 135, 135, 135])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), BG_MUTED),
            ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, 0), 15),
            ('BOTTOMPADDING', (0, 1), (-1, 1), 15),
            ('LINEAFTER', (0, 0), (2, -1), 1, BORDER_COLOR), # Vertical dividers
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 30))

        # 3. Expense Breakdown & Pie Chart
        elements.append(Paragraph(_("expense_breakdown"), section_header_style))
        
        txs_breakdown = Transaction.objects.filter(
            user=request.user,
            date__gte=report.start_date,
            date__lte=report.end_date,
            category__group__transaction_type='expenses'
        ).values('category__name').annotate(total=Sum('amount')).order_by('-total')

        if txs_breakdown.exists():
            # Create Data for Chart
            data = [float(item['total']) for item in txs_breakdown[:7]]
            labels = [item['category__name'] for item in txs_breakdown[:7]]
            
            # Handle "Other" if more than 7 categories
            if txs_breakdown.count() > 7:
                others_sum = sum(float(item['total']) for item in txs_breakdown[7:])
                data.append(others_sum)
                labels.append(_("Others"))

            # Drawing for Pie Chart
            d = Drawing(width=500, height=200)
            pc = Pie()
            pc.x = 20
            pc.y = 25
            pc.width = 150
            pc.height = 150
            pc.data = data
            pc.labels = labels
            pc.sideLabels = True
            pc.slices.strokeWidth = 0.5
            pc.slices.strokeColor = colors.white
            
            # Color cycle for slices
            chart_colors = [PRIMARY_TEAL, SECONDARY_TEAL, HexColor('#2dd4bf'), HexColor('#5eead4'), HexColor('#99f6e4'), HexColor('#ccfbf1')]
            for i, val in enumerate(data):
                pc.slices[i].fillColor = chart_colors[i % len(chart_colors)]

            # Add Legend
            legend = Legend()
            legend.x = 220
            legend.y = 160
            legend.dx = 10
            legend.dy = 10
            legend.fontName = 'Helvetica'
            legend.fontSize = 9
            legend.columnMaximum = 10
            legend.alignment = 'right'
            
            legend_data = []
            for i, label in enumerate(labels):
                legend_data.append((pc.slices[i].fillColor, label))
            legend.colorNamePairs = legend_data
            
            d.add(pc)
            d.add(legend)
            
            elements.append(d)
        else:
            elements.append(Paragraph(_("no_expenses_in_period"), styles["Italic"]))

        elements.append(Spacer(1, 20))

        # 4. Detailed Transaction Table
        elements.append(Paragraph(_("period_transactions"), section_header_style))
        
        detail_txs = Transaction.objects.filter(
            user=request.user,
            date__gte=report.start_date,
            date__lte=report.end_date
        ).select_related('category', 'category__group').order_by('date')

        table_data = [[_("date"), _("description"), _("category"), _("amount")]]
        for tx in detail_txs:
            color = SUCCESS_GREEN if tx.category.group.transaction_type == 'income' else TEXT_DARK
            prefix = "+" if tx.category.group.transaction_type == 'income' else "-"
            table_data.append([
                tx.date.strftime('%Y-%m-%d'),
                tx.description,
                tx.category.name,
                Paragraph(f"{prefix}${tx.amount:,.2f}", ParagraphStyle('Amt', fontSize=9, textColor=color, alignment=2))
            ])

        if detail_txs.exists():
            table = Table(table_data, colWidths=[80, 220, 140, 90])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('TEXTCOLOR', (0, 0), (-1, 0), TEXT_DARK),
                ('BACKGROUND', (0, 0), (-1, 0), BG_MUTED),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_MUTED]),
                ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
                ('LINEBELOW', (0, 0), (-1, 0), 1, BORDER_COLOR),
            ]))
            elements.append(table)
        else:
            elements.append(Paragraph(_("No transactions found for this period."), styles["Italic"]))

        doc.build(elements)
        
        buffer.seek(0)
        formatted_date = report.end_date.strftime('%Y_%m')
        filename = f"FinOrbit_Report_{formatted_date}.pdf"
        return HttpResponse(buffer, content_type='application/pdf', headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        })
