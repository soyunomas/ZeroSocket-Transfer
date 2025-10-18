import asyncio
import base64
import os
import socket
import threading
from collections import defaultdict

import websockets
from zeroconf import ServiceInfo, Zeroconf

from config import max_size
from utils import log_message, get_primary_local_ip

# Estado del servidor
server_clients = defaultdict(set)
stop_server_event = asyncio.Event()


class ServiceAdvertiser:
    """Anuncia un servicio en la red local usando Zeroconf (mDNS)."""
    def __init__(self, name, port, topic, log_queue):
        self.name = name
        self.port = port
        self.topic = topic
        self.log_queue = log_queue
        self.zeroconf = None
        self.info = None
        self._stop_event = threading.Event()

    def run(self):
        """Inicia el anuncio del servicio en un hilo."""
        try:
            ip_address = get_primary_local_ip()
            hostname = socket.gethostname()
            
            service_type = "_ws-file-xfer._tcp.local."
            service_name = f"{self.name} on {hostname}:{self.port}.{service_type}"

            properties = {
                "topic": self.topic.encode('utf-8')
            }

            self.info = ServiceInfo(
                type_=service_type,
                name=service_name,
                addresses=[socket.inet_aton(ip_address)],
                port=self.port,
                properties=properties,
            )
            
            self.zeroconf = Zeroconf()
            self.zeroconf.register_service(self.info)
            log_message(self.log_queue, f"Servicio '{self.name}' (Topic: {self.topic}) anunciado en {ip_address}:{self.port}")
            
            # Mantener el hilo vivo hasta que se llame a stop
            self._stop_event.wait()

        except Exception as e:
            log_message(self.log_queue, f"Error en el anunciador de servicios: {e}")
        finally:
            # --- LÍNEA CORREGIDA ---
            # Se usa self.log_queue (la cola individual) en lugar de self.log_queues.
            log_message(self.log_queue, "Anuncio de servicio detenido.")

    def stop(self):
        """Detiene el anuncio del servicio y libera los recursos."""
        if self.zeroconf and self.info:
            log_message(self.log_queue, "Deteniendo anuncio de servicio...")
            self.zeroconf.unregister_service(self.info)
            self.zeroconf.close()
        self._stop_event.set()


async def server_handler(websocket, log_queue):
    """Manejador de conexiones del servidor WebSocket."""
    remote_ip = websocket.remote_address
    log_message(log_queue, f"Cliente conectado desde {remote_ip}")
    try:
        async for message in websocket:
            if message.startswith("subscribe:"):
                topic = message.split(":", 1)[1]
                server_clients[topic].add(websocket)
                log_message(log_queue, f"Cliente {remote_ip} suscrito al topic: {topic}")
            elif message.startswith("message:"):
                parts = message.split(":", 4)
                if len(parts) == 5:
                    _, topic, mime_type, file_name, file_data = parts
                    log_message(log_queue, f"Recibido archivo '{file_name}' en el topic '{topic}'")
                    clients_to_send = list(server_clients[topic])
                    if clients_to_send:
                        log_message(log_queue, f"Distribuyendo a {len(clients_to_send)} cliente(s)...")
                        message_to_send = f"{mime_type}:{file_name}:{file_data}"
                        websockets.broadcast(clients_to_send, message_to_send)
                else:
                    log_message(log_queue, f"Recibido mensaje con formato incorrecto: {message[:50]}...")
    except websockets.exceptions.ConnectionClosed:
        log_message(log_queue, f"Cliente {remote_ip} desconectado.")
    finally:
        for clients_in_topic in server_clients.values():
            clients_in_topic.discard(websocket)


async def start_server_async(ip, port, log_queue):
    """Inicia el servidor WebSocket y espera a que se detenga."""
    stop_server_event.clear()

    async def handler(websocket):
        await server_handler(websocket, log_queue)

    log_message(log_queue, f"Iniciando servidor en {ip}:{port}...")
    try:
        async with websockets.serve(handler, ip, port, max_size=max_size) as server:
            log_message(log_queue, "Servidor iniciado y escuchando.")
            await stop_server_event.wait()
    except Exception as e:
        log_message(log_queue, f"Error al iniciar el servidor: {e}")
    finally:
        log_message(log_queue, "El servidor se ha detenido correctamente.")


async def receive_files_async(uri, topic, log_queue, stop_event, save_directory):
    """Cliente que se conecta, suscribe y recibe archivos."""
    log_message(log_queue, f"Intentando conectar a {uri}...")
    log_message(log_queue, f"Los archivos se guardarán en: {save_directory}")
    try:
        async with websockets.connect(uri, max_size=max_size) as websocket:
            log_message(log_queue, f"Conectado al servidor en {uri}")
            await websocket.send(f"subscribe:{topic}")
            log_message(log_queue, f"Suscrito al topic: {topic}")

            while not stop_event.is_set():
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    parts = message.split(":", 2)
                    if len(parts) == 3:
                        _, file_name, file_data = parts
                        log_message(log_queue, f"Archivo '{file_name}' recibido del topic '{topic}'.")
                        try:
                            file_bytes = base64.b64decode(file_data)
                            os.makedirs(save_directory, exist_ok=True)
                            save_path = os.path.join(save_directory, file_name)
                            with open(save_path, "wb") as f:
                                f.write(file_bytes)
                            log_message(log_queue, f"Archivo '{file_name}' guardado en '{save_path}'.")
                        except Exception as e:
                            log_message(log_queue, f"Error al guardar el archivo '{file_name}': {e}")
                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    log_message(log_queue, "Conexión cerrada por el servidor.")
                    break
    except Exception as e:
        log_message(log_queue, f"Error en el cliente: {e}")
    finally:
        log_message(log_queue, "Cliente desconectado.")


async def send_file_async(uri, topic, file_path, log_queue, callback):
    """Cliente que se conecta, envía un archivo y se desconecta."""
    try:
        log_message(log_queue, f"Intentando conectar a {uri} para enviar...")
        async with websockets.connect(uri, max_size=max_size) as websocket:
            log_message(log_queue, f"Conectado. Leyendo archivo '{os.path.basename(file_path)}'...")
            
            with open(file_path, "rb") as file:
                file_data_encoded = base64.b64encode(file.read()).decode('utf-8')

            mime_type = "application/octet-stream"
            file_name = os.path.basename(file_path)
            message = f"message:{topic}:{mime_type}:{file_name}:{file_data_encoded}"
            
            if len(message.encode('utf-8')) > max_size:
                log_message(log_queue, f"Error: Archivo supera tamaño máximo de {max_size / (1024*1024):.0f} MB.")
                return

            await websocket.send(message)
            log_message(log_queue, "Archivo enviado correctamente.")
    except FileNotFoundError:
        log_message(log_queue, f"Error: No se encontró el archivo en la ruta: {file_path}")
    except Exception as e:
        log_message(log_queue, f"Error durante el envío del archivo: {e}")
    finally:
        if callback:
            callback()
