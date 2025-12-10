# Modelo de Datos

Este documento describe el esquema de la base de datos PostgreSQL utilizada en el proyecto. El modelo está diseñado para almacenar configuraciones del sitio, estructura física (habitaciones y sensores) y datos de series temporales de alta frecuencia.

## Diagrama Entidad-Relación (Conceptual)

```ascii
+----------------+       +--------------+       +--------------+
|      Room      | <---- |    Sensor    |       |   DataPoint  |
+----------------+       +--------------+       +--------------+
| id (PK)        |       | id (PK)      |       | id (PK)      |
| name           |       | name         |       | timestamp    |
+----------------+       | room_id (FK) |       | sensor (str) |
                         +--------------+       | metric       |
                                                | value        |
                                                +--------------+

+--------------------+
| SiteConfigurations |
+--------------------+
| id (PK)            |
| key                |
| value              |
+--------------------+
```

## Descripción de Entidades

### Room (Habitación)
Representa una ubicación física o lógica donde se agrupan los sensores.
- **Campos**:
    - `name`: Nombre descriptivo de la habitación (e.g., "Invernadero 1").

### Sensor (Sensor)
Representa un dispositivo físico instalado en una habitación específica.
- **Campos**:
    - `name`: Identificador único o nombre del sensor.
    - `room`: Clave foránea (ForeignKey) hacia el modelo `Room`. Indica la ubicación del sensor.
- **Relación**: Muchos sensores pertenecen a una habitación (`Many-to-One`).

### DataPoint (Punto de Datos)
Almacena las lecturas individuales de los sensores. Esta tabla está optimizada para series temporales y consultas de agregación.
- **Campos**:
    - `timestamp`: Fecha y hora de la lectura. Indexado para búsquedas por rango de tiempo.
    - `sensor`: Nombre del sensor (CharField). **Nota**: No es una ForeignKey directa al modelo `Sensor` para optimizar la ingestión masiva y desacoplar la escritura de datos de la existencia previa de la entidad sensor.
    - `metric`: Identificador del tipo de medición (e.g., 't' para temperatura, 'h' para humedad).
    - `value`: Valor numérico de la medición (Float).
- **Índices**:
    - Compuestos: `(sensor, timestamp)`, `(sensor, metric, timestamp)`, `(sensor, metric, value)`, `(metric, timestamp)`.
    - Simples: `(timestamp)`.

### SiteConfigurations (Configuraciones del Sitio)
Almacenamiento clave-valor para parámetros de configuración global del sistema.
- **Campos**:
    - `key`: Clave única de configuración.
    - `value`: Valor de la configuración.
- **Métodos**:
    - `get_all_parameters()`: Método de clase para recuperar todas las configuraciones como un diccionario.
