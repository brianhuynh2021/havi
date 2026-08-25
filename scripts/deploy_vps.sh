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
# Để trống khi Nginx proxy API cùng domain; đặt URL tuyệt đối nếu API tách domain.
NEXT_PUBLIC_API_BASE_URL=
EOF
    echo "✅ Đã tạo file .env.production với các khoá bảo mật mã hoá ngẫu nhiên."
fi

# 3. Build và khởi chạy toàn bộ dịch vụ qua Docker Compose
echo "🐳 Đang build và khởi chạy các Docker Container..."
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build

# 4. Chờ API sẵn sàng và chạy Migration Database
echo "⏳ Đang chờ PostgreSQL và FastAPI khởi động..."
sleep 8
# KHÔNG `|| true`. Migration hỏng mà deploy vẫn báo thành công là cách app chạy
# lên với schema cũ: các truy vấn tham chiếu cột chưa tồn tại sẽ đổ ở request
# đầu tiên của khách, chứ không đổ ở đây nơi có người đang nhìn.
if ! docker compose -f docker-compose.prod.yml exec -T api alembic upgrade head; then
    echo "❌ Migration THẤT BẠI — dừng deploy. Schema chưa được cập nhật."
    echo "   Xem log: docker compose -f docker-compose.prod.yml logs api"
    exit 1
fi

# Model và schema phải khớp. `upgrade head` chạy được không có nghĩa là khớp —
# một index quên đổi tên vẫn cho `upgrade` xanh nhưng khiến môi trường dựng mới
# khác môi trường nâng cấp dần.
if ! docker compose -f docker-compose.prod.yml exec -T api alembic check; then
    echo "⚠️  CẢNH BÁO: schema lệch so với model (alembic check đỏ)."
    echo "   Deploy vẫn tiếp tục, nhưng phải vá drift trước lần phát hành sau."
fi

echo "========================================================"
echo "🎉 CHÚC MỪNG! HỆ THỐNG HAVI ĐÃ SẴN SÀNG TRÊN PRODUCTION!"
echo "🌐 Frontend (PWA):  https://<DOMAIN>"
echo "🔌 Backend (API):   https://<DOMAIN>/api"
echo "📜 API Docs:        https://<DOMAIN>/docs"
echo "💳 VietQR Webhook:  https://<DOMAIN>/webhooks/payos"
echo
echo "⚠️  Nginx chỉ khởi động khi đã có chứng chỉ TLS tại"
echo "   /etc/letsencrypt/live/havi/. Chưa cấp thì chạy certbot trước:"
echo "   docker compose -f docker-compose.prod.yml run --rm certbot certonly \\"
echo "     --webroot -w /var/www/certbot -d <DOMAIN> --cert-name havi"
echo "========================================================"
