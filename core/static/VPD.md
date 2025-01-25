# Cálculo del Déficit de Presión de Vapor (VPD) para Cultivo de Cannabis Medicinal

El Déficit de Presión de Vapor (**VPD**, por sus siglas en inglés: Vapor Pressure Deficit) es un parámetro crucial para el manejo óptimo de la humedad y la temperatura en cultivos farmacológicos de cannabis medicinal. Controlar el VPD asegura un desarrollo saludable de las plantas, optimizando tanto la fotosíntesis como la transpiración.

## ¿Qué es el VPD y por qué es importante?

El VPD mide la diferencia entre la presión de saturación de vapor de agua en el aire (**es**) y la presión de vapor actual (**ea**). Este valor indica cuánto "espacio" tiene el aire para absorber agua adicional de las hojas de las plantas. Un VPD bien ajustado:

1. **Promueve la transpiración:** Permite el intercambio óptimo de gases, lo que ayuda al crecimiento saludable y vigoroso de la planta.
2. **Previene estrés hídrico:** Un VPD bajo puede favorecer enfermedades fúngicas, mientras que un VPD alto puede provocar deshidratación.
3. **Optimiza la fotosíntesis:** Mantiene el equilibrio entre la absorción de dióxido de carbono y la pérdida de agua.

## Fórmula del VPD

Para calcular el VPD en un cultivo de cannabis medicinal, se emplean las siguientes fórmulas:

### 1. Presión de Saturación de Vapor (**es**):
La presión de saturación de vapor se calcula a partir de la temperatura del aire (**T**, en grados Celsius):

```
es = 0.6108 * exp((17.27 * T) / (T + 237.3))
```

### 2. Presión de Vapor Actual (**ea**):
La presión de vapor actual se obtiene a partir de la humedad relativa (**HR**, en porcentaje):

```
ea = es * (HR / 100)
```

### 3. Déficit de Presión de Vapor (**VPD**):
Finalmente, el VPD es la diferencia entre la presión de saturación y la presión actual:

```
VPD = es - ea
```

## Rango Óptimo de VPD para Cannabis Medicinal

En un entorno farmacológico de cannabis medicinal, los rangos ideales de VPD suelen variar ligeramente dependiendo de la etapa de crecimiento:

- **Etapa vegetativa:** 0.8 - 1.2 kPa.
- **Etapa de floración:** 1.2 - 1.8 kPa.

Es esencial monitorear constantemente el VPD y ajustarlo mediante controladores automáticos de temperatura y humedad para garantizar un ambiente estable.