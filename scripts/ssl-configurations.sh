#!/bin/bash
set -euo pipefail

# Gerekli paket kurulumu
sudo apt update && sudo apt install -y openssl

# Sunucu IP adresi (SSL sertifikasına eklenecek)
SERVER_IP=$(curl -s ifconfig.me)

echo "SSL sertifika dosyaları oluşturuluyor..."

# Root CA anahtarı ve sertifikası
openssl genrsa -out rootCA.key 4096
openssl req -x509 -new -nodes -key rootCA.key -sha256 -days 3650 \
    -out rootCA.crt -subj "/C=TR/CN=RootCA"

# Sunucu anahtarı ve sertifika isteği
openssl genrsa -out server.key 4096
openssl req -new -key server.key -out server.csr -subj "/C=TR/CN=$SERVER_IP"

# subjectAltName bilgisi için geçici dosya
echo "subjectAltName=IP:$SERVER_IP" > san.cnf

# Sunucu sertifikasını rootCA ile imzalama
openssl x509 -req -in server.csr -CA rootCA.crt -CAkey rootCA.key \
    -CAcreateserial -out server.crt -days 3650 -sha256 -extfile san.cnf

# Sertifika zincirini doğrula
openssl verify -CAfile rootCA.crt server.crt || {
    echo "Sertifika doğrulaması başarısız oldu!" >&2
    exit 1
}

# Dosyaları hedef klasöre taşı
echo "Dosyalar ./config/secrets/ssl altına taşınıyor..."
mkdir -p ./config/secrets/ssl
cp rootCA.crt server.crt server.key ./config/secrets/ssl/

# Geçici ve özel dosyaları sil
rm -f rootCA.srl rootCA.crt rootCA.key server.csr server.crt server.key san.cnf

# PostgreSQL için izinleri ayarla
sudo chown 999:999 ./config/secrets/ssl/*
sudo chmod 600 ./config/secrets/ssl/*

echo "SSL sertifikaları başarıyla oluşturuldu ve yapılandırıldı."
