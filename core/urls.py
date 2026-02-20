from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import (
    CustomLoginView, DashboardView, SignUpView, CategoriesView,
    CategoryGroupCreateView, CategoryGroupUpdateView, CategoryCreateView,
    CategoryUpdateView, CategoryDeleteView
)

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('categories/', CategoriesView.as_view(), name='categories'),
    path('categories/group/create/', CategoryGroupCreateView.as_view(), name='category_group_create'),
    path('categories/group/<int:pk>/update/', CategoryGroupUpdateView.as_view(), name='category_group_update'),
    path('categories/create/', CategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/update/', CategoryUpdateView.as_view(), name='category_update'),
    path('categories/<int:pk>/delete/', CategoryDeleteView.as_view(), name='category_delete'),
    path('', DashboardView.as_view(), name='home'),
]
