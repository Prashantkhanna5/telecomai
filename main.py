import os
from app.main import launch_app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    launch_app(port)
