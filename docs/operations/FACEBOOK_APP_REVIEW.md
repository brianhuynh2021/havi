# Facebook-first Pilot and Meta App Review

This is the operational checklist for testing Havi with one Facebook Page and
for later requesting Advanced Access. It deliberately covers only capabilities
implemented today: approved Page posts/photos, Facebook Reels, Messenger, and
public Page comments. Havi does not create or manage ads.

## 1. Pilot boundary

Use a dedicated test Page first. In Meta Development mode, every Facebook user
in the pilot must have an app role and the required Page tasks. Do not test on a
customer's production Page until the complete dry run below passes.

Havi never publishes a generated draft without human approval. “Duyệt & đăng
ngay” is the explicit approval action. A successful API request must also return
a provider object ID; a 2xx response without an ID is treated as ambiguous and
must be checked on Facebook before any retry.

## 2. Meta Dashboard configuration

### App settings

- Display name: `Havi — Vận hành Facebook Page`
- Category: `Business and Pages`
- App icon: 1024 × 1024 PNG
- App domain: the production web domain
- Privacy policy: `https://<web-domain>/privacy`
- Terms: `https://<web-domain>/terms`
- Data deletion instructions: `https://<web-domain>/data-deletion`
- Data deletion callback: `https://<api-domain>/connections/facebook/data-deletion`

### Facebook Login for Business

- Valid OAuth redirect URI:
  `https://<api-domain>/connections/facebook/callback`
- Enforce HTTPS: enabled
- Put every permission in the Login for Business configuration listed below.
- Copy its configuration ID to `HAVI_FACEBOOK_CONFIG_ID`. Leave the variable
  empty only when intentionally using classic Facebook Login.

### Webhooks

- Product/object: `Page`
- Callback URL: `https://<api-domain>/webhooks/meta`
- Verify token: the exact value of `HAVI_META_WEBHOOK_VERIFY_TOKEN`
- App-level subscribed fields: `messages` and `feed`

OAuth completion also calls `/{page-id}/subscribed_apps` with
`subscribed_fields=messages,feed`. Havi does not store the connection until Meta
confirms this Page-level subscription.

## 3. Permissions and their implemented use

| Permission | Havi use | Demonstration required |
|---|---|---|
| `pages_show_list` | Find Pages the authenticated person can operate and retrieve the selected Page ID/token. | OAuth and connected Page name. |
| `pages_read_engagement` | Read Page metadata needed by Page and Messenger operations. | Connected Page and incoming activity. |
| `pages_read_user_content` | Receive user-authored Page comments through the `feed` webhook. | A new public comment appearing in Havi. |
| `pages_manage_posts` | Publish a human-approved Page post/photo or Reel. | Draft → approval → verified Facebook post. |
| `pages_manage_engagement` | Reply publicly beneath a Facebook Page comment. | Explicit reply action and matching Facebook reply. |
| `pages_manage_metadata` | Subscribe the selected Page to `messages` and `feed` webhooks. | Connect Page, then receive a webhook. |
| `pages_messaging` | Receive and explicitly reply to Messenger conversations. | Incoming message and reply within Meta's allowed window. |

The OAuth adapter verifies `/me/permissions` and the Page tasks
`CREATE_CONTENT`, `MESSAGING`, and `MODERATE`. Partial consent fails closed and
does not create a green connection.

## 4. Reviewer justification text

### Page discovery and reading

> Havi is a social operations application for businesses. We use
> `pages_show_list` and `pages_read_engagement` during Facebook Login to identify
> the Facebook Page the authenticated person is authorized to operate, show the
> connected Page name, and obtain the Page access token required for the Page
> operations demonstrated in this submission.

### Approved publishing

> Havi uses `pages_manage_posts` only to publish Facebook Page posts, photos, or
> Reels that a human has reviewed and explicitly approved. AI-generated content
> remains a draft. Nothing is sent to Meta until the user selects “Duyệt & đăng
> ngay” or approves a scheduled publishing time. Havi does not create or manage
> advertising campaigns.

### Comments

> Havi uses `pages_read_user_content` to receive user-authored comments on the
> connected Page through Meta's `feed` webhook. It uses
> `pages_manage_engagement` only after a Havi user explicitly submits a public
> reply. Havi replies to the original comment ID and does not convert a public
> comment into an unsolicited private message.

### Messenger and webhooks

> Havi uses `pages_manage_metadata` to subscribe the selected Page to the
> `messages` and `feed` webhook fields. It uses `pages_messaging` to display
> messages sent to that Page in Havi's shared inbox and to send a reply only
> after a Havi user explicitly submits it. Replies respect Meta's Messenger
> policy and messaging window.

## 5. Screencast script

Record the browser address bar and all clicks. Do not edit out the OAuth dialog
or Facebook-side verification.

1. Open `https://<web-domain>/login` and sign in with the reviewer account.
2. Open **Kênh kết nối**, choose Facebook, and click **Kết nối**.
3. Complete the official Meta permission flow. Show the connected Page name and
   **Đã kết nối** state in Havi.
4. Open **Tạo nội dung**, choose **Bài viết** and **Trang Facebook**, upload one
   test image, enter a short brief, and create the draft.
5. Review the draft and click **Duyệt & đăng ngay**. Wait for Havi to report the
   provider-confirmed state; do not present queue acceptance as publication.
6. Open the test Facebook Page and show the matching post and image.
7. From a second Facebook account, send a Messenger message to the Page. Show it
   in Havi's inbox, submit a reply, and show the same reply in Messenger.
8. Add a public comment to the test post. Show the comment in Havi, submit a
   public reply, and show it beneath the original comment on Facebook.

If Meta asks for a separate recording per permission, split steps 2–3, 4–6,
7, and 8 into focused videos rather than submitting one ambiguous recording.

## 6. Safe environment preflight

Do not mix the local test gate with the public pilot gate. First, run the local
gate while developing; localhost URLs and a missing public webhook are valid at
this stage:

```bash
cd apps/backend
.venv/bin/python scripts/facebook_preflight.py
```

After the full local test suite passes and immediately before deploying the
closed pilot, run the stricter public-environment gate explicitly:

```bash
.venv/bin/python scripts/facebook_preflight.py --mode pilot
```

Both commands are offline and print no credential values. All required
`--mode pilot` checks must pass before opening OAuth on the dedicated test Page.

- `HAVI_ENV=staging` for the closed pilot; never `local` on a public host.
- `HAVI_USE_FAKE_PUBLISHER=false`
- `HAVI_FACEBOOK_CLIENT_ID`
- `HAVI_FACEBOOK_CLIENT_SECRET`
- `HAVI_FACEBOOK_REDIRECT_URI=https://<api-domain>/connections/facebook/callback`
- `HAVI_FACEBOOK_CONFIG_ID` when using Login for Business
- `HAVI_META_WEBHOOK_VERIFY_TOKEN`
- a non-default `HAVI_TOKEN_ENCRYPTION_KEY`
- `HAVI_MEDIA_PUBLIC_URL` is HTTPS and fetchable from outside the private network
- the web origin is present in `HAVI_CORS_ORIGINS`

## 7. Test matrix before a real Page

- [ ] Privacy, terms, and data deletion pages load without authentication.
- [ ] A valid Meta-signed deletion request removes every Facebook connection
      granted by that app-scoped user; missing/invalid signatures remove nothing.
- [ ] Meta verifies `GET /webhooks/meta` with the configured verify token.
- [ ] A bad webhook signature returns 403 and creates no inbox item.
- [ ] OAuth cancellation or one declined permission creates no connection.
- [ ] A connected Page has `CREATE_CONTENT`, `MESSAGING`, and `MODERATE` tasks.
- [ ] The Page is subscribed to `messages,feed` after OAuth.
- [ ] Text-only Page post publishes once and stores the Facebook post ID.
- [ ] One-photo Page post publishes once and stores the post ID, not the photo ID.
- [ ] Reel completes Meta's start/upload/finish flow and is verified before success.
- [ ] Duplicate webhook delivery creates only one inbox item.
- [ ] A Messenger echo from the Page is ignored.
- [ ] Messenger reply works inside Meta's allowed messaging window.
- [ ] Public comment reply uses `/{comment-id}/comments`.
- [ ] A 2xx publish response without an object ID is not retried automatically.
- [ ] Token/permission error marks the channel for reconnection.
- [ ] Full backend, web, accessibility, and visual suites pass on a fresh server.
- [ ] Reviewer credentials and screencasts are supplied only in Meta's review form.

Only check an item after observing it in the target environment. Repository tests
cover request construction and failure handling, but they do not replace the
Meta-side dry run on the dedicated Page.
