from django.contrib import admin
from inventory.models import Category, Customer, Product, Inventory
from django.utils.html import format_html


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
    list_display = ('name', 'code', 'category', 'unit', 'price', 'stock_quantity', 'barcode_preview', 'is_active')
    list_filter = ('category', 'is_active', 'unit')
    search_fields = ('name', 'code', 'slug')
    readonly_fields = ('barcode_preview', 'created_at', 'updated_at')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [InventoryInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'unit', 'price', 'stock_quantity', 'image', 'category', 'is_active')
        }),
        ('Barcode', {
            'fields': ('code', 'barcode', 'barcode_preview')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def barcode_preview(self, obj):
        if obj.barcode:
            return format_html('<img src="{}" width="150" />', obj.barcode.url)
        return "-"
    barcode_preview.short_description = "Barcode Preview"


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'change_type', 'quantity', 'created_by', 'timestamp')
    list_filter = ('change_type', 'created_by')
    search_fields = ('product__name', 'created_by__username', 'note')
    readonly_fields = ('timestamp',)
    ordering = ('-timestamp',)