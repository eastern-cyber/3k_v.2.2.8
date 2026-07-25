from django.shortcuts import render

def terms_view(request):
    return render(request, 'a_pages/terms.html')

def privacy_view(request):
    return render(request, 'a_pages/privacy.html')
