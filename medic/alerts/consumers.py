import json
from channels.generic.websocket import AsyncWebsocketConsumer


class AlertConsumer(AsyncWebsocketConsumer):

    async def connect(self):

        await self.channel_layer.group_add(
            "doctor_alerts",
            self.channel_name
        )

        await self.accept()


    async def disconnect(self, close_code):

        await self.channel_layer.group_discard(
            "doctor_alerts",
            self.channel_name
        )


    async def send_alert(self, event):

        await self.send(text_data=json.dumps({
            "message": event["message"],
            "severity": event["severity"]
        }))