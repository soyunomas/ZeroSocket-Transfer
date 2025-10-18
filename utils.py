import socket

def log_message(log_queue, message):
    """Función segura para hilos para encolar mensajes de log."""
    log_queue.put(message)

def format_file_size(size_bytes):
    """Convierte un tamaño en bytes a un formato legible (KB, MB, GB)."""
    if size_bytes == 0:
        return "0 B"
    power = 1024
    n = 0
    power_labels = {0: '', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size_bytes >= power and n < len(power_labels):
        size_bytes /= power
        n += 1
    return f"{size_bytes:.2f} {power_labels[n]}"

def get_primary_local_ip():
    """Obtiene y retorna la IP local primaria no-loopback."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except socket.gaierror:
            return "127.0.0.1"

def get_local_ips():
    """Obtiene y retorna las IPs locales de forma fiable como una cadena."""
    local_ips = ["127.0.0.1"]
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.1)
            try:
                s.connect(('10.254.254.254', 1))
                ip = s.getsockname()[0]
                if ip not in local_ips:
                    local_ips.append(ip)
            except Exception:
                try:
                    hostname = socket.gethostname()
                    ips = socket.gethostbyname_ex(hostname)[2]
                    non_local_ips = [ip for ip in ips if not ip.startswith('127.')]
                    for ip in non_local_ips:
                        if ip not in local_ips:
                            local_ips.append(ip)
                except socket.gaierror:
                    pass
        
        return ", ".join(local_ips)
    except Exception:
        return "Error al obtener IPs. Comprueba la conexión de red."
