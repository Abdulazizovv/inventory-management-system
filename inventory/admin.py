from django.contrib import admin
from inventory.models import Category, Customer, Product, Inventory
from django.utils.html import format_html

import os
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm


def export_barcodes_as_pdf(modeladmin, request, queryset):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="product_barcodes.pdf"'

    c = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    x = 20 * mm
    y = height - 30 * mm
    row_height = 30 * mm
    col_width = 80 * mm
    items_per_row = 2
    counter = 0

    for product in queryset:
        if product.barcode and os.path.exists(product.barcode.path):
            col = counter % items_per_row
            row = counter // items_per_row

            current_x = x + (col * col_width)
            current_y = y - (row * row_height)

            c.drawString(current_x, current_y + 20 * mm, f"{product.name} ({product.code})")
            c.drawImage(product.barcode.path, current_x, current_y, width=60, height=20)

            counter += 1
            if counter % (items_per_row * 10) == 0:
                c.showPage()
                y = height - 30 * mm
                counter = 0

    c.save()
    return response

export_barcodes_as_pdf.short_description = "📄 Export selected barcodes as PDF"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent_category', 'is_active', 'created_at', 'image_tag')
    list_filter = ('is_active', 'parent_category')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at', 'image_tag')
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'parent_category', 'description', 'is_active')
        }),
        ('Image', {
            'fields': ('image', 'image_tag'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="80" style="border-radius:4px;" />', obj.image.url)
        return "-"
    image_tag.short_description = 'Image Preview'


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone_number', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'phone_number')
    ordering = ('last_name', 'first_name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('first_name', 'last_name', 'email', 'phone_number', 'address')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

class InventoryInline(admin.TabularInline):
    model = Inventory
    extra = 0
    readonly_fields = ('change_type', 'quantity', 'note', 'created_by', 'timestamp')
    can_delete = False
    verbose_name_plural = 'Inventory Logs'
    show_change_link = False


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'code', 'category', 'unit', 'price',
        'stock_quantity', 'barcode_preview', 'product_image_preview', 'is_active'
    )
    list_filter = ('category', 'is_active', 'unit')
    search_fields = ('name', 'code', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('barcode_preview', 'product_image_preview', 'created_at', 'updated_at')
    inlines = [InventoryInline]
    actions = [export_barcodes_as_pdf]

    fieldsets = (
        (None, {
            'fields': (
                'name', 'slug', 'description', 'unit', 'price',
                'stock_quantity', 'image', 'product_image_preview',
                'category', 'is_active'
            )
        }),
        ('Barcode', {
            'fields': ('code', 'barcode', 'barcode_preview')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def product_image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" />', obj.image.url)
        return "-"
    product_image_preview.short_description = "Product Image"

    def barcode_preview(self, obj):
        if obj.barcode:
            return format_html('<img src="{}" width="100" />', obj.barcode.url)
        return "-"
    barcode_preview.short_description = "Barcode Preview"


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'change_type', 'quantity', 'created_by', 'timestamp')
    list_filter = ('change_type', 'created_by')
    search_fields = ('product__name', 'created_by__username', 'note')
    readonly_fields = ('timestamp',)
    ordering = ('-timestamp',)