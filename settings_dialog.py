import os
import tkinter as tk
from tkinter import ttk, filedialog

class SettingsDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Configuración")
        self.parent = parent
        self.config = parent.config.copy()  # Trabajar con una copia

        self.transient(parent)
        self.grab_set()

        self._create_variables()
        self._create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _create_variables(self):
        self.server_port = tk.StringVar(value=self.config.get("server_port", "8765"))
        self.server_topic = tk.StringVar(value=self.config.get("server_topic", "chat")) # <-- AÑADIDO
        self.sender_ip = tk.StringVar(value=self.config.get("sender_ip", "localhost"))
        self.sender_port = tk.StringVar(value=self.config.get("sender_port", "8765"))
        self.sender_topic = tk.StringVar(value=self.config.get("sender_topic", "chat"))
        self.receiver_ip = tk.StringVar(value=self.config.get("receiver_ip", "localhost"))
        self.receiver_port = tk.StringVar(value=self.config.get("receiver_port", "8765"))
        self.receiver_topic = tk.StringVar(value=self.config.get("receiver_topic", "chat"))
        self.download_folder = tk.StringVar(value=self.config.get("download_folder", ""))

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill="both")

        # --- CAMBIO: Añadido campo de Topic al Servidor ---
        self._create_section(main_frame, "Servidor por Defecto", [
            ("Puerto:", self.server_port), 
            ("Topic:", self.server_topic)
        ])
        self._create_section(main_frame, "Emisor por Defecto", [
            ("IP Servidor:", self.sender_ip), ("Puerto:", self.sender_port), ("Topic:", self.sender_topic)
        ])
        self._create_section(main_frame, "Receptor por Defecto", [
            ("IP Servidor:", self.receiver_ip), ("Puerto:", self.receiver_port), ("Topic:", self.receiver_topic)
        ])

        # Carpeta de Descarga
        download_frame = ttk.LabelFrame(main_frame, text="Carpeta de Descargas", padding="10")
        download_frame.pack(fill="x", pady=5)
        ttk.Entry(download_frame, textvariable=self.download_folder, state="readonly").pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(download_frame, text="Examinar...", command=self.select_download_folder).pack(side="left")

        # Botones de acción
        button_frame = ttk.Frame(main_frame, padding="10 0 0 0")
        button_frame.pack(fill="x", side="bottom")
        ttk.Button(button_frame, text="Guardar", command=self.save_and_close).pack(side="right", padx=5)
        ttk.Button(button_frame, text="Cancelar", command=self.destroy).pack(side="right")

    def _create_section(self, parent, title, fields):
        frame = ttk.LabelFrame(parent, text=title, padding="10")
        frame.pack(fill="x", pady=5)
        for i, (label_text, var) in enumerate(fields):
            ttk.Label(frame, text=label_text).grid(row=i, column=0, sticky="w", padx=5, pady=2)
            ttk.Entry(frame, textvariable=var).grid(row=i, column=1, sticky="ew", padx=5)
        frame.columnconfigure(1, weight=1)

    def select_download_folder(self):
        folder = filedialog.askdirectory(initialdir=self.download_folder.get() or os.getcwd())
        if folder:
            self.download_folder.set(folder)
            
    def save_and_close(self):
        self.config["server_port"] = self.server_port.get()
        self.config["server_topic"] = self.server_topic.get() # <-- AÑADIDO
        self.config["sender_ip"] = self.sender_ip.get()
        self.config["sender_port"] = self.sender_port.get()
        self.config["sender_topic"] = self.sender_topic.get()
        self.config["receiver_ip"] = self.receiver_ip.get()
        self.config["receiver_port"] = self.receiver_port.get()
        self.config["receiver_topic"] = self.receiver_topic.get()
        self.config["download_folder"] = self.download_folder.get()

        self.parent.save_and_apply_config(self.config)
        self.destroy()
