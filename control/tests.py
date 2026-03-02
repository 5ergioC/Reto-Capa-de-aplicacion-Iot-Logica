from django.test import SimpleTestCase

from control import event_rules


class EventRulesTests(SimpleTestCase):
    def test_build_station_summaries_groups_measurements_by_station(self):
        rows = [
            {
                "station_id": 7,
                "station__user__username": "sergi",
                "station__location__city__name": "bogota",
                "station__location__state__name": "cundinamarca",
                "station__location__country__name": "colombia",
                "measurement__name": "temperatura",
                "check_value": 29.4,
            },
            {
                "station_id": 7,
                "station__user__username": "sergi",
                "station__location__city__name": "bogota",
                "station__location__state__name": "cundinamarca",
                "station__location__country__name": "colombia",
                "measurement__name": "humedad",
                "check_value": 72.1,
            },
        ]

        summaries = event_rules.build_station_summaries(rows)

        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0]["measurements"]["temperatura"], 29.4)
        self.assertEqual(summaries[0]["measurements"]["humedad"], 72.1)

    def test_should_trigger_oled_event_requires_both_thresholds(self):
        summary = {
            "measurements": {
                "temperatura": 29.0,
                "humedad": 71.0,
            }
        }

        self.assertTrue(
            event_rules.should_trigger_oled_event(
                summary,
                temp_threshold=28.0,
                humidity_threshold=70.0,
            )
        )
        self.assertFalse(
            event_rules.should_trigger_oled_event(
                summary,
                temp_threshold=30.0,
                humidity_threshold=70.0,
            )
        )

    def test_build_oled_message_formats_display_payload(self):
        summary = {
            "measurements": {
                "temperatura": 29.5,
                "humedad": 76.2,
            }
        }

        message = event_rules.build_oled_message(summary)

        self.assertEqual(
            message,
            "OLED;ALERTA CLIMA;Temp 29.5C;Hum 76.2%;Ventilar ahora",
        )
