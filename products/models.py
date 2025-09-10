from django.db import models

# Create your models here.
from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    alloy = models.TextField()
    width = models.TextField()
    length = models.TextField()
    deliverylocation = models.TextField()
    description = models.TextField()
    categorie= models.keys(x, y)
    def __str__(self):
        return self.name