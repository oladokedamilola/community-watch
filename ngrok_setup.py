# Run this script to start ngrok tunnel for HTTPS testing
import subprocess
import sys

def setup_ngrok():
    """Start ngrok tunnel for HTTPS testing"""
    try:
        # Check if ngrok is installed
        subprocess.run(['ngrok', '--version'], capture_output=True)
        
        print("Starting ngrok tunnel on port 8000...")
        subprocess.run(['ngrok', 'http', '8000'])
        
    except FileNotFoundError:
        print("ngrok not found. Please install ngrok from https://ngrok.com/download")
        print("Then run: ngrok http 8000")
        sys.exit(1)

if __name__ == '__main__':
    setup_ngrok()

# Alternative: Use localtunnel
# npm install -g localtunnel
# lt --port 8000 --subdomain gridwatch