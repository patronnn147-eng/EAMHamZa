import logging
import asyncio
from typing import Dict, List

logger = logging.getLogger(__name__)

class NotificationBroadcaster:
    """Manages SSE connections for notifications"""
    def __init__(self):
        self.user_queues: Dict[int, List[asyncio.Queue]] = {}

    async def subscribe(self, user_id: int) -> asyncio.Queue:
        queue = asyncio.Queue()
        if user_id not in self.user_queues:
            self.user_queues[user_id] = []
        self.user_queues[user_id].append(queue)
        logger.debug(f"User {user_id} subscribed to notifications. Total queues: {len(self.user_queues[user_id])}")
        return queue

    def unsubscribe(self, user_id: int, queue: asyncio.Queue):
        if user_id in self.user_queues:
            self.user_queues[user_id].remove(queue)
            if not self.user_queues[user_id]:
                del self.user_queues[user_id]
        logger.debug(f"User {user_id} unsubscribed from notifications.")

    async def broadcast(self, user_id: int, notification_data: dict):
        if user_id in self.user_queues:
            # Create a list of tasks to put in each queue concurrently
            tasks = [queue.put(notification_data) for queue in self.user_queues[user_id]]
            if tasks:
                await asyncio.gather(*tasks)
            logger.debug(f"Broadcasted notification to user {user_id} (found {len(tasks)} active queues)")


# Global broadcaster instance
broadcaster = NotificationBroadcaster()
