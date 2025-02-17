from django.utils import timezone
from rest_framework import viewsets, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from abc import ABC, abstractmethod
from .models import DataPoint, Sensor, Room
from .serializers import DataPointSerializer, DataPointRoomSensorSerializer, DataPointRoomSerializer
from .utils import TIMEFRAME_MAP, get_timedelta_from_timeframe, get_start_date, to_bool
import pandas as pd


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

    def list(self, request, *args, **kwargs):
        processor = ListData(queryset=self.queryset, query_parameters=request.query_params, request=request)
        return Response(processor.process())

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

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
        processor = LatestData(queryset=self.queryset, query_parameters=request.GET, request=request)
        return Response(processor.process())

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
        processor = TimeframedData(queryset=self.queryset, query_parameters=request.GET, request=request)
        return Response(processor.process())


class DataPointQueryProcessor(generics.GenericAPIView, ABC):
    def __init__(self, queryset, query_parameters=None, request=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = queryset
        self.query_parameters = query_parameters if query_parameters is not None else {}
        self.request = request
        self.include_room = to_bool(self.query_parameters.get('include_room', False))
        self.paginate = to_bool(self.query_parameters.get('paginate', True))  # Default to True
        if self.include_room:
            self.sensor_room_map = {
                sensor.name: sensor.room.name 
                for sensor in Sensor.objects.select_related('room').all()
            }

    def _filter_by_metric_range(self, queryset):
        t_min, t_max = 2, 70
        h_min, h_max = 2, 99
        s_min, s_max = 2, 99

        # Efficiently filter using Q objects
        from django.db.models import Q
        queryset = queryset.filter(
            Q(metric='t', value__range=(t_min, t_max)) |
            Q(metric='h', value__range=(h_min, h_max)) |
            Q(metric='s', value__range=(s_min, s_max)) |
            ~Q(metric__in=['t', 'h', 's'])
        )
        return queryset

    def apply_filters(self, query_parameters):
        self.VALID_RANGES = {
            't': {'min': 2, 'max': 70},
            'h': {'min': 2, 'max': 100}
        }
        queryset = self.queryset

        queryset = self._filter_by_metric_range(queryset)

        
        if 'start_date' in query_parameters:
            try:
                queryset = queryset.filter(timestamp__gte=query_parameters['start_date'])
            except Exception as e:
                print(f"Error al filtrar por start_date: {e}")

        if 'end_date' in query_parameters:
            try:
                queryset = queryset.filter(timestamp__lte=query_parameters['end_date'])
            except Exception as e:
                print(f"Error al filtrar por end_date: {e}")

        if 'sensors' in query_parameters:
            queryset = queryset.filter(sensor=query_parameters['sensors'])
        
        # Aplicamos filtros de rango por tipo de sensor
        valid_ranges_filter = None
        for metric, ranges in self.VALID_RANGES.items():
            metric_filter = (
                queryset.filter(metric=metric)
                .filter(value__gte=ranges['min'])
                .filter(value__lte=ranges['max'])
            )
            
            # Para métricas que no están en VALID_RANGES
            other_metrics_filter = queryset.exclude(metric=metric)
            
            if valid_ranges_filter is None:
                valid_ranges_filter = metric_filter | other_metrics_filter
            else:
                valid_ranges_filter = valid_ranges_filter | metric_filter | other_metrics_filter
        
        return valid_ranges_filter if valid_ranges_filter is not None else queryset

    def get_room_for_sensor(self, sensor_name):
        """Helper method to get room name for a sensor"""
        return self.sensor_room_map.get(sensor_name, '')

    def get_values_list(self):
        """Helper method to get the list of fields to query"""
        return ['timestamp', 'sensor', 'metric', 'value']

    @abstractmethod
    def get(self):
        pass

    def process(self):
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

        elapsed_time = (timezone.now() - start_time).total_seconds()

        if to_bool(self.query_parameters.get('metadata', False)):
            metadata_dict = {
                'start_time': start_time.isoformat(),
                'elapsed_time': elapsed_time,
                'start_date': start_date,
                'end_date': end_date,
            }
            if hasattr(self, 'timeframe'):
                metadata_dict['timeframe'] = self.timeframe
            return {
                'data': result,
                'metadata': metadata_dict
            }
        return result


class ListData(DataPointQueryProcessor):
    def get(self):
        queryset_filtered = self.apply_filters(self.query_parameters)
        context = {
            'include_room': self.include_room, 
            'sensor_room_map': self.sensor_room_map if self.include_room else {}
        }
        if self.include_room:
            data = DataPointRoomSensorSerializer(queryset_filtered, many=True, context=context).data
        else:
            data = DataPointSerializer(queryset_filtered, many=True, context=context).data
        return data

class LatestData(ListData):
    def get(self):
        queryset_filtered = self.apply_filters(self.query_parameters)
        queryset_latest = queryset_filtered.order_by('sensor', 'metric', '-timestamp').distinct('sensor', 'metric')
        context = {
            'include_room': self.include_room, 
            'sensor_room_map': self.sensor_room_map if self.include_room else {}
        }
        if self.include_room:
            data = DataPointRoomSensorSerializer(queryset_latest, many=True, context=context).data
        else:
            data = DataPointSerializer(queryset_latest, many=True, context=context).data
        return data


class TimeframedData(ListData):
    def __init__(self, queryset, query_parameters=None):
        super().__init__(queryset, query_parameters)
        self.timeframe = query_parameters.get('timeframe', '1H').upper() if query_parameters else '1H'
        self.aggregations = to_bool(query_parameters.get('aggregations', False)) if query_parameters else False

    def get(self):
        queryset_filtered = self.apply_filters(self.query_parameters)
        end_date = timezone.now()
        start_date = get_start_date(self.timeframe, end_date)
        queryset_timeframed = queryset_filtered.filter(timestamp__gte=start_date, timestamp__lte=end_date)

        df = pd.DataFrame(list(queryset_timeframed.values(*self.get_values_list())))
        if df.empty:
            return []

        df['timestamp'] = pd.to_datetime(df['timestamp'])
        if self.include_room:
            df['room'] = df['sensor'].map(self.sensor_room_map)
            df['room'] = df['room'].fillna('')
        df = df.set_index('timestamp').sort_index()

        if self.include_room:
            group_cols = ['room', 'metric']
        else:
            group_cols = ['sensor', 'metric']

        if self.aggregations:
            results = self._process_with_aggregations(df, group_cols)
        else:
            results = self._process_without_aggregations(df, group_cols)

        if self.include_room:
            return DataPointRoomSerializer(results, many=True).data
        return DataPointSerializer(results, many=True).data

    def _process_with_aggregations(self, df, group_cols):
        agg_funcs = ['mean', 'min', 'max', 'first', 'last']
        grouped = df.groupby([*group_cols, pd.Grouper(freq=TIMEFRAME_MAP[self.timeframe])])['value'].agg(agg_funcs).reset_index()
        grouped = grouped.rename(columns={'timestamp': 'timeframed_timestamp'})
        
        results = []
        for _, row in grouped.iterrows():
            result_dict = {
                'timestamp': row['timeframed_timestamp'].isoformat(),
            }
            if self.include_room:
                result_dict['room'] = row['room']
            result_dict.update({
                'sensor': row['sensor'],
                'metric': row['metric'],
                'value': {
                    'mean': round(row['mean'], 2),
                    'min': round(row['min'], 2),
                    'max': round(row['max'], 2),
                    'first': round(row['first'], 2),
                    'last': round(row['last'], 2)
                }
            })
            results.append(result_dict)
        return results

    def _process_without_aggregations(self, df, group_cols):
        grouped = df.groupby([*group_cols, pd.Grouper(freq=TIMEFRAME_MAP[self.timeframe])])['value'].mean().reset_index()
        grouped = grouped.rename(columns={'timestamp': 'timeframed_timestamp', 'value': 'mean_value'})
        
        results = []
        for _, row in grouped.iterrows():
            result_dict = {
                'timestamp': row['timeframed_timestamp'].isoformat(),
            }
            if self.include_room:
                result_dict['room'] = row['room']
            result_dict.update({
                'sensor': row['sensor'],
                'metric': row['metric'],
                'value': round(row['mean_value'], 2)
            })
            results.append(result_dict)
        return results
