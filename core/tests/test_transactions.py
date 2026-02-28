from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import Category, CategoryGroup, Transaction, Account
from decimal import Decimal

class TransactionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client = Client()
        self.client.login(username='testuser', password='password123')
        
        self.group = CategoryGroup.objects.create(
            user=self.user,
            name='Test Group',
            transaction_type='expenses'
        )
        self.category = Category.objects.create(
            group=self.group,
            name='Test Category'
        )
        self.account = Account.objects.create(
            user=self.user,
            name='Test Account',
            type='checking',
            balance=Decimal('1000.00')
        )

    def test_transaction_creation(self):
        url = reverse('transaction_create')
        data = {
            'description': 'Test Transaction',
            'amount': '50.00',
            'category': self.category.id,
            'account': self.account.id,
            'date': '2023-01-01'
        }
        
        # Test AJAX creation
        response = self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        
        # Verify transaction in DB
        transaction = Transaction.objects.get(description='Test Transaction')
        self.assertEqual(transaction.amount, Decimal('50.00'))
        self.assertEqual(transaction.user, self.user)
        self.assertEqual(transaction.category, self.category)
        self.assertEqual(transaction.account, self.account)

    def test_transaction_list_view(self):
        Transaction.objects.create(
            user=self.user,
            category=self.category,
            account=self.account,
            amount=Decimal('10.00'),
            description='List Test',
            date='2023-01-01'
        )
        
        url = reverse('transactions')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'List Test')
        self.assertIn('transactions', response.context)
        self.assertEqual(len(response.context['transactions']), 1)

    def test_category_protection(self):
        Transaction.objects.create(
            user=self.user,
            category=self.category,
            account=self.account,
            amount=Decimal('10.00'),
            description='Protection Test'
        )
        
        # Try to delete category
        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            self.category.delete()
