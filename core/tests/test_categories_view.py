import pytest
from django.urls import reverse
from django.contrib.auth.models import User

@pytest.mark.django_db
def test_categories_view_access_unauthenticated(client):
    url = reverse('categories')
    print(f"REVERSED URL: {url}")
    # Try with follow=True to see where it lands if it redirects
    response = client.get(url, follow=True)
    print(f"RESPONSE STATUS: {response.status_code}")
    print(f"REDIRECT CHAIN: {response.redirect_chain}")
    # If it land on a 404, we want to know where
    
    # Actually, let's test the 302 without following first
    response_no_follow = client.get(url)
    assert response_no_follow.status_code == 302
    assert '/login/' in response_no_follow.url

@pytest.mark.django_db
def test_categories_view_access_authenticated(client):
    user = User.objects.create_user(username='testuser', password='password')
    client.force_login(user)
    
    url = reverse('categories')
    response = client.get(url)
    
    assert response.status_code == 200
    assert 'core/categories.html' in [t.name for t in response.templates]
    assert 'Category Management' in response.content.decode()
    
    # Check for modals code
    content = response.content.decode()
    assert 'id="create-group-modal"' in content
    assert 'id="add-category-modal"' in content
    
    # Check for standardized labels
    assert 'aria-label="Edit Group"' in content
    assert 'aria-label="Edit Category"' in content
    assert 'aria-label="Delete Category"' in content
    assert 'aria-label="Close Modal"' in content
