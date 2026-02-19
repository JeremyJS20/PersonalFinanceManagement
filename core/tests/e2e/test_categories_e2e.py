import pytest
from playwright.sync_api import Page, expect
from django.urls import reverse
from django.contrib.auth.models import User

import os

@pytest.mark.django_db(transaction=True)
def test_categories_page_e2e(page: Page, live_server):
    os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
    # Create user inside the test marked with transaction=True
    user = User.objects.create_user(username='e2e_user', password='password123')
    
    # Log in manually through the UI (as per E2E standards)
    page.goto(live_server.url + reverse('login'))
    page.fill('input[name="username"]', 'e2e_user')
    page.fill('input[name="password"]', 'password123')
    page.click('button[type="submit"]')
    
    # Wait for dashboard and negotiate to categories
    expect(page).to_have_url(live_server.url + reverse('dashboard'))
    
    # Click on Categories link in navbar
    page.click('a:has-text("Categories")')
    
    # Verify redirected to categories page
    expect(page).to_have_url(live_server.url + reverse('categories'))
    
    # Verify "Category Management" header exists
    expect(page.locator('h1')).to_contain_text('Category Management')
    
    # Verify "Create Category Group" button exists
    expect(page.locator('#create-group-btn')).to_be_visible()
    
    # Verify Lucide icons are rendered
    expect(page.locator('i[data-lucide="folder-plus"]')).to_be_visible()

    # Test Create Group Modal
    page.click('#create-group-btn')
    expect(page.locator('#create-group-modal')).to_be_visible()
    expect(page.locator('#modal-title-group')).to_have_text('Create Category Group')
    
    # Check close button aria-label
    expect(page.locator('button[aria-label="Close Modal"]')).to_be_visible()
    page.click('button[aria-label="Close Modal"]')
    expect(page.locator('#create-group-modal')).not_to_be_visible()

    # Test Add Category Modal
    page.click('.add-category-btn:has-text("Add Category")')
    expect(page.locator('#add-category-modal')).to_be_visible()
    expect(page.locator('#target-group-name')).to_have_text('Financial Expenses')
    
    # Close via Cancel button
    page.click('#add-category-modal .modal-close:has-text("Cancel")')
    expect(page.locator('#add-category-modal')).not_to_be_visible()
