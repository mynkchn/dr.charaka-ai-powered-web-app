from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Contact
from django.contrib import messages
# Create your views here.

def home(request):
    return render(request, 'core/home.html')

# @login_required
# def home_after_login(request):
#     return render(request, 'core/home_after_login.html')

def about(request):
    return render(request, 'core/about.html')

# def contact(request):
#     if request.method == 'POST':
#         name = request.POST.get('name')
#         email = request.POST.get('email')
#         subject = request.POST.get('subject')
#         message = request.POST.get('message')
    
#     obj=Contact.objects.create(name=name,email=email,subject=subject,message=message)
#     obj.save()
#     print(name, email, message)
#     return render(request, 'core/contact.html')

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        obj = Contact.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message
        )
        obj.save()
        messages.success(request, 'Contact Successful!')
    
        print(name, email, message)

    return render(request, 'core/contact.html')
