from datetime import timedelta

from django.conf import settings
from django.db.models import Avg
from django.utils import timezone

from receiver.models import Data

TEMPERATURE_MEASUREMENT = "temperatura"
HUMIDITY_MEASUREMENT = "humedad"


def get_recent_station_measurement_averages(window_minutes=None):
    """
    Consulta en la base de datos los promedios recientes de temperatura y humedad
    por estacion. La consulta es el pre-requisito del nuevo procesamiento de eventos.
    """
    window = window_minutes or settings.OLED_EVENT_WINDOW_MINUTES
    window_start = timezone.now() - timedelta(minutes=window)
    return list(
        Data.objects.filter(
            base_time__gte=window_start,
            measurement__name__in=[TEMPERATURE_MEASUREMENT, HUMIDITY_MEASUREMENT],
        )
        .values(
            "station_id",
            "station__user__username",
            "station__location__city__name",
            "station__location__state__name",
            "station__location__country__name",
            "measurement__name",
        )
        .annotate(check_value=Avg("avg_value"))
    )


def build_station_summaries(rows):
    """
    Reorganiza los resultados agregados para evaluar reglas que dependen de
    varias mediciones de una misma estacion.
    """
    summaries = {}
    for row in rows:
        station_id = row["station_id"]
        summary = summaries.setdefault(
            station_id,
            {
                "station_id": station_id,
                "user": row["station__user__username"],
                "city": row["station__location__city__name"],
                "state": row["station__location__state__name"],
                "country": row["station__location__country__name"],
                "measurements": {},
            },
        )
        summary["measurements"][row["measurement__name"].lower()] = row["check_value"]
    return list(summaries.values())


def should_trigger_oled_event(
    summary,
    temp_threshold=None,
    humidity_threshold=None,
):
    """
    Determina si debe activarse el evento OLED "clima caliente y humedo".
    """
    temp_limit = (
        settings.OLED_EVENT_TEMP_THRESHOLD
        if temp_threshold is None
        else temp_threshold
    )
    humidity_limit = (
        settings.OLED_EVENT_HUMIDITY_THRESHOLD
        if humidity_threshold is None
        else humidity_threshold
    )

    temperature = summary["measurements"].get(TEMPERATURE_MEASUREMENT)
    humidity = summary["measurements"].get(HUMIDITY_MEASUREMENT)

    if temperature is None or humidity is None:
        return False

    return temperature >= temp_limit and humidity >= humidity_limit


def build_oled_message(summary):
    """
    Crea un comando compacto para la OLED.
    Formato: OLED;linea1;linea2;linea3;linea4
    """
    temperature = summary["measurements"][TEMPERATURE_MEASUREMENT]
    humidity = summary["measurements"][HUMIDITY_MEASUREMENT]
    return "OLED;ALERTA CLIMA;Temp {:.1f}C;Hum {:.1f}%;Ventilar ahora".format(
        temperature,
        humidity,
    )


def build_station_topic(summary):
    return "{country}/{state}/{city}/{user}/in".format(
        country=summary["country"],
        state=summary["state"],
        city=summary["city"],
        user=summary["user"],
    )
