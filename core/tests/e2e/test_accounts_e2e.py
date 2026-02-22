import pytest
from playwright.sync_api import Page, expect
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import Account
import os

@pytest.fixture
def test_user(db):
    """Fixture to create a test user."""
    return User.objects.create_user(username='tester', password='password123')

@pytest.fixture
def logged_in_page(page: Page, live_server, test_user):
    """Fixture to provide a logged-in page."""
    page.goto(live_server.url + reverse('login'))
    page.wait_for_load_state("networkidle")
    page.fill('#username', 'tester')
    page.fill('#password', 'password123')
    page.click('button[type="submit"]')
    expect(page).to_have_url(live_server.url + reverse('dashboard'))
    return page

@pytest.mark.django_db(transaction=True)
def test_accounts_page_navigation(logged_in_page: Page, live_server):
    """Test navigation to accounts page and automatic URL sync."""
    page = logged_in_page
    page.click('a:has-text("Accounts")')
    # Verify URL automatically syncs to include filter parameter
    expect(page).to_have_url(live_server.url + reverse('accounts') + "?filter=all")
    expect(page.locator('h1')).to_contain_text('Accounts')

@pytest.mark.django_db(transaction=True)
def test_accounts_filtering(logged_in_page: Page, live_server, test_user):
    """Test filtering accounts by assets/liabilities."""
    page = logged_in_page
    
    # Create an asset and a liability for testing
    Account.objects.create(user=test_user, name='Asset Acc', type='checking', balance=100.0, icon='university')
    Account.objects.create(user=test_user, name='Debt Acc', type='credit', balance=50.0, icon='credit-card')
    
    page.goto(live_server.url + reverse('accounts'))
    
    # Assets Filter
    page.click('button[data-account-filter="assets"]')
    expect(page).to_have_url(live_server.url + reverse('accounts') + "?filter=assets")
    expect(page.locator('text=Asset Acc')).to_be_visible()
    expect(page.locator('text=Debt Acc')).not_to_be_visible()
    
    # Liabilities Filter
    page.click('button[data-account-filter="liabilities"]')
    expect(page).to_have_url(live_server.url + reverse('accounts') + "?filter=liabilities")
    expect(page.locator('text=Debt Acc')).to_be_visible()
    expect(page.locator('text=Asset Acc')).not_to_be_visible()

@pytest.mark.django_db(transaction=True)
def test_accounts_persistence(logged_in_page: Page, live_server):
    """Test that selected filter persists after page reload."""
    page = logged_in_page
    page.goto(live_server.url + reverse('accounts'))
    
    # Click Liabilities
    page.click('button[data-account-filter="liabilities"]')
    expect(page).to_have_url(live_server.url + reverse('accounts') + "?filter=liabilities")
    
    # Reload
    page.reload()
    expect(page).to_have_url(live_server.url + reverse('accounts') + "?filter=liabilities")

@pytest.mark.django_db(transaction=True)
def test_accounts_crud(logged_in_page: Page, live_server, test_user):
    """Test Create, Update, and Delete operations for an account."""
    page = logged_in_page
    page.goto(live_server.url + reverse('accounts'))
    
    # 1. Create
    page.click('button:has-text("Add Account")')
    page.fill('#account-name', 'New Account')
    page.select_option('#account-type', 'checking')
    page.fill('#account-balance', '1000.00')
    
    # Wait for icons to be rendered and visible
    icon_btn = page.locator('.icon-option[data-icon="landmark"]')
    expect(icon_btn).to_be_visible()
    icon_btn.click()
    
    # Submit
    page.click('#modal-submit-account')
    
    # Use exact=True to avoid matching "Add New Account" or modal descriptions
    expect(page.get_by_text("New Account", exact=True)).to_be_visible()
    
    # 2. Update
    # Use a more resilient Playwright filter to find the account container
    account_row = page.locator('.group').filter(has_text="New Account")
    account_row.locator('.modal-open-btn[data-pfm-bind-mode="edit"]').click()
    
    page.fill('#account-name', 'Updated Name')
    page.click('#modal-submit-account')
    expect(page.get_by_text("Updated Name", exact=True)).to_be_visible()
    
    # 3. Delete
    # Filter for the updated name
    updated_row = page.locator('.group').filter(has_text="Updated Name")
    updated_row.locator('.modal-open-btn[data-pfm-modal-target="delete-account-modal"]').click()
    
    page.click('#confirm-delete-account-btn')
    expect(page.get_by_text("Updated Name", exact=True)).not_to_be_visible()

@pytest.mark.django_db(transaction=True)
def test_accounts_full_workflow(logged_in_page: Page, live_server, test_user):
    """
    A single test that runs through the complete user journey:
    Navigation -> Filtering -> CRUD -> Persistence
    """
    page = logged_in_page
    
    # 1. Navigation
    page.click('a:has-text("Accounts")')
    expect(page).to_have_url(live_server.url + reverse('accounts') + "?filter=all")
    
    # 2. CRUD - Create
    page.click('button:has-text("Add Account")')
    page.fill('#account-name', 'Journey Account')
    page.select_option('#account-type', 'checking')
    page.fill('#account-balance', '5000.00')
    icon_btn = page.locator('.icon-option[data-icon="landmark"]')
    icon_btn.click()
    page.click('#modal-submit-account')
    expect(page.get_by_text("Journey Account", exact=True)).to_be_visible()
    
    # 3. Filtering
    page.click('button[data-account-filter="assets"]')
    expect(page.locator('.group').filter(has_text="Journey Account")).to_be_visible()
    
    page.click('button[data-account-filter="liabilities"]')
    expect(page.locator('.group').filter(has_text="Journey Account")).not_to_be_visible()
    
    # 4. Persistence
    page.reload()
    expect(page).to_have_url(live_server.url + reverse('accounts') + "?filter=liabilities")
    
    # 5. CRUD - Update
    page.click('button[data-account-filter="all"]')
    row = page.locator('.group').filter(has_text="Journey Account")
    row.locator('.modal-open-btn[data-pfm-bind-mode="edit"]').click()
    page.fill('#account-name', 'Final Name')
    page.click('#modal-submit-account')
    expect(page.get_by_text("Final Name", exact=True)).to_be_visible()
    
    # 6. CRUD - Delete
    final_row = page.locator('.group').filter(has_text="Final Name")
    final_row.locator('.modal-open-btn[data-pfm-modal-target="delete-account-modal"]').click()
    page.click('#confirm-delete-account-btn')
    expect(page.get_by_text("Final Name", exact=True)).not_to_be_visible()
