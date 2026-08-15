import asyncio
import os

from .infrai_storage import InfraiStorage


async def setup() -> None:
    bucket = os.environ.get("COURSE_ASSET_BUCKET", "course-delivery-assets")
    storage = InfraiStorage()
    try:
        await storage.create_bucket(bucket)
    finally:
        await storage.close()
    print(f"Bucket ready: {bucket}")


def main() -> None:
    asyncio.run(setup())
