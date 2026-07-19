from django.shortcuts import render
from django.http import HttpResponse
from django.views import View

class OriginHome(View):
    def get(self, request):
        return HttpResponse('Home directory')