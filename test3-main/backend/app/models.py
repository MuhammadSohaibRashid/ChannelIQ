from django.db import models

# Create your models here.
class React(models.Model):
    employee=models.CharField(max_length=30)
    department=models.CharField(max_length=200)

class ClipGenerationTask(models.Model):
    video_url = models.URLField()
    clip_length = models.IntegerField()
    clip_count = models.IntegerField()
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

