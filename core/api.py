from django.utils import timezone
from django.db.models import Q, OuterRef, Subquery, Max
from rest_framework import viewsets, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from abc import ABC, abstractmethod
from functools import lru_cache
from .models import DataPoint, Sensor, Room
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
    """Convierte segundos en un formato legible para humanos"""
    if delta_seconds < 0.001:
        return f"{delta_seconds * 1000000:.2f} μs"  # microsegundos
    elif delta_seconds < 1:
        return f"{delta_seconds * 1000:.2f} ms"  # milisegundos
    elif delta_seconds < 60:
        return f"{delta_seconds:.2f} s"  # segundos
    else:
        # Para tiempos muy largos, usar formato más completo
        delta = timedelta(seconds=delta_seconds)
        minutes, seconds = divmod(delta.seconds, 60)
        return f"{minutes}m {seconds:.2f}s"


class DataPointViewSet(viewsets.ModelViewSet):
    """
    Módulo API para DataPoint.

    Este módulo expone endpoints para consultar datos a partir del modelo DataPoint.
    Se pueden aplicar filtros por fecha de inicio (start_date), fecha fin (end_date) y lista de sensores.
    La respuesta puede incluir metadatos (como tiempo de procesamiento y rango de fechas usado) si se especifica el parámetro 'metadata'.
    También puede incluir información del room asociado a cada sensor si se especifica include_room=true.

    Endpoints:
      - GET /api/data-point/         : Listado/creación de DataPoint.
      - GET /api/data-point/latest   : Últimos registros por sensor.
      - GET /api/data-point/timeframed : Registros dentro de un intervalo definido (ej., '1h', '4h', etc.).

    Parámetros comunes:
        - start_date: Fecha de inicio en formato ISO8601
        - end_date: Fecha fin en formato ISO8601
        - sensors: Lista de nombres de sensores
        - metadata: Booleano para incluir metadatos en la respuesta
        - include_room: Booleano para incluir el room asociado a cada sensor
    """
    queryset = DataPoint.objects.all()
    serializer_class = DataPointSerializer
    filterset_class = DataPointFilter
    filter_backends = [DjangoFilterBackend]

    def list(self, request, *args, **kwargs):
        # Registrar el inicio del endpoint
        endpoint = "GET /api/data-point/"
        start_time = time.time()
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        endpoints_logger.debug(f"[{timestamp}] ▶️ Iniciando {endpoint}")
        
        # Lógica del endpoint
        filtered_queryset = self.filter_queryset(self.get_queryset())
        processor = ListData(queryset=filtered_queryset, query_parameters=request.query_params, request=request)
        response = Response(processor.process())
        
        # Registrar el fin del endpoint con el tiempo de ejecución
        end_time = time.time()
        execution_time = end_time - start_time
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        endpoints_logger.debug(f"[{timestamp}] ✅ Completado {endpoint} en {format_time_delta(execution_time)}")
        
        return response

    def create(self, request, *args, **kwargs):
        # Registrar el inicio del endpoint
        endpoint = "POST /api/data-point/"
        start_time = time.time()
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        endpoints_logger.debug(f"[{timestamp}] ▶️ Iniciando {endpoint}")
        
        # Lógica del endpoint
        response = super().create(request, *args, **kwargs)
        
        # Registrar el fin del endpoint con el tiempo de ejecución
        end_time = time.time()
        execution_time = end_time - start_time
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        endpoints_logger.debug(f"[{timestamp}] ✅ Completado {endpoint} en {format_time_delta(execution_time)}")
        
        return response

    @action(detail=False, methods=['get'])
    def latest(self, request):
        """
        Retorna el último registro de cada sensor.

        Parámetros (opcional, vía query string):
            - start_date: Fecha de inicio en formato ISO8601
            - end_date: Fecha fin en formato ISO8601
            - sensors: Lista de nombres de sensores
            - metadata: Booleano para incluir metadatos en la respuesta
            - include_room: Booleano para incluir el room asociado a cada sensor
        """
        # Registrar el inicio del endpoint
        endpoint = "GET /api/data-point/latest/"
        start_time = time.time()
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        endpoints_logger.debug(f"[{timestamp}] ▶️ Iniciando {endpoint}")
        
        # Lógica del endpoint
        filtered_queryset = self.filter_queryset(self.get_queryset())
        processor = LatestData(queryset=filtered_queryset, query_parameters=request.GET, request=request)
        response = Response(processor.process())
        
        # Registrar el fin del endpoint con el tiempo de ejecución
        end_time = time.time()
        execution_time = end_time - start_time
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        endpoints_logger.debug(f"[{timestamp}] ✅ Completado {endpoint} en {format_time_delta(execution_time)}")
        
        return response

    @action(detail=False, methods=['get'])
    def timeframed(self, request):
        """
        Retorna registros agrupados por intervalos de tiempo.

        Parámetros (opcional, vía query string):
            - start_date: Fecha de inicio en formato ISO8601
            - end_date: Fecha fin en formato ISO8601
            - sensors: Lista de nombres de sensores
            - timeframe: Intervalo de tiempo ('5S', '1T', '30T', '1H', '4H', '1D')
            - aggregations: Si es True, devuelve min, max, first, last, mean. Por defecto False (devuelve solo mean)
            - metadata: Booleano para incluir metadata en la respuesta
            - include_room: Booleano para incluir el room asociado a cada sensor
        """
        # Registrar el inicio del endpoint
        endpoint = "GET /api/data-point/timeframed/"
        timeframe = request.GET.get('timeframe', '1H')
        start_time = time.time()
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        endpoints_logger.debug(f"[{timestamp}] ▶️ Iniciando {endpoint} con timeframe={timeframe}")
        
        # Lógica del endpoint
        filtered_queryset = self.filter_queryset(self.get_queryset())
        processor = TimeframedData(queryset=filtered_queryset, query_parameters=request.GET, request=request)
        response = Response(processor.process())
        
        # Registrar el fin del endpoint con el tiempo de ejecución
        end_time = time.time()
        execution_time = end_time - start_time
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        endpoints_logger.debug(f"[{timestamp}] ✅ Completado {endpoint} en {format_time_delta(execution_time)}")
        
        return response


class DataPointQueryProcessor(generics.GenericAPIView, ABC):
    """
    Clase base para procesadores de consultas de DataPoint.
    Abstrae la lógica común de procesamiento, filtrado y serialización.
    """
    
    def __init__(self, queryset, query_parameters=None, request=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = queryset
        self.query_parameters = query_parameters if query_parameters is not None else {}
        self.request = request
        self.include_room = to_bool(self.query_parameters.get('include_room', False))
        self.paginate = to_bool(self.query_parameters.get('paginate', True))  # Default to True
        
        # Solo cargamos el mapa de sensor-habitación si realmente lo necesitamos
        self.sensor_room_map = None
        if self.include_room:
            self.sensor_room_map = self._get_sensor_room_map()

    @lru_cache(maxsize=32)
    def _get_sensor_room_map(self):
        """
        Obtiene el mapeo de sensores a habitaciones y aplica caché para mejorar rendimiento
        """
        return {
            sensor.name: sensor.room.name 
            for sensor in Sensor.objects.select_related('room').all()
        }
    
    def _get_sensor_room_map_filtered(self, sensor_names):
        """
        Optimización: obtiene solo el mapeo para los sensores específicos
        """
        if not sensor_names:
            result = self._get_sensor_room_map()
        else:
            result = {
                sensor.name: sensor.room.name 
                for sensor in Sensor.objects.select_related('room').filter(name__in=sensor_names)
            }
        return result

    def _filter_by_metric_range(self, queryset):
        """
        Optimización: filtra por rangos de métricas en una sola consulta eficiente
        """
        valid_ranges = {
            't': {'min': 2, 'max': 70},
            'h': {'min': 2, 'max': 99},
            's': {'min': 2, 'max': 99}
        }
        
        # Construir un Q object para filtrado eficiente
        metric_filter = Q()
        for metric, ranges in valid_ranges.items():
            metric_filter |= (
                Q(metric=metric) & 
                Q(value__gte=ranges['min']) & 
                Q(value__lte=ranges['max'])
            )
        
        # Añadir condición para métricas no especificadas
        defined_metrics = list(valid_ranges.keys())
        metric_filter |= ~Q(metric__in=defined_metrics)
        
        result = queryset.filter(metric_filter)
        return result

    def apply_filters(self):
        """
        Aplica filtros adicionales específicos del procesador que no maneja DataPointFilter
        """
        # Los filtros básicos ya están aplicados gracias a filterset_class
        return self.queryset

    def get_values_list(self):
        """Helper method to get the list of fields to query"""
        return ['timestamp', 'sensor', 'metric', 'value']

    def get_serializer_context(self):
        """Construye el contexto para el serializer de forma consistente"""
        return {
            'include_room': self.include_room, 
            'sensor_room_map': self.sensor_room_map if self.include_room else {}
        }
    
    def get_appropriate_serializer(self, queryset, include_room=False, context=None):
        """
        Selecciona el serializer apropiado basado en include_room y lo configura
        """
        context = context or self.get_serializer_context()
        
        if include_room:
            result = DataPointRoomSensorSerializer(queryset, many=True, context=context).data
        else:
            result = DataPointSerializer(queryset, many=True, context=context).data
        return result

    @abstractmethod
    def get(self):
        """
        Método abstracto para obtener datos según la clase específica.
        Debe ser implementado por subclases.
        """
        pass

    def process(self):
        """
        Método principal para procesar datos y devolver respuesta formateada.
        Maneja paginación y metadata de forma consistente.
        """
        start_time = timezone.now()
        
        # Determinar fechas para metadata
        start_date = self.query_parameters.get('start_date') 
        if not start_date:
            start_date = (timezone.now() - get_timedelta_from_timeframe('1D')).isoformat()

        end_date = self.query_parameters.get('end_date')
        if not end_date:
            end_date = timezone.now().isoformat()

        # Obtener los resultados desde la implementación específica
        result = self.get()

        # Aplicar paginación si es necesario
        if self.request and hasattr(self, 'paginate_queryset') and self.paginate:
            paginated = self.paginate_queryset(result)
            if paginated is not None:
                result = self.get_paginated_response(paginated).data

        # Generar metadata si se solicita
        if to_bool(self.query_parameters.get('metadata', False)):
            elapsed_time = (timezone.now() - start_time).total_seconds()
            
            metadata_dict = {
                'start_time': start_time.isoformat(),
                'elapsed_time': elapsed_time,
                'start_date': start_date,
                'end_date': end_date,
            }
            
            # Añadir timeframe si está disponible
            if hasattr(self, 'timeframe'):
                metadata_dict['timeframe'] = self.timeframe
            
            result = {
                'data': result,
                'metadata': metadata_dict
            }
            
        return result


class ListData(DataPointQueryProcessor):
    """
    Procesador para obtener una lista filtrada de DataPoints.
    Simple passthrough ya que el filtrado es manejado por el ViewSet.
    """
    
    def get(self):
        # Optimización: limitar la cantidad de registros si no se requiere paginación
        if not self.paginate:
            # Si no se requiere paginación, limitar a un máximo razonable
            queryset_limited = self.queryset[:1000]
        else:
            queryset_limited = self.queryset
            
        # Optimización: usar select_related si se incluye room
        if self.include_room:
            # Precargamos los sensores y sus habitaciones para evitar N+1 queries
            sensor_names = set(queryset_limited.values_list('sensor', flat=True).distinct())
            self.sensor_room_map = self._get_sensor_room_map_filtered(sensor_names)
            
        # Serializar el queryset ya filtrado
        return self.get_appropriate_serializer(
            queryset_limited, 
            include_room=self.include_room
        )


class LatestData(DataPointQueryProcessor):
    """
    Procesador para obtener los últimos registros de DataPoints por sensor/métrica.
    """
    
    def get(self):
        # Optimized query using a subquery approach instead of distinct on
        
        # Get the latest timestamp for each sensor/metric combination
        latest_timestamps = self.queryset.values('sensor', 'metric').annotate(
            latest_timestamp=Max('timestamp')
        )
        
        # Use these timestamps to filter the original queryset
        latest_datapoints = []
        for item in latest_timestamps:
            datapoint = self.queryset.filter(
                sensor=item['sensor'],
                metric=item['metric'],
                timestamp=item['latest_timestamp']
            ).first()
            if datapoint:
                latest_datapoints.append(datapoint)
        
        # Serializar el resultado
        return self.get_appropriate_serializer(
            latest_datapoints, 
            include_room=self.include_room
        )


class TimeframedData(DataPointQueryProcessor):
    """
    Procesador para obtener datos de DataPoints agrupados por intervalos de tiempo.
    Optimizado para procesar eficientemente grandes conjuntos de datos.
    """
    
    def __init__(self, queryset, query_parameters=None, request=None, *args, **kwargs):
        super().__init__(queryset, query_parameters, request, *args, **kwargs)
        self.timeframe = query_parameters.get('timeframe', '1H').upper() if query_parameters else '1H'
        self.aggregations = to_bool(query_parameters.get('aggregations', False)) if query_parameters else False

    def get(self):
        # Optimización: Aplicar filtros de fecha directamente en la consulta inicial
        end_date = timezone.now()
        start_date = get_start_date(self.timeframe, end_date)
        
        # Limitar la consulta solo al rango de fechas necesario
        queryset_timeframed = self.queryset.filter(timestamp__gte=start_date, timestamp__lte=end_date)
        
        # Optimización: Limitar los campos recuperados solo a los necesarios
        values_list = self.get_values_list()
        
        # Optimización: Usar values() con only() para reducir la carga de datos
        queryset_optimized = queryset_timeframed.only(*values_list)
        data_values = list(queryset_optimized.values(*values_list))
        
        # Si no hay datos, retornar temprano
        if not data_values:
            return []
        
        # Optimización: si necesitamos información de habitación, obtenemos solo los sensores presentes
        if self.include_room:
            unique_sensors = set(item['sensor'] for item in data_values)
            self.sensor_room_map = self._get_sensor_room_map_filtered(unique_sensors)
        
        # Crear DataFrame con los datos mínimos necesarios
        df = pd.DataFrame(data_values)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Añadir información de habitación si es necesario
        if self.include_room:
            df['room'] = df['sensor'].map(self.sensor_room_map)
            df['room'] = df['room'].fillna('')
        
        # Preparar DataFrame para agrupación
        df = df.set_index('timestamp').sort_index()
        
        # Determinar columnas de agrupación
        group_cols = ['room', 'metric'] if self.include_room else ['sensor', 'metric']
        
        # Aplicar procesamiento según el tipo de agregación
        if self.aggregations:
            results = self._process_with_aggregations(df, group_cols)
        else:
            results = self._process_without_aggregations(df, group_cols)
        
        # Seleccionar serializer apropiado
        return DataPointRoomSerializer(results, many=True).data if self.include_room else DataPointSerializer(results, many=True).data

    def _process_with_aggregations(self, df, group_cols):
        """Procesa los datos con múltiples agregaciones"""
        if df.empty:
            return []
            
        # Optimización: Usar solo las columnas necesarias para la agrupación
        df_reduced = df[['value'] + [col for col in group_cols if col in df.columns]]
        
        # Aplicar agregaciones
        agg_funcs = ['mean', 'min', 'max', 'first', 'last']
        grouped = df_reduced.groupby([*group_cols, pd.Grouper(freq=TIMEFRAME_MAP[self.timeframe])])['value'].agg(agg_funcs).reset_index()
        grouped = grouped.rename(columns={'timestamp': 'timeframed_timestamp'})
        
        # Convertir a formato adecuado para serializer
        results = []
        for _, row in grouped.iterrows():
            result_dict = {
                'timestamp': row['timeframed_timestamp'].isoformat(),
            }
            
            # Añadir datos específicos según las columnas
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
        """Procesa los datos con solo media como agregación"""
        if df.empty:
            return []
            
        # Optimización: Usar solo las columnas necesarias para la agrupación
        df_reduced = df[['value'] + [col for col in group_cols if col in df.columns]]
        
        # Aplicar agregación simple (media)
        grouped = df_reduced.groupby([*group_cols, pd.Grouper(freq=TIMEFRAME_MAP[self.timeframe])])['value'].mean().reset_index()
        grouped = grouped.rename(columns={'timestamp': 'timeframed_timestamp', 'value': 'mean_value'})
        
        # Convertir a formato adecuado para serializer
        results = []
        for _, row in grouped.iterrows():
            result_dict = {
                'timestamp': row['timeframed_timestamp'].isoformat(),
            }
            
            # Añadir datos específicos según las columnas
            if 'room' in group_cols:
                result_dict['room'] = row['room']
            else:
                result_dict['sensor'] = row['sensor']
                
            result_dict['metric'] = row['metric']
            result_dict['value'] = round(row['mean_value'], 2)
            
            results.append(result_dict)
        
        return results
