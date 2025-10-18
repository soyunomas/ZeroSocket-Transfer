import socket

def log_message(log_queue, message):
    """Función segura para hilos para encolar mensajes de log."""
    log_queue.put(message)

def get_primary_local_ip():
    """Obtiene y retorna la IP local primaria no-loopback."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # Conectar a una IP externa (no necesita ser alcanzable)
            # para que el SO elija la interfaz de red apropiada.
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            return ip
    except Exception:
        # Si falla, intenta con el hostname como fallback
        try:
            return socket.gethostbyname(socket.gethostname())
        except socket.gaierror:
            # Si todo falla, devuelve la loopback
            return "127.0.0.1"

def get_local_ips():
    """Obtiene y retorna las IPs locales de forma fiable como una cadena."""
    local_ips = ["127.0.0.1"]
    try:
        # Método fiable para encontrar la IP de la LAN
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.1)
            try:
                # No es necesario que la IP sea alcanzable, solo para que el SO elija una interfaz
                s.connect(('10.254.254.254', 1))
                ip = s.getsockname()[0]
                if ip not in local_ips:
                    local_ips.append(ip)
            except Exception:
                # Si falla, puede que no haya red o que el método no funcione en este SO
                # Intentamos un método de respaldo
                try:
                    hostname = socket.gethostname()
                    ips = socket.gethostbyname_ex(hostname)[2]
                    non_local_ips = [ip for ip in ips if not ip.startswith('127.')]
                    for ip in non_local_ips:
                        if ip not in local_ips:
                            local_ips.append(ip)
                except socket.gaierror:
                    pass  # Falla silenciosamente si el método de respaldo tampoco funciona
        
        return ", ".join(local_ips)
    except Exception:
        return "Error al obtener IPs. Comprueba la conexión de red."
