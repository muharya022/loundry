# accounts/waha_service.py
import requests

class WAHAHandler:
    def __init__(self):
        self.base_url = "http://waha.menaralaundry.site"
        self.api_key = "88bce2e5513f686f2eb823004ddb48733c434e7b4e95b3228639c6f207b48b14"
        self.session_name = "default"
        self.timeout = 30
    
    def send_message(self, phone_number: str, message: str) -> bool:
        """Kirim pesan via WhatsApp"""
        try:
            # Format nomor untuk WAHA
            wa_number = f"{phone_number}@c.us"
            
            # Endpoint yang benar
            url = f"{self.base_url}/api/sendText"
            
            print(f"📤 Mengirim ke: {phone_number}")
            print(f"📍 URL: {url}")
            print(f"📱 Chat ID: {wa_number}")
            
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": self.api_key
            }
            
            # Body dengan session name
            payload = {
                "chatId": wa_number,
                "text": message,
                "session": self.session_name
            }
            
            print(f"📦 Payload: {payload}")
            
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            print(f"📊 Status: {response.status_code}")
            print(f"📊 Response: {response.text}")
            
            if response.status_code == 200:
                print(f"✅ Pesan berhasil dikirim ke {phone_number}")
                return True
            elif response.status_code == 201:
                print(f"✅ Pesan berhasil dikirim!")
                return True
            else:
                print(f"❌ Gagal: {response.text}")
                return False
                
        except requests.exceptions.ConnectionError:
            print("❌ Gagal konek ke WAHA. Pastikan WAHA berjalan di localhost:3000")
            return False
        except requests.exceptions.Timeout:
            print("❌ Timeout: WAHA tidak merespon")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def send_otp(self, phone_number: str, otp: str) -> bool:
        """Kirim OTP untuk verifikasi"""
        message = f"""🔐 *Verifikasi Menara Laundry*

Kode OTP Anda: *{otp}*

⏰ Berlaku 5 menit

Jangan berikan kode ini ke siapapun!

---
Menara Laundry"""
        return self.send_message(phone_number, message)
    
    def check_connection(self) -> bool:
        """Cek koneksi ke WAHA"""
        try:
            headers = {"X-API-Key": self.api_key}
            response = requests.get(
                f"{self.base_url}/api/sessions",
                headers=headers,
                timeout=5
            )
            
            print(f"🔍 Cek koneksi: {response.status_code}")
            
            if response.status_code == 200:
                sessions = response.json()
                print(f"✅ WAHA terhubung! Sessions: {sessions}")
                return True
            else:
                print(f"❌ WAHA error: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False