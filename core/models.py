from django.db import models, transaction
from django.db.models import F
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class CategoryGroup(models.Model):
    TRANSACTION_TYPES = [
        ('expenses', _('Expenses')),
        ('income', _('Income')),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='category_groups')
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, default='folder')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, default='expenses')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Category Group')
        verbose_name_plural = _('Category Groups')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_transaction_type_display()})"

class Category(models.Model):
    group = models.ForeignKey(CategoryGroup, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, default='tag')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')
        ordering = ['name']

    def __str__(self):
        return self.name

class Account(models.Model):
    ACCOUNT_TYPES = [
        ('checking', _('Checking')),
        ('savings', _('Savings')),
        ('bank', _('Bank')),
        ('brokerage', _('Brokerage')),
        ('cash', _('Cash')),
        ('real_estate', _('Real Estate')),
        ('crypto', _('Crypto')),
        ('credit', _('Credit Card')),
        ('loan', _('Loan')),
        ('mortgage', _('Mortgage')),
        ('line_of_credit', _('Line of Credit')),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='accounts')
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    include_in_total = models.BooleanField(default=True)
    icon = models.CharField(max_length=50, default='landmark')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Account')
        verbose_name_plural = _('Accounts')
        ordering = ['name']

    def __str__(self):
        return self.name

class Transaction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255)
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Transaction')
        verbose_name_plural = _('Transactions')
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.description} ({self.amount})"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            is_new = self.pk is None
            
            if not is_new:
                # Revert the old transaction's effect on its account
                old_tx = Transaction.objects.select_related('category__group', 'account').get(pk=self.pk)
                if old_tx.account:
                    factor = 1 if old_tx.category.group.transaction_type == 'income' else -1
                    Account.objects.filter(pk=old_tx.account.pk).update(balance=F('balance') - (old_tx.amount * factor))

            super().save(*args, **kwargs)
            
            # Apply the new transaction's effect
            if self.account:
                # Ensure we have the latest type
                factor = 1 if self.category.group.transaction_type == 'income' else -1
                Account.objects.filter(pk=self.account.pk).update(balance=F('balance') + (self.amount * factor))
                # Refresh current account instance balance if needed (for immediate use in view)
                self.account.refresh_from_db(fields=['balance'])

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            if self.account:
                factor = 1 if self.category.group.transaction_type == 'income' else -1
                Account.objects.filter(pk=self.account.pk).update(balance=F('balance') - (self.amount * factor))
                
            super().delete(*args, **kwargs)
