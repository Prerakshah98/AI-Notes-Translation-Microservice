from rest_framework import serializers
from .models import Note

class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ['id', 'title', 'original_text', 'original_language', 'translated_text', 'translated_language', 'created_at', 'updated_at']
        
        read_only_fields = ['translated_text', 'translated_language']