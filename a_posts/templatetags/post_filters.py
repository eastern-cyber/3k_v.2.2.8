# a_posts/templatetags/post_filters.py
from django import template

register = template.Library()

@register.filter
def clean_url(url):
    """Remove http://, https://, and www. from URL for display"""
    if not url:
        return url
    
    # Remove protocol
    cleaned = url.replace('https://', '').replace('http://', '')
    
    # Remove www. if it exists
    if cleaned.startswith('www.'):
        cleaned = cleaned[4:]
    
    return cleaned