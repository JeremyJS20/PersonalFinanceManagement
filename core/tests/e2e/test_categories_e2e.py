import pytest
from playwright.sync_api import Page, expect
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import CategoryGroup, Category
import os
import re

def compile_regex(text):
    return re.compile(text)

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
def test_categories_page_navigation(logged_in_page: Page, live_server):
    """Test navigation to categories page and automatic URL sync."""
    page = logged_in_page
    page.click('a:has-text("Categories")')
    # Verify URL automatically syncs to include tab parameter
    expect(page).to_have_url(live_server.url + reverse('categories') + "?tab=expenses")
    expect(page.locator('h1')).to_contain_text('Categories Management')

@pytest.mark.django_db(transaction=True)
def test_categories_tab_persistence(logged_in_page: Page, live_server):
    """Test that selected tab (Expenses/Income) persists after page reload."""
    page = logged_in_page
    page.goto(live_server.url + reverse('categories'))
    
    # Click Income tab
    page.click('button[data-pfm-tab-target="income"]')
    expect(page).to_have_url(live_server.url + reverse('categories') + "?tab=income")
    
    # Reload
    page.reload()
    expect(page).to_have_url(live_server.url + reverse('categories') + "?tab=income")

@pytest.mark.django_db(transaction=True)
def test_categories_crud(logged_in_page: Page, live_server, test_user):
    """Test Create, Update, and Delete operations for Category Groups and Categories."""
    page = logged_in_page
    page.goto(live_server.url + reverse('categories'))
    
    # 1. Create Group
    page.click('#create-group-btn')
    page.fill('#group-name', 'Test Group')
    page.fill('#group-description', 'Test Description')
    # Select an icon
    icon_btn = page.locator('.icon-option[data-icon="shopping-cart"]')
    expect(icon_btn).to_be_visible()
    icon_btn.click()
    page.click('#modal-submit-group')
    
    expect(page.locator('section').get_by_text("Test Group", exact=True)).to_be_visible()
    
    # 2. Add Category to Group
    group_card = page.locator('section').filter(has_text="Test Group")
    group_card.locator('button:has-text("Add Category")').click()
    
    page.fill('#category-name', 'Test Category')
    page.fill('#category-description', 'Category Desc')
    # Select an icon for category
    cat_icon_btn = page.locator('.icon-option[data-icon="tag"]')
    expect(cat_icon_btn).to_be_visible()
    cat_icon_btn.click()
    page.click('#modal-submit-category')
    
    expect(page.locator('section').get_by_text("Test Category", exact=True)).to_be_visible()
    
    # 3. Update Category
    category_row = page.locator('.group').filter(has_text="Test Category")
    category_row.locator('.modal-open-btn[aria-label="Edit Category"]').click()
    page.fill('#category-name', 'Updated Category')
    page.click('#modal-submit-category')
    # Scope to the main content area to avoid matching text in hidden modals
    expect(page.locator('section').get_by_text("Updated Category", exact=True)).to_be_visible()
    
    # 4. Update Group
    group_header = page.locator('section').filter(has_text="Test Group")
    group_header.locator('.modal-open-btn[aria-label="Edit Group"]').click()
    page.fill('#group-name', 'Updated Group')
    page.click('#modal-submit-group')
    expect(page.locator('section').get_by_text("Updated Group", exact=True)).to_be_visible()
    
    # 5. Delete Category
    updated_cat_row = page.locator('.group').filter(has_text="Updated Category")
    updated_cat_row.locator('.category-delete-btn').click()
    # Handle delete confirmation modal
    expect(page.locator('#delete-category-modal')).to_be_visible()
    page.click('#confirm-delete-category-btn')
    expect(page.locator('section').get_by_text("Updated Category", exact=True)).not_to_be_visible()
    
    # 6. Delete Group (Currently requires no categories or implemented via separate logic if needed)
    # Note: If group deletion is not fully UI-implemented as a separate button yet,
    # we'll focus on the Category CRUD as that's what was refined.
    # If Group Delete is available, we'd test it here.

@pytest.mark.django_db(transaction=True)
def test_categories_behavior_verification(logged_in_page: Page, live_server):
    """Specifically verify the UI refinements: right-aligned buttons and bold labels."""
    page = logged_in_page
    page.goto(live_server.url + reverse('categories'))
    
    # Open Create Group Modal
    page.click('#create-group-btn')
    
    # Verify button alignment container class
    # The container should have 'justify-end'
    footer = page.locator('#create-group-modal .bg-pfm-bg\\/50')
    expect(footer).to_have_class(compile_regex("justify-end"))
    
    # Verify label styling
    label = page.locator('label[for="group-name"]')
    expect(label).to_have_class(compile_regex(r"text-xs.*font-black.*uppercase"))

@pytest.mark.django_db(transaction=True)
def test_categories_full_workflow(logged_in_page: Page, live_server, test_user):
    """
    A single test that runs through the complete user journey for categories:
    Navigation -> CRUD (Group & Category) -> Persistence -> UI Verification
    """
    page = logged_in_page
    page.goto(live_server.url + reverse('categories'))
    
    # 1. Navigation & Initial State
    expect(page).to_have_url(live_server.url + reverse('categories') + "?tab=expenses")
    
    # 2. Create Group
    page.click('#create-group-btn')
    page.fill('#group-name', 'Journey Group')
    page.locator('.icon-option[data-icon="shopping-cart"]').click()
    page.click('#modal-submit-group')
    expect(page.locator('section').get_by_text("Journey Group", exact=True)).to_be_visible()
    
    # 3. Create Category
    group_card = page.locator('section').filter(has_text="Journey Group")
    group_card.locator('button:has-text("Add Category")').click()
    page.fill('#category-name', 'Journey Category')
    page.locator('.icon-option[data-icon="tag"]').click()
    page.click('#modal-submit-category')
    expect(page.locator('section').get_by_text("Journey Category", exact=True)).to_be_visible()
    
    # 4. Tab Persistence
    page.click('button[data-pfm-tab-target="income"]')
    expect(page).to_have_url(live_server.url + reverse('categories') + "?tab=income")
    page.reload()
    expect(page).to_have_url(live_server.url + reverse('categories') + "?tab=income")
    
    # 5. Update & UI Verification (Back to Expenses)
    page.click('button[data-pfm-tab-target="expenses"]')
    row = page.locator('.group').filter(has_text="Journey Category")
    row.locator('.modal-open-btn[aria-label="Edit Category"]').click()
    
    # Verify bold labels in update mode too
    label = page.locator('label[for="category-name"]')
    expect(label).to_have_class(compile_regex(r"text-xs.*font-black.*uppercase"))
    
    page.fill('#category-name', 'Final Journey Item')
    page.click('#modal-submit-category')
    expect(page.locator('section').get_by_text("Final Journey Item", exact=True)).to_be_visible()
    
    # 6. Delete
    final_row = page.locator('.group').filter(has_text="Final Journey Item")
    final_row.locator('.category-delete-btn').click()
    page.click('#confirm-delete-category-btn')
    expect(page.locator('section').get_by_text("Final Journey Item", exact=True)).not_to_be_visible()


