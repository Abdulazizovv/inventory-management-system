from django.urls import path
from inventory import views


urlpatterns = [
    path("", views.home, name="index"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("products/", views.products_page, name="products"),
    path("products/<int:product_id>/edit/", views.product_detail, name="product_detail"),
    path("products/add/", views.add_product, name="add_product"),
    path("products/<int:product_id>/delete/", views.delete_product, name="delete_product"),
    path("categories/", views.category_list, name="categories"),
    path("categories/<int:category_id>/", views.category_detail, name="category_detail"),
    path("categories/<int:category_id>/delete/", views.delete_category, name="delete_category"),
    path('customers/', views.customers_page, name='customers'),
    path('customers/add/', views.add_customer, name='add_customer'),
    path('customers/<int:customer_id>/edit/', views.edit_customer, name='edit_customer'),
    path('customers/<int:customer_id>/delete/', views.delete_customer, name='delete_customer'),
    path('sales/create/', views.create_sale_view, name='sale_create_page'),
    path('sales/create/new/', views.create_sale, name='create_sale'),
    path('sales/<int:pk>/', views.sale_detail, name='sale_detail'),
    path('sales/list/', views.sale_list, name='sale_list'),
    path('customers/ajax/add/', views.add_customer_ajax, name='add_customer_ajax'),
]
