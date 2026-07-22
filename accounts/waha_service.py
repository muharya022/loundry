# accounts/waha_service.py
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class WAHAHandler:
    def __init__(self):
        # Gunakan settings untuk konfigurasi
        self.base_url = getattr(settings, 'WAHA_API_URL', 'http://localhost:3000')
        self.api_key = getattr(settings, 'WAHA_API_KEY', '')
        self.session_name = getattr(settings, 'WAHA_SESSION', 'default')
        self.timeout = 30
        
        # Logging konfigurasi
        logger.info(f"WAHA Handler initialized with URL: {self.base_url}")
        logger.info(f"Session: {self.session_name}")
        logger.info(f"API Key set: {'Yes' if self.api_key else 'No'}")
    
    def _get_headers(self):
        """Get headers for WAHA API requests"""
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        return headers
    
    def send_message(self, phone_number: str, message: str) -> tuple:
        """
        Kirim pesan via WhatsApp
        
        Returns:
            tuple: (success: bool, response_message: str)
        """
        try:
            # Format nomor telepon untuk WAHA
            # Hapus '+' jika ada, dan pastikan format internasional
            clean_number = phone_number.replace('+', '').replace(' ', '').replace('-', '')
            
            # Jika nomor dimulai dengan 0, ganti dengan 62
            if clean_number.startswith('0'):
                clean_number = '62' + clean_number[1:]
            
            # Jika nomor tidak dimulai dengan kode negara, tambahkan 62
            if not clean_number.startswith('62'):
                clean_number = '62' + clean_number
            
            wa_number = f"{clean_number}@c.us"
            
            # Endpoint yang benar untuk WAHA v2
            url = f"{self.base_url}/api/sendText"
            
            logger.info(f"📤 Mengirim ke: {clean_number}")
            logger.info(f"📍 URL: {url}")
            logger.info(f"📱 Chat ID: {wa_number}")
            
            headers = self._get_headers()
            
            # Body dengan session name
            payload = {
                "chatId": wa_number,
                "text": message,
                "session": self.session_name
            }
            
            logger.info(f"📦 Payload: {payload}")
            
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            logger.info(f"📊 Status: {response.status_code}")
            logger.info(f"📊 Response: {response.text[:200]}...")
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Pesan berhasil dikirim ke {clean_number}")
                return True, "Pesan berhasil dikirim"
            elif response.status_code == 401:
                logger.error(f"❌ Unauthorized: API Key tidak valid atau tidak ada")
                return False, "Unauthorized: Periksa API Key WAHA"
            elif response.status_code == 404:
                logger.error(f"❌ Endpoint tidak ditemukan: {url}")
                return False, f"Endpoint tidak ditemukan: {url}"
            else:
                logger.error(f"❌ Gagal: {response.text}")
                return False, f"Gagal: {response.text}"
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ Gagal konek ke WAHA. Pastikan WAHA berjalan di {self.base_url}")
            logger.error(f"Error detail: {e}")
            return False, "Tidak dapat terhubung ke WAHA API"
            
        except requests.exceptions.Timeout as e:
            logger.error(f"❌ Timeout: WAHA tidak merespon")
            logger.error(f"Error detail: {e}")
            return False, "WAHA timeout - tidak merespon"
            
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return False, f"Error: {str(e)}"
    
    def send_otp(self, phone_number: str, otp: str, user_name: str = "") -> tuple:
        """
        Kirim OTP untuk verifikasi
        
        Returns:
            tuple: (success: bool, response_message: str)
        """
        message = f"""🔐 *Verifikasi Menara Laundry*

Halo {user_name}! 

Kode OTP Anda: *{otp}*

⏰ Berlaku 5 menit

⚠️ Jangan berikan kode ini ke siapapun!

---
Menara Laundry"""
        return self.send_message(phone_number, message)
    
    def send_reset_password_otp(self, phone_number: str, otp: str, user_name: str = "") -> tuple:
        """
        Kirim OTP untuk reset password
        
        Returns:
            tuple: (success: bool, response_message: str)
        """
        message = f"""🔐 *Reset Password Menara Laundry*

Halo {user_name}!

Kami menerima permintaan reset password.

━━━━━━━━━━━━━━━━━━━━
🔑 *Kode OTP Anda:*
*{otp}*
━━━━━━━━━━━━━━━━━━━━

⏰ Kode ini berlaku *5 menit*

Jika Anda tidak meminta reset password, abaikan pesan ini.

---
Menara Laundry"""
        return self.send_message(phone_number, message)
    
    def check_connection(self) -> tuple:
        """
        Cek koneksi ke WAHA
        
        Returns:
            tuple: (is_connected: bool, message: str, sessions: list)
        """
        try:
            headers = self._get_headers()
            
            # Cek kesehatan WAHA
            health_url = f"{self.base_url}/health"
            health_response = requests.get(
                health_url,
                headers=headers,
                timeout=5
            )
            
            if health_response.status_code != 200:
                return False, f"WAHA tidak sehat: {health_response.status_code}", None
            
            # Cek sessions
            sessions_url = f"{self.base_url}/api/sessions"
            sessions_response = requests.get(
                sessions_url,
                headers=headers,
                timeout=5
            )
            
            if sessions_response.status_code == 200:
                sessions = sessions_response.json()
                session_status = "Unknown"
                
                # Cek status session specific
                for session in sessions:
                    if session.get('name') == self.session_name:
                        session_status = session.get('status', 'Unknown')
                        break
                
                return True, f"WAHA terhubung! Status: {session_status}", sessions
            else:
                return False, f"Error: {sessions_response.status_code}", None
                
        except requests.exceptions.ConnectionError:
            return False, "Tidak dapat terhubung ke WAHA", None
        except Exception as e:
            return False, f"Error: {str(e)}", None
    
    def create_session(self, session_name: str = None) -> tuple:
        """
        Membuat session baru di WAHA
        
        Returns:
            tuple: (success: bool, message: str)
        """
        if not session_name:
            session_name = self.session_name
        
        try:
            headers = self._get_headers()
            url = f"{self.base_url}/api/sessions"
            
            response = requests.post(
                url,
                json={"name": session_name},
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                return True, f"Session '{session_name}' berhasil dibuat"
            else:
                return False, f"Gagal: {response.text}"
                
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def get_qr_code(self, session_name: str = None) -> tuple:
        """
        Mendapatkan QR Code untuk scan WhatsApp
        
        Returns:
            tuple: (success: bool, qr_data: str, message: str)
        """
        if not session_name:
            session_name = self.session_name
        
        try:
            headers = self._get_headers()
            url = f"{self.base_url}/api/sessions/{session_name}/qr"
            
            response = requests.get(
                url,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                qr_data = data.get('qr', '')
                return True, qr_data, "QR Code berhasil didapatkan"
            else:
                return False, None, f"Gagal: {response.text}"
                
        except Exception as e:
            return False, None, f"Error: {str(e)}"


# ===================== INSTANCE GLOBAL =====================
waha_handler = WAHAHandler()


# ===================== FUNGSI HELPER =====================

def send_whatsapp_message(phone_number: str, message: str) -> tuple:
    """
    Helper function untuk kirim pesan WhatsApp
    """
    return waha_handler.send_message(phone_number, message)


def send_otp_whatsapp(phone_number: str, otp: str, user_name: str = "") -> tuple:
    """
    Helper function untuk kirim OTP via WhatsApp
    """
    return waha_handler.send_otp(phone_number, otp, user_name)


def send_reset_password_otp(phone_number: str, otp: str, user_name: str = "") -> tuple:
    """
    Helper function untuk kirim OTP reset password via WhatsApp
    """
    return waha_handler.send_reset_password_otp(phone_number, otp, user_name)


def check_waha_connection() -> tuple:
    """
    Helper function untuk cek koneksi WAHA
    """
    return waha_handler.check_connection()