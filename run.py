from hypercorn.config import Config
from hypercorn.asyncio import serve
import asyncio
from app import create_app

app = create_app()

config = Config()
config.bind = ["localhost:5000"]
config.use_reloader = True

if __name__ == "__main__":
    asyncio.run(serve(app, config))
