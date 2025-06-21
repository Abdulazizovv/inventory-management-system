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
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Customers'
        ordering = ['last_name', 'first_name']

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
        ordering = ['name']

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
        super().save(*args, **kwargs)

        # Automatically update product stock
        self.product.stock_quantity += self.quantity
        if self.product.stock_quantity < 0:
            self.product.stock_quantity = 0
        self.product.save()