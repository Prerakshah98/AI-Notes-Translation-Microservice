from re import A
from venv import logger
from celery import shared_task
from .models import Note
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

@shared_task
def translate_note_task(note_id, target_language):
    try:
        note = Note.objects.get(id=note_id)

        model_name = f'Helsinki-NLP/opus-mt-{note.original_language}-{target_language}'
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name, use_safetensors=True)

        inputs = tokenizer(note.original_text, return_tensors="pt", padding=True, truncation=True)
        translated_ids = model.generate(**inputs)
        translated_text = tokenizer.decode(translated_ids[0], skip_special_tokens=True)

        note.translated_text = translated_text
        note.translated_language = target_language
        note.save()
        
        cache_key = f'note_{note_id}'
        cache.delete(cache_key)

        logger.info(f"Successfully translated note {note_id} to {target_language}")
        return f"Translation complete for note {note_id}"
    except Note.DoesNotExist:
        logger.error(f"Note with id {note_id} does not exist.")
        return "Note not found."
    except Exception as e:
        logger.error(f"Error translating note {note_id}: {str(e)}")
        return f"Translation failed: {str(e)}"
