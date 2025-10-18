import socket
import tkinter as tk
from tkinter import ttk

class DiscoveryDialog(tk.Toplevel):
    """
    Un diálogo que muestra una lista de servidores descubiertos
    y permite al usuario seleccionar uno.
    """
    def __init__(self, parent, services):
        super().__init__(parent)
        self.title("Servidores Encontrados")
        self.parent = parent
        self.services = services
        self.result = None
        self.services_map = {}

        # Configurar la ventana
        self.transient(parent)
        # --- CAMBIO: Ajuste de geometría para el diálogo ---
        self.geometry("450x300") 
        self.grab_set()

        # Crear widgets
        self._create_widgets()
        self._populate_list()
        
        # Esperar hasta que esta ventana se cierre
        self.wait_window(self)

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill="both")

        ttk.Label(main_frame, text="Selecciona un servidor de la lista:").pack(fill="x", pady=(0, 5))

        list_frame = ttk.Frame(main_frame)
        list_frame.pack(expand=True, fill="both")

        self.listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE)
        self.listbox.pack(side="left", expand=True, fill="both")
        self.listbox.bind("<Double-1>", self.on_select)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)

        button_frame = ttk.Frame(main_frame, padding="10 0 0 0")
        button_frame.pack(fill="x", side="bottom")

        ttk.Button(button_frame, text="Seleccionar", command=self.on_select).pack(side="right", padx=5)
        ttk.Button(button_frame, text="Cancelar", command=self.destroy).pack(side="right")

    def _populate_list(self):
        """Llena la Listbox con los nombres amigables de los servicios."""
        if not self.services:
            self.listbox.insert(tk.END, "No se encontraron servidores.")
            self.listbox.config(state="disabled")
            return

        for info in self.services:
            # Extraer un nombre amigable del service name
            # Ej: "File Transfer Server on MI-PC:8766._ws-file-xfer._tcp.local."
            friendly_name = info.name.replace(f".{info.type}", "")
            
            # --- CAMBIO: Mostrar también el topic ---
            # Las propiedades son bytes, así que decodificamos el topic
            topic_bytes = info.properties.get(b"topic") # Buscar la propiedad 'topic'
            topic_str = topic_bytes.decode('utf-8') if topic_bytes else "N/A"
            display_text = f"{friendly_name} (Topic: {topic_str})"
            
            self.listbox.insert(tk.END, display_text)
            # Mapear el texto a mostrar al objeto ServiceInfo completo
            self.services_map[display_text] = info

    def on_select(self, event=None):
        """Manejador para la selección de un servidor."""
        selection_indices = self.listbox.curselection()
        if not selection_indices:
            return

        selected_text = self.listbox.get(selection_indices[0])
        info = self.services_map.get(selected_text)

        if info:
            ip_address = socket.inet_ntoa(info.addresses[0])
            port = info.port
            self.result = (ip_address, port)
            self.destroy()
