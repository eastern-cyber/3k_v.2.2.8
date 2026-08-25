# a_posts/forms.py
from django import forms
from .models import Post

class PostForm(forms.ModelForm):
    tags = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'input-field','placeholder': '#tags - separated by a space', 'maxlength': '80'}))
    file = forms.FileField()
    link_url = forms.URLField(required=False, widget=forms.URLInput(attrs={
        'class': 'input-field',
        'placeholder': 'https://example.com',
        'maxlength': '200'
    }))
    link_title = forms.CharField(required=False, max_length=100, widget=forms.TextInput(attrs={
        'class': 'input-field',
        'placeholder': 'Link caption (optional)',
        'maxlength': '100'
    }))
    
    class Meta:
        model = Post
        fields = ['body', 'link_url', 'link_title']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['link_url'].required = False
        self.fields['link_title'].required = False


class PostEditForm(forms.ModelForm):
    tags = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'input-field','placeholder': '#tags - separated by a space', 'maxlength': '80'}))
    link_url = forms.URLField(required=False, widget=forms.URLInput(attrs={
        'class': 'input-field',
        'placeholder': 'https://example.com',
        'maxlength': '200'
    }))
    link_title = forms.CharField(required=False, max_length=100, widget=forms.TextInput(attrs={
        'class': 'input-field',
        'placeholder': 'Link caption (optional)',
        'maxlength': '100'
    }))
    
    class Meta:
        model = Post
        fields = ['body', 'link_url', 'link_title']
        widgets = {
            'body': forms.Textarea(attrs={'class': 'input-field resize-none','rows':2, 'placeholder': 'Add a caption here...', 'maxlength': '80'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['link_url'].required = False
        self.fields['link_title'].required = False
        
        if self.instance.pk:
            # Handle tags
            tag_objs = self.instance.tags.all()
            tags = [str(tag) for tag in tag_objs] 
            if tags:
                self.initial['tags'] = " ".join(tags)
            else:
                self.initial['tags'] = ""
            
            # Handle link_url
            if self.instance.link_url:
                self.initial['link_url'] = self.instance.link_url
            else:
                self.initial['link_url'] = ""
            
            # Handle link_title
            if self.instance.link_title:
                self.initial['link_title'] = self.instance.link_title
            else:
                self.initial['link_title'] = ""
    
    def clean_link_url(self):
        """Clean and validate the link_url field"""
        link_url = self.cleaned_data.get('link_url', '').strip()
        if not link_url:
            return None
        
        # Validate against allowed domains
        try:
            from urllib.parse import urlparse
            
            # Ensure URL has a scheme, add https:// if missing
            if not link_url.startswith(('http://', 'https://')):
                link_url = 'https://' + link_url
            
            parsed = urlparse(link_url)
            
            # Check if URL has a valid netloc
            if not parsed.netloc:
                raise forms.ValidationError("Please enter a valid URL.")
            
            # List of allowed domains (including subdomains)
            allowed_domains = [
                'dfi.fund',
                '3kok.app',
                'google.com',
                'google.co.th',
                'youtube.com',
                'youtu.be',
                'tiktok.com',
                'facebook.com',
                'instagram.com',
                'whatsapp.com',
                'x.com',
                'discord.com',
                'line.me',
                'linkedin.com',
                'xiaohongshu.com',
                'pinterest.com',
                'github.com',
                'apple.com',
                'shopee.co.th',
                'lazada.co.th'
            ]
            
            # Get the domain from the URL
            domain = parsed.netloc.lower()
            
            # Remove 'www.' prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Remove port number if present (e.g., example.com:8080)
            if ':' in domain:
                domain = domain.split(':')[0]
            
            # Check if the domain or any of its subdomains are allowed
            is_allowed = False
            for allowed_domain in allowed_domains:
                # Check if the domain exactly matches or is a subdomain
                if domain == allowed_domain or domain.endswith(f'.{allowed_domain}'):
                    is_allowed = True
                    break
            
            if not is_allowed:
                raise forms.ValidationError(
                    f"Only specific domains are allowed. Please use one of the following: {', '.join(allowed_domains)}"
                )
            
            return link_url
            
        except Exception as e:
            raise forms.ValidationError("Invalid URL format. Please enter a valid URL.")