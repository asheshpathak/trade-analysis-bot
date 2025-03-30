"""
Simple HTTP server to capture Zerodha authentication redirect and token.
"""
import http.server
import socketserver
import urllib.parse
import threading
import webbrowser
import ssl
import os
from typing import Optional

# Shared variable to store the captured request token
captured_request_token = None
server_started = threading.Event()

class TokenHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler to capture Zerodha redirect with token."""

    def log_message(self, format, *args):
        """Silence server logs."""
        return

    def do_GET(self):
        """Handle GET request, capture token and display success message."""
        global captured_request_token

        # Parse URL and query parameters
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)

        # Check if request token is in the URL
        if parsed_path.path == '/redirect' and 'request_token' in query_params:
            # Capture the token
            captured_request_token = query_params['request_token'][0]

            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            success_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authentication Successful</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; text-align: center; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
                    .success {{ color: green; font-size: 24px; margin-bottom: 20px; }}
                    .token {{ background-color: #f5f5f5; padding: 10px; border-radius: 3px; word-break: break-all; text-align: left; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="success">✓ Authentication Successful!</div>
                    <p>Your request token has been captured:</p>
                    <div class="token">{captured_request_token}</div>
                    <p>You can now close this window and return to the application.</p>
                </div>
            </body>
            </html>
            """

            self.wfile.write(success_html.encode())
        else:
            # Any other path, return 404
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'Not Found')


def start_server(port=5000, use_https=False):  # Changed default to HTTP
    """
    Start the token capturing server.

    Args:
        port: Port number to listen on
        use_https: Whether to use HTTPS

    Returns:
        Server thread
    """
    global server_started

    httpd = socketserver.TCPServer(("", port), TokenHandler)

    if use_https:
        try:
            # Create or use certfile path directly
            certfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.pem")

            # Create a self-signed certificate if it doesn't exist
            if not os.path.exists(certfile):
                print("Creating self-signed certificate...")
                from OpenSSL import crypto

                # Create a key pair
                k = crypto.PKey()
                k.generate_key(crypto.TYPE_RSA, 2048)

                # Create a self-signed cert
                cert = crypto.X509()
                cert.get_subject().CN = "localhost"
                cert.set_serial_number(1000)
                cert.gmtime_adj_notBefore(0)
                cert.gmtime_adj_notAfter(10*365*24*60*60)  # 10 years
                cert.set_issuer(cert.get_subject())
                cert.set_pubkey(k)
                cert.sign(k, 'sha256')

                # Write PEM file with both key and cert
                with open(certfile, "wb") as f:
                    f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))
                    f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

            # Wrap the socket with SSL
            httpd.socket = ssl.wrap_socket(
                httpd.socket,
                certfile=certfile,
                server_side=True
            )
            protocol = "HTTPS"
        except Exception as e:
            print(f"Failed to set up HTTPS: {e}")
            print("Falling back to HTTP")
            use_https = False
            protocol = "HTTP"
    else:
        protocol = "HTTP"

    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    server_started.set()
    print(f"{protocol} server started on port {port}...")
    return server_thread, httpd


def capture_token(api_key, port=5000, use_https=False):  # Changed default to HTTP
    """
    Start server, open browser with login URL, and capture the token.

    Args:
        api_key: Zerodha API key
        port: Port to run the server on
        use_https: Whether to use HTTPS

    Returns:
        Captured request token
    """
    global captured_request_token

    # Clear any previous token
    captured_request_token = None

    # Determine the protocol
    protocol = "https" if use_https else "http"

    # Start the server in a thread
    server_thread, httpd = start_server(port, use_https)

    # Wait for server to start
    server_started.wait()

    # Construct the login URL
    redirect_uri = f"{protocol}://localhost:{port}/redirect"
    login_url = f"https://kite.zerodha.com/connect/login?v=3&api_key={api_key}&redirect_uri={redirect_uri}"

    print("\n==== ZERODHA AUTHENTICATION ====")
    print(f"\nOpening browser to authenticate with Zerodha...")
    print(f"Login URL: {login_url}")

    # Open the browser
    try:
        webbrowser.open(login_url)
    except:
        print("Could not open browser automatically. Please copy and paste the URL manually.")

    print("\nWaiting for authentication... (Check your browser)")

    # Wait for the token to be captured
    try:
        while captured_request_token is None:
            import time
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
        httpd.shutdown()
        return None

    # Token captured, shut down the server
    httpd.shutdown()

    print(f"\nRequest token captured: {captured_request_token}")
    return captured_request_token


if __name__ == "__main__":
    # For testing, replace with your API key
    test_api_key = "your_api_key"
    token = capture_token(test_api_key)
    print(f"Final token: {token}")