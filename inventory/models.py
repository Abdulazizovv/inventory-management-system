from django.db import models
from django.utils.text import slugify
from typing import TYPE_CHECKING
import os
from io import BytesIO
from django.core.files import File
from barcode import Code128
from barcode.writer import ImageWriter
import random

if TYPE_CHECKING:
    from users.models import User  # Assuming User model is in users app



def generate_4_digit_numeric_code():
    return f"{random.randint(0, 9999):04d}" 


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)

    is_active = models.BooleanField(default=True)
    parent_category = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='subcategories',
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        full_path = [self.name]
        parent = self.parent_category
        while parent:
            full_path.append(parent.name)
            parent = parent.parent_category
        return " → ".join(reversed(full_path))
    

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            i = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{i}"
                i += 1
            self.slug = slug
        
        super().save(*args, **kwargs)



    

class Customer(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Customers'
        ordering = ['last_name', 'first_name']

    @property
    def full_name(self):
        return self.first_name

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone_number})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    

class Product(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    unit = models.CharField(max_length=50, default='dona')  # e.g., dona, kg, liter, m, etc
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    barcode = models.ImageField(upload_to='barcodes/', blank=True, null=True)
    code = models.CharField(max_length=10, unique=True, blank=True)  # 4-digit numeric code
    category: "Category" = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Products'
        ordering = ['stock_quantity']

    def __str__(self):
        return self.name

    def generate_barcode(self):
        buffer = BytesIO()
        code128 = Code128(self.code, writer=ImageWriter())
        code128.write(buffer)
        filename = f"{self.code}.png"
        self.barcode.save(filename, File(buffer), save=False)


    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            i = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{i}"
                i += 1
            self.slug = slug

        if not self.code:
            for _ in range(10):  # Try 10 times to find a unique 4-digit code
                candidate = generate_4_digit_numeric_code()
                if not Product.objects.filter(code=candidate).exists():
                    self.code = candidate
                    break
            else:
                raise ValueError("Unable to generate unique 4-digit code")
        
        super().save(*args, **kwargs)

        # Generate Code128 barcode
        if not self.barcode:
            buffer = BytesIO()
            barcode_obj = Code128(self.code, writer=ImageWriter())
            barcode_obj.write(buffer)
            filename = f"{self.code}_product_barcode.png"
            self.barcode.save(filename, File(buffer), save=False)
            super().save(update_fields=['barcode'])


class Inventory(models.Model):
    class ChangeType(models.TextChoices):
        ADD = 'ADD', 'Added'         # e.g., purchased, received
        REMOVE = 'REMOVE', 'Removed' # e.g., sale, damage, expired
        ADJUST = 'ADJUST', 'Adjusted'

    product: "Product" = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory_logs')
    change_type = models.CharField(max_length=10, choices=ChangeType.choices)
    quantity = models.IntegerField()  # Positive or negative depending on change
    note = models.TextField(blank=True, null=True)

    created_by: "User" = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_change_type_display()} {self.quantity} of {self.product.name}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding  # True if this is a new object
        original_quantity = 0

        if not is_new:
            try:
                original = Inventory.objects.get(pk=self.pk)
                original_quantity = original.quantity
            except Inventory.DoesNotExist:
                pass  # should not happen

        # Ensure REMOVE has negative quantity
        if self.change_type == Inventory.ChangeType.REMOVE:
            self.quantity = -abs(self.quantity)

        elif self.change_type == Inventory.ChangeType.ADD:
            self.quantity = abs(self.quantity)

        # If ADJUST, quantity stays as is (positive or negative)

        super().save(*args, **kwargs)

        # Adjust stock only if it's a new log or quantity has changed
        if is_new:
            delta = self.quantity
        else:
            delta = self.quantity - original_quantity

        product = self.product
        product.stock_quantity += delta
        if product.stock_quantity < 0:
            product.stock_quantity = 0

        # Direct update to avoid triggering Product.save() again
        Product.objects.filter(pk=product.pk).update(stock_quantity=product.stock_quantity)


class Sale(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    location = models.CharField(max_length=255, blank=True, null=True)  # e.g., store name or address
    payment_method = models.CharField(max_length=50, blank=True, null=True)  # e.g., cash, card, etc
    description = models.TextField(blank=True, null=True)  # Additional notes about the sale
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @property
    def total_price(self):
        return (self.unit_price * self.quantity) - self.discount