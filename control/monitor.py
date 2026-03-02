import ssl
import time
from datetime import timedelta

from django.conf import settings
from django.db.models import Avg
from django.utils import timezone
import paho.mqtt.client as mqtt
import schedule

from receiver.models import Data
from . import event_rules

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, settings.MQTT_USER_PUB)


def analyze_data():
    print("Calculando alertas...")
    threshold_alerts = send_threshold_alerts()
    oled_events = send_oled_climate_events()
    print(threshold_alerts, "alertas de rango enviadas")
    print(oled_events, "eventos OLED enviados")


def send_threshold_alerts():
    """
    Conserva la regla original del tutorial: promedio fuera del rango permitido.
    """
    aggregation = list(
        Data.objects.filter(base_time__gte=timezone.now() - timedelta(hours=1))
        .values(
            "station_id",
            "station__user__username",
            "measurement__name",
            "measurement__max_value",
            "measurement__min_value",
            "station__location__city__name",
            "station__location__state__name",
            "station__location__country__name",
        )
        .annotate(check_value=Avg("avg_value"))
    )

    alerts = 0
    for item in aggregation:
        variable = item["measurement__name"]
        max_value = item["measurement__max_value"]
        min_value = item["measurement__min_value"]

        country = item["station__location__country__name"]
        state = item["station__location__state__name"]
        city = item["station__location__city__name"]
        user = item["station__user__username"]

        check_value = item["check_value"] or 0
        above_max = max_value is not None and check_value > max_value
        below_min = min_value is not None and check_value < min_value

        if above_max or below_min:
            message = "ALERT {} {} {}".format(variable, min_value, max_value)
            topic = "{}/{}/{}/{}/in".format(country, state, city, user)
            print(timezone.now(), "Sending alert to {} {}".format(topic, variable))
            client.publish(topic, message)
            alerts += 1

    print(len(aggregation), "dispositivos revisados")
    return alerts


def send_oled_climate_events():
    """
    Nuevo evento:
    consulta la base de datos para obtener el promedio reciente de temperatura
    y humedad; si ambos superan los umbrales configurados, se envia un comando
    al actuador OLED del NodeMCU.
    """
    summaries = event_rules.build_station_summaries(
        event_rules.get_recent_station_measurement_averages()
    )

    events = 0
    for summary in summaries:
        if not event_rules.should_trigger_oled_event(summary):
            continue

        topic = event_rules.build_station_topic(summary)
        message = event_rules.build_oled_message(summary)
        print(
            timezone.now(),
            "Sending OLED event to {} for {}".format(topic, summary["user"]),
        )
        client.publish(topic, message)
        events += 1

    return events


def on_connect(client, userdata, flags, rc):
    """
    Funcion que se ejecuta cuando se conecta al broker.
    """
    print("Conectando al broker MQTT...", mqtt.connack_string(rc))


def on_disconnect(client: mqtt.Client, userdata, rc):
    """
    Funcion que se ejecuta cuando se desconecta del broker.
    Intenta reconectar al broker.
    """
    print("Desconectado con mensaje:" + str(mqtt.connack_string(rc)))
    print("Reconectando...")
    client.reconnect()


def setup_mqtt():
    """
    Configura el cliente MQTT para conectarse al broker.
    """
    print("Iniciando cliente MQTT...", settings.MQTT_HOST, settings.MQTT_PORT)
    global client
    try:
        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION1,
            settings.MQTT_USER_PUB,
        )
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect

        if settings.MQTT_USE_TLS:
            client.tls_set(
                ca_certs=settings.CA_CRT_PATH,
                tls_version=ssl.PROTOCOL_TLSv1_2,
                cert_reqs=ssl.CERT_NONE,
            )

        client.username_pw_set(
            settings.MQTT_USER_PUB,
            settings.MQTT_PASSWORD_PUB,
        )
        client.connect(settings.MQTT_HOST, settings.MQTT_PORT)
        client.loop_start()

    except Exception as e:
        print("Ocurrio un error al conectar con el broker MQTT:", e)


def start_cron():
    """
    Inicia el cron que se encarga de ejecutar la funcion analyze_data cada 5 minutos.
    """
    print("Iniciando cron...")
    schedule.every(5).minutes.do(analyze_data)
    print("Servicio de control iniciado")
    while 1:
        schedule.run_pending()
        time.sleep(1)
