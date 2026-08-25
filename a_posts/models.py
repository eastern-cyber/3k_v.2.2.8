# a_posts/models.py
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from io import BytesIO
import uuid
import os

try:
    import cv2
    from PIL import Image
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("Warning: OpenCV (cv2) not installed. Video thumbnail generation will be disabled.")

class Post(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    image = models.ImageField(upload_to='posts/', null=True, blank=True)
    video = models.FileField(upload_to='posts/videos/', null=True, blank=True)
    thumbnail = models.ImageField(upload_to='posts/thumbnails/', null=True, blank=True)
    body = models.CharField(max_length=80, null=True, blank=True)
    link_url = models.URLField(max_length=200, blank=True, null=True, verbose_name="External Link")
    link_title = models.CharField(max_length=100, blank=True, null=True, verbose_name="Link Title/Caption")
    tags = models.ManyToManyField('Tag', related_name='posts', blank=True)
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="likedposts", through="LikedPost")
    bookmarks = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="bookmarkedposts", through="BookmarkedPost")
    reposts = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='repostedposts', through='Repost')
    created_at = models.DateTimeField(auto_now_add=True)
    
    @property
    def parent_comments(self):
        return self.comments.filter(parent_comment__isnull=True)
    
    def generate_thumbnail(self):
        """Generate a thumbnail from the video file"""
        if not self.video or not CV2_AVAILABLE:
            return None
        
        try:
            # Open the video file
            video_path = self.video.path
            cap = cv2.VideoCapture(video_path)
            
            # Read the first frame
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                # Convert frame to RGB (cv2 uses BGR)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Convert to PIL Image
                pil_image = Image.fromarray(frame_rgb)
                
                # Create a thumbnail (max 1280x720)
                pil_image.thumbnail((1280, 720), Image.Resampling.LANCZOS)
                
                # Save to BytesIO
                image_io = BytesIO()
                pil_image.save(image_io, format='JPEG', quality=85)
                image_io.seek(0)
                
                # Save to the thumbnail field
                filename = os.path.basename(self.video.name).rsplit('.', 1)[0] + '.jpg'
                self.thumbnail.save(filename, ContentFile(image_io.read()), save=False)
                return self.thumbnail
                
        except Exception as e:
            print(f"Error generating thumbnail for post {self.id}: {e}")
            return None
        
        return None
    
    def save(self, *args, **kwargs):
        # Generate thumbnail when video is uploaded and no thumbnail exists
        is_new = self.pk is None
        
        # Save first to get the file path and UUID
        super().save(*args, **kwargs)
        
        # Generate thumbnail for video posts
        if self.video and not self.thumbnail and CV2_AVAILABLE:
            thumbnail = self.generate_thumbnail()
            if thumbnail:
                # Save again with the thumbnail
                super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-created_at'] 
    
    def __str__(self):
        return str(self.uuid) 
    
    def get_absolute_url(self):
        return reverse('post_page', kwargs={'pk': self.uuid})


class Tag(models.Model):
    name = models.CharField(max_length=25, unique=True)
    count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-count', 'name'] 
        
    def __str__(self):
        return f"#{self.name}"
    
    
class LikedPost(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at'] 
        unique_together = ('user', 'post')
        
    @property
    def type(self):
        return "likedpost"
        
        
class BookmarkedPost(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at'] 
        unique_together = ('user', 'post')
        
        
class Repost(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at'] 
        unique_together = ('user', 'post')
        
    @property
    def type(self):
        return "repost"
        
        
class Comment(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    post = models.ForeignKey('Post', related_name='comments', on_delete=models.CASCADE)
    parent_comment = models.ForeignKey('self', null=True, blank=True, related_name='replies', on_delete=models.CASCADE)
    parent_reply = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE)
    body = models.CharField(max_length=250)
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="likedcomments", through="LikedComment")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Comment by {self.author} | {self.created_at.strftime('%b %d, %Y')} | {self.uuid}" 
    
    @property
    def type(self):
        return "comment"
    
    
class LikedComment(models.Model):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at'] 
        unique_together = ('user', 'comment')
        
    @property
    def type(self):
        return "likedcomment"