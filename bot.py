from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityTextUrl
from telethon.tl.functions.users import GetFullUserRequest
import re
import os
import asyncio

# Environment variables dan ma'lumotlarni olish
API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')
TARGET_CHANNEL = os.environ.get('TARGET_CHANNEL')

# Session string for non-interactive authentication (MUHIM!)
SESSION_STRING = os.environ.get('SESSION_STRING', None)

# Sessiya fayli uchun
SESSION_NAME = 'userbot_session'

# Environment variables orqali telefon raqami va parol
PHONE_NUMBER = os.environ.get('PHONE_NUMBER', None)
PASSWORD = os.environ.get('PASSWORD', None)  # 2FA parol bo'lsa

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

async def start_client():
    """Start client with non-interactive authentication"""
    
    # FIRST METHOD: Use session string if provided (BEST for Railway)
    if SESSION_STRING:
        print("🔑 Session string orqali ulanish...")
        try:
            # Connect first
            await client.connect()
            # Then sign in with session string
            await client.start(session_string=SESSION_STRING)
            print("✅ Session string orqali muvaffaqiyatli ulandi!")
            return await client.get_me()
        except Exception as e:
            print(f"❌ Session string xatosi: {e}")
            raise
    
    # SECOND METHOD: Use phone number (but this still requires interactive code)
    elif PHONE_NUMBER:
        print(f"📱 Telefon raqami: {PHONE_NUMBER}")
        
        # Connect first
        await client.connect()
        
        # Check if already authorized
        if not await client.is_user_authorized():
            print("📱 Telefon raqamiga kod yuborilmoqda...")
            
            # Send code request
            try:
                await client.send_code_request(PHONE_NUMBER)
                print("✅ Kod yuborildi!")
                
                # Get code from environment
                CODE = os.environ.get('CODE', None)
                
                if CODE:
                    print(f"🔑 Koddan foydalanilmoqda: {CODE}")
                    await client.sign_in(PHONE_NUMBER, CODE)
                else:
                    print("❌ CODE environment variable topilmadi!")
                    print("💡 Iltimos, quyidagi o'zgaruvchilarni o'rnating:")
                    print("   - PHONE_NUMBER")
                    print("   - CODE (Telegramdan kelgan kod)")
                    print("   - PASSWORD (agar 2FA yoqilgan bo'lsa)")
                    raise Exception("Verification code required")
                
                # Handle 2FA if needed
                if PASSWORD:
                    print("🔐 2FA paroli tekshirilmoqda...")
                    await client.sign_in(password=PASSWORD)
                    
            except Exception as e:
                print(f"❌ Kod yuborish xatosi: {e}")
                raise
        else:
            print("✅ Oldingi sessiya mavjud!")
        
        print("✅ Telefon raqami orqali ulandi!")
        return await client.get_me()
    
    # THIRD METHOD: Try to use existing session file
    else:
        print("💾 Mavjud sessiya fayli tekshirilmoqda...")
        await client.connect()
        
        if await client.is_user_authorized():
            print("✅ Mavjud sessiya fayli ishlatilmoqda!")
            return await client.get_me()
        else:
            print("❌ Hech qanday autentifikatsiya ma'lumoti topilmadi!")
            print("💡 Iltimos, quyidagi o'zgaruvchilardan birini o'rnating:")
            print("   - SESSION_STRING (Tavsiya etiladi)")
            print("   - PHONE_NUMBER + CODE")
            raise Exception("No authentication method available")

@client.on(events.NewMessage)
async def handler(event):
    # O'z xabarlarimizni ignore qilish
    if event.out:
        return
    
    message = event.message
    
    # Faqat matnli xabarlarni tekshirish
    if not message.text:
        return
    
    print(f"\n📨 Yangi xabar: {message.text[:100]}")
    
    # Link bor yoki yo'qligini tekshirish
    has_link = False
    
    # 1. Textdagi linklarni tekshirish
    links = re.findall(r'https?://[^\s]+', message.text)
    if links:
        has_link = True
        print(f"🔗 Topilgan linklar: {links}")
    
    # 2. Entity linklarni tekshirish
    if message.entities:
        for entity in message.entities:
            if isinstance(entity, MessageEntityTextUrl):
                has_link = True
                print(f"🔗 Entity link: {entity.url}")
                break
    
    # Agar link bo'lsa, xabar yuborgan odamning ma'lumotlarini saqlash
    if has_link:
        sender = await event.get_sender()
        print(f"👤 Link yuborgan odam: {sender.first_name if sender else 'Unknown'}")
        await save_user_info(sender, message)
    else:
        print("❌ Link topilmadi")

async def save_user_info(user, original_message):
    """Foydalanuvchining barcha ma'lumotlarini yig'ib kanalga yuborish"""
    try:
        print(f"📥 Ma'lumot yig'ilmoqda: {user.first_name} (@{user.username})")
        
        # To'liq foydalanuvchi ma'lumotlarini olish
        try:
            full_user = await client(GetFullUserRequest(user.id))
        except:
            full_user = None
        
        # Bio/About ni to'g'ri olish
        bio = "❌ Yo'q"
        if full_user:
            if hasattr(full_user, 'about') and full_user.about and full_user.about != "None":
                bio = str(full_user.about)
            elif hasattr(full_user, 'full_user') and full_user.full_user and hasattr(full_user.full_user, 'about'):
                if full_user.full_user.about:
                    bio = str(full_user.full_user.about)
        
        if bio and bio != "❌ Yo'q" and isinstance(bio, str):
            if len(bio) > 200:
                bio = bio[:197] + "..."
        
        # Statusni aniqlash
        status_text = "⚫️ Offline"
        try:
            if hasattr(user, 'status') and user.status:
                status_str = str(user.status)
                if 'Online' in status_str:
                    status_text = "🔵 Online"
                elif 'was_online' in status_str or 'WasOnline' in status_str:
                    if hasattr(user.status, 'was_online'):
                        status_text = f"📅 Oxirgi marta: {user.status.was_online}"
                    else:
                        status_text = "📅 Offline (vaqt ko'rinmaydi)"
        except:
            status_text = "⚫️ Ma'lumot yo'q"
        
        # Telefon raqami
        phone = "❌ Ko'rinmaydi"
        try:
            if hasattr(user, 'phone') and user.phone:
                phone = user.phone
            elif full_user and hasattr(full_user, 'phone') and full_user.phone:
                phone = full_user.phone
            elif full_user and hasattr(full_user, 'user') and full_user.user and hasattr(full_user.user, 'phone'):
                if full_user.user.phone:
                    phone = full_user.user.phone
        except:
            phone = "❌ Ko'rinmaydi"
        
        # Profil rasmlari
        photos = []
        try:
            photos = await client.get_profile_photos(user, limit=3)
        except:
            photos = []
        
        # Xabardagi linkni topish
        link_text = original_message.text
        links = re.findall(r'https?://[^\s]+', link_text)
        first_link = links[0] if links else "Link topilmadi"
        
        first_name = user.first_name if user.first_name else "❌ Yo'q"
        last_name = user.last_name if user.last_name else ""
        username = user.username if user.username else "❌ Yo'q"
        
        # Formatlangan ma'lumot
        info = f"""
╔══════════════════════════════════════════════════╗
║         👤 LINK YUBORGAN FOYDALANUVCHI              ║
╠══════════════════════════════════════════════════╣
║ 📛 Ism: {first_name} {last_name}
║ 🏷 Username: @{username}
║ 🆔 ID: {user.id}
║ 📱 Telefon: {phone}
║ 📝 Bio: {bio}
║ 📊 Status: {status_text}
║ 🤖 Bot: {"✅ Ha" if user.bot else "❌ Yo'q"}
╠══════════════════════════════════════════════════╣
║ 🔗 Yuborgan linki:
║ {first_link}
╠══════════════════════════════════════════════════╣
║ 📨 To'liq xabar:
║ {original_message.text[:200]}
║ 📅 Sana: {original_message.date}
║ 💬 Chat ID: {original_message.chat_id}
╚══════════════════════════════════════════════════╝
"""
        
        # Kanalga yuborish
        try:
            if photos and len(photos) > 0:
                await client.send_file(TARGET_CHANNEL, photos[0], caption=info)
                if len(photos) > 1:
                    await client.send_message(TARGET_CHANNEL, f"📸 {first_name}ning qo'shimcha rasmlari ({len(photos)-1} ta):")
                    for photo in photos[1:]:
                        try:
                            await client.send_file(TARGET_CHANNEL, photo)
                        except:
                            pass
            else:
                await client.send_message(TARGET_CHANNEL, info)
            
            print(f"✅ {first_name} (@{username}) ma'lumotlari {TARGET_CHANNEL} kanaliga saqlandi!")
        except Exception as e:
            print(f"❌ Kanalga yuborishda xato: {e}")
            await client.send_message('me', f"❌ Kanalga yuborib bo'lmadi: {e}\n\nMa'lumotlar Saved Messages'ga yuborilmoqda...")
            if photos and len(photos) > 0:
                await client.send_file('me', photos[0], caption=info)
            else:
                await client.send_message('me', info)
        
        # JSON formatda ham saqlash
        import json
        from datetime import datetime
        
        user_data = {
            "saved_date": str(datetime.now()),
            "user": {
                "name": f"{first_name} {last_name}".strip(),
                "username": user.username if user.username else None,
                "id": user.id,
                "phone": phone if phone != "❌ Ko'rinmaydi" else None,
                "bio": bio if bio != "❌ Yo'q" else None,
                "is_bot": user.bot
            },
            "sent_link": first_link,
            "original_message": original_message.text[:300],
            "message_date": str(original_message.date)
        }
        
        try:
            json_text = f"📊 JSON MA'LUMOTLAR:\n```json\n{json.dumps(user_data, indent=2, ensure_ascii=False)}\n```"
            await client.send_message(TARGET_CHANNEL, json_text)
        except:
            pass
        
    except Exception as e:
        error_msg = f"❌ Xato: {str(e)}"
        print(error_msg)
        try:
            await client.send_message(TARGET_CHANNEL, f"❌ Xato yuz berdi: {str(e)}\n\nFoydalanuvchi: {user.first_name if user else 'Unknown'}")
        except:
            await client.send_message('me', f"❌ Xato yuz berdi: {str(e)}")

async def main():
    print("🚀 Userbot ishga tushmoqda...")
    
    try:
        # Connect client first
        await client.connect()
        print("✅ Client ulandi!")
        
        # Then start authentication
        me = await start_client()
        print(f"✅ Userbot ishlayapti: {me.first_name} (@{me.username})")
        print("="*50)
        print(f"📨 Ma'lumotlar yuboriladigan kanal: {TARGET_CHANNEL}")
        print("="*50)
        print("⏹ To'xtatish: Ctrl+C\n")
        
        await client.run_until_disconnected()
    except Exception as e:
        print(f"❌ Ulanish xatosi: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == '__main__':
    try:
        client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\n⏹ Userbot to'xtatildi")
    except Exception as e:
        print(f"\n❌ Dastur xatosi: {e}")
