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
from .utils import get_timedelta_from_timeframe, get_start_date, format_timestamp

class SensorDataViewSet(viewsets.ModelViewSet):
    """
    API para gestionar datos de sensores. Permite obtener, filtrar y escribir datos.
    Incluye metadatos sobre el rango de fechas, número de registros y demora del backend.

    Parámetros:
    - seconds: Opcional. Número de segundos para obtener datos.
    - start_date y end_date: Opcional. Rango de fechas para obtener datos.
    - metric: Opcional. Métrica a obtener ('t' temperatura, 'h' humedad).
    - timeframe: Intervalo de tiempo ('5s', '5T', '30T', '1h', '4h', '1D').

    Endpoints:
    - GET /api/sensor-data/ : Lista de registros con metadatos
    - GET /api/sensor-data/timeframed/ : Datos agrupados por intervalos
    - GET /api/sensor-data/latest/ : Últimos valores por sensor
    """
    serializer_class = SensorDataSerializer
    filterset_class = SensorDataFilter
    _query_start_time = None
    _query_timestamp = None

    def initial(self, request, *args, **kwargs):
        """Método DRF: Se ejecuta al inicio de cada solicitud"""
        self._query_timestamp = datetime.now(timezone.utc)
        self._query_start_time = perf_counter()
        super().initial(request, *args, **kwargs)

    def get_metadata(self, queryset) -> Dict:
        """Genera metadatos para el queryset actual"""
        timeframe = self.request.query_params.get('timeframe', '5s')
        end_date = datetime.now(timezone.utc)
        time_window = get_timedelta_from_timeframe(timeframe)
        start_date = get_start_date(timeframe, end_date)

        return {
            **queryset.aggregate(
                start_date=Min('timestamp'),
                end_date=Max('timestamp'),
                record_count=Count('id')
            ),
            'sensor_ids': sorted(list(set(queryset.values_list('sensor', flat=True)))),
            'query_timestamp': self._query_timestamp,
            'query_delay': round(perf_counter() - self._query_start_time, 3),
            'timeframe': timeframe,
            'time_window': int(time_window.total_seconds()),
            'debug': {
                'timeframe': timeframe,
                'window_seconds': int(time_window.total_seconds()),
                'start_pretty': format_timestamp(start_date),
                'end_pretty': format_timestamp(end_date),
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'delay_ms': round((perf_counter() - self._query_start_time) * 1000, 1)
            }
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
        """
        Obtiene el último valor de cada sensor activo.
        
        Retorna una lista de lecturas recientes (últimos 5 minutos) por sensor:
        [
            {
                "timestamp": "2025-01-06T12:35:50.068720-03:00",
                "sensor": "vege-d4",
                "t": 19.4,
                "h": 62.3
            },
            ...
        ]
        """
        since = datetime.now(timezone.utc) - timedelta(minutes=5)
        base_queryset = SensorData.objects.filter(timestamp__gte=since)
        
        latest_data = []
        sensors = base_queryset.values_list('sensor', flat=True).distinct()
        
        for sensor in sensors:
            latest_record = base_queryset.filter(sensor=sensor).order_by('-timestamp').first()
            if latest_record:
                latest_data.append({
                    'timestamp': latest_record.timestamp.isoformat(),
                    'timestamp_pretty': format_timestamp(latest_record.timestamp, include_seconds=True),
                    'sensor': latest_record.sensor,
                    't': round(latest_record.t, 2),
                    'h': round(latest_record.h, 2)
                })

        return Response(latest_data)

    @action(detail=False, methods=['get'])
    def timeframed(self, request) -> Response:
        """
        Agrupa datos por intervalos para cada sensor, calculando estadísticas.
        
        Ejemplos de uso:
        ```python
        # Datos del último día agrupados por hora
        GET /api/sensor-data/timeframed/?timeframe=1h

        # Datos entre fechas específicas agrupados cada 30 minutos
        GET /api/sensor-data/timeframed/?timeframe=30T&start_date=2025-01-06T00:00:00Z&end_date=2025-01-07T00:00:00Z

        # Datos de un sensor específico agrupados cada 5 segundos
        GET /api/sensor-data/timeframed/?timeframe=5s&sensor=vege-d4
        ```

        Parámetros:
        - timeframe (str): Intervalo de agrupación ('5s', '5T', '30T', '1h', '4h', '1D')
        - start_date (str): Fecha inicial en formato ISO (opcional)
        - end_date (str): Fecha final en formato ISO (opcional)
        - sensor (str): ID del sensor para filtrar (opcional)

        Respuesta:
        {
            "metadata": {...},
            "results": [...]
        }
        """
        freq = request.query_params.get('timeframe', '5s')
        
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
        grouped = df.groupby(['sensor', pd.Grouper(freq=freq)]).agg({
            't': ['mean', 'min', 'max', 'count', 'first', 'last'],
            'h': ['mean', 'min', 'max', 'first', 'last']
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

