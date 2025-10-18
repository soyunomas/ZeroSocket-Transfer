import asyncio
import os
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog

from PIL import Image, ImageTk
from ttkthemes import ThemedTk
from zeroconf import ServiceBrowser, Zeroconf

import config_manager
import network_logic as net
from discovery_dialog import DiscoveryDialog
from gui_tabs import ServerTab, SenderTab, ReceiverTab
from settings_dialog import SettingsDialog
from utils import log_message, format_file_size


class FileTransferApp(ThemedTk):
    def __init__(self):
        super().__init__(theme="arc")
        self.title("ZeroSocket File Transfer")
        self.geometry("950x700")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # --- Configuración y Estado ---
        self.config = config_manager.load_config()
        self.server_thread = None
        self.service_advertiser = None
        self.advertiser_thread = None
        self.client_thread = None
        self.stop_client_event = threading.Event()
        
        # --- CAMBIO: Variables de estado para el archivo a enviar ---
        self.file_to_send_path = tk.StringVar()
        self.file_to_send_name = tk.StringVar(value="Ningún archivo seleccionado")
        self.file_to_send_details = tk.StringVar(value="Tamaño: N/A")
        
        self.logo_image = None

        # --- Colas de Logs ---
        self.log_queues = {
            "server": queue.Queue(),
            "sender": queue.Queue(),
            "client": queue.Queue(),
        }

        # --- Construcción de la GUI ---
        self._create_toolbar()
        
        main_frame = ttk.Frame(self)
        main_frame.pack(expand=True, fill="both")

        self._create_sidebar(main_frame)
        self._create_notebook(main_frame)
        
        self.apply_config()
        self.after(100, self.process_log_queues)
        
        self.after(500, self.trigger_auto_discovery_and_connect)


    def _create_toolbar(self):
        toolbar = ttk.Frame(self, padding="5")
        toolbar.pack(side="top", fill="x")
        settings_button = ttk.Button(toolbar, text="Configuración", command=self.open_settings)
        settings_button.pack(side="left")

    def _create_sidebar(self, parent):
        sidebar_frame = ttk.Frame(parent, width=150)
        sidebar_frame.pack(side="left", fill="y", padx=(10, 0), pady=10)
        sidebar_frame.pack_propagate(False)

        try:
            logo_path = os.path.join("img", "logo.png")
            original_image = Image.open(logo_path)
            
            target_height = 120
            width, height = original_image.size
            aspect_ratio = width / height
            new_width = int(target_height * aspect_ratio)
            
            resized_image = original_image.resize((new_width, target_height), Image.LANCZOS)
            self.logo_image = ImageTk.PhotoImage(resized_image)

            logo_label = ttk.Label(sidebar_frame, image=self.logo_image)
            logo_label.pack(pady=20)
            
        except FileNotFoundError:
            error_label = ttk.Label(sidebar_frame, text="Logo no encontrado\nen img/logo.png", justify="center")
            error_label.pack(pady=20, padx=5)
        except Exception as e:
            print(f"Error al cargar el logo: {e}")
            error_label = ttk.Label(sidebar_frame, text="Error al\ncargar logo", justify="center")
            error_label.pack(pady=20, padx=5)

    def _create_notebook(self, parent):
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(side="left", expand=True, fill="both", padx=10, pady=10)

        self.server_tab = ServerTab(self.notebook, self)
        # --- CAMBIO: Pasar las nuevas variables a la pestaña Emisor ---
        self.sender_tab = SenderTab(
            self.notebook, 
            self, 
            self.file_to_send_name, 
            self.file_to_send_details
        )
        self.receiver_tab = ReceiverTab(self.notebook, self)

        self.notebook.add(self.receiver_tab, text="Cliente / Receptor")
        self.notebook.add(self.sender_tab, text="Emisor")
        self.notebook.add(self.server_tab, text="Servidor")
        
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def apply_config(self):
        self.server_tab.port_entry.delete(0, tk.END)
        self.server_tab.port_entry.insert(0, self.config.get("server_port", "8765"))
        self.server_tab.topic_entry.delete(0, tk.END)
        self.server_tab.topic_entry.insert(0, self.config.get("server_topic", "filetransfer"))

        self.sender_tab.uri_entry.delete(0, tk.END)
        self.sender_tab.uri_entry.insert(0, self.config.get("sender_ip", "localhost"))
        self.sender_tab.port_entry.delete(0, tk.END)
        self.sender_tab.port_entry.insert(0, self.config.get("sender_port", "8765"))
        self.sender_tab.topic_entry.delete(0, tk.END)
        self.sender_tab.topic_entry.insert(0, self.config.get("sender_topic", "filetransfer"))

        self.receiver_tab.uri_entry.delete(0, tk.END)
        self.receiver_tab.uri_entry.insert(0, self.config.get("receiver_ip", "localhost"))
        self.receiver_tab.port_entry.delete(0, tk.END)
        self.receiver_tab.port_entry.insert(0, self.config.get("receiver_port", "8765"))
        self.receiver_tab.topic_entry.delete(0, tk.END)
        self.receiver_tab.topic_entry.insert(0, self.config.get("receiver_topic", "filetransfer"))

    def save_and_apply_config(self, new_config):
        self.config = new_config
        config_manager.save_config(self.config)
        self.apply_config()

    def open_settings(self):
        SettingsDialog(self)

    def log_to_widget(self, widget, message):
        widget.config(state="normal")
        widget.insert(tk.END, message + "\n")
        widget.see(tk.END)
        widget.config(state="disabled")

    def process_log_queues(self):
        if not self.log_queues["server"].empty():
            self.log_to_widget(self.server_tab.log_widget, self.log_queues["server"].get_nowait())
        if not self.log_queues["client"].empty():
            self.log_to_widget(self.receiver_tab.log_widget, self.log_queues["client"].get_nowait())
        if not self.log_queues["sender"].empty():
            self.log_to_widget(self.sender_tab.log_widget, self.log_queues["sender"].get_nowait())
        self.after(100, self.process_log_queues)

    # --- Lógica de Control ---
    
    def on_tab_changed(self, event):
        selected_tab_index = self.notebook.index(self.notebook.select())
        if selected_tab_index == 0:
            self.trigger_auto_discovery_and_connect()

    def trigger_auto_discovery_and_connect(self):
        is_client_active = self.client_thread is not None and self.client_thread.is_alive()
        if self.config.get("auto_connect_on_startup", False) and not is_client_active:
            self.discover_server(is_automatic=True)

    def start_server(self):
        port = self.server_tab.port_entry.get()
        server_topic = self.server_tab.topic_entry.get()
        if not port.isdigit() or not server_topic:
            log_message(self.log_queues["server"], "Error: Puerto y Topic no pueden estar vacíos.")
            return

        def run_loop():
            try:
                asyncio.set_event_loop(asyncio.new_event_loop())
                asyncio.get_event_loop().run_until_complete(
                    net.start_server_async("0.0.0.0", int(port), self.log_queues["server"])
                )
            except Exception as e:
                log_message(self.log_queues["server"], f"Error fatal en el hilo del servidor: {e}")

        self.server_thread = threading.Thread(target=run_loop, daemon=True)
        self.server_thread.start()
        self.server_tab.set_state("running")
        
        log_message(self.log_queues["server"], "Iniciando anuncio de servicio en la red...")
        self.service_advertiser = net.ServiceAdvertiser(
            "File Transfer Server", int(port), server_topic, self.log_queues["server"]
        )
        self.advertiser_thread = threading.Thread(target=self.service_advertiser.run, daemon=True)
        self.advertiser_thread.start()

    def stop_server(self):
        if self.service_advertiser:
            self.service_advertiser.stop()
        if self.server_thread and self.server_thread.is_alive():
            net.stop_server_event.set()
        self.server_tab.set_state("stopped")

    def select_file(self):
        """
        Lógica mejorada para seleccionar un archivo, recordando la última carpeta
        y mostrando detalles claros del archivo seleccionado.
        """
        # --- LÓGICA MEJORADA ---
        # 1. Obtener la última carpeta usada desde la configuración
        last_folder = self.config.get("last_used_folder", os.path.expanduser("~"))

        # 2. Abrir el diálogo de archivo comenzando en esa carpeta
        filepath = filedialog.askopenfilename(initialdir=last_folder)

        # 3. Si el usuario selecciona un archivo, procesarlo
        if filepath:
            # Guardar la ruta completa en la variable de estado interna
            self.file_to_send_path.set(filepath)

            # Obtener y mostrar el nombre del archivo
            filename = os.path.basename(filepath)
            self.file_to_send_name.set(filename)

            # Obtener, formatear y mostrar el tamaño del archivo
            try:
                size_bytes = os.path.getsize(filepath)
                self.file_to_send_details.set(f"Tamaño: {format_file_size(size_bytes)}")
            except OSError:
                self.file_to_send_details.set("Tamaño: Desconocido")

            # 4. Actualizar y guardar la configuración con la nueva carpeta
            new_folder = os.path.dirname(filepath)
            self.config["last_used_folder"] = new_folder
            config_manager.save_config(self.config)

    def start_sender(self):
        uri = f"ws://{self.sender_tab.uri_entry.get()}:{self.sender_tab.port_entry.get()}"
        topic = self.sender_tab.topic_entry.get()
        file_path = self.file_to_send_path.get()
        if not all([uri, topic, file_path]):
            log_message(self.log_queues["sender"], "Error: Todos los campos y un archivo son requeridos.")
            return

        def re_enable_button():
            self.sender_tab.send_button.config(state="normal")
        def run_sender():
            try:
                asyncio.run(net.send_file_async(uri, topic, file_path, self.log_queues["sender"], re_enable_button))
            except Exception as e:
                log_message(self.log_queues["sender"], f"Error fatal en el hilo del emisor: {e}")
                re_enable_button()

        self.sender_tab.send_button.config(state="disabled")
        threading.Thread(target=run_sender, daemon=True).start()

    def start_client(self):
        uri = f"ws://{self.receiver_tab.uri_entry.get()}:{self.receiver_tab.port_entry.get()}"
        topic = self.receiver_tab.topic_entry.get()
        download_folder = self.config.get("download_folder", ".")
        if not all([uri, topic]):
            log_message(self.log_queues["client"], "Error: Todos los campos son requeridos.")
            return

        self.stop_client_event.clear()
        
        def run_client():
            try:
                asyncio.set_event_loop(asyncio.new_event_loop())
                asyncio.get_event_loop().run_until_complete(
                    net.receive_files_async(uri, topic, self.log_queues["client"], self.stop_client_event, download_folder)
                )
            except Exception as e:
                log_message(self.log_queues["client"], f"Error fatal en el hilo del cliente: {e}")
            finally:
                self.after(0, self.on_client_disconnected)

        self.client_thread = threading.Thread(target=run_client, daemon=True)
        self.client_thread.start()
        self.receiver_tab.set_state("running")

    def stop_client(self):
        self.stop_client_event.set()
        self.on_client_disconnected()

    def on_client_disconnected(self):
        self.receiver_tab.set_state("stopped")

    def discover_server(self, is_automatic=False):
        if not is_automatic:
            log_message(self.log_queues["client"], "Buscando servidores en la red local (3 segundos)...")
        else:
            log_message(self.log_queues["client"], "Buscando servidores automáticamente...")
            
        self.receiver_tab.discover_button.config(state="disabled")
        threading.Thread(target=self._run_discovery, args=(is_automatic,), daemon=True).start()

    def _run_discovery(self, is_automatic=False):
        class ServiceListener:
            def __init__(self): self.found_services = {}
            def add_service(self, zc, type_, name): self.update_service(zc, type_, name)
            def update_service(self, zc, type_, name):
                info = zc.get_service_info(type_, name)
                if info: self.found_services[name] = info
            def remove_service(self, zc, type_, name): self.found_services.pop(name, None)

        zeroconf = Zeroconf()
        listener = ServiceListener()
        browser = ServiceBrowser(zeroconf, "_ws-file-xfer._tcp.local.", listener)
        time.sleep(3)
        found_services = list(listener.found_services.values())
        
        def show_dialog(services):
            log_message(self.log_queues["client"], f"Búsqueda finalizada. Se encontraron {len(services)} servidor(es).")
            dialog = DiscoveryDialog(self, services)
            if dialog.result:
                self.update_receiver_fields(*dialog.result)

        def auto_connect_or_show_dialog(services):
            num_found = len(services)
            if num_found == 1:
                log_message(self.log_queues["client"], "Un único servidor encontrado. Conectando automáticamente...")
                info = services[0]
                ip = net.get_ip_from_service(info)
                
                if ip:
                    port = info.port
                    topic = info.properties.get(b'topic', b'filetransfer').decode('utf-8')
                    self.update_receiver_fields(ip, port, topic)
                    self.start_client()
                else:
                    log_message(self.log_queues["client"], f"Error: No se pudo obtener la IP para el servicio {info.name}")

            elif num_found > 1:
                log_message(self.log_queues["client"], "Múltiples servidores encontrados. Por favor, selecciona uno.")
                show_dialog(services)
            else:
                log_message(self.log_queues["client"], "No se encontraron servidores para conexión automática.")
        try:
            if is_automatic:
                self.after(0, lambda: auto_connect_or_show_dialog(found_services))
            else:
                self.after(0, lambda: show_dialog(found_services))
        finally:
            browser.cancel()
            zeroconf.close()
            self.after(0, lambda: self.receiver_tab.discover_button.config(state="normal"))

    def update_receiver_fields(self, ip, port, topic=None):
        log_message(self.log_queues["client"], f"Servidor seleccionado: {ip}:{port}")
        self.receiver_tab.uri_entry.delete(0, tk.END)
        self.receiver_tab.uri_entry.insert(0, ip)
        self.receiver_tab.port_entry.delete(0, tk.END)
        self.receiver_tab.port_entry.insert(0, str(port))
        if topic:
             self.receiver_tab.topic_entry.delete(0, tk.END)
             self.receiver_tab.topic_entry.insert(0, topic)

    def on_closing(self):
        self.stop_server()
        self.stop_client()
        self.destroy()

if __name__ == "__main__":
    app = FileTransferApp()
    app.mainloop()
