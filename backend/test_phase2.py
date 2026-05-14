import requests

BASE_URL = "http://localhost:8000/api/v1"

print("--- FAZ 2 TESTİ BAŞLIYOR ---\n")

# 1. OTP ile Giriş Yap / Kayıt Ol
print("1. OTP ile Giriş Yapılıyor...")
login_res = requests.post(
    f"{BASE_URL}/auth/login/otp",
    params={"phone_number": "5551234567", "otp_code": "1234"}
)
token_data = login_res.json()
print("Yanıt:", token_data)
token = token_data.get("access_token")
headers = {"Authorization": f"Bearer {token}"}
print("---------------------------------\n")

# 2. Profili Getir
print("2. Kullanıcı Profili Getiriliyor...")
me_res = requests.get(f"{BASE_URL}/users/me", headers=headers)
print("Yanıt:", me_res.json())
print("---------------------------------\n")

# 3. Profili Güncelle
print("3. Kullanıcı Boy/Kilo Bilgisi Güncelleniyor...")
update_res = requests.put(
    f"{BASE_URL}/users/me",
    headers=headers,
    json={"full_name": "Ahmet Yılmaz", "height": 180, "weight": 75}
)
print("Yanıt:", update_res.json())
print("---------------------------------\n")

# 4. Premium'a Yükselt (Paycell)
print("4. Premium Abonelik Başlatılıyor (Paycell)...")
upgrade_res = requests.post(
    f"{BASE_URL}/payment/upgrade",
    headers=headers,
    json={"payment_method": "PAYCELL"}
)
print("Yanıt:", upgrade_res.json())
print("---------------------------------\n")

# 5. Güncel Profili Tekrar Getir (Rolün Değiştiğini Görmek İçin)
print("5. Güncel Kullanıcı Profili Getiriliyor (Rol Kontrolü)...")
me_res_final = requests.get(f"{BASE_URL}/users/me", headers=headers)
print("Yanıt:", me_res_final.json())
print("---------------------------------\n")

print("--- TEST BAŞARIYLA TAMAMLANDI ---")
