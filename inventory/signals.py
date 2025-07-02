from django.db.models.signals import post_save
from django.dispatch import receiver
from inventory.models import Product, Inventory


@receiver(post_save, sender=Product)
def create_inventory_log(sender, instance, created, **kwargs):
    if created:
        Inventory.objects.create(
            product=instance,
            change_type=Inventory.ChangeType.ADD,
            quantity=instance.stock_quantity,  # Initial quantity when product is created
            note="Product created"
        )
    else:
        # Update the inventory log if the product is updated
        Inventory.objects.create(
            product=instance,
            change_type=Inventory.ChangeType.ADJUST,
            quantity=0,  # No change in quantity on update
            note="Product updated"
        )