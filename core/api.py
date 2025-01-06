# Python built-in
from datetime import datetime, timedelta, timezone
from typing import Dict
from time import perf_counter

# Django y DRF
from django.conf import settings
from django.db.models import QuerySet, Min, Max, Count
from django.db.models.functions import TruncSecond, TruncMinute, TruncHour, TruncDay
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
import pandas as pd

# Local
from .models import SensorData
from .serializers import SensorDataSerializer
from .filters import SensorDataFilter
from .utils import get_start_date

class SensorDataViewSet(viewsets.ModelViewSet):
    """
    API para gestionar datos de sensores. Permite obtener, filtrar y escribir datos.
    Incluye metadatos sobre el rango de fechas, número de registros y demora del backend.

    Parámetros:
    - seconds: Opcional. Número de segundos para obtener datos.
    - start_date y end_date: Opcional. Rango de fechas para obtener datos.
    - metric: Opcional. Métrica a obtener ('t' temperatura, 'h' humedad).
    - freq: Frecuencia para agrupar datos ('5s', '5T', '30T', '1H', '4H', '1D').

    Endpoints:
    - GET /api/sensor-data/ : Lista de registros con metadatos
    - GET /api/sensor-data/timeframed/ : Datos agrupados por intervalos
    - GET /api/sensor-data/latest/ : Últimos valores por sensor
    """
    serializer_class = SensorDataSerializer
    filterset_class = SensorDataFilter
    _query_start_time = None
    _query_timestamp = None

    TIMEFRAME_MAPPING = {
        '5s': ('5S', TruncSecond, 'second'),
        '5T': ('5min', TruncMinute, 'minute'),
        '30T': ('30min', TruncMinute, 'minute'),
        '1H': ('1H', TruncHour, 'hour'),
        '4H': ('4H', TruncHour, 'hour'),
        '1D': ('1D', TruncDay, 'day')
    }

    def _get_timeframe_params(self, freq: str) -> tuple:
        """Obtiene los parámetros de agrupación para un timeframe dado"""
        if freq not in self.TIMEFRAME_MAPPING:
            raise ValueError(f"Frecuencia {freq} no válida. Valores permitidos: {list(self.TIMEFRAME_MAPPING.keys())}")
        return self.TIMEFRAME_MAPPING[freq]

    def initial(self, request, *args, **kwargs):
        """Método DRF: Se ejecuta al inicio de cada solicitud"""
        self._query_timestamp = datetime.now(timezone.utc)
        self._query_start_time = perf_counter()
        super().initial(request, *args, **kwargs)

    def get_metadata(self, queryset) -> Dict:
        """Genera metadatos para el queryset actual"""
        metadata = queryset.aggregate(
            start_date=Min('timestamp'),
            end_date=Max('timestamp'),
            record_count=Count('id')
        )
        return {
            **metadata,
            'sensor_ids': sorted(list(set(queryset.values_list('sensor', flat=True)))),
            'query_timestamp': self._query_timestamp,
            'query_delay': round(perf_counter() - self._query_start_time, 3)
        }

    def get_queryset(self) -> QuerySet[SensorData]:
        """Método DRF: Define el queryset base con filtros temporales"""
        queryset = SensorData.objects.all().order_by('-timestamp')
        
        max_time_threshold = datetime.now(timezone.utc) - timedelta(minutes=settings.MAX_DATA_MINUTES)
        seconds = self.request.query_params.get('seconds', None)
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        if seconds:
            seconds = int(seconds)
            since = max(max_time_threshold, datetime.now(timezone.utc) - timedelta(seconds=seconds))
            queryset = queryset.filter(timestamp__gte=since)
        elif start_date:
            start_date = datetime.fromisoformat(start_date)
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            queryset = queryset.filter(timestamp__gte=start_date)
        elif end_date:
            end_date = datetime.fromisoformat(end_date)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            queryset = queryset.filter(timestamp__lte=end_date)
        
        action = getattr(self, 'action', None)
        if not any([seconds, start_date, end_date]) and action not in ['timeframed', 'latest']:
            queryset = queryset[:settings.DEFAULT_QUERY_LIMIT]
        
        return queryset

    def list(self, request, *args, **kwargs):
        """Método DRF: Lista registros incluyendo metadatos"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        metadata = self.get_metadata(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data['metadata'] = metadata
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'metadata': metadata,
            'results': serializer.data
        })

    @action(detail=False, methods=['get'])
    def latest(self, request) -> Response:
        """Obtiene el último valor de cada sensor en los últimos 5 minutos"""
        since = datetime.now(timezone.utc) - timedelta(minutes=5)
        base_queryset = SensorData.objects.filter(timestamp__gte=since)
        
        latest_data = []
        sensors = base_queryset.values_list('sensor', flat=True).distinct()
        
        for sensor in sensors:
            latest_record = base_queryset.filter(sensor=sensor).order_by('-timestamp').first()
            if latest_record:
                latest_data.append({
                    'timestamp': latest_record.timestamp.isoformat(),
                    'sensor': latest_record.sensor,
                    't': round(latest_record.t, 2),
                    'h': round(latest_record.h, 2)
                })

        return Response(latest_data)

    @action(detail=False, methods=['get'])
    def timeframed(self, request) -> Response:
        """
        Datos agrupados por intervalos con estadísticas.
        Útil para gráficos de velas (OHLC) y análisis estadístico.
        
        Parámetros:
        - freq: Intervalo de agrupación ('5s', '5T', '30T', '1H', '4H', '1D')
        - start_date, end_date: Rango de fechas (opcional)
        - sensor: ID del sensor (opcional)
        """
        freq = request.query_params.get('freq', '30T')
        pandas_freq, trunc_func, field = self._get_timeframe_params(freq)
        
        queryset = self.filter_queryset(self.get_queryset())
        df = pd.DataFrame(list(queryset.values('timestamp', 'sensor', 't', 'h')))
        
        if df.empty:
            return Response({
                'metadata': self.get_metadata(queryset),
                'results': []
            })

        # Ordenar por timestamp para asegurar first/last correctos
        df = df.sort_values('timestamp')
        
        # Configurar índice y agrupar con funciones adicionales
        df.set_index('timestamp', inplace=True)
        grouped = df.groupby(['sensor', pd.Grouper(freq=pandas_freq)]).agg({
            't': [
                ('mean', 'mean'),
                ('min', 'min'),
                ('max', 'max'),
                ('count', 'count'),
                ('first', 'first'),
                ('last', 'last')
            ],
            'h': [
                ('mean', 'mean'),
                ('min', 'min'),
                ('max', 'max'),
                ('first', 'first'),
                ('last', 'last')
            ]
        }).round(2)

        # Formatear resultados
        results = []
        for (sensor, timestamp), data in grouped.iterrows():
            results.append({
                'timestamp': timestamp.isoformat(),
                'sensor': sensor,
                'temperature': {
                    'mean': data[('t', 'mean')],
                    'min': data[('t', 'min')],
                    'max': data[('t', 'max')],
                    'count': int(data[('t', 'count')]),
                    'first': data[('t', 'first')],
                    'last': data[('t', 'last')]
                },
                'humidity': {
                    'mean': data[('h', 'mean')],
                    'min': data[('h', 'min')],
                    'max': data[('h', 'max')],
                    'first': data[('h', 'first')],
                    'last': data[('h', 'last')]
                }
            })

        return Response({
            'metadata': {
                **self.get_metadata(queryset),
                'timeframe': freq,
                'groups': len(results)
            },
            'results': results
        })

