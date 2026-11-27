import os

from backend import create_app

app = create_app()

if __name__ == "__main__":
    # debug only when asked, never on a public host
    app.run(debug=os.getenv("FLASK_DEBUG") == "1", port=5000)
