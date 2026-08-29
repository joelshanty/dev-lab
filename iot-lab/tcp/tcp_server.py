import asyncio
import threading
import time

# specify the host and port for the TCP servers
TCP_SERVER_CONFIGS = [("127.0.0.1", 50000), ("127.0.0.1", 50001)]

class TCPServer:
    def __init__(self, host, port, name=None):
        self.host = host
        self.port = port
        self.name = name or f"{host}:{port}"
        self._server = None
        self._loop = None
        self._thread = None
        self._server_task = None
        self._client_tasks = set()


    async def handle_client(self, reader, writer):
        task = asyncio.current_task()
        self._client_tasks.add(task)
        addr = writer.get_extra_info('peername')
        print(f"[{self.name}] Connection from {addr}")
        try:
            while True:
                data = await reader.read(100)
                if not data:
                    break
                msg = data.decode().strip()
                print(f"[{self.name}] Received: {msg}")
                writer.write(f"Echo: {msg}\n".encode())
                await writer.drain()
        except asyncio.CancelledError:
            print(f"[{self.name}] Client task cancelled.")
        except Exception as e:
            print(f"[{self.name}] Error: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                print(f"[{self.name}] Error closing writer: {e}")
            self._client_tasks.discard(task)
            print(f"[{self.name}] Connection closed")


    async def _start(self):
        self._server = await asyncio.start_server(self.handle_client, self.host, self.port, reuse_address=True, reuse_port=True)
        print(f"[{self.name}] Server started on {self.host}:{self.port}")
        self._server_task = asyncio.create_task(self._server.serve_forever())

            
    def run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.create_task(self._start())
            self._loop.run_forever()
        except Exception as e:
            print(f"[{self.name}] Error in run loop: {e}")
        finally:
            self._loop.run_until_complete(self.stop())
            self._loop.close()
            print(f"[{self.name}] Event loop closed")



    async def stop(self):
        print(f"[{self.name}] Stopping server...")

        # Cancel serve_forever task
        if self._server_task:
            self._server_task.cancel()
            try:
                await self._server_task
            except asyncio.CancelledError:
                pass

        # Cancel all client tasks
        for task in list(self._client_tasks):
            task.cancel()
        await asyncio.gather(*self._client_tasks, return_exceptions=True)
        self._client_tasks.clear()

        # Close the server
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            print(f"[{self.name}] Server stopped")


    def stop_server_from_main(self):
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.stop(), self._loop)
            self._loop.call_soon_threadsafe(self._loop.stop)


class TCPServerManager:
    def __init__(self, configs):
        self.configs = configs
        self.servers = []

    def start_all(self):
        for host, port in self.configs:
            server = TCPServer(host, port)
            thread = threading.Thread(target=server.run, daemon=True)
            thread.start()
            server._thread = thread  # Keep reference
            self.servers.append(server)
            print(f"[Manager] Started server on {host}:{port}")

    def stop_all(self):
        print("[Manager] Stopping all servers...")
        for server in self.servers:
            server.stop_server_from_main()
        time.sleep(1)  # Allow shutdown to complete


if __name__ == "__main__":
    
    manager = TCPServerManager(TCP_SERVER_CONFIGS)
    manager.start_all()

    try:
        print("[Main] Servers running. Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[Main] Caught interrupt. Cleaning up...")
        manager.stop_all()
        print("[Main] Shutdown complete.")

