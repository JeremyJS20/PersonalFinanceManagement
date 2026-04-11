from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import Transaction, Category, Account, CutoffReport, Budget

class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(label=_("First name"), max_length=30, required=True, help_text=_('Required.'))
    last_name = forms.CharField(label=_("Last name"), max_length=30, required=True, help_text=_('Required.'))
    email = forms.EmailField(label=_("Email"), max_length=254, required=True, help_text=_('Required. Inform a valid email address.'))

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

class CutoffReportForm(forms.ModelForm):
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'pfm-input w-full h-12 px-4 rounded-lg bg-pfm-bg border border-pfm-border focus:border-pfm-primary focus:ring-2 focus:ring-pfm-primary/20 outline-none transition-all font-medium'
        })
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'pfm-input w-full h-12 px-4 rounded-lg bg-pfm-bg border border-pfm-border focus:border-pfm-primary focus:ring-2 focus:ring-pfm-primary/20 outline-none transition-all font-medium'
        })
    )

    class Meta:
        model = CutoffReport
        fields = ['name', 'start_date', 'end_date']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'pfm-input w-full h-12 px-4 rounded-lg bg-pfm-bg border border-pfm-border focus:border-pfm-primary focus:ring-2 focus:ring-pfm-primary/20 outline-none transition-all placeholder:text-pfm-text-light/50 font-medium',
                'placeholder': _('eg_monthly_cutoff_jan_2026')
            }),
        }

class TransactionForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'pfm-input w-full h-12 px-4 rounded-lg bg-pfm-bg border border-pfm-border focus:border-pfm-primary focus:ring-2 focus:ring-pfm-primary/20 outline-none transition-all font-medium'
        }),
        initial=timezone.now
    )

    class Meta:
        model = Transaction
        fields = ['date', 'description', 'category', 'account', 'amount']
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'pfm-input w-full h-12 px-4 rounded-lg bg-pfm-bg border border-pfm-border focus:border-pfm-primary focus:ring-2 focus:ring-pfm-primary/20 outline-none transition-all placeholder:text-pfm-text-light/50 font-medium',
                'placeholder': _('eg_grocery_shopping')
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'pfm-input w-full h-12 px-4 rounded-lg bg-pfm-bg border border-pfm-border focus:border-pfm-primary focus:ring-2 focus:ring-pfm-primary/20 outline-none transition-all font-medium',
                'placeholder': '0.00',
                'step': '0.01'
            }),
            'category': forms.Select(attrs={
                'class': 'pfm-input w-full h-12 px-4 rounded-lg bg-pfm-bg border border-pfm-border focus:border-pfm-primary focus:ring-2 focus:ring-pfm-primary/20 outline-none transition-all font-medium'
            }),
            'account': forms.Select(attrs={
                'class': 'pfm-input w-full h-12 px-4 rounded-lg bg-pfm-bg border border-pfm-border focus:border-pfm-primary focus:ring-2 focus:ring-pfm-primary/20 outline-none transition-all font-medium'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['category'].queryset = Category.objects.filter(group__user=user)
            self.fields['account'].queryset = Account.objects.filter(user=user)

class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['category', 'amount']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'pfm-input w-full h-12 px-4 rounded-lg bg-pfm-bg border border-pfm-border focus:border-pfm-primary focus:ring-2 focus:ring-pfm-primary/20 outline-none transition-all font-medium',
                'placeholder': '0.00',
                'step': '0.01'
            }),
            'category': forms.Select(attrs={
                'class': 'pfm-input w-full h-12 px-4 rounded-lg bg-pfm-bg border border-pfm-border focus:border-pfm-primary focus:ring-2 focus:ring-pfm-primary/20 outline-none transition-all font-medium'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            # Only show expense categories for budgets
            self.fields['category'].queryset = Category.objects.filter(group__user=user, group__transaction_type='expenses')
