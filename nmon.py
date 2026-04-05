""" 
Netmon - Network Monitor version 1.0

    Copyright (C) 2023-2024 Free and Open Source Software "No Copyrights"

    This program is free software: you can redistribute it or modify it under the terms of the project that means you can do whatever you want with this program.

    Program's purpose and goal:
       This software allows you to monitor your device's network adapters traffic in real time
       This software allow you to see how much of network resources your device is consuming

       By Sam Jamsh also known as cyb3rguy
"""



import psutil
import socket
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from datetime import datetime, timedelta
import os



LOG_FOLDER = "logs"
TABLE_UPDATE_INTERVAL = 1000  # Atualiza tabela a cada 1 segundo
HISTORY_CHECK_INTERVAL = 60*1000  # Verifica log a cada 1 minuto
if not os.path.exists(LOG_FOLDER):
    os.makedirs(LOG_FOLDER)

daily_totals = {}
history_widget = None
last_log_hour = None
last_log_day = None
last_history_pos = 0  # ultima linha lida do log



def get_ip(interface_name):
    """Retorna o IP da interface, se existir."""
    addrs = psutil.net_if_addrs()
    if interface_name not in addrs:
        return "N/A"
    for addr in addrs[interface_name]:
        if addr.family == socket.AF_INET:
            return addr.address
    return "N/A"

def format_bytes(bytes_count):
    """Converte bytes para KB."""
    return bytes_count / 1024

def format_mb(bytes_count):
    """Converte bytes para MB."""
    return bytes_count / (1024*1024)

def update_history_from_log():
    """Atualiza o historico na GUI lendo novas linhas do arquivo de log."""
    global last_history_pos, history_widget
    filename = f"log_{datetime.now().strftime('%Y-%m-%d')}.log"
    filepath = os.path.join(LOG_FOLDER, filename)
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            lines = f.readlines()
            new_lines = lines[last_history_pos:]
            if new_lines and history_widget:
                history_widget.configure(state='normal')
                for line in new_lines:
                    if line.startswith("# Daily Summary") or "Total Down" in line:
                        history_widget.insert(tk.END, line, "daily")  # destaque diario
                    else:
                        history_widget.insert(tk.END, line)
                history_widget.see(tk.END)
                history_widget.configure(state='disabled')
                last_history_pos = len(lines)

def write_hourly_log():
    """Escreve logs por hora no arquivo."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    filename = f"log_{datetime.now().strftime('%Y-%m-%d')}.log"
    filepath = os.path.join(LOG_FOLDER, filename)
    if not os.path.exists(filepath):
        with open(filepath, "w") as f:
            f.write(f"# Network Monitor Daily Log - {datetime.now().strftime('%Y-%m-%d')}\n")
            f.write("# Format: [Timestamp] IF: <interface> | IP: <local_ip> | Down: X KB/s | Up: Y KB/s | Total Down: A MB | Total Up: B MB\n")
            f.write("-"*100 + "\n")
    with open(filepath, "a") as f:
        for iface, stats in monitor.state.items():
            down_speed = format_bytes(stats["down_speed"])
            up_speed = format_bytes(stats["up_speed"])
            total_down = format_mb(stats["total_bytes_recv"])
            total_up = format_mb(stats["total_bytes_sent"])
            line = f"[{timestamp}] IF: {iface} | IP: {stats['ip']} | Down: {down_speed:.2f} KB/s | Up: {up_speed:.2f} KB/s | Total Down: {total_down:.2f} MB | Total Up: {total_up:.2f} MB"
            f.write(line + "\n")

def write_daily_summary():
    """Escreve o resumo diário ao final do arquivo de log."""
    filename = f"log_{datetime.now().strftime('%Y-%m-%d')}.log"
    filepath = os.path.join(LOG_FOLDER, filename)
    with open(filepath, "a") as f:
        f.write("-"*100 + "\n")
        f.write(f"# Daily Summary: {datetime.now().strftime('%d/%B/%Y %A %H:%M:%S')}\n")
        for iface, stats in monitor.state.items():
            total_down = format_mb(stats["total_bytes_recv"])
            total_up = format_mb(stats["total_bytes_sent"])
            line = f"IF: {iface} | Total Down: {total_down:.2f} MB | Total Up: {total_up:.2f} MB"
            f.write(line + "\n")


class NetworkMonitor:
    def __init__(self):
        self.state = {}
        self.init_interfaces()

    def init_interfaces(self):
        """Inicializa cada interface com estatísticas iniciais."""
        net_io = psutil.net_io_counters(pernic=True)
        for iface, counters in net_io.items():
            self.state[iface] = {
                "prev_bytes_sent": counters.bytes_sent,
                "prev_bytes_recv": counters.bytes_recv,
                "total_bytes_sent": 0,
                "total_bytes_recv": 0,
                "down_speed": 0.0,
                "up_speed": 0.0,
                "ip": get_ip(iface)
            }

    def update_stats(self):
        """Atualiza estatísticas de cada interface."""
        net_io = psutil.net_io_counters(pernic=True)
        for iface, stats in self.state.items():
            counters = net_io.get(iface)
            if not counters:
                continue
            delta_sent = counters.bytes_sent - stats["prev_bytes_sent"]
            delta_recv = counters.bytes_recv - stats["prev_bytes_recv"]
            stats["down_speed"] = delta_recv
            stats["up_speed"] = delta_sent
            stats["total_bytes_recv"] += delta_recv
            stats["total_bytes_sent"] += delta_sent
            stats["prev_bytes_sent"] = counters.bytes_sent
            stats["prev_bytes_recv"] = counters.bytes_recv


class NetworkMonitorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NetMon (Live)")
        self.root.configure(bg="#1b1b1b")
        self.running = False
        self.stopped = False
        self.status = tk.StringVar()
        self.status.set("Ready")

        # Tenta adicionar icone da janela
        try:
            root.iconbitmap(r"C:\Users\cyber\Pictures\PngIco\modem_wifi_router_network_internet_icon_190949.ico")
        except:
            pass

        # Tabela de interfaces
        columns = ("Interface","IP","Down KB/s","Up KB/s","Total Down MB","Total Up MB")
        self.tree = ttk.Treeview(root, columns=columns, show="headings", height=12)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=140, anchor="center")
        self.tree.pack(padx=10, pady=10, fill="both", expand=True)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", font=("Helvetica",11))
        style.configure("Treeview.Heading", background="#1f1f1f", foreground="white", font=("Helvetica",12,"bold"))
        style.map("Treeview", background=[('selected', '#555555')])

        # Cores para linhas ativas
        self.tree.tag_configure("active", background="#4caf50", foreground="white", font=("Helvetica",11,"bold"))

        # Totais
        total_frame = tk.Frame(root,bg="#1b1b1b")
        total_frame.pack(pady=10)
        self.total_down_var = tk.StringVar()
        self.total_up_var = tk.StringVar()
        tk.Label(total_frame,text="Total Down (MB):",bg="#1b1b1b",fg="white",font=("Helvetica",12,"bold")).pack(side="left", padx=5)
        tk.Label(total_frame,textvariable=self.total_down_var,bg="#1b1b1b",fg="#4caf50",font=("Helvetica",12,"bold")).pack(side="left", padx=5)
        tk.Label(total_frame,text="Total Up (MB):",bg="#1b1b1b",fg="white",font=("Helvetica",12,"bold")).pack(side="left", padx=20)
        tk.Label(total_frame,textvariable=self.total_up_var,bg="#1b1b1b",fg="#f44336",font=("Helvetica",12,"bold")).pack(side="left", padx=5)

        status_frame = tk.Frame(root,bg="#1b1b1b")
        status_frame.pack(pady=12)

        tk.Label(status_frame,text="Status:",bg="#1b1b1b",fg="white",font=("Helvetica",12,"bold")).pack(side="left", padx=16)
        self.statusLabel = tk.Label(status_frame,textvariable=self.status,bg="#1b1b1b",fg="#1e3d29",font=("Helvetica",12,"bold"))
        self.statusLabel.pack(side="left", padx=4)


        # Historico
        global history_widget
        history_widget = ScrolledText(root,height=15,bg="#1b1b1b",fg="white",font=("Consolas",10))
        history_widget.pack(fill="both", expand=True, padx=10, pady=10)
        history_widget.configure(state='disabled')
        history_widget.tag_configure("daily", foreground="#ffeb3b", font=("Consolas",10,"bold"))

        # Botoes
        button_frame = tk.Frame(root,bg="#1b1b1b")
        button_frame.pack(pady=10)
        tk.Button(button_frame,text="Start",bg="#7FE384",fg="#313031",width=10,font=("Helvetica",12,"bold"),command=self.start_monitor).pack(side="left", padx=10)
        tk.Button(button_frame,text="Stop",bg="#f08078",fg="#302F30",width=10,font=("Helvetica",12,"bold"),command=self.stop_monitor).pack(side="left", padx=10)
        tk.Button(button_frame,text="About", bg="#c6d7e2", fg="#434043", width=10, font=("Helvetica",12,"bold"), command=self.show_about).pack(side="left", padx=10)

    def show_about(self):
        """Popup About com logo, informações do projeto e criador."""
        about_win = tk.Toplevel(self.root)
        about_win.title("About NetMon (Live)")
        about_win.configure(bg="#1b1b1b")
        about_win.geometry("400x350")

        # Logo
        try:
            about_win.iconbitmap(r"C:\Users\cyber\Pictures\PngIco\modem_wifi_router_network_internet_icon_190949.ico")
            logo_img = tk.PhotoImage(file=r"C:\Users\cyber\Pictures\PngIco\Antenna_double_internet_online_router_web_wifi_icon-icons.com_53555.png")
            tk.Label(about_win, image=logo_img, bg="#1b1b1b").pack(pady=10)
            about_win.logo_img = logo_img  # mantem referência
        except:
            tk.Label(about_win, text="[Logo is unavailable]", bg="#1b1b1b", fg="white").pack(pady=10)

        # Informacoes do projeto
        tk.Label(about_win, text="NetMon (Live)", font=("Helvetica",16,"bold"),
                 bg="#1b1b1b", fg="#4caf50").pack(pady=5)
        tk.Label(about_win, text="Live network monitoring for windows\nMonitor your network traffic usage",
                 font=("Helvetica",12), bg="#1b1b1b", fg="white", justify="center").pack(pady=5)
        tk.Label(about_win, text="Developer: Sam Jamsh\nVersion: 1.0",
                 font=("Helvetica",12), bg="#1b1b1b", fg="white", justify="center").pack(pady=5)
        tk.Button(about_win, text="Close", bg="#954842", fg="white",
                  width=10, command=about_win.destroy).pack(pady=15)

    def start_monitor(self):
        self.status.set("Running")
        self.statusLabel.configure(fg="#4bc549")
        self.stopped = False
        self.running = True
        self.update_table_loop()
        self.update_log_loop()

    def stop_monitor(self):
        if self.stopped == False and self.running == True:
            self.status.set("Stopped")
            self.statusLabel.configure(fg="#ff4c4c")
            self.stopped = True
            self.running = False
            write_daily_summary()
            update_history_from_log()

    def update_table_loop(self):
        if not self.running:
            return
        monitor.update_stats()
        data = []
        for iface, stats in monitor.state.items():
            down_kb = format_bytes(stats["down_speed"])
            up_kb = format_bytes(stats["up_speed"])
            total_down = format_mb(stats["total_bytes_recv"])
            total_up = format_mb(stats["total_bytes_sent"])
            data.append((iface, stats["ip"], f"{down_kb:.2f}", f"{up_kb:.2f}", f"{total_down:.2f}", f"{total_up:.2f}", stats["down_speed"]>0 or stats["up_speed"]>0))
        # Limpa tabela
        for row in self.tree.get_children():
            self.tree.delete(row)
        for row in data:
            if row[6]:  # interface ativa
                self.tree.insert("", "end", values=row[:6], tags=("active",))
            else:
                self.tree.insert("", "end", values=row[:6])
        # Totais combinados
        self.total_down_var.set(f"{sum([float(r[4]) for r in data]):.2f}")
        self.total_up_var.set(f"{sum([float(r[5]) for r in data]):.2f}")
        self.root.after(TABLE_UPDATE_INTERVAL, self.update_table_loop)

    def update_log_loop(self):
        global last_log_hour, last_log_day
        if not self.running:
            return
        now = datetime.now()
        if last_log_hour is None:
            last_log_hour = now.replace(minute=0, second=0, microsecond=0)
        if last_log_day is None:
            last_log_day = now.date()

        if now >= last_log_hour + timedelta(hours=1):
            write_hourly_log()
            update_history_from_log()
            last_log_hour = now.replace(minute=0, second=0, microsecond=0)

        if now.date() != last_log_day:
            write_daily_summary()
            update_history_from_log()
            last_log_day = now.date()

        self.root.after(HISTORY_CHECK_INTERVAL, self.update_log_loop)


if __name__=="__main__":
    monitor = NetworkMonitor()
    root = tk.Tk()
    root.geometry("950x700")
    app = NetworkMonitorGUI(root)
    root.mainloop()
