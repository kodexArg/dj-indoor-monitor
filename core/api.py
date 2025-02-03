# Standard library imports
from datetime import datetime, timedelta, timezone
from time import perf_counter

# Django & DRF imports
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
import pandas as pd

# Local imports
from .models import SensorData, Room, DataPoint
from .serializers import SensorDataSerializer, DataPointSerializer
from .filters import SensorDataFilter
from .utils import get_timedelta_from_timeframe, get_start_date, format_timestamp

class SensorDataViewSet(viewsets.ModelViewSet):
    """
    API para gestionar datos de sensores del modelo SensorData.
    Incluye metadatos sobre el rango de fechas, número de registros y demora del backend.

    Parámetros:
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
    pagination_class = None
    _query_start_time = None
    _query_timestamp = None

    def initial(self, request, *args, **kwargs):
        """Método DRF sobreescrito: Se ejecuta al inicio de cada solicitud"""
        self._query_timestamp = datetime.now(timezone.utc)
        self._query_start_time = perf_counter()
        super().initial(request, *args, **kwargs)

    def get_metadata(self, queryset):
        """Genera metadatos del queryset incluyendo métricas de tiempo y conteos"""
        timeframe = self.request.query_params.get('timeframe', '5s')
        metric = self.request.query_params.get('metric', 't')
        end_date = datetime.now(timezone.utc)
        time_window = get_timedelta_from_timeframe(timeframe)
        start_date = get_start_date(timeframe, end_date)

        return {
            'timeframe': timeframe,
            'metric': metric,
            'window_minutes': int(time_window.total_seconds() / 60),
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'start_pretty': format_timestamp(start_date),
            'end_pretty': format_timestamp(end_date),
            'record_count': queryset.count(),
            'sensor_ids': sorted(list(set(queryset.values_list('sensor', flat=True)))),
            'query_duration_s': round(perf_counter() - self._query_start_time, 3) 
        }

    def get_queryset(self):
        """Método DRF sobreescrito: Define el queryset base aplicando filtros de tiempo según los parámetros recibidos"""
        queryset = SensorData.objects.order_by('-timestamp')
        
        end_date = self.request.query_params.get('end_date', None)
        start_date = self.request.query_params.get('start_date', None)

        if end_date:
            end_date = datetime.fromisoformat(end_date)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
        else:
            end_date = datetime.now(timezone.utc)

        if start_date:
            start_date = datetime.fromisoformat(start_date)
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
        else:
            start_date = end_date - timedelta(minutes=30)

        return queryset.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date
        )

    def list(self, request, *args, **kwargs):
        """Método DRF sobreescrito: Lista registros con sus metadatos asociados"""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        metadata = self.get_metadata(queryset)
        
        return Response({
            'results': serializer.data,
            'metadata': metadata
        })

    @action(detail=False, methods=['get'])
    def latest(self, request):
        """
        Obtiene el último valor de cada sensor activo o rooms.
        
        Parámetros:
        - room (bool): Agrupar por habitación y promediar valores (default: False)
        """
        since = datetime.now(timezone.utc) - timedelta(days=1)
        base_queryset = SensorData.objects.filter(timestamp__gte=since)
        room = self.request.query_params.get('room', 'false').lower() == 'true'
        
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

        if room:
            rooms_data = {}
            for room_obj in Room.objects.all():
                if not room_obj.sensors:
                    continue
                
                room_sensors = [s.strip() for s in room_obj.sensors.split(',') if s.strip()]
                room_records = [r for r in latest_data if r['sensor'] in room_sensors]
                
                if room_records:
                    rooms_data[room_obj.name] = {
                        'timestamp': max(r['timestamp'] for r in room_records),
                        'timestamp_pretty': max(r['timestamp_pretty'] for r in room_records),
                        't': round(sum(r['t'] for r in room_records) / len(room_records), 1),
                        'h': round(sum(r['h'] for r in room_records) / len(room_records), 1),
                        'sensor': room_obj.name
                    }
            
            latest_data = list(rooms_data.values())

        return Response(latest_data)

    @action(detail=False, methods=['get'])
    def timeframed(self, request):
        """
        Agrupa datos por intervalos para cada sensor, calculando estadísticas.
        
        Parámetros:
        - timeframe (str): Intervalo de agrupación ('5s', '5T', '30T', '1h', '4h', '1D')
        - start_date (str): Fecha inicial en formato ISO (opcional)
        - end_date (str): Fecha final en formato ISO (opcional)
        - sensor (str): ID del sensor para filtrar (opcional)
        - metadata (bool): Incluir metadatos en la respuesta (por defecto: true)
        - room (bool): Agrupar por habitación en lugar de por sensor (por defecto: false)
        """
        # Parámetros de consulta
        end_date = self.request.query_params.get('end_date', None)
        start_date = self.request.query_params.get('start_date', None)
        timeframe = self.request.query_params.get('timeframe', '1h')
        sensor = self.request.query_params.get('sensor', None)
        include_metadata = self.request.query_params.get('metadata', 'true').lower() == 'true'
        room = self.request.query_params.get('room', 'false').lower() == 'true'

        # Normalización de fechas
        if end_date:
            end_date = datetime.fromisoformat(end_date)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
        else:
            end_date = datetime.now(timezone.utc)

        if start_date:
            start_date = datetime.fromisoformat(start_date)
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
        else:
            start_date = get_start_date(timeframe, end_date)
            self.request.query_params._mutable = True
            self.request.query_params['start_date'] = start_date.isoformat()
            self.request.query_params['end_date'] = end_date.isoformat()
            self.request.query_params._mutable = False

        # Preparación del dataset
        queryset = self.filter_queryset(self.get_queryset())
        
        # Creamos el DataFrame base
        df = pd.DataFrame(list(queryset.values('timestamp', 'sensor', 't', 'h')))
        
        if df.empty:
            response_data = {}
            if include_metadata:
                response_data['metadata'] = self.get_metadata(queryset)
            response_data['results'] = []
            return Response(response_data)

        df = df.sort_values('timestamp')
        
        if room:
            # Creamos DataFrame de rooms y sus sensores
            rooms_data = []
            for room in Room.objects.all():
                for sensor in room.sensors.split(','):
                    rooms_data.append({
                        'sensor': sensor.strip(),
                        'room_name': room.name
                    })
            rooms_df = pd.DataFrame(rooms_data)
            
            # Merge con el DataFrame principal
            df = df.merge(rooms_df, on='sensor', how='left')
            # Usamos room_name como sensor si existe, sino mantenemos el sensor original
            df['sensor'] = df['room_name'].fillna(df['sensor'])
            df = df.drop('room_name', axis=1)

        df.set_index('timestamp', inplace=True)
        
        # Agregación de datos por timeframe
        grouped = df.groupby(['sensor', pd.Grouper(freq=timeframe)]).agg({
            't': ['mean', 'min', 'max', 'first', 'last'],
            'h': ['mean', 'min', 'max', 'first', 'last']
        }).round(2)

        # Formateo de resultados
        results = []
        for (sensor, timestamp), data in grouped.iterrows():
            results.append({
                'timestamp': timestamp.isoformat(),
                'sensor': sensor,
                'temperature': {
                    'mean': data[('t', 'mean')],
                    'min': data[('t', 'min')],
                    'max': data[('t', 'max')],
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

        response_data = {}
        if include_metadata:
            response_data['metadata'] = {
                **self.get_metadata(queryset),
                'timeframe': timeframe,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'sensor': sensor,
                'groups': len(results)
            }
        response_data['results'] = results

        return Response(response_data)


class DataPointViewSet(viewsets.ViewSet):
    """
    API para gestionar puntos de datos.
    
    GET: Obtiene todos los registros de las últimas 24 horas
    POST: Crea un nuevo registro. Campos requeridos: sensor, metric, value.
          El timestamp es opcional, si no se proporciona se usa la hora actual.
    """
    def list(self, request):
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        points = DataPoint.objects.filter(
            timestamp__gte=since
        ).order_by('-timestamp')
        
        serializer = DataPointSerializer(points, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """
        Obtiene el último valor por sensor y métrica en las últimas 24 horas
        
        Parámetros:
        - sensor: Opcional, filtrar por sensor específico
        """
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        base_queryset = DataPoint.objects.filter(timestamp__gte=since)
        
        if 'sensor' in request.query_params:
            base_queryset = base_queryset.filter(sensor=request.query_params['sensor'])
        
        latest_data = []
        # Obtener el último registro para cada combinación de sensor y métrica
        for sensor in base_queryset.values_list('sensor', flat=True).distinct():
            latest_points = []
            for metric in ['t', 'h', 's', 'l', 'r']:
                point = (base_queryset
                    .filter(sensor=sensor, metric=metric)
                    .order_by('-timestamp')
                    .first())
                
                if point:
                    latest_points.append({
                        'timestamp': point.timestamp.isoformat(),
                        'sensor': point.sensor,
                        'metric': point.metric,
                        'value': round(point.value, 2)
                    })
            
            if latest_points:
                latest_data.extend(latest_points)

        return Response(latest_data)

    def create(self, request):
        required_fields = ['sensor', 'metric', 'value']
        
        # Validar campos requeridos
        if not all(field in request.data for field in required_fields):
            return Response(
                {'error': f'Missing required fields. Required: {", ".join(required_fields)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Obtener timestamp o usar now() si no existe
            if 'timestamp' in request.data:
                timestamp = datetime.fromisoformat(request.data['timestamp'])
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
            else:
                timestamp = datetime.now(timezone.utc)
            
            # Validar valor numérico
            value = float(request.data['value'])
            
            # Crear punto de datos
            data_point = DataPoint.objects.create(
                timestamp=timestamp,
                sensor=request.data['sensor'],
                metric=request.data['metric'],
                value=value
            )
            
            serializer = DataPointSerializer(data_point)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response(
                {'error': f'Invalid data format: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Error creating data point: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )