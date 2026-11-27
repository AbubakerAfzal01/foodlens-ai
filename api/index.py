# Vercel entry point (untested): exposes the Flask app as `app`.
from backend import create_app

app = create_app()
