# Reto Capa de Aplicacion IoT Logica

Este repositorio parte del codigo base del tutorial de la capa de aplicacion IoT
y fue modificado para cumplir el reto de agregar un nuevo procesamiento de
eventos sobre datos del sistema IoT.

## Objetivo del reto

Se debia extender la aplicacion para que:

- evaluara una nueva condicion a partir de una consulta a la base de datos
- ejecutara una accion sobre un actuador del dispositivo IoT
- mantuviera el flujo de recepcion, monitoreo y visualizacion del tutorial

En esta solucion el actuador elegido fue la pantalla OLED SSD1306 conectada al
NodeMCU.

## Resumen de cambios

### 1. Nuevo evento en el backend

Se agrego una nueva regla de negocio en el servicio `control`.

La nueva condicion consulta en base de datos los promedios recientes de:

- `temperatura`
- `humedad`

Si ambos promedios superan los umbrales configurados, el backend publica un
comando MQTT al dispositivo para que muestre una alerta en la OLED.

Archivos principales:

- `control/event_rules.py`
- `control/monitor.py`
- `control/tests.py`

### 2. Configuracion del evento

En `IOTMonitoringServer/settings.py` se agregaron variables de configuracion
para la nueva regla:

- `OLED_EVENT_WINDOW_MINUTES`
- `OLED_EVENT_TEMP_THRESHOLD`
- `OLED_EVENT_HUMIDITY_THRESHOLD`

Estas variables permiten cambiar la ventana de tiempo y los umbrales sin tocar
la logica del monitor.

### 3. Ajustes de despliegue

Se actualizaron valores de configuracion del tutorial para el entorno usado:

- `ALLOWED_HOSTS`
- `DATABASES["default"]["HOST"]`
- `MQTT_HOST`

Estos cambios fueron necesarios para que la aplicacion pudiera conectarse a:

- el visualizador desplegado
- la base de datos TimescaleDB
- el broker MQTT

### 4. Adaptacion del codigo del dispositivo IoT

El archivo base del dispositivo:

- `IOTDeviceScript/IOTDeviceScript.ino`

fue extendido de forma incremental, sin cambiar su estructura general, para que
ademas de las alertas originales `ALERT ...` tambien entienda el nuevo comando:

```text
OLED;linea1;linea2;linea3;linea4
```

Con esto el NodeMCU puede:

- seguir publicando `temperatura` y `humedad`
- seguir escuchando mensajes MQTT en el topico `.../in`
- mostrar mensajes multilinea en la pantalla OLED

Tambien se ajusto el manejo del temporizador de alertas para que cada mensaje
nuevo reinicie correctamente el tiempo de visualizacion.

## Flujo del nuevo evento

1. El NodeMCU mide temperatura y humedad con el sensor DHT11.
2. El dispositivo publica esas mediciones en MQTT usando el topico `.../out`.
3. El servicio `receiver` recibe los datos y los almacena en PostgreSQL/Timescale.
4. El servicio `control` consulta la base de datos y calcula promedios recientes.
5. Si la condicion del nuevo evento se cumple, `control` publica un mensaje MQTT
   al topico `.../in`.
6. El NodeMCU recibe ese mensaje y lo muestra en la OLED.

## Formato del mensaje OLED

El backend envia mensajes con este formato:

```text
OLED;ALERTA CLIMA;Temp 29.5C;Hum 76.2%;Ventilar ahora
```

El sketch del NodeMCU separa el mensaje por `;` y usa cada fragmento como una
linea distinta en la pantalla.

## Archivos modificados

- `IOTMonitoringServer/settings.py`
- `control/monitor.py`
- `control/event_rules.py`
- `control/tests.py`
- `IOTDeviceScript/IOTDeviceScript.ino`

## Decisiones tecnicas

- Se mantuvo la alerta original por rango del tutorial para no romper el
  comportamiento previo.
- El nuevo evento se implemento aparte, para que la consulta a base de datos y
  la evaluacion de la condicion quedaran mas claras y testeables.
- Se reutilizo la pantalla OLED incluida en el kit como actuador, sin agregar
  hardware extra.
- El codigo del dispositivo se modifico sobre el sketch base del tutorial,
  agregando solo lo necesario para soportar el nuevo mensaje.

## Pruebas realizadas

En el entorno local de trabajo se valido:

- compilacion de los modulos Python con `python -m compileall`
- consistencia basica de la nueva regla con pruebas en `control/tests.py`

Durante el despliegue tambien se reviso:

- conectividad del broker MQTT
- credenciales MQTT
- arranque del visualizador Django
- acceso HTTP al servidor desplegado

## Pendientes o pasos finales recomendados

Para cerrar completamente la entrega conviene verificar:

1. que el NodeMCU tenga configurados sus `TODO` de WiFi, broker, usuario y
   topicos
2. que el dispositivo este suscrito al topico correcto `.../in`
3. que los umbrales del evento permitan activar facilmente la alerta durante la
   demostracion
4. que los cambios esten subidos al fork de GitHub

## Nota sobre despliegue

El proyecto usa `runserver` de Django para pruebas y demostracion. Eso es
suficiente para el tutorial y la validacion funcional, pero no es una
configuracion de produccion.
