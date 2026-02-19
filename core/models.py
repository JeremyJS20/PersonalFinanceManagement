from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

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
