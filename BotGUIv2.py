import discord
import asyncio
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime, timedelta, timezone

# --- CONFIGURACIÓN ---
# Pega tu token aquí dentro de las comillas. 
# Al ser un .exe personal, es aceptable tenerlo aquí.
DISCORD_TOKEN = "TU_TOKEN_AQUI_PEGALO_DENTRO" 

class DiscordBotThread(threading.Thread):
    def __init__(self, token, gui_callback):
        super().__init__()
        self.token = token
        self.gui_callback = gui_callback # Función para enviar logs a la GUI
        self.loop = asyncio.new_event_loop()
        self.bot = discord.Client(intents=self._get_intents())
        self.ready_event = threading.Event() # Para saber cuando el bot conectó
        
        # Eventos del bot
        self.bot.event(self.on_ready)

    def _get_intents(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        return intents

    def run(self):
        """Este método se ejecuta en un hilo separado (background)"""
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.bot.start(self.token))
        except Exception as e:
            self.gui_callback(f"❌ Error de conexión: {e}")

    async def on_ready(self):
        self.gui_callback(f"✅ Bot conectado como: {self.bot.user}")
        self.ready_event.set() # Avisar a la GUI que ya puede buscar servidores

    def get_guilds(self):
        """Devuelve lista de servidores (ID, Nombre)"""
        return [(g.id, g.name) for g in self.bot.guilds]

    def start_deletion(self, guild_id, target_user_id):
        """Inicia la tarea de eliminación en el loop del bot de forma segura"""
        asyncio.run_coroutine_threadsafe(
            self._delete_task(guild_id, target_user_id), 
            self.loop
        )

    async def _delete_task(self, guild_id, target_user_id):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            self.gui_callback("❌ Error: No se encuentra el servidor seleccionado.")
            return

        self.gui_callback(f"\n🚀 INICIANDO EN: {guild.name}")
        self.gui_callback(f"🎯 OBJETIVO ID: {target_user_id}")
        
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        text_channels = [ch for ch in guild.text_channels]
        
        total_deleted = 0
        
        def check_message(msg):
            return (msg.author.id == target_user_id and 
                    msg.created_at.replace(tzinfo=timezone.utc) > seven_days_ago)

        for i, channel in enumerate(text_channels, 1):
            perms = channel.permissions_for(guild.me)
            if not perms.manage_messages or not perms.read_message_history:
                self.gui_callback(f"⚠️ Saltando #{channel.name} (Sin permisos)")
                continue

            self.gui_callback(f"[{i}/{len(text_channels)}] Escaneando #{channel.name}...")
            
            try:
                # Purge es muy eficiente y maneja el bulk delete automáticamente
                deleted = await channel.purge(
                    limit=None, 
                    check=check_message, 
                    after=seven_days_ago,
                    reason="Limpieza Bot GUI"
                )
                count = len(deleted)
                if count > 0:
                    self.gui_callback(f"   ✅ Eliminados: {count}")
                    total_deleted += count
                
                # Pausa vital para evitar Rate Limits y desconexiones
                await asyncio.sleep(1.0) 
                
            except Exception as e:
                self.gui_callback(f"   ❌ Error en #{channel.name}: {e}")

        self.gui_callback(f"\n🏁 PROCESO TERMINADO. Total eliminados: {total_deleted}")
        self.gui_callback("="*40)


class BotApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Discord Cleaner Bot - GUI")
        self.geometry("600x550")
        self.resizable(False, False)
        
        # Configuración de estilo
        style = ttk.Style()
        style.theme_use('clam') 

        # Variables
        self.bot_thread = None
        self.guild_map = {} # Diccionario para mapear "Nombre Servidor" -> ID

        self._create_widgets()
        self._start_bot_thread()

    def _create_widgets(self):
        # Frame Principal
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Título y Estado
        lbl_title = ttk.Label(main_frame, text="Discord Message Deleter", font=("Helvetica", 16, "bold"))
        lbl_title.pack(pady=(0, 10))

        self.lbl_status = ttk.Label(main_frame, text="🔌 Conectando bot...", foreground="orange")
        self.lbl_status.pack(pady=5)

        # 2. Selector de Servidor
        lbl_server = ttk.Label(main_frame, text="Seleccionar Servidor:")
        lbl_server.pack(anchor="w", pady=(10, 2))
        
        self.combo_guilds = ttk.Combobox(main_frame, state="readonly")
        self.combo_guilds.pack(fill=tk.X)
        self.combo_guilds.set("Esperando conexión...")

        # 3. Input de Usuario
        lbl_user = ttk.Label(main_frame, text="ID del Usuario (Click derecho en usuario -> Copiar ID):")
        lbl_user.pack(anchor="w", pady=(15, 2))
        
        self.entry_user_id = ttk.Entry(main_frame)
        self.entry_user_id.pack(fill=tk.X)

        # 4. Botón de Acción
        self.btn_run = ttk.Button(main_frame, text="🗑️ ELIMINAR MENSAJES (Últimos 7 días)", command=self.confirm_and_run)
        self.btn_run.pack(fill=tk.X, pady=20)
        self.btn_run.config(state="disabled") # Desactivado hasta que cargue el bot

        # 5. Consola de Logs
        lbl_log = ttk.Label(main_frame, text="Registro de operaciones:")
        lbl_log.pack(anchor="w")
        
        self.log_area = scrolledtext.ScrolledText(main_frame, height=12, state='disabled', font=("Consolas", 9))
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def log(self, message):
        """Función segura para escribir en la GUI desde otro hilo"""
        # self.after(0, func) pone la tarea en la cola del hilo principal de la GUI
        self.after(0, self._log_internal, message)

    def _log_internal(self, message):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END) # Auto-scroll
        self.log_area.config(state='disabled')

    def _start_bot_thread(self):
        if "TU_TOKEN" in DISCORD_TOKEN:
            messagebox.showerror("Error", "Edita el archivo y coloca tu TOKEN real en la variable DISCORD_TOKEN")
            return

        self.bot_thread = DiscordBotThread(DISCORD_TOKEN, self.log)
        self.bot_thread.daemon = True # El hilo muere si cierras la ventana
        self.bot_thread.start()
        
        # Revisar periódicamente si el bot ya conectó
        self.after(1000, self.check_connection)

    def check_connection(self):
        if self.bot_thread.ready_event.is_set():
            self.lbl_status.config(text="✅ Conectado y Listo", foreground="green")
            self.load_guilds()
        else:
            self.after(1000, self.check_connection)

    def load_guilds(self):
        guilds = self.bot_thread.get_guilds()
        if not guilds:
            self.log("⚠️ El bot no está en ningún servidor.")
            return
            
        guild_names = []
        self.guild_map = {}
        
        for gid, gname in guilds:
            display_name = f"{gname} (ID: {gid})"
            guild_names.append(display_name)
            self.guild_map[display_name] = gid
            
        self.combo_guilds['values'] = guild_names
        if guild_names:
            self.combo_guilds.current(0)
            self.btn_run.config(state="normal")
            self.log("📋 Lista de servidores actualizada.")

    def confirm_and_run(self):
        selected_text = self.combo_guilds.get()
        user_id_str = self.entry_user_id.get().strip()
        
        if not selected_text or selected_text == "Esperando conexión...":
            messagebox.showerror("Error", "Selecciona un servidor válido.")
            return
            
        if not user_id_str.isdigit():
            messagebox.showerror("Error", "El ID de usuario debe ser numérico.")
            return
            
        guild_id = self.guild_map[selected_text]
        user_id = int(user_id_str)
        
        confirm = messagebox.askyesno(
            "Confirmación de Seguridad", 
            f"⚠️ ESTA ACCIÓN ES IRREVERSIBLE\n\n¿Estás seguro de eliminar los mensajes del usuario:\nID: {user_id}\n\nEn los últimos 7 días?"
        )
        
        if confirm:
            self.btn_run.config(state="disabled")
            self.log("\n" + "-" * 30)
            self.bot_thread.start_deletion(guild_id, user_id)
            
            # Reactivar el botón después de 5 segundos (solo para evitar doble clic accidental)
            self.after(5000, lambda: self.btn_run.config(state="normal"))

if __name__ == "__main__":
    app = BotApp()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        pass
