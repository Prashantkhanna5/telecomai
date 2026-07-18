import os
from app.main import demo

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting TeleHeal Web Service via root launcher on port {port}...")
    demo.launch(server_name="0.0.0.0", server_port=port, share=False)
