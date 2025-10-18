import asyncio
import queue
import socket
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog

from ttkthemes import ThemedTk
from zeroconf import ServiceBrowser, Zeroconf

import config_manager
import network_logic as net
from discovery_dialog import DiscoveryDialog
from gui_tabs import ServerTab, SenderTab, ReceiverTab
from settings_dialog import SettingsDialog
from utils import log_message


class FileTransferApp(ThemedTk):
    def __init__(self):
        super().__init__(theme="arc")
        self.title("WebSocket File Transfer")
        self.geometry("850x700") 
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # --- Configuración y Estado ---
        self.config = config_manager.load_config()
        self.server_thread = None
        self.service_advertiser = None
        self.advertiser_thread = None
        self.client_thread = None
        self.stop_client_event = threading.Event()
        self.file_to_send_path = tk.StringVar()

        # --- Colas de Logs ---
        self.log_queues = {
            "server": queue.Queue(),
            "sender": queue.Queue(),
            "client": queue.Queue(),
        }

        # --- Construcción de la GUI ---
        self._create_toolbar()
        self._create_notebook()
        self.apply_config()
        self.after(100, self.process_log_queues)

    def _create_toolbar(self):
        toolbar = ttk.Frame(self, padding="5")
        toolbar.pack(side="top", fill="x")
        settings_button = ttk.Button(toolbar, text="Configuración", command=self.open_settings)
        settings_button.pack(side="left")

    def _create_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        # Crear e instanciar las pestañas desde gui_tabs.py
        self.server_tab = ServerTab(self.notebook, self)
        self.sender_tab = SenderTab(self.notebook, self, self.file_to_send_path)
        self.receiver_tab = ReceiverTab(self.notebook, self)

        self.notebook.add(self.server_tab, text="Servidor")
        self.notebook.add(self.sender_tab, text="Emisor")
        self.notebook.add(self.receiver_tab, text="Cliente / Receptor")

    def apply_config(self):
        """Aplica la configuración cargada a los widgets de la GUI."""
        self.server_tab.port_entry.delete(0, tk.END)
        self.server_tab.port_entry.insert(0, self.config.get("server_port", "8765"))
        # --- CAMBIO: Rellenar el campo de topic del servidor ---
        self.server_tab.topic_entry.delete(0, tk.END)
        self.server_tab.topic_entry.insert(0, self.config.get("server_topic", "chat"))

        self.sender_tab.uri_entry.delete(0, tk.END)
        self.sender_tab.uri_entry.insert(0, self.config.get("sender_ip", "localhost"))
        self.sender_tab.port_entry.delete(0, tk.END)
        self.sender_tab.port_entry.insert(0, self.config.get("sender_port", "8765"))
        self.sender_tab.topic_entry.delete(0, tk.END)
        self.sender_tab.topic_entry.insert(0, self.config.get("sender_topic", "chat"))

        self.receiver_tab.uri_entry.delete(0, tk.END)
        self.receiver_tab.uri_entry.insert(0, self.config.get("receiver_ip", "localhost"))
        self.receiver_tab.port_entry.delete(0, tk.END)
        self.receiver_tab.port_entry.insert(0, self.config.get("receiver_port", "8765"))
        self.receiver_tab.topic_entry.delete(0, tk.END)
        self.receiver_tab.topic_entry.insert(0, self.config.get("receiver_topic", "chat"))

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
        """Procesa mensajes de las colas de log y los muestra en la GUI."""
        if not self.log_queues["server"].empty():
            self.log_to_widget(self.server_tab.log_widget, self.log_queues["server"].get_nowait())
        if not self.log_queues["client"].empty():
            self.log_to_widget(self.receiver_tab.log_widget, self.log_queues["client"].get_nowait())
        if not self.log_queues["sender"].empty():
            self.log_to_widget(self.sender_tab.log_widget, self.log_queues["sender"].get_nowait())
        self.after(100, self.process_log_queues)

    # --- Lógica de Control ---

    def start_server(self):
        # --- CAMBIO: Leer puerto Y topic desde la GUI del servidor ---
        port = self.server_tab.port_entry.get()
        server_topic = self.server_tab.topic_entry.get()
        
        if not port.isdigit():
            log_message(self.log_queues["server"], "Error: El puerto debe ser un número.")
            return
            
        if not server_topic:
            log_message(self.log_queues["server"], "Error: El topic del servidor no puede estar vacío.")
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
            self.service_advertiser = None
            if self.advertiser_thread:
                self.advertiser_thread.join(timeout=1)

        if self.server_thread and self.server_thread.is_alive():
            log_message(self.log_queues["server"], "Enviando señal de detención al servidor...")
            net.stop_server_event.set()
        self.server_tab.set_state("stopped")

    def select_file(self):
        filepath = filedialog.askopenfilename()
        if filepath:
            self.file_to_send_path.set(filepath)

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

        self.client_thread = threading.Thread(target=run_client, daemon=True)
        self.client_thread.start()
        self.receiver_tab.set_state("running")

    def stop_client(self):
        self.stop_client_event.set()
        self.receiver_tab.set_state("stopped")

    def discover_server(self):
        log_message(self.log_queues["client"], "Buscando servidores en la red local (3 segundos)...")
        self.receiver_tab.discover_button.config(state="disabled")
        threading.Thread(target=self._run_discovery, daemon=True).start()

    def _run_discovery(self):
        
        class ServiceListener:
            def __init__(self):
                self.found_services = {}

            def add_service(self, zeroconf, type_, name):
                info = zeroconf.get_service_info(type_, name)
                if info:
                    self.found_services[name] = info
            
            def update_service(self, zeroconf, type_, name):
                info = zeroconf.get_service_info(type_, name)
                if info:
                    self.found_services[name] = info

            def remove_service(self, zeroconf, type_, name):
                self.found_services.pop(name, None)

        zeroconf_instance = Zeroconf()
        listener = ServiceListener()
        browser = ServiceBrowser(zeroconf_instance, "_ws-file-xfer._tcp.local.", listener)
        
        time.sleep(3)

        found_services_list = list(listener.found_services.values())

        def show_results_dialog(services):
            log_message(self.log_queues["client"], f"Búsqueda finalizada. Se encontraron {len(services)} servidor(es).")
            
            dialog = DiscoveryDialog(self, services)
            
            if dialog.result:
                ip, port = dialog.result
                log_message(self.log_queues["client"], f"Servidor seleccionado en {ip}:{port}")
                self.receiver_tab.uri_entry.delete(0, tk.END)
                self.receiver_tab.uri_entry.insert(0, ip)
                self.receiver_tab.port_entry.delete(0, tk.END)
                self.receiver_tab.port_entry.insert(0, str(port))
            else:
                log_message(self.log_queues["client"], "Ningún servidor seleccionado.")

        try:
            self.after(0, lambda: show_results_dialog(found_services_list))
        finally:
            browser.cancel()
            zeroconf_instance.close()
            self.after(0, lambda: self.receiver_tab.discover_button.config(state="normal"))

    def on_closing(self):
        self.stop_server()
        self.stop_client()
        self.destroy()

if __name__ == "__main__":
    app = FileTransferApp()
    app.mainloop()
