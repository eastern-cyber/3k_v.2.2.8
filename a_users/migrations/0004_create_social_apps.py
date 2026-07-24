import os
from django.db import migrations
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

def create_social_apps(apps, schema_editor):
    site, created = Site.objects.get_or_create(
        domain='v228.3kok.app',
        defaults={'name': 'v228.3kok.app'}
    )
    
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    secret = os.getenv('GOOGLE_SECRET')
    
    if client_id and secret:
        app, created = SocialApp.objects.get_or_create(
            provider='google',
            defaults={
                'name': 'Google',
                'client_id': client_id,
                'secret': secret,
            }
        )
        if site not in app.sites.all():
            app.sites.add(site)

def delete_social_apps(apps, schema_editor):
    SocialApp = apps.get_model('socialaccount', 'SocialApp')
    SocialApp.objects.filter(provider='google').delete()

class Migration(migrations.Migration):
    dependencies = [
        ('a_users', '0003_auto_20260724_1642'),
    ]

    operations = [
        migrations.RunPython(create_social_apps, delete_social_apps),
    ]
