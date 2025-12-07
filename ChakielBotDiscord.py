"""
Discord Message Deleter Bot (Corregido)
============================
Bot que elimina todos los mensajes de un usuario específico en los últimos 7 días.
SOLUCIÓN APLICADA: Implementación de inputs no bloqueantes para evitar errores de Heartbeat.
"""

import discord
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
import os
from dotenv import load_dotenv

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot_deletion.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class MessageDeleterBot(discord.Client):
    """Bot especializado en eliminación masiva de mensajes por usuario"""
    
    def __init__(self):
        # Intents necesarios
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True  # Para buscar por nombre de usuario
        
        super().__init__(intents=intents)
        
        self.total_deleted = 0
        self.channels_processed = 0
        self.errors_count = 0
    
    async def async_input(self, prompt: str) -> str:
        """
        Función auxiliar para manejar inputs de forma asíncrona.
        Esto evita que el bot se desconecte o lance errores de Heartbeat mientras espera.
        """
        return await asyncio.to_thread(input, prompt)

    async def on_ready(self):
        """Ejecuta el proceso de eliminación cuando el bot está listo"""
        logger.info(f'✅ Bot conectado como {self.user} (ID: {self.user.id})')
        logger.info(f'📊 Conectado a {len(self.guilds)} servidor(es)')
        
        try:
            await self.start_deletion_process()
        except Exception as e:
            logger.error(f'❌ Error crítico: {e}', exc_info=True)
        finally:
            await self.close()
    
    async def start_deletion_process(self):
        """Proceso principal de eliminación"""
        print("\n" + "="*60)
        print("🤖 BOT DE ELIMINACIÓN MASIVA DE MENSAJES")
        print("="*60 + "\n")
        
        # Paso 1: Seleccionar servidor
        guild = await self.select_guild()
        if not guild:
            return
        
        # Paso 2: Obtener usuario objetivo
        target_user_id = await self.get_target_user(guild)
        if not target_user_id:
            return
        
        # Paso 3: Confirmación de seguridad
        if not await self.confirm_deletion(target_user_id, guild):
            print("❌ Operación cancelada por el usuario.")
            return
        
        # Paso 4: Ejecutar eliminación
        await self.delete_messages_from_user(guild, target_user_id)
        
        # Paso 5: Mostrar resumen
        self.show_summary()
    
    async def select_guild(self) -> Optional[discord.Guild]:
        """Permite seleccionar el servidor donde eliminar mensajes"""
        if len(self.guilds) == 0:
            logger.error("❌ El bot no está en ningún servidor.")
            return None
        
        if len(self.guilds) == 1:
            guild = self.guilds[0]
            print(f"📍 Servidor seleccionado: {guild.name}")
            return guild
        
        print("\n📋 Servidores disponibles:")
        for idx, g in enumerate(self.guilds, 1):
            print(f"  {idx}. {g.name} (ID: {g.id})")
        
        while True:
            try:
                # CORRECCIÓN: Usar async_input
                choice = await self.async_input("\n🔢 Selecciona el número del servidor: ")
                choice = choice.strip()
                idx = int(choice) - 1
                if 0 <= idx < len(self.guilds):
                    return self.guilds[idx]
                print("⚠️  Número inválido. Intenta de nuevo.")
            except (ValueError, KeyboardInterrupt):
                print("\n❌ Entrada inválida.")
                return None
    
    async def get_target_user(self, guild: discord.Guild) -> Optional[int]:
        """Obtiene el ID del usuario objetivo mediante input"""
        print("\n" + "-"*60)
        print("🎯 IDENTIFICACIÓN DEL USUARIO OBJETIVO")
        print("-"*60)
        print("\nOpciones de búsqueda:")
        print("  1. Por ID de usuario (más preciso)")
        print("  2. Por nombre de usuario (username)")
        print("  3. Por nombre en el servidor (nickname)")
        
        while True:
            # CORRECCIÓN: Usar async_input
            choice = await self.async_input("\n🔍 Selecciona método de búsqueda (1/2/3): ")
            choice = choice.strip()
            
            if choice == "1":
                return await self.get_user_by_id()
            elif choice == "2":
                return await self.get_user_by_username(guild)
            elif choice == "3":
                return await self.get_user_by_nickname(guild)
            else:
                print("⚠️  Opción inválida. Usa 1, 2 o 3.")
    
    async def get_user_by_id(self) -> Optional[int]:
        """Obtiene usuario por ID directo"""
        while True:
            # CORRECCIÓN: Usar async_input
            user_input = await self.async_input("\n👤 Ingresa el ID del usuario: ")
            user_input = user_input.strip()
            
            if not user_input.isdigit():
                print("⚠️  El ID debe ser numérico. Intenta de nuevo.")
                continue
            
            user_id = int(user_input)
            
            # Validar que el usuario existe
            try:
                user = await self.fetch_user(user_id)
                print(f"✅ Usuario encontrado: {user.name} ({user.display_name})")
                return user_id
            except discord.NotFound:
                print("❌ Usuario no encontrado. Verifica el ID.")
                # CORRECCIÓN: Usar async_input
                retry = await self.async_input("¿Intentar de nuevo? (s/n): ")
                if retry.strip().lower() != 's':
                    return None
            except discord.HTTPException as e:
                logger.error(f"Error al buscar usuario: {e}")
                return None
    
    async def get_user_by_username(self, guild: discord.Guild) -> Optional[int]:
        """Busca usuario por nombre de usuario"""
        # CORRECCIÓN: Usar async_input
        username = await self.async_input("\n👤 Ingresa el nombre de usuario (sin @): ")
        username = username.strip()
        
        # Buscar en miembros del servidor
        member = discord.utils.get(guild.members, name=username)
        
        if member:
            print(f"✅ Usuario encontrado: {member.name}#{member.discriminator} (ID: {member.id})")
            return member.id
        else:
            print(f"❌ No se encontró usuario con nombre '{username}' en este servidor.")
            return None
    
    async def get_user_by_nickname(self, guild: discord.Guild) -> Optional[int]:
        """Busca usuario por nickname en el servidor"""
        # CORRECCIÓN: Usar async_input
        nickname = await self.async_input("\n👤 Ingresa el nickname en el servidor: ")
        nickname = nickname.strip()
        
        # Buscar por display_name (nickname o username)
        member = discord.utils.find(
            lambda m: m.display_name.lower() == nickname.lower(),
            guild.members
        )
        
        if member:
            print(f"✅ Usuario encontrado: {member.display_name} (ID: {member.id})")
            return member.id
        else:
            print(f"❌ No se encontró usuario con nickname '{nickname}' en este servidor.")
            return None
    
    async def confirm_deletion(self, user_id: int, guild: discord.Guild) -> bool:
        """Confirmación de seguridad antes de eliminar"""
        print("\n" + "⚠️ "*20)
        print("⚠️  ADVERTENCIA: OPERACIÓN IRREVERSIBLE")
        print("⚠️ "*20)
        print(f"\n📋 Detalles de la operación:")
        print(f"   • Servidor: {guild.name}")
        print(f"   • Usuario ID: {user_id}")
        print(f"   • Periodo: Últimos 7 días")
        print(f"   • Canales: Todos los canales de texto accesibles")
        
        # CORRECCIÓN: Usar async_input
        confirmation = await self.async_input("\n❓ ¿Confirmas esta eliminación? Escribe 'ELIMINAR' para continuar: ")
        
        return confirmation.strip() == "ELIMINAR"
    
    async def delete_messages_from_user(self, guild: discord.Guild, user_id: int):
        """Elimina todos los mensajes del usuario en el servidor"""
        print("\n" + "="*60)
        print("🚀 INICIANDO PROCESO DE ELIMINACIÓN")
        print("="*60 + "\n")
        
        # Calcular fecha límite (7 días atrás)
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        
        # Obtener canales de texto
        text_channels = [ch for ch in guild.text_channels if isinstance(ch, discord.TextChannel)]
        
        print(f"📊 Total de canales a procesar: {len(text_channels)}\n")
        
        for idx, channel in enumerate(text_channels, 1):
            await self.process_channel(channel, user_id, seven_days_ago, idx, len(text_channels))
    
    async def process_channel(self, channel: discord.TextChannel, user_id: int, 
                             after_date: datetime, current: int, total: int):
        """Procesa un canal individual"""
        # Verificar permisos
        permissions = channel.permissions_for(channel.guild.me)
        if not permissions.manage_messages or not permissions.read_message_history:
            logger.warning(f"⚠️  Sin permisos en #{channel.name}")
            return
        
        print(f"[{current}/{total}] 🔍 Procesando #{channel.name}...", end=" ")
        
        try:
            # Definir función de check para purge
            def check_message(msg):
                return (msg.author.id == user_id and 
                       msg.created_at.replace(tzinfo=timezone.utc) > after_date)
            
            # Ejecutar purge con manejo robusto
            deleted = await channel.purge(
                limit=None,  # Sin límite, buscará todos
                check=check_message,
                after=after_date,
                bulk=True,
                reason=f"Eliminación masiva de mensajes del usuario ID: {user_id}"
            )
            
            deleted_count = len(deleted)
            self.total_deleted += deleted_count
            self.channels_processed += 1
            
            if deleted_count > 0:
                print(f"✅ {deleted_count} mensajes eliminados")
                logger.info(f"Canal #{channel.name}: {deleted_count} mensajes eliminados")
            else:
                print("⚪ Sin mensajes")
            
            # Pequeña pausa para evitar rate limits agresivos
            await asyncio.sleep(0.5)
            
        except discord.Forbidden:
            print("❌ Sin permisos")
            self.errors_count += 1
            logger.error(f"Sin permisos en #{channel.name}")
        
        except discord.HTTPException as e:
            print(f"⚠️  Error: {e}")
            self.errors_count += 1
            logger.error(f"Error HTTP en #{channel.name}: {e}")
        
        except Exception as e:
            print(f"❌ Error inesperado")
            self.errors_count += 1
            logger.error(f"Error inesperado en #{channel.name}: {e}", exc_info=True)
    
    def show_summary(self):
        """Muestra resumen final de la operación"""
        print("\n" + "="*60)
        print("📊 RESUMEN DE LA OPERACIÓN")
        print("="*60)
        print(f"\n✅ Mensajes eliminados: {self.total_deleted}")
        print(f"📁 Canales procesados: {self.channels_processed}")
        print(f"⚠️  Errores encontrados: {self.errors_count}")
        print(f"\n📝 Log detallado guardado en: bot_deletion.log")
        print("="*60 + "\n")


async def main():
    """Función principal"""
    # Cargar token
    load_dotenv()
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        print("❌ ERROR: No se encontró DISCORD_TOKEN")
        print("\n📝 Instrucciones:")
        print("1. Crea un archivo .env en el mismo directorio")
        print("2. Agrega la línea: DISCORD_TOKEN=tu_token_aqui")
        print("3. Obtén el token en: https://discord.com/developers/applications")
        
        # Opción alternativa: solicitar token por input (Esto está bien aquí porque el bot no ha iniciado)
        token = input("\nO ingresa el token ahora (Enter para cancelar): ").strip()
        if not token:
            return
    
    # Crear e iniciar bot
    bot = MessageDeleterBot()
    
    try:
        await bot.start(token)
    except discord.LoginFailure:
        logger.error("❌ Token inválido. Verifica tu DISCORD_TOKEN.")
    except KeyboardInterrupt:
        logger.info("⚠️  Proceso interrumpido por el usuario.")
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}", exc_info=True)


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║     🤖 DISCORD MESSAGE DELETER BOT v1.0 (FIXED)         ║
    ║                                                          ║
    ║  Elimina mensajes de usuarios específicos en 7 días     ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Bot cerrado correctamente.")
