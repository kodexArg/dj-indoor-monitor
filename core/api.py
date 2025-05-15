from django.utils import timezone
from django.db.models import Q, F, Window, OuterRef, Subquery, Max
from django.db.models.functions import Rank
from rest_framework import viewsets, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from abc import ABC, abstractmethod
from functools import lru_cache
from .models import DataPoint, Sensor
from .serializers import DataPointSerializer, DataPointRoomSensorSerializer, DataPointRoomSerializer
from .utils import TIMEFRAME_MAP, get_timedelta_from_timeframe, get_start_date, to_bool
from .filters import DataPointFilter
import pandas as pd
from django_filters.rest_framework import DjangoFilterBackend
import logging
import time
from datetime import timedelta

# Configurar logger para endpoints
endpoints_logger = logging.getLogger('core.api.endpoints')

def format_time_delta(delta_seconds):
    """Convierte delta de segundos a formato legible (μs, ms, s, o Xm Ys)."""
    if delta_seconds < 0.001:
        return f"{delta_seconds * 1000000:.2f} μs"
    elif delta_seconds < 1:
        return f"{delta_seconds * 1000:.2f} ms"
    elif delta_seconds < 60:
        return f"{delta_seconds:.2f} s"
    else:
        delta = timedelta(seconds=delta_seconds)
        minutes, seconds = divmod(delta.seconds, 60)
        return f"{minutes}m {seconds:.2f}s"


class DataPointViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el modelo DataPoint. Proporciona endpoints CRUD estándar y acciones personalizadas.

    **Endpoints Estándar (derivados de ModelViewSet):**
      - `GET /api/data-point/`: Lista todos los DataPoints.
      - `POST /api/data-point/`: Crea un nuevo DataPoint.
      - `GET /api/data-point/{id}/`: Obtiene un DataPoint específico.
      - `PUT /api/data-point/{id}/`: Actualiza un DataPoint específico.
      - `PATCH /api/data-point/{id}/`: Actualiza parcialmente un DataPoint específico.
      - `DELETE /api/data-point/{id}/`: Elimina un DataPoint específico.

    **Acciones Personalizadas:**
      - `GET /api/data-point/latest/`: Obtiene el último registro para cada sensor.
      - `GET /api/data-point/timeframed/`: Obtiene registros agregados por un intervalo de tiempo (`timeframe`).

    **Parámetros de Consulta Comunes (aplicables a `list`, `latest`, `timeframed` y potencialmente a endpoints de detalle donde tenga sentido):**
      - `start_date`: Fecha de inicio (ISO8601) para filtrar los datos.
      - `end_date`: Fecha de fin (ISO8601) para filtrar los datos.
      - `sensors`: Lista de nombres de sensores (separados por coma o parámetro múltiple) para filtrar.
      - `metadata`: Booleano (`true`/`false`). Si es `true`, incluye metadatos sobre la consulta en la respuesta.
      - `include_room`: Booleano (`true`/`false`). Si es `true`, incluye el nombre del `room` asociado a cada sensor.
      - Para `timeframed` específicamente:
          - `timeframe`: Intervalo de agregación (e.g., '5S', '1T', '1H', '1D').
          - `aggregations`: Booleano (`true`/`false`). Si es `true`, devuelve múltiples agregaciones (min, max, mean, first, last); si es `false` (defecto), solo `mean`.
    """
    queryset = DataPoint.objects.all()
    serializer_class = DataPointSerializer
    filterset_class = DataPointFilter
    filter_backends = [DjangoFilterBackend]

    def list(self, request, *args, **kwargs):
        endpoint = "GET /api/data-point/"
        start_time = time.time()
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        endpoints_logger.debug(f"[{timestamp}] ▶️ Iniciando {endpoint}")
        
        filtered_queryset = self.filter_queryset(self.get_queryset())
        processor = ListData(queryset=filtered_queryset, query_parameters=request.query_params, request=request)
        response = Response(processor.process())
        
        end_time = time.time()
        execution_time = end_time - start_time
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        endpoints_logger.debug(f"[{timestamp}] ✅ Completado {endpoint} en {format_time_delta(execution_time)}")
        
        return response

    def create(self, request, *args, **kwargs):
        endpoint = "POST /api/data-point/"
        start_time = time.time()
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        endpoints_logger.debug(f"[{timestamp}] ▶️ Iniciando {endpoint}")
        
        response = super().create(request, *args, **kwargs)
        
        end_time = time.time()
        execution_time = end_time - start_time
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        endpoints_logger.debug(f"[{timestamp}] ✅ Completado {endpoint} en {format_time_delta(execution_time)}")
        
        return response

    @action(detail=False, methods=['get'])
    def latest(self, request):
        """
        Último registro por sensor.

        Filtros opcionales (query params): `start_date`, `end_date`, `sensors`, `metadata`, `include_room`.
        """
        endpoint = "GET /api/data-point/latest/"
        start_time = time.time()
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        endpoints_logger.debug(f"[{timestamp}] ▶️ Iniciando {endpoint}")
        
        filtered_queryset = self.filter_queryset(self.get_queryset())
        processor = LatestData(queryset=filtered_queryset, query_parameters=request.GET, request=request)
        response = Response(processor.process())
        
        end_time = time.time()
        execution_time = end_time - start_time
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        endpoints_logger.debug(f"[{timestamp}] ✅ Completado {endpoint} en {format_time_delta(execution_time)}")
        
        return response

    @action(detail=False, methods=['get'])
    def timeframed(self, request):
        """
        Registros agregados por intervalo (`timeframe`).

        Filtros/parámetros (query params): `start_date`, `end_date`, `sensors`, `timeframe` (e.g., '1H'), `aggregations` (bool), `metadata`, `include_room`.
        """
        endpoint = "GET /api/data-point/timeframed/"
        timeframe = request.GET.get('timeframe', '1H')
        start_time = time.time()
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        endpoints_logger.debug(f"[{timestamp}] ▶️ Iniciando {endpoint} con timeframe={timeframe}")

        filtered_queryset = self.filter_queryset(self.get_queryset())
        sensors = request.GET.getlist('sensors') or request.GET.get('sensors')
        if sensors:
            if isinstance(sensors, str):
                sensors = [s.strip() for s in sensors.split(',')]
            filtered_queryset = filtered_queryset.filter(sensor__in=sensors)
        metrics = request.GET.getlist('metrics') or request.GET.get('metrics')
        if metrics:
            if isinstance(metrics, str):
                metrics = [m.strip() for m in metrics.split(',')]
            filtered_queryset = filtered_queryset.filter(metric__in=metrics)
        from_date = request.GET.get('start_date')
        to_date = request.GET.get('end_date')
        max_days = 7
        if from_date and to_date:
            from_dt = pd.to_datetime(from_date)
            to_dt = pd.to_datetime(to_date)
            if (to_dt - from_dt).days > max_days:
                from_dt = to_dt - pd.Timedelta(days=max_days)
                filtered_queryset = filtered_queryset.filter(timestamp__gte=from_dt)
        processor = TimeframedData(queryset=filtered_queryset, query_parameters=request.GET, request=request)
        response = Response(processor.process())
        end_time = time.time()
        execution_time = end_time - start_time
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        endpoints_logger.debug(f"[{timestamp}] ✅ Completado {endpoint} en {format_time_delta(execution_time)}")
        return response


class DataPointQueryProcessor(generics.GenericAPIView, ABC):
    """
    Clase base abstracta para procesar consultas de DataPoint.

    Maneja lógica común de filtrado, paginación y serialización.
    Requiere `queryset` y opcionalmente `query_parameters` y `request`.
    Determina `include_room` y `paginate` basado en `query_parameters`.
    """
    
    def __init__(self, queryset, query_parameters=None, request=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = queryset
        self.query_parameters = query_parameters if query_parameters is not None else {}
        self.request = request
        self.include_room = to_bool(self.query_parameters.get('include_room', False))
        self.paginate = to_bool(self.query_parameters.get('paginate', True))  # Default to True
        
        self.sensor_room_map = None
        if self.include_room:
            self.sensor_room_map = self._get_sensor_room_map()

    @lru_cache(maxsize=32)
    def _get_sensor_room_map(self):
        """Cachea y retorna mapeo sensor -> room.name."""
        return {
            sensor.name: sensor.room.name 
            for sensor in Sensor.objects.select_related('room').all()
        }
    
    def _get_sensor_room_map_filtered(self, sensor_names):
        """Cachea y retorna mapeo sensor -> room.name para sensores específicos."""
        if not sensor_names:
            result = self._get_sensor_room_map()
        else:
            result = {
                sensor.name: sensor.room.name 
                for sensor in Sensor.objects.select_related('room').filter(name__in=sensor_names)
            }
        return result

    def _filter_by_metric_range(self, queryset):
        """Filtra queryset por rangos de métricas válidos (t, h, s) y preserva métricas no definidas."""
        valid_ranges = {
            't': {'min': 2, 'max': 70},
            'h': {'min': 2, 'max': 99},
            's': {'min': 2, 'max': 99}
        }
        
        metric_filter = Q()
        for metric, ranges in valid_ranges.items():
            metric_filter |= (
                Q(metric=metric) & 
                Q(value__gte=ranges['min']) & 
                Q(value__lte=ranges['max'])
            )
        
        defined_metrics = list(valid_ranges.keys())
        metric_filter |= ~Q(metric__in=defined_metrics)
        
        result = queryset.filter(metric_filter)
        return result

    def apply_filters(self):
        """Aplica filtros adicionales específicos del procesador (no manejados por DataPointFilter)."""
        return self.queryset

    def get_values_list(self):
        """Retorna lista de campos estándar para consultas de DataPoint."""
        return ['timestamp', 'sensor', 'metric', 'value']

    def get_serializer_context(self):
        """Construye contexto para el serializador, incluyendo `include_room` y `sensor_room_map`."""
        return {
            'include_room': self.include_room, 
            'sensor_room_map': self.sensor_room_map if self.include_room else {}
        }
    
    def get_appropriate_serializer(self, queryset, include_room=False, context=None):
        """Selecciona y configura `DataPointRoomSensorSerializer` o `DataPointSerializer` según `include_room`."""
        context = context or self.get_serializer_context()
        
        if include_room:
            result = DataPointRoomSensorSerializer(queryset, many=True, context=context).data
        else:
            result = DataPointSerializer(queryset, many=True, context=context).data
        return result

    @abstractmethod
    def get(self):
        """Método abstracto para obtener datos; implementado por subclases."""
        pass

    def process(self):
        """Procesa datos y retorna respuesta formateada, manejando paginación y metadata."""
        start_time = timezone.now()
        
        start_date = self.query_parameters.get('start_date') 
        if not start_date:
            start_date = (timezone.now() - get_timedelta_from_timeframe('1D')).isoformat()

        end_date = self.query_parameters.get('end_date')
        if not end_date:
            end_date = timezone.now().isoformat()

        result = self.get()

        if self.request and hasattr(self, 'paginate_queryset') and self.paginate:
            paginated = self.paginate_queryset(result)
            if paginated is not None:
                result = self.get_paginated_response(paginated).data

        if to_bool(self.query_parameters.get('metadata', False)):
            elapsed_time = (timezone.now() - start_time).total_seconds()
            
            metadata_dict = {
                'start_time': start_time.isoformat(),
                'elapsed_time': elapsed_time,
                'start_date': start_date,
                'end_date': end_date,
            }
            
            if hasattr(self, 'timeframe'):
                metadata_dict['timeframe'] = self.timeframe
            
            result = {
                'data': result,
                'metadata': metadata_dict
            }
            
        return result


class ListData(DataPointQueryProcessor):
    """Procesador para listar DataPoints filtrados. El filtrado principal es delegado al ViewSet."""
    
    def get(self):
        if not self.paginate:
            queryset_limited = self.queryset[:1000]
        else:
            queryset_limited = self.queryset
            
        if self.include_room:
            sensor_names = set(queryset_limited.values_list('sensor', flat=True).distinct())
            self.sensor_room_map = self._get_sensor_room_map_filtered(sensor_names)
            
        return self.get_appropriate_serializer(
            queryset_limited, 
            include_room=self.include_room
        )


class LatestData(DataPointQueryProcessor):
    """Procesador para obtener últimos DataPoints por sensor/métrica en un rango."""
    def get(self):
        start_date = self.query_parameters.get('start_date')
        end_date = self.query_parameters.get('end_date')
        if not end_date:
            end_date = timezone.now()
        else:
            end_date = timezone.make_aware(timezone.datetime.fromisoformat(end_date))
        if not start_date:
            start_date = end_date - get_timedelta_from_timeframe('1D')
        else:
            start_date = timezone.make_aware(timezone.datetime.fromisoformat(start_date))

        filtered_qs = self.queryset.filter(timestamp__gte=start_date, timestamp__lte=end_date)

        values_fields = ['timestamp', 'sensor', 'metric', 'value']
        latest_datapoints = filtered_qs.order_by('sensor', '-timestamp').distinct('sensor').values(*values_fields)

        if self.include_room:
            sensor_names = set(item['sensor'] for item in latest_datapoints)
            self.sensor_room_map = self._get_sensor_room_map_filtered(sensor_names)
            for item in latest_datapoints:
                item['room'] = self.sensor_room_map.get(item['sensor'], '')

        if self.include_room:
            return [
                {
                    'timestamp': item['timestamp'].isoformat() if hasattr(item['timestamp'], 'isoformat') else str(item['timestamp']),
                    'room': item['room'],
                    'sensor': item['sensor'],
                    'metric': item['metric'],
                    'value': item['value']
                }
                for item in latest_datapoints
            ]
        else:
            return [
                {
                    'timestamp': item['timestamp'].isoformat() if hasattr(item['timestamp'], 'isoformat') else str(item['timestamp']),
                    'sensor': item['sensor'],
                    'metric': item['metric'],
                    'value': item['value']
                }
                for item in latest_datapoints
            ]


class TimeframedData(DataPointQueryProcessor):
    """Procesador para obtener DataPoints agrupados por intervalos de tiempo."""
    
    def __init__(self, queryset, query_parameters=None, request=None, *args, **kwargs):
        super().__init__(queryset, query_parameters, request, *args, **kwargs)
        self.timeframe = query_parameters.get('timeframe', '1H').upper() if query_parameters else '1H'
        self.aggregations = to_bool(query_parameters.get('aggregations', False)) if query_parameters else False

    def get(self):
        end_date = timezone.now()
        start_date = get_start_date(self.timeframe, end_date)
        queryset_timeframed = self.queryset.filter(timestamp__gte=start_date, timestamp__lte=end_date)
        values_list = self.get_values_list()
        data_values = list(queryset_timeframed.values(*values_list))
        if not data_values:
            return []
        if self.include_room:
            unique_sensors = set(item['sensor'] for item in data_values)
            self.sensor_room_map = self._get_sensor_room_map_filtered(unique_sensors)
        df = pd.DataFrame(data_values)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        if self.include_room:
            df['room'] = df['sensor'].map(self.sensor_room_map)
            df['room'] = df['room'].fillna('')
        df = df.set_index('timestamp').sort_index()
        group_cols = ['room', 'metric'] if self.include_room else ['sensor', 'metric']
        if self.aggregations:
            results = self._process_with_aggregations(df, group_cols)
        else:
            results = self._process_without_aggregations(df, group_cols)
        return DataPointRoomSerializer(results, many=True).data if self.include_room else DataPointSerializer(results, many=True).data

    def _process_with_aggregations(self, df, group_cols):
        """Procesa DataFrame aplicando múltiples agregaciones (media, min, max, first, last)."""
        if df.empty:
            return []
            
        df_reduced = df[['value'] + [col for col in group_cols if col in df.columns]]
        
        agg_funcs = ['mean', 'min', 'max', 'first', 'last']
        grouped = df_reduced.groupby([*group_cols, pd.Grouper(freq=TIMEFRAME_MAP[self.timeframe])])['value'].agg(agg_funcs).reset_index()
        grouped = grouped.rename(columns={'timestamp': 'timeframed_timestamp'})
        
        results = []
        for _, row in grouped.iterrows():
            result_dict = {
                'timestamp': row['timeframed_timestamp'].isoformat(),
            }
            
            if 'room' in group_cols:
                result_dict['room'] = row['room']
            else:
                result_dict['sensor'] = row['sensor']
                
            result_dict['metric'] = row['metric']
            result_dict['value'] = {
                'mean': round(row['mean'], 2),
                'min': round(row['min'], 2),
                'max': round(row['max'], 2),
                'first': round(row['first'], 2),
                'last': round(row['last'], 2)
            }
            
            results.append(result_dict)
        
        return results
    def _process_without_aggregations(self, df, group_cols):
        """Procesa DataFrame aplicando solo la media como agregación."""
        if df.empty:
            return []
            
        df_reduced = df[['value'] + [col for col in group_cols if col in df.columns]]
        
        grouped = df_reduced.groupby([*group_cols, pd.Grouper(freq=TIMEFRAME_MAP[self.timeframe])])['value'].mean().reset_index()
        grouped = grouped.rename(columns={'timestamp': 'timeframed_timestamp', 'value': 'mean_value'})
        
        results = []
        for _, row in grouped.iterrows():
            result_dict = {
                'timestamp': row['timeframed_timestamp'].isoformat(),
            }
            
            if 'room' in group_cols:
                result_dict['room'] = row['room']
            else:
                result_dict['sensor'] = row['sensor']
                
            result_dict['metric'] = row['metric']
            result_dict['value'] = round(row['mean_value'], 2)
            
            results.append(result_dict)
        
        return results
