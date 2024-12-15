import os
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
import threading
import time

class TestApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.connected = False
        print("Initializing connection...")
        
    def error(self, reqId, errorCode, errorString, *args):
        print(f"Error {errorCode}: {errorString}")
        
    def connectAck(self):
        print("Connection acknowledged")
        
    def nextValidId(self, orderId):
        print(f"Connected! Next valid order ID: {orderId}")
        self.connected = True

def main():
    print("Starting test with Docker container...")
    app = TestApp()
    
    # Test avec différentes configurations
    hosts = ["127.0.0.1", "localhost", "0.0.0.0"]
    ports = [4001, 4002]
    client_ids = [123]
    
    for host in hosts:
        for port in ports:
            for client_id in client_ids:
                try:
                    print(f"\nTesting connection to {host}:{port}:{client_id}")
                    app = TestApp()
                    app.connect(host, port, clientId=client_id)
                    
                    api_thread = threading.Thread(target=lambda: app.run(), daemon=True)
                    api_thread.start()
                    
                    time.sleep(2)
                    
                    if app.isConnected():
                        print(f"✅ Success with {host}:{port}:{client_id}")
                        return
                    else:
                        print(f"❌ Failed with {host}:{port}:{client_id}")
                    
                    app.disconnect()
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"Error with {host}:{port}: {str(e)}")
                    continue

if __name__ == "__main__":
    main()