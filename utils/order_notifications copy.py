# utils/order_notifications.py
import requests
import logging
from django.conf import settings
from django.shortcuts import redirect
from django.contrib import messages

logger = logging.getLogger(__name__)


class WhatsAppNotifier:
    def __init__(self):
        self.base_url = getattr(settings, 'WAHA_API_URL', 'http://localhost:3000')
        self.api_key = getattr(settings, 'WAHA_API_KEY', '123456')
        self.session_name = getattr(settings, 'WAHA_SESSION', 'default')
        self.auth_enabled = getattr(settings, 'WAHA_AUTH_ENABLED', True)
        self.timeout = 30
        
        # Debug
        print(f"🔧 WAHA Config:")
        print(f"   URL: {self.base_url}")
        print(f"   Session: {self.session_name}")
        print(f"   Auth Enabled: {self.auth_enabled}")
        print(f"   API Key: {self.api_key}")
    
    def _get_headers(self):
        """Get headers for WAHA API with API Key"""
        headers = {
            "Content-Type": "application/json",
        }
        if self.auth_enabled and self.api_key:
            headers["X-Api-Key"] = self.api_key
        return headers
    
    def _format_phone(self, phone):
        if not phone:
            return None
        import re
        clean = re.sub(r"[^0-9]", "", str(phone))
        if clean.startswith('0'):
            clean = '62' + clean[1:]
        elif not clean.startswith('62') and len(clean) < 12:
            clean = '62' + clean
        return clean
    
    def _send_waha_message(self, phone, message):
        if not phone or not message:
            return False
        
        try:
            formatted_phone = self._format_phone(phone)
            if not formatted_phone:
                return False
            
            url = f"{self.base_url}/api/sendText"
            headers = self._get_headers()
            
            payload = {
                "chatId": f"{formatted_phone}@c.us",
                "text": message,
                "session": self.session_name
            }
            
            print(f"📤 Sending to: {formatted_phone}")
            print(f"📍 URL: {url}")
            print(f"📋 Headers: {headers}")
            print(f"📦 Payload: {payload}")
            
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            print(f"📊 Status: {response.status_code}")
            print(f"📊 Response: {response.text[:200]}")
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ WAHA message sent to {formatted_phone}")
                return True
            elif response.status_code == 401:
                logger.error("❌ Unauthorized! API Key salah atau tidak valid")
                print(f"❌ ERROR: Unauthorized! API Key: {self.api_key}")
                return False
            else:
                logger.error(f"❌ WAHA failed: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Cannot connect to WAHA at {self.base_url}")
            print(f"❌ ERROR: Tidak bisa konek ke WAHA di {self.base_url}")
            return False
        except Exception as e:
            logger.error(f"❌ WAHA error: {e}")
            return False
    
    def _get_coordinates_text(self, order):
        """Get coordinates text from order - menggunakan field latitude dan longitude"""
        coords_text = ""
        # PERBAIKAN: gunakan latitude dan longitude (tanpa prefix pickup_)
        if hasattr(order, 'latitude') and hasattr(order, 'longitude'):
            if order.latitude and order.longitude:
                lat = float(order.latitude)
                lng = float(order.longitude)
                coords_text = f"""
📍 *Koordinat Pickup (untuk Kurir)*
Latitude: {lat}
Longitude: {lng}
🔗 Google Maps: https://www.google.com/maps?q={lat},{lng}
📌 Short URL: https://maps.google.com/?q={lat},{lng}

💡 *Cara Pakai:*
• Klik link Maps untuk navigasi
• Atau copy koordinat ke Google Maps
• Bisa juga paste di Waze (cari lokasi dengan koordinat)"""
        return coords_text
    
    def _build_message(self, order, event_type, target):
        """Build WhatsApp message based on event type and target"""
        
        # Base message
        base = f"""🏪 *Menara Laundry*

📋 *Order #{order.id}*
Status: {order.get_order_status_display()}
Pembayaran: {order.get_payment_status_display()}

👤 *Pelanggan*
Nama: {order.customer.username if order.customer else 'N/A'}
Telepon: {order.customer.phone if order.customer else 'N/A'}

📦 *Detail Pesanan*
"""
        
        # Add order items
        if hasattr(order, 'order_items') and order.order_items.exists():
            items = []
            for item in order.order_items.all():
                if item.service:
                    weight_text = f" ({item.weight} kg)" if item.weight else ""
                    items.append(f"- {item.service.name}{weight_text}")
                elif item.laundry_item:
                    items.append(f"- {item.laundry_item.name} x{item.quantity}")
            base += "\n".join(items) + "\n"
        
        base += f"""
💰 *Total: Rp {order.price_total:,.0f}*

📍 *Alamat Pickup*
{order.pickup_address}

📅 *Tanggal Order*
{order.created_at.strftime('%d %B %Y, %H:%M')}
"""
        
        # PERBAIKAN: Add coordinates if available and target is courier
        if target == 'courier':
            coords = self._get_coordinates_text(order)
            if coords:
                base += f"\n{coords}"
        
        # Event-specific messages
        event_messages = {
            'order_created': f"""📢 *ORDER BARU DITERIMA*

{base}

✅ Pesanan Anda telah kami terima dan akan segera diproses.

---
Menara Laundry - Layanan Laundry Profesional""",
            
            'order_picked_up': f"""🚗 *PESANAN DIJEMPUT*

{base}

🔄 Pesanan Anda sedang dalam perjalanan ke laundry.

Estimasi selesai: {order.estimated_completion.strftime('%d %B %Y, %H:%M') if order.estimated_completion else 'Akan diinfokan'}

---
Menara Laundry - Layanan Laundry Profesional""",
            
            'order_processing': f"""⚙️ *PESANAN DIPROSES*

{base}

🧺 Pesanan Anda sedang diproses oleh tim laundry kami.

---
Menara Laundry - Layanan Laundry Profesional""",
            
            'order_ready': f"""✅ *PESANAN SIAP*

{base}

🎉 Pesanan Anda sudah selesai diproses dan siap diambil/diantar.

---
Menara Laundry - Layanan Laundry Profesional""",
            
            'order_delivered': f"""🎊 *PESANAN SELESAI*

{base}

✨ Terima kasih telah menggunakan jasa Menara Laundry!

Kami senang bisa melayani Anda. Sampai jumpa di pesanan berikutnya! 🧺

---
Menara Laundry - Layanan Laundry Profesional""",
            
            'order_cancelled': f"""⚠️ *PESANAN DIBATALKAN*

{base}

❌ Pesanan Anda telah dibatalkan.

Jika ada pertanyaan, silakan hubungi customer service kami.

---
Menara Laundry - Layanan Laundry Profesional""",
            
            'payment_confirmed': f"""💳 *PEMBAYARAN DIKONFIRMASI*

{base}

✅ Pembayaran Anda telah kami terima dan dikonfirmasi.

---
Menara Laundry - Layanan Laundry Profesional""",
            
            'courier_assigned': f"""🚴 *KURIR DITUGASKAN*

{base}

👤 Kurir: {order.assigned_courier.username if order.assigned_courier else 'N/A'}
📞 Telepon: {order.assigned_courier.phone if order.assigned_courier else 'N/A'}

📌 *Instruksi untuk Kurir:*
1. Gunakan koordinat di atas untuk navigasi
2. Hubungi pelanggan jika perlu
3. Konfirmasi setelah mengambil pesanan

---
Menara Laundry - Layanan Laundry Profesional""",
            
            'courier_pickup_reminder': f"""⏰ *PENGINGAT PICKUP KURIR*

{base}

🚨 *Untuk Kurir:*
Segera lakukan pickup di alamat di atas.

📍 Gunakan koordinat untuk navigasi yang akurat.

---
Menara Laundry - Layanan Laundry Profesional"""
        }
        
        return event_messages.get(event_type, f"""📌 *UPDATE PESANAN*

{base}

---
Menara Laundry - Layanan Laundry Profesional""")
    
    def send_notification(self, order, event_type, target='customer'):
        """
        Send notification to customer or courier
        
        Args:
            order: Order object
            event_type: String (order_created, order_picked_up, etc)
            target: 'customer' or 'courier'
        
        Returns:
            dict: Status of delivery
        """
        if target == 'customer':
            phone = order.customer.phone if order.customer else None
            if not phone:
                return {'status': 'error', 'message': 'Customer has no phone number'}
        elif target == 'courier':
            if not order.assigned_courier:
                return {'status': 'error', 'message': 'No courier assigned'}
            phone = order.assigned_courier.phone
            if not phone:
                return {'status': 'error', 'message': 'Courier has no phone number'}
        else:
            return {'status': 'error', 'message': 'Invalid target'}
        
        # Build message with target context
        message = self._build_message(order, event_type, target)
        success = self._send_waha_message(phone, message)
        
        return {
            'status': 'sent' if success else 'failed',
            'target': target,
            'phone': phone,
            'event': event_type,
            'order_id': order.id
        }
    
    def send_location_to_courier(self, order):
        """
        Send location coordinates specifically to courier
        
        Args:
            order: Order object with coordinates
        
        Returns:
            dict: Status of delivery
        """
        if not order.assigned_courier:
            return {'status': 'error', 'message': 'No courier assigned'}
        
        # PERBAIKAN: gunakan latitude dan longitude (tanpa prefix pickup_)
        if not order.latitude or not order.longitude:
            return {'status': 'error', 'message': 'No coordinates available'}
        
        phone = order.assigned_courier.phone
        if not phone:
            return {'status': 'error', 'message': 'Courier has no phone number'}
        
        lat = float(order.latitude)
        lng = float(order.longitude)
        
        message = f"""📍 *LOKASI PICKUP UNTUK KURIR*

🏪 Menara Laundry
📋 Order #{order.id}

👤 Pelanggan: {order.customer.username if order.customer else 'N/A'}
📞 Telepon: {order.customer.phone if order.customer else 'N/A'}

📍 *Alamat Lengkap:*
{order.pickup_address}

🗺️ *Koordinat GPS (Akurat):*
Latitude: {lat}
Longitude: {lng}

🔗 *Link Google Maps:*
https://www.google.com/maps?q={lat},{lng}

📌 *Link Short (Google Maps):*
https://maps.google.com/?q={lat},{lng}

💡 *Tips untuk Kurir:*
1. Klik link Maps untuk navigasi langsung
2. Atau copy koordinat untuk paste di Google Maps/Waze
3. Jika sulit ditemukan, hubungi pelanggan di nomor di atas

⏰ *Jadwal Pickup:*
{order.scheduled_pickup.strftime('%d %B %Y, %H:%M') if order.scheduled_pickup else 'Segera'}

---
Menara Laundry - Tim Kurir"""
        
        success = self._send_waha_message(phone, message)
        
        return {
            'status': 'sent' if success else 'failed',
            'target': 'courier',
            'phone': phone,
            'event': 'location_sent',
            'order_id': order.id,
            'coordinates': {
                'latitude': lat,
                'longitude': lng
            }
        }


def trigger_whatsapp_notification(order, event_type, include_courier=False):
    """
    Send WhatsApp notification to customer and optionally courier
    
    Args:
        order: Order object
        event_type: String (order_created, order_picked_up, etc)
        include_courier: Boolean, whether to also send to courier
    
    Returns:
        dict: Status of all deliveries
    """
    notifier = WhatsAppNotifier()
    results = {
        'customer': None,
        'courier': None,
        'status': 'ok'
    }
    
    # Send to customer
    customer_result = notifier.send_notification(order, event_type, 'customer')
    results['customer'] = customer_result
    
    if customer_result['status'] == 'failed':
        results['status'] = 'partial_failure'
        logger.error(f"Failed to send to customer: {customer_result}")
    
    # Send to courier if requested and assigned
    if include_courier and order.assigned_courier:
        courier_result = notifier.send_notification(order, event_type, 'courier')
        results['courier'] = courier_result
        
        if courier_result['status'] == 'failed':
            results['status'] = 'partial_failure'
            logger.error(f"Failed to send to courier: {courier_result}")
    else:
        results['courier'] = {'status': 'skipped', 'message': 'Courier not included or not assigned'}
    
    return results


def send_coordinates_to_courier(order):
    """
    Send only coordinates to courier
    
    Args:
        order: Order object with coordinates
    
    Returns:
        dict: Status of delivery
    """
    notifier = WhatsAppNotifier()
    return notifier.send_location_to_courier(order)


def notify_courier_pickup(order):
    """
    Notify courier about pickup with coordinates
    
    Args:
        order: Order object
    
    Returns:
        dict: Status
    """
    notifier = WhatsAppNotifier()
    
    # Send to customer first
    customer_result = notifier.send_notification(order, 'courier_assigned', 'customer')
    
    # Send to courier with coordinates
    courier_result = notifier.send_location_to_courier(order)
    
    return {
        'customer': customer_result,
        'courier': courier_result,
        'status': 'ok' if courier_result['status'] == 'sent' else 'failed'
    }