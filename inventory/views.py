from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Count, Sum
from decimal import Decimal, InvalidOperation
import json
from django.core.paginator import Paginator
from django.utils.timezone import now, timedelta

from inventory.models import Category, Product, Inventory, Customer, Sale, SaleItem


@login_required
def home(request):
    today = now().date()

    total_products = Product.objects.count()
    total_customers = Customer.objects.count()
    today_sales = (
        Sale.objects.filter(created_at__date=today)
        .aggregate(total=Sum('total_amount'))['total'] or 0
    )
    total_stock = Product.objects.aggregate(total=Sum('stock_quantity'))['total'] or 0

    recent_sales = Sale.objects.select_related('customer').order_by('-created_at')[:5]
    low_stock_products = Product.objects.filter(stock_quantity__lt=10, is_active=True)

    context = {
        'total_products': total_products,
        'total_customers': total_customers,
        'today_sales': today_sales,
        'total_stock': total_stock,
        'recent_sales': recent_sales,
        'low_stock_products': low_stock_products,
    }
    return render(request, 'inventory/home.html', context)

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


def create_sale_view(request):
    customers = Customer.objects.all()
    products = Product.objects.all()
    return render(request, 'sales/sale_pos.html', {
        'customers': customers,
        'products': products,
    })


@login_required
def create_sale(request):
    if request.method == 'POST':
        customer_id = request.POST.get('customer_id')
        location = request.POST.get('location', '')
        description = request.POST.get('description', '')
        cart_data = request.POST.get('cart_data', '[]')

        if not customer_id or not cart_data:
            messages.error(request, "Mijoz va mahsulotlar talab qilinadi.")
            return redirect('sale_create_page')  # replace with your actual URL name

        try:
            customer = Customer.objects.get(id=customer_id)
            cart_items = json.loads(cart_data)

            # 1. Create Sale
            sale = Sale.objects.create(
                customer=customer,
                created_by=request.user,
                location=location,
                description=description,
                total_amount=sum((item['price'] * item['quantity']) - item['discount'] for item in cart_items)
            )

            # 2. Create SaleItems
            for item in cart_items:
                product = Product.objects.get(id=item['id'])
                SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    unit_price=item['price'],
                    quantity=item['quantity'],
                    discount=item['discount']
                )
            # 3. Update Product Stock
            for item in cart_items:
                product = Product.objects.get(id=item['id'])
                product.stock_quantity -= item['quantity']
                if product.stock_quantity < 0:
                    messages.error(request, f"{product.name} uchun yetarli zaxira mavjud emas.")
                    return redirect('sale_create_page')
                product.save()

            messages.success(request, "Buyurtma muvaffaqiyatli yaratildi.")
            # return redirect('sale_create_page')
            return redirect('sale_detail', pk=sale.pk)

        except Exception as e:
            messages.error(request, f"Xatolik yuz berdi: {e}")
            return redirect('sale_create_page')

    return redirect('sale_create_page')

def sale_detail(request, pk):
    sale = get_object_or_404(Sale.objects.select_related('customer').prefetch_related('items__product'), pk=pk)
    return render(request, 'sales/sale_detail.html', {'sale': sale})


def add_customer_ajax(request):
    if request.method == 'POST':
        customer = Customer.objects.create(
            first_name=request.POST['first_name'],
            last_name=request.POST.get('last_name', ''),
            phone_number=request.POST.get('phone_number', ''),
            address=request.POST.get('address', '')
        )
        return JsonResponse({
            'success': True,
            'customer': {
                'id': customer.id,
                'full_name': customer.full_name,
                'phone_number': customer.phone_number,
                'address': customer.address
            }
        })
    return JsonResponse({'success': False}, status=400)


from django.shortcuts import render
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.utils.timezone import now
from datetime import timedelta
from .models import Sale, Customer

def sale_list(request):
    sales = Sale.objects.select_related("customer").order_by("-created_at")

    q = request.GET.get("q")
    customer_id = request.GET.get("customer_id")  # HTML da `name="customer_id"`
    date_from = request.GET.get("from_date")      # HTML da `name="from_date"`
    date_to = request.GET.get("to_date")          # HTML da `name="to_date"`

    # Filtering
    if q:
        sales = sales.filter(
            Q(customer__first_name__icontains=q) |
            Q(customer__last_name__icontains=q) |
            Q(customer__phone_number__icontains=q)
        )

    if customer_id:
        sales = sales.filter(customer_id=customer_id)

    if date_from:
        sales = sales.filter(created_at__date__gte=date_from)

    if date_to:
        sales = sales.filter(created_at__date__lte=date_to)

    # Pagination
    paginator = Paginator(sales, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Statistika
    today = now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today.replace(day=1)

    stats = {
        'today': Sale.objects.filter(created_at__date=today).count(),
        'today_total': Sale.objects.filter(created_at__date=today).aggregate(Sum('total_amount'))['total_amount__sum'] or 0,

        'week': Sale.objects.filter(created_at__date__gte=week_ago).count(),
        'week_total': Sale.objects.filter(created_at__date__gte=week_ago).aggregate(Sum('total_amount'))['total_amount__sum'] or 0,

        'month': Sale.objects.filter(created_at__date__gte=month_ago).count(),
        'month_total': Sale.objects.filter(created_at__date__gte=month_ago).aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
    }

    context = {
        "sales": page_obj,
        "customers": Customer.objects.all(),
        "stats": stats,
        "q": q,
        "customer_id": customer_id,
        "from_date": date_from,
        "to_date": date_to,
    }
    return render(request, "sales/sale_list.html", context)
