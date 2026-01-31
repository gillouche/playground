import asyncio
import uuid
from typing import Optional
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from config import KafkaConfig


class KafkaClient:
    def __init__(self, config: KafkaConfig):
        self.config = config
        self.producer: Optional[AIOKafkaProducer] = None

    async def connect(self):
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.config.bootstrap_servers
        )
        await self.producer.start()

    async def disconnect(self):
        if self.producer:
            await self.producer.stop()

    async def produce(self, message: str, topic: Optional[str] = None) -> dict:
        target_topic = topic or self.config.topic
        await self.producer.send_and_wait(target_topic, message.encode("utf-8"))
        return {"topic": target_topic, "message": message, "status": "produced"}

    async def consume(self, topic: Optional[str] = None, timeout: float = 5.0) -> list[dict]:
        target_topic = topic or self.config.topic
        unique_group = f"infra-check-{uuid.uuid4().hex[:8]}"
        consumer = AIOKafkaConsumer(
            target_topic,
            bootstrap_servers=self.config.bootstrap_servers,
            auto_offset_reset="earliest",
            group_id=unique_group
        )
        await consumer.start()
        messages = []
        try:
            end_time = asyncio.get_event_loop().time() + timeout
            while asyncio.get_event_loop().time() < end_time and len(messages) < 10:
                result = await consumer.getmany(timeout_ms=1000, max_records=10)
                for tp, msgs in result.items():
                    for msg in msgs:
                        messages.append({
                            "topic": msg.topic,
                            "partition": msg.partition,
                            "offset": msg.offset,
                            "value": msg.value.decode("utf-8")
                        })
                if messages:
                    break
        finally:
            await consumer.stop()
        return messages

    async def health_check(self) -> dict:
        try:
            metadata = await self.producer.client.fetch_all_metadata()
            return {
                "status": "healthy",
                "bootstrap_servers": self.config.bootstrap_servers,
                "topics": list(metadata.topics())
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
