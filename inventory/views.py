from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Count
from decimal import Decimal, InvalidOperation

from inventory.models import Category, Product, Inventory, Customer


@login_required
def home(request):
    """
    Render the home page of the inventory app.
    """
    return render(request, 'inventory/home.html')

def login_view(request):
    """
    Render the login page of the inventory app.
    """

    if request.user.is_authenticated:
        # If the user is already authenticated, redirect to the home page
        return redirect('index')

    if request.method == 'POST':
        # Handle the login logic here (e.g., authenticate user)
        phone_number = request.POST.get('login')
        password = request.POST.get('password')
        print(f"Attempting to log in user: {phone_number}")
        # Authenticate the user
        if not phone_number or not password:
            return render(request, 'inventory/login.html', {'error': 'phone number and password are required.'})
        # Authenticate the user
        user = authenticate(request, phone=phone_number, password=password)
        if user is not None:
            login(request, user)
            return redirect('index')  # Redirect to the home page after login
        else:
            # Invalid login credentials
            return render(request, 'inventory/login.html', {'error': 'Invalid phone number or password'})

    return render(request, 'inventory/login.html')


def logout_view(request):
    """
    Handle user logout.
    """
    if request.method == 'POST':
        # Log out the user and redirect to the login page
        logout(request)
        return redirect('login')  # Redirect to the login page after logout
    return render(request, 'inventory/login.html')


def products_page(request):
    """
    Render the products page of the inventory app.
    """
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Filter products
    search_query = request.GET.get('search', '').strip()
    if search_query:
        products = Product.objects.filter(Q(name__icontains=search_query) | Q(code=search_query)).distinct()
    else:
        products = Product.objects.all()
    # Filter categories
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category__id=category_id)

    min_price = request.GET.get('min_price', None)
    max_price = request.GET.get('max_price', None)

    try:
        if min_price:
            products = products.filter(price__gte=Decimal(min_price))
        if max_price:
            products = products.filter(price__lte=Decimal(max_price))
    except InvalidOperation:
        pass


    # Stock filters
    min_stock = request.GET.get('min_stock')
    max_stock = request.GET.get('max_stock')
    if min_stock:
        try:
            products = products.filter(stock_quantity__gte=int(min_stock))
        except:
            pass
    if max_stock:
        try:
            products = products.filter(stock_quantity__lte=int(max_stock))
        except:
            pass 

    # Get all active categories
    categories = Category.objects.all()

    context = {
        'products': products,
        'categories': categories,
    }

    return render(request, 'inventory/products.html', context)


@login_required
def product_detail(request, product_id):
    """
    Render and update the detail page for a specific product.
    """
    product = get_object_or_404(Product, id=product_id)
    categories = Category.objects.filter(is_active=True)

    if request.method == 'POST':
        name = request.POST.get('name')
        price = request.POST.get('price', '0').replace(',', '.')
        unit = request.POST.get('unit', 'dona')
        stock_quantity = request.POST.get('stock_quantity', '0')
        description = request.POST.get('description', '')
        is_active = request.POST.get('is_active') == 'on'
        category_id = request.POST.get('category')

        # Convert price and quantity safely
        try:
            product.price = float(price)
            product.stock_quantity = int(stock_quantity)
        except ValueError:
            messages.error(request, "Narx yoki miqdor noto‘g‘ri formatda.")
            return redirect('product_detail', product_id=product.id)

        product.name = name
        product.unit = unit
        product.description = description
        product.is_active = is_active

        if category_id:
            product.category = Category.objects.filter(id=category_id).first()
        else:
            product.category = None

        if 'image' in request.FILES:
            product.image = request.FILES['image']

        product.save()
        messages.success(request, "Mahsulot muvaffaqiyatli yangilandi.")
        return redirect('product_detail', product_id=product.id)

    context = {
        'product': product,
        'categories': categories,
    }
    return render(request, 'inventory/product_detail.html', context)


@login_required
def add_product(request):
    """
    Render the add product page and handle product creation.
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        price = request.POST.get('price', '0').replace(',', '.')
        unit = request.POST.get('unit', 'dona')
        stock_quantity = request.POST.get('stock_quantity', '0')
        description = request.POST.get('description', '')
        is_active = request.POST.get('is_active') == 'on'
        category_id = request.POST.get('category')

        # Convert price and quantity safely
        try:
            price = float(price)
            stock_quantity = int(stock_quantity)
        except ValueError:
            messages.error(request, "Narx yoki miqdor noto‘g‘ri formatda.")
            return redirect('add_product')

        product = Product(
            name=name,
            price=price,
            unit=unit,
            stock_quantity=stock_quantity,
            description=description,
            is_active=is_active
        )

        if category_id:
            product.category = Category.objects.filter(id=category_id).first()
        
        if 'image' in request.FILES:
            product.image = request.FILES['image']

        product.save()
        messages.success(request, "Mahsulot muvaffaqiyatli qo‘shildi.")
        return redirect('products')
    
    category_id = request.GET.get('category')
    selected_category = None
    if category_id:
        try:
            selected_category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            selected_category = None

    categories = Category.objects.filter(is_active=True)
    context = {
        'categories': categories,
        'selected_category': selected_category,
    }
    return render(request, 'inventory/product_add.html', context)

@login_required
def delete_product(request, product_id):
    """
    Handle deletion of a product.
    """
    if not request.user.is_authenticated:
        return redirect('login')

    try:
        product = Product.objects.get(id=product_id)
        product.delete()
        messages.success(request, "Mahsulot muvaffaqiyatli o‘chirildi.")
    except Product.DoesNotExist:
        messages.error(request, "Mahsulot topilmadi.")

    return redirect('products')


@login_required
def category_list(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        is_active = request.POST.get('is_active') == 'on'

        if name:
            Category.objects.create(name=name, description=description, is_active=is_active)
            messages.success(request, "Kategoriya muvaffaqiyatli qo‘shildi.")
        else:
            messages.error(request, "Kategoriya nomi majburiy.")

        return redirect('categories')

    # Annotate product count
    categories = Category.objects.annotate(product_count=Count('products'))
    return render(request, 'inventory/categories.html', {'categories': categories})


def category_detail(request, category_id):
    if not request.user.is_authenticated:
        return redirect('login')

    try:
        category = Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        messages.error(request, "Kategoriya topilmadi.")
        return redirect('categories')

    if request.method == 'POST':
        category.name = request.POST.get('name')
        category.description = request.POST.get('description')
        category.is_active = request.POST.get('is_active') == 'on'
        category.save()
        messages.success(request, "Kategoriya yangilandi.")
        return redirect('category_detail', category_id=category.id)

    products = Product.objects.filter(category=category)

    return render(request, 'inventory/category_detail.html', {
        'category': category,
        'products': products,
    })

@login_required
def delete_category(request, category_id):
    """
    Handle deletion of a category.
    """
    if not request.user.is_authenticated:
        return redirect('login')

    try:
        category = Category.objects.get(id=category_id)
        category.delete()
        messages.success(request, "Kategoriya muvaffaqiyatli o‘chirildi.")
    except Category.DoesNotExist:
        messages.error(request, "Kategoriya topilmadi.")

    return redirect('categories')

def customers_page(request):
    if not request.user.is_authenticated:
        return redirect('login')

    search_query = request.GET.get('search', '').strip()
    if search_query:
        customers = Customer.objects.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(phone_number__icontains=search_query)
        )
    else:
        customers = Customer.objects.all()

    context = {
        'customers': customers,
    }
    return render(request, 'inventory/customers.html', context)


def add_customer(request):
    if request.method == 'POST':
        customer = Customer(
            first_name=request.POST.get('first_name'),
            last_name=request.POST.get('last_name'),
            phone_number=request.POST.get('phone_number'),
            address=request.POST.get('address')
        )
        customer.save()
        messages.success(request, 'Mijoz muvaffaqiyatli qo‘shildi.')
        return redirect('customers')

    return render(request, 'inventory/customer_form.html', {
        'title': 'Yangi mijoz qo‘shish',
        'customer': {},
    })

def edit_customer(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)

    if request.method == 'POST':
        customer.first_name = request.POST.get('first_name')
        customer.last_name = request.POST.get('last_name')
        customer.phone_number = request.POST.get('phone_number')
        customer.address = request.POST.get('address')
        customer.save()
        messages.success(request, 'Mijoz maʼlumotlari yangilandi.')
        return redirect('customers')

    return render(request, 'inventory/customer_form.html', {
        'title': 'Mijozni tahrirlash',
        'customer': customer,
    })


def delete_customer(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    customer.delete()
    messages.success(request, 'Mijoz o‘chirildi.')
    return redirect('customers')