# kosar/run.py

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Bind to 0.0.0.0 to be accessible externally on the same network
    app.run(debug=True, host="0.0.0.0", port=7778)