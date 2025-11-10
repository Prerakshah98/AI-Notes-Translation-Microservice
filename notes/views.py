import re
from django.shortcuts import render
from rest_framework import viewsets
from .models import Note
from .serializers import NoteSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .tasks import translate_note_task
from django.core.cache import cache


class NoteViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.all().order_by('-created_at')
    serializer_class = NoteSerializer
    
    @action(detail=True, methods=['post'], url_path='translate')
    def translate(self, request, pk=None):
        note = self.get_object()
        target_language = request.data.get('target_language')

        if not target_language:
            return Response({"error": "Target language not provided."}, status=status.HTTP_400_BAD_REQUEST)

        # Call the Celery task
        translate_note_task.delay(note.id, target_language)

        return Response({"message": "Translation task started."}, status=status.HTTP_202_ACCEPTED)
    
    def retrieve(self, request, *args, **kwargs):
        note_id = kwargs.get('pk')
        cache_key = f'note_{note_id}'
        
        cached_data = cache.get(cache_key)
        if cached_data:
            print(f"Serving note {note_id} from cache")
            return Response(cached_data)
        
        print(f"Serving note {note_id} from database")
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data
        
        cache.set(cache_key, data, timeout=300) 
        return Response(data)
    
    
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
            note_id = kwargs.get('pk')
            cache.delete(f'note_{note_id}')
            print(f"Cache DELETED for note {note_id}")

        return response

    def destroy(self, request, *args, **kwargs):
        note_id = kwargs.get('pk') 

        response = super().destroy(request, *args, **kwargs)

        cache.delete(f'note_{note_id}')
        print(f"Cache DELETED for note {note_id}")
        return response