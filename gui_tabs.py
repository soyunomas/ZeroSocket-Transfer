import tkinter as tk
from tkinter import ttk, scrolledtext
from utils import get_local_ips

class ServerTab(ttk.Frame):
    def __init__(self, parent_notebook, app_controller):
        super().__init__(parent_notebook)
        self.app = app_controller

        controls_frame = ttk.LabelFrame(self, text="Configuración del Servidor")
        controls_frame.pack(side="top", fill="x", padx=10, pady=10)

        ip_frame = ttk.Frame(controls_frame)
        ip_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(ip_frame, text="IPs del equipo:").pack(side="left")
        
        self.ip_text_widget = tk.Text(ip_frame, height=2, width=50, state="disabled", relief="flat")
        
        self.ip_text_widget.pack(side="left", fill="x", expand=True, padx=5)
        self.update_ip_display()

        config_grid = ttk.Frame(controls_frame)
        config_grid.pack(fill="x", padx=5, pady=5)
        config_grid.columnconfigure(1, weight=1)

        ttk.Label(config_grid, text="Puerto:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.port_entry = ttk.Entry(config_grid, width=10)
        self.port_entry.grid(row=0, column=1, sticky="w")
        
        ttk.Label(config_grid, text="Topic:").grid(row=1, column=0, sticky="w", padx=(0, 5), pady=(5,0))
        self.topic_entry = ttk.Entry(config_grid)
        self.topic_entry.grid(row=1, column=1, sticky="ew", pady=(5,0))
        
        button_frame = ttk.Frame(controls_frame)
        button_frame.pack(fill="x", padx=5, pady=10)
        self.start_button = ttk.Button(button_frame, text="Iniciar Servidor", command=self.app.start_server)
        self.start_button.pack(side="left", padx=0)
        self.stop_button = ttk.Button(button_frame, text="Detener Servidor", command=self.app.stop_server, state="disabled")
        self.stop_button.pack(side="left", padx=5)

        log_frame = ttk.LabelFrame(self, text="Log del Servidor")
        log_frame.pack(expand=True, fill="both", padx=10, pady=(0, 10))
        self.log_widget = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state="disabled")
        self.log_widget.pack(expand=True, fill="both")

    def update_ip_display(self):
        self.ip_text_widget.config(state="normal")
        self.ip_text_widget.delete("1.0", tk.END)
        ip_string = get_local_ips()
        self.ip_text_widget.insert("1.0", ip_string)
        self.ip_text_widget.config(state="disabled")

    def set_state(self, state):
        is_running = (state == "running")
        self.start_button.config(state="disabled" if is_running else "normal")
        self.stop_button.config(state="normal" if is_running else "disabled")
        self.port_entry.config(state="disabled" if is_running else "normal")
        self.topic_entry.config(state="disabled" if is_running else "normal")


class SenderTab(ttk.Frame):
    def __init__(self, parent_notebook, app_controller, file_name_var, file_details_var):
        super().__init__(parent_notebook)
        self.app = app_controller

        controls_frame = ttk.LabelFrame(self, text="Parámetros de Envío")
        controls_frame.pack(side="top", fill="x", padx=10, pady=10)

        uri_frame = ttk.Frame(controls_frame)
        uri_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(uri_frame, text="IP del Servidor:").pack(side="left")
        self.uri_entry = ttk.Entry(uri_frame)
        self.uri_entry.pack(side="left", padx=5, fill="x", expand=True)
        ttk.Label(uri_frame, text="Puerto:").pack(side="left", padx=(10, 0))
        self.port_entry = ttk.Entry(uri_frame, width=10)
        self.port_entry.pack(side="left", padx=5)

        topic_frame = ttk.Frame(controls_frame)
        topic_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(topic_frame, text="Topic:").pack(side="left")
        self.topic_entry = ttk.Entry(topic_frame)
        self.topic_entry.pack(side="left", padx=5, fill="x", expand=True)

        # --- CAMBIO: Nuevo layout para mostrar detalles del archivo ---
        file_frame = ttk.LabelFrame(controls_frame, text="Archivo para Enviar", padding=10)
        file_frame.pack(fill="x", padx=5, pady=5, expand=True)

        # Contenedor para el botón y los detalles
        file_content_frame = ttk.Frame(file_frame)
        file_content_frame.pack(fill="x", expand=True)
        
        select_button = ttk.Button(file_content_frame, text="Seleccionar Archivo...", command=self.app.select_file)
        select_button.pack(side="left", padx=(0, 15), anchor="n")

        # Frame para los detalles (nombre y tamaño)
        details_frame = ttk.Frame(file_content_frame)
        details_frame.pack(side="left", fill="x", expand=True)
        
        # Usamos tk.Label porque ttk.Label a veces trunca el texto
        file_name_label = tk.Label(details_frame, textvariable=file_name_var, anchor="w", justify="left", font="-weight bold")
        file_name_label.pack(fill="x")
        
        file_details_label = tk.Label(details_frame, textvariable=file_details_var, anchor="w", justify="left")
        file_details_label.pack(fill="x")

        # Botón de envío
        action_frame = ttk.Frame(controls_frame)
        action_frame.pack(fill="x", padx=5, pady=10)
        self.send_button = ttk.Button(action_frame, text="Enviar Archivo", command=self.app.start_sender)
        self.send_button.pack()

        # Log
        log_frame = ttk.LabelFrame(self, text="Log del Emisor")
        log_frame.pack(expand=True, fill="both", padx=10, pady=(0, 10))
        self.log_widget = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state="disabled")
        self.log_widget.pack(expand=True, fill="both")


class ReceiverTab(ttk.Frame):
    def __init__(self, parent_notebook, app_controller):
        super().__init__(parent_notebook)
        self.app = app_controller

        controls_frame = ttk.LabelFrame(self, text="Parámetros de Conexión")
        controls_frame.pack(side="top", fill="x", padx=10, pady=10)

        uri_frame = ttk.Frame(controls_frame)
        uri_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(uri_frame, text="IP del Servidor:").pack(side="left")
        self.uri_entry = ttk.Entry(uri_frame)
        self.uri_entry.pack(side="left", padx=5, fill="x", expand=True)
        self.discover_button = ttk.Button(uri_frame, text="Buscar", command=self.app.discover_server)
        self.discover_button.pack(side="left", padx=(0, 5))
        ttk.Label(uri_frame, text="Puerto:").pack(side="left", padx=(10, 0))
        self.port_entry = ttk.Entry(uri_frame, width=10)
        self.port_entry.pack(side="left", padx=5)

        topic_frame = ttk.Frame(controls_frame)
        topic_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(topic_frame, text="Topic:").pack(side="left")
        self.topic_entry = ttk.Entry(topic_frame)
        self.topic_entry.pack(side="left", padx=5, fill="x", expand=True)
        self.connect_button = ttk.Button(topic_frame, text="Conectar", command=self.app.start_client)
        self.connect_button.pack(side="left", padx=5)
        self.disconnect_button = ttk.Button(topic_frame, text="Desconectar", command=self.app.stop_client, state="disabled")
        self.disconnect_button.pack(side="left", padx=5)
        
        log_frame = ttk.LabelFrame(self, text="Log del Cliente")
        log_frame.pack(expand=True, fill="both", padx=10, pady=(0, 10))
        self.log_widget = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state="disabled")
        self.log_widget.pack(expand=True, fill="both")
        
    def set_state(self, state):
        is_running = (state == "running")
        self.connect_button.config(state="disabled" if is_running else "normal")
        self.disconnect_button.config(state="normal" if is_running else "disabled")
        self.discover_button.config(state="disabled" if is_running else "normal")
        for entry in [self.uri_entry, self.port_entry, self.topic_entry]:
            entry.config(state="disabled" if is_running else "normal")
