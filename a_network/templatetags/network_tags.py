from django import template
from ..models import Follow

register = template.Library()

@register.filter
def is_following(user, this_user):
    """
    Check if `user` is following `this_user`.
    Use as: {{ user|is_following:other_user }}
    Returns False if either user is not authenticated.
    """
    # Check if user is authenticated before querying
    if not user or not user.is_authenticated:
        return False
    if not this_user:
        return False
    return Follow.objects.filter(follower=user, following=this_user).exists()

@register.simple_tag
def is_following_tag(user, this_user):
    """
    Check if `user` is following `this_user`.
    Use as: {% is_following_tag user other_user %}
    Returns False if either user is not authenticated.
    """
    if not user or not user.is_authenticated:
        return False
    if not this_user:
        return False
    return Follow.objects.filter(follower=user, following=this_user).exists()