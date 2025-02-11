from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from abc import ABC, abstractmethod
from .models import DataPoint
from .serializers import DataPointSerializer
from .utils import TIMEFRAME_MAP, get_timedelta_from_timeframe, get_start_date, to_bool
import pandas as pd


class DataPointViewSet(viewsets.ModelViewSet):
    """
    Módulo API para DataPoint.

    Este módulo expone endpoints para consultar datos a partir del modelo DataPoint.
    Se pueden aplicar filtros por fecha de inicio (start_date), fecha fin (end_date) y lista de sensores.
    La respuesta puede incluir metadatos (como tiempo de procesamiento y rango de fechas usado) si se especifica el parámetro 'metadata'.

    Endpoints:
      - GET /api/data-point/         : Listado/creación de DataPoint.
      - GET /api/data-point/latest   : Últimos registros por sensor.
      - GET /api/data-point/timeframed : Registros dentro de un intervalo definido (ej., '1h', '4h', etc.).
    """
    queryset = DataPoint.objects.all()
    serializer_class = DataPointSerializer

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def latest(self, request):
        """
        Retorna el último registro de cada sensor.

        Parámetros (opcional, vía query string):
            - start_date: Fecha de inicio en formato ISO8601.
            - end_date: Fecha fin en formato ISO8601.
            - sensors: Lista de nombres de sensores.
            - metadata: Booleano para incluir metadatos en la respuesta.
        """
        processor = LatestData(queryset=self.get_queryset(), query_parameters=request.GET)
        return Response(processor.process())

    @action(detail=False, methods=['get'])
    def timeframed(self, request):
        """
        Retorna registros agrupados por intervalos de tiempo.

        Parámetros (opcional, vía query string):
            - start_date: Fecha de inicio en formato ISO8601.
            - end_date: Fecha fin en formato ISO8601.
            - sensors: Lista de nombres de sensores.
            - timeframe: Intervalo de tiempo ('5S', '1T', '30T', '1H', '4H', '1D').
            - aggregations: Si es True, devuelve min, max, first, last, mean. Por defecto False (devuelve solo mean)
            - metadata: Booleano para incluir metadata en la respuesta.
        """
        processor = TimeframedData(queryset=self.get_queryset(), query_parameters=request.GET)
        return Response(processor.process())


class DataPointQueryProcessor(ABC):
    def __init__(self, queryset, query_parameters=None):
        self.queryset = queryset
        self.query_parameters = query_parameters if query_parameters is not None else {}

    def apply_filters(self, query_parameters):
        queryset = self.queryset
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
            queryset = queryset.filter(sensor__in(query_parameters['sensors']))
        
        return queryset

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


class LatestData(DataPointQueryProcessor):
    def __init__(self, queryset, query_parameters=None):
        super().__init__(queryset, query_parameters)
        self.query_parameters = query_parameters if query_parameters is not None else {}

    def get(self):
        queryset_filtered = self.apply_filters(self.query_parameters)
        queryset_latest = queryset_filtered.order_by('sensor', 'metric', '-timestamp').distinct('sensor', 'metric')
        return DataPointSerializer(queryset_latest, many=True).data


class TimeframedData(DataPointQueryProcessor):
    def __init__(self, queryset, query_parameters=None):
        super().__init__(queryset, query_parameters)
        self.timeframe = query_parameters.get('timeframe', '1H').upper() if query_parameters else '1H'
        self.aggregations = to_bool(query_parameters.get('aggregations', False)) if query_parameters else False
        self.query_parameters = query_parameters if query_parameters is not None else {}

    def get(self):
        queryset_filtered = self.apply_filters(self.query_parameters)
        end_date = timezone.now()
        start_date = get_start_date(self.timeframe, end_date)
        queryset_timeframed = queryset_filtered.filter(timestamp__gte=start_date, timestamp__lte=end_date)

        df = pd.DataFrame(list(queryset_timeframed.values('timestamp', 'sensor', 'metric', 'value')))
        if df.empty:
            return []

        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp').sort_index()

        if self.aggregations:
            agg_funcs = ['mean', 'min', 'max', 'first', 'last']
            grouped = df.groupby(['sensor', 'metric', pd.Grouper(freq=TIMEFRAME_MAP[self.timeframe])])['value'].agg(agg_funcs).reset_index()
            grouped = grouped.rename(columns={'timestamp': 'timeframed_timestamp'})
            results = []
            for _, row in grouped.iterrows():
                results.append({
                    'timestamp': row['timeframed_timestamp'].isoformat(),
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
            return results
        else:
            grouped = df.groupby(['sensor', 'metric', pd.Grouper(freq=TIMEFRAME_MAP[self.timeframe])])['value'].mean().reset_index()
            grouped = grouped.rename(columns={'timestamp': 'timeframed_timestamp', 'value': 'mean_value'})
            results = []
            for _, row in grouped.iterrows():
                results.append({
                    'timestamp': row['timeframed_timestamp'].isoformat(),
                    'sensor': row['sensor'],
                    'metric': row['metric'],
                    'value': round(row['mean_value'], 2)
                })
            return results