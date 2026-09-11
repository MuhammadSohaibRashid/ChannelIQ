from django.db import models
from django.conf import settings
import google.oauth2.credentials
import googleapiclient.discovery
from datetime import datetime, timedelta
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
class YouTubeAuth(models.Model):
    """Model to store YouTube OAuth credentials"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    credentials = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def is_valid(self):
        """Check if credentials are valid"""
        if not self.credentials:
            return False
            
        # Check if we have the necessary credentials
        required_fields = ['token', 'refresh_token', 'token_uri', 'client_id', 'client_secret']
        for field in required_fields:
            if field not in self.credentials:
                return False
        
        try:
            # Create credentials object
            credentials = google.oauth2.credentials.Credentials(
                token=self.credentials.get('token'),
                refresh_token=self.credentials.get('refresh_token'),
                token_uri=self.credentials.get('token_uri'),
                client_id=self.credentials.get('client_id'),
                client_secret=self.credentials.get('client_secret'),
                scopes=self.credentials.get('scopes')
            )
            
            # Try to build YouTube service
            youtube = googleapiclient.discovery.build('youtube', 'v3', credentials=credentials)
            
            # Make a simple API call to test credentials
            response = youtube.channels().list(part='snippet', mine=True).execute()
            
            # Update token if it was refreshed
            if credentials.token != self.credentials.get('token'):
                self.credentials['token'] = credentials.token
                self.save()
                
            return True
            
        except Exception:
            return False

