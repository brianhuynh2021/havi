#!/usr/bin/env bash
#
# Lấy chat id Telegram cho kênh nhắc gia hạn, và gửi một tin thử để xác nhận
# đường đi thật sự chạy.
#
# Vì sao cần script: `chat_id` không hiện ở đâu trong app Telegram. Cách duy nhất
# lấy được là đọc `getUpdates` của bot, và cách đó chỉ trả về sau khi CON NGƯỜI
# nhắn cho bot trước — Telegram không cho bot mở hội thoại.
#
# Dùng:
#   bash scripts/telegram-setup.sh <BOT_TOKEN>
#
set -euo pipefail

TOKEN="${1:-}"

if [[ -z "$TOKEN" ]]; then
  cat <<'HELP'
Thiếu bot token.

Cách lấy token — làm trong app Telegram, mất khoảng một phút:

  1. Tìm  @BotFather  rồi bấm Start
  2. Gửi  /newbot
  3. Đặt tên hiển thị, ví dụ:  Havi Ops
  4. Đặt username, PHẢI kết thúc bằng "bot", ví dụ:  havi_ops_bot
  5. BotFather trả về một dòng dạng  123456789:AAH...  — đó là token

Rồi chạy lại:

  bash scripts/telegram-setup.sh 123456789:AAH...

HELP
  exit 1
fi

API="https://api.telegram.org/bot${TOKEN}"

echo "→ Kiểm token…"
ME=$(curl -sS "${API}/getMe")
if ! echo "$ME" | grep -q '"ok":true'; then
  echo "✗ Token không dùng được. Telegram trả về:"
  echo "$ME"
  exit 1
fi
BOT_NAME=$(echo "$ME" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['username'])")
echo "✓ Bot: @${BOT_NAME}"

echo
echo "→ Bây giờ mở Telegram, tìm  @${BOT_NAME}  rồi NHẮN cho nó một câu bất kỳ."
echo "  (Bắt buộc. Telegram không cho bot nhắn trước cho ai chưa từng nhắn nó.)"
echo
echo "  Muốn cả đội cùng nhận: tạo một group, thêm @${BOT_NAME} vào, rồi nhắn"
echo "  một câu trong group đó. Chat id của group là số ÂM."
echo
read -r -p "Nhắn xong thì bấm Enter… " _

echo "→ Đọc chat id…"
UPDATES=$(curl -sS "${API}/getUpdates")

CHAT_ID=$(echo "$UPDATES" | python3 -c '
import json, sys

data = json.load(sys.stdin)
results = data.get("result", [])
if not results:
    sys.exit(1)

# Lấy lượt CUỐI: nếu bot từng được dùng cho việc khác, các lượt cũ có thể là chat
# của người khác. Lượt cuối là chat vừa nhắn xong.
seen = {}
for item in results:
    message = item.get("message") or item.get("channel_post") or {}
    chat = message.get("chat") or {}
    if chat.get("id") is not None:
        seen[chat["id"]] = chat.get("title") or chat.get("username") or chat.get("first_name") or "?"

if not seen:
    sys.exit(1)

for chat_id, name in seen.items():
    print(f"{chat_id}\t{name}", file=sys.stderr)

print(list(seen)[-1])
' 2>/tmp/havi-telegram-chats) || {
  echo "✗ Chưa thấy tin nhắn nào."
  echo "  Nhắn cho @${BOT_NAME} rồi chạy lại script này."
  echo
  echo "  Nếu bạn nhắn trong group mà vẫn không thấy: BotFather → /setprivacy →"
  echo "  chọn Disable, để bot đọc được tin nhắn thường trong group."
  exit 1
}

echo "✓ Các chat đã thấy:"
sed 's/^/    /' /tmp/havi-telegram-chats
rm -f /tmp/havi-telegram-chats

echo
echo "→ Gửi tin thử tới chat ${CHAT_ID}…"
SEND=$(curl -sS -X POST "${API}/sendMessage" \
  -H 'Content-Type: application/json' \
  -d "{\"chat_id\":\"${CHAT_ID}\",\"text\":\"✓ Havi đã nối được Telegram. Nhắc gia hạn sẽ về đây.\"}")

if echo "$SEND" | grep -q '"ok":true'; then
  echo "✓ Đã gửi. Kiểm Telegram xem có tin chưa."
else
  echo "✗ Gửi thất bại:"
  echo "$SEND"
  exit 1
fi

cat <<CONF

────────────────────────────────────────────────────────────
Dán hai dòng này vào  apps/backend/.env

  HAVI_TELEGRAM_BOT_TOKEN=${TOKEN}
  HAVI_TELEGRAM_DEFAULT_CHAT_ID=${CHAT_ID}

Backend chỉ đọc apps/backend/.env — nó chạy từ thư mục đó, và env_file
là đường dẫn tương đối. Đặt ở .env gốc sẽ KHÔNG ăn.

Rồi khởi động lại backend. Nhắc gia hạn chạy 8h sáng giờ VN mỗi ngày.

Muốn thử ngay không cần đợi tới 8h sáng:

  cd apps/backend
  uv run python -c "from scheduler.tasks import notify_due_renewals; notify_due_renewals()"
────────────────────────────────────────────────────────────
CONF
