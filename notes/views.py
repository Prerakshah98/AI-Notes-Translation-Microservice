from django.shortcuts import render
from rest_framework import viewsets
from .models import Note
from .serializers import NoteSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .tasks import translate_note_task

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