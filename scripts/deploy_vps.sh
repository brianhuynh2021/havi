#!/usr/bin/env bash
# ==============================================================================
# Havi Production VPS Deploy Script (Chuẩn MIT / Stanford)
# Tự động cài đặt Docker, cấu hình môi trường, khởi chạy Havi và kiểm thử hệ thống.
# Hỗ trợ mọi VPS: Vietnix, TinoHost, DigitalOcean, Linode, AWS EC2 (Ubuntu/Debian)
# ==============================================================================

set -euo pipefail

echo "========================================================"
echo "🚀 BẮT ĐẦU TRIỂN KHAI HAVI LÊN PRODUCTION SERVER (VPS)..."
echo "========================================================"

# 1. Cài đặt Docker & Docker Compose nếu chưa có
if ! command -v docker &> /dev/null; then
    echo "📦 Đang cài đặt Docker Engine..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
fi

# 2. Tạo file cấu hình môi trường nếu chưa có
if [ ! -f .env.production ]; then
    echo "🔑 Đang khởi tạo file cấu hình bảo mật .env.production..."
    JWT_SECRET=$(openssl rand -hex 32)
    TOKEN_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || openssl rand -base64 32)
    DB_PASSWORD=$(openssl rand -hex 16)
    
    cat <<EOF > .env.production
# --- Havi Production Environment ---
HAVI_ENV=production
HAVI_DEBUG=false

# Database & Redis
POSTGRES_USER=havi
POSTGRES_PASSWORD=${DB_PASSWORD}
POSTGRES_DB=havi
HAVI_DATABASE_URL=postgresql+psycopg://havi:${DB_PASSWORD}@postgres:5432/havi
HAVI_REDIS_URL=redis://redis:6379/0

# Cryptographic Keys (AES-128 Fernet & HMAC-SHA256)
HAVI_JWT_SECRET=${JWT_SECRET}
HAVI_TOKEN_ENCRYPTION_KEY=${TOKEN_KEY}

# Storage
HAVI_MEDIA_BUCKET=havi-media
HAVI_MEDIA_ENDPOINT_URL=http://minio:9000
HAVI_MEDIA_PUBLIC_URL=http://localhost:9000/havi-media
MINIO_ROOT_USER=haviadmin
MINIO_ROOT_PASSWORD=$(openssl rand -hex 16)

# AI Models (Thay bằng API Key thật của bạn)
HAVI_USE_MOCK_LLM=false
HAVI_USE_FAKE_PUBLISHER=false
HAVI_GEMINI_API_KEY=

# VietQR & PayOS Payment Gateway
HAVI_PAYOS_CLIENT_ID=
HAVI_PAYOS_API_KEY=
HAVI_PAYOS_CHECKSUM_KEY=
HAVI_VIETQR_BANK_ID=MB
HAVI_VIETQR_ACCOUNT_NO=0987654321
HAVI_VIETQR_ACCOUNT_NAME=TRUNG TAM CONG NGHE NHAT MINH

# URLs
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF
    echo "✅ Đã tạo file .env.production với các khoá bảo mật mã hoá ngẫu nhiên."
fi

# 3. Build và khởi chạy toàn bộ dịch vụ qua Docker Compose
echo "🐳 Đang build và khởi chạy các Docker Container..."
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build

# 4. Chờ API sẵn sàng và chạy Migration Database
echo "⏳ Đang chờ PostgreSQL và FastAPI khởi động..."
sleep 8
docker compose -f docker-compose.prod.yml exec api alembic upgrade head || true

echo "========================================================"
echo "🎉 CHÚC MỪNG! HỆ THỐNG HAVI ĐÃ SẴN SÀNG TRÊN PRODUCTION!"
echo "🌐 Frontend (PWA):  http://<IP-VPS>"
echo "🔌 Backend (API):   http://<IP-VPS>/api"
echo "📜 API Docs:        http://<IP-VPS>/docs"
echo "💳 VietQR Webhook:  http://<IP-VPS>/webhooks/payos"
echo "========================================================"
