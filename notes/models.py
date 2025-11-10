from django.db import models

# Create your models here.
class Note(models.Model):
    title = models.CharField(max_length=200)
    original_text = models.TextField()
    original_language = models.CharField(max_length=50, default='en')
    
    translated_text = models.TextField(blank=True, null=True)
    translated_language = models.CharField(max_length=50, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title