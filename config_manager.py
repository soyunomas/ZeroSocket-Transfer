import json
import os
from tkinter import messagebox
from pathlib import Path  # <-- Importamos la clase Path

CONFIG_FILE = "app_config.json"

def get_default_config():
    """Retorna un diccionario con la configuración por defecto."""
    
    # --- LÓGICA MEJORADA ---
    # Busca la carpeta de descargas estándar del usuario de forma multiplataforma.
    # Path.home() obtiene el directorio de inicio (ej: /home/usuario o C:\Users\Usuario)
    # Luego le añadimos la carpeta "Downloads". Lo convertimos a string para guardarlo en JSON.
    try:
        default_downloads = str(Path.home() / "Downloads")
    except Exception:
        # Si por alguna razón no se puede encontrar, volvemos al método anterior como fallback.
        default_downloads = os.path.join(os.getcwd(), "downloads")

    return {
        "server_port": "8765",
        "server_topic": "filetransfer",
        "sender_ip": "localhost",
        "sender_port": "8765",
        "sender_topic": "filetransfer",
        "receiver_ip": "localhost",
        "receiver_port": "8765",
        "receiver_topic": "filetransfer",
        "download_folder": default_downloads  # <-- Usamos la nueva ruta por defecto
    }

def load_config():
    """Carga la configuración desde el archivo JSON o retorna los valores por defecto."""
    defaults = get_default_config()
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        # Asegurarse de que todas las claves por defecto existan en el archivo cargado
        for key, value in defaults.items():
            config.setdefault(key, value)
        return config
    except (FileNotFoundError, json.JSONDecodeError):
        return defaults

def save_config(config):
    """Guarda el diccionario de configuración en el archivo JSON."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        messagebox.showerror("Error de Configuración", f"No se pudo guardar la configuración:\n{e}")
