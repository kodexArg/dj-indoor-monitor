from django.shortcuts import render
from django.views.generic import TemplateView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from django.utils.timezone import localtime
from datetime import datetime, timedelta, timezone
from django.core.exceptions import ValidationError
from loguru import logger
import json
from .models import SensorData
from .serializers import SensorDataSerializer


LATEST_DATA_MINUTES = 600 

class HomeView(TemplateView):
    template_name = 'home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['minutes'] = LATEST_DATA_MINUTES
        return context

class DevelopmentView(TemplateView):
    template_name = 'development.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['minutes'] = LATEST_DATA_MINUTES
        time_threshold = datetime.now(timezone.utc) - timedelta(minutes=LATEST_DATA_MINUTES)
        context['data'] = SensorData.objects.filter(
            timestamp__gte=time_threshold
        ).order_by('-timestamp')
        return context

class SensorDataAPIView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            raspberry_pi_id = kwargs.get('raspberry_pi_id')
            seconds = kwargs.get('seconds', LATEST_DATA_MINUTES * 60)
            time_threshold = datetime.now(timezone.utc) - timedelta(seconds=seconds)

            qs = SensorData.objects.filter(timestamp__gte=time_threshold)

            if raspberry_pi_id:
                qs = qs.filter(rpi=raspberry_pi_id)

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

def latest_data_table(request):
    time_threshold = datetime.now(timezone.utc) - timedelta(minutes=LATEST_DATA_MINUTES)
    data = SensorData.objects.filter(timestamp__gte=time_threshold).order_by('-timestamp')
    return render(request, 'partials/latest-data-table-rows.html', {'data': data})

