# Django and DRF 
from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import JsonResponse, HttpResponse
from django.utils.timezone import localtime
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.template import loader
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

# Python 
from datetime import datetime, timedelta, timezone
import json
import requests

# Third-party and local imports
from loguru import logger
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
from .models import SensorData
from .serializers import SensorDataSerializer


MAX_DATA_MINUTES = 5

class HomeView(TemplateView):
    template_name = 'home.html'
    
class DevelopmentView(TemplateView):
    template_name = 'development.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['minutes'] = MAX_DATA_MINUTES
        time_threshold = datetime.now(timezone.utc) - timedelta(minutes=MAX_DATA_MINUTES)
        context['data'] = SensorData.objects.filter(
            timestamp__gte=time_threshold
        ).order_by('-timestamp')
        return context

class SensorDataAPIView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            rpi = request.GET.get('rpi')
            since = request.GET.get('since')
            seconds = request.GET.get('seconds')
            
            if since:
                time_threshold = datetime.fromisoformat(since)
            elif seconds:
                seconds = min(int(seconds), MAX_DATA_MINUTES * 60)
                time_threshold = datetime.now(timezone.utc) - timedelta(seconds=seconds)
            else:
                time_threshold = datetime.now(timezone.utc) - timedelta(seconds=MAX_DATA_MINUTES * 60)

            qs = SensorData.objects.filter(timestamp__gte=time_threshold)
            if rpi:
                qs = qs.filter(rpi=rpi)
            
            qs = qs.order_by('-timestamp')  # Asegurar orden descendente

            serializer = SensorDataSerializer(qs, many=True)
            return JsonResponse(serializer.data, safe=False, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error processing GET request: {str(e)}")
            return JsonResponse(
                {"error": "Error processing request", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request, *args, **kwargs):
        try:
            serializer = SensorDataSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                timestamp = localtime(serializer.instance.timestamp).strftime('%H:%M:%S')
                logger.debug(f"S: {timestamp} ✅")
                return JsonResponse({"message": "Data received"}, status=status.HTTP_201_CREATED)
            
            logger.error(f"Validation error: {serializer.errors}")
            return JsonResponse(
                {"error": "Validation error", "detail": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        except json.JSONDecodeError:
            return JsonResponse(
                {"error": "Invalid JSON format"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error processing POST request: {str(e)}")
            return JsonResponse(
                {"error": "Error processing request", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

def fetch_data(request, rpi=None, seconds=None):
    """Fetch sensor data from the API using the current request context."""
    api_url = request.build_absolute_uri(reverse('sensor-data'))
    
    params = {}
    if seconds:
        params['seconds'] = seconds
    if rpi:
        params['rpi'] = rpi
    
    response = requests.get(api_url, params=params)
    data = response.json()
    
    for item in data:
        item['timestamp'] = datetime.fromisoformat(item['timestamp'])
    
    return data

def latest_data_table(request):
    data = fetch_data(request)
    return render(request, 'partials/latest-data-table-rows.html', {'data': data})

def latest_data_chart(request):
    time_threshold = datetime.now(timezone.utc) - timedelta(minutes=MAX_DATA_MINUTES)
    logger.debug(f"Time threshold: {time_threshold}")
    data = SensorData.objects.filter(timestamp__gte=time_threshold).order_by('-timestamp')
    logger.debug(f"Data: {data}")
    df = pd.DataFrame(list(data.values('timestamp', 'temperature', 'rpi')))
    data_json = df.to_json(orient='records', date_format='iso')

    context = {
        'data_json': data_json
    }
    return HttpResponse(request, 'partials/latest-data-chart.html')

