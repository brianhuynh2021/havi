# Facebook App Review Submission Package & Guide

> **Document purpose:** Complete step-by-step guide and submission texts for Meta App Review when submitting Havi for live production Graph API access (`pages_show_list`, `pages_read_engagement`, `pages_manage_posts`).

---

## 1. Prerequisites & App Dashboard Setup

Before clicking **Submit for Review** in the Meta Developer Dashboard:

### 1.1 App Settings -> Basic
* **Display Name:** `Havi — AI Marketing Employee`
* **App Icon:** 1024x1024 PNG logo.
* **Category:** `Business and Pages`
* **Privacy Policy URL:** `https://<your-domain>/bao-mat`
* **Terms of Service URL:** `https://<your-domain>/dieu-khoan`
* **User Data Deletion:**
  * Select **Data Deletion Instructions URL**: `https://<your-domain>/huong-dan-xoa-du-lieu`
  * Or **Data Deletion Request Callback**: `https://api.<your-domain>/connections/facebook/data-deletion`

### 1.2 Facebook Login for Business / Products Setup
* **Valid OAuth Redirect URIs:** `https://api.<your-domain>/connections/facebook/callback`
* **Enforce HTTPS:** `Yes`

---

## 2. Permission Request Details

Havi requests three permissions for the closed-loop publishing workflow:

| Permission | Purpose in Havi | Meta Scope Name |
|---|---|---|
| **`pages_show_list`** | Display list of Facebook Pages managed by the small business owner so they can select which Page to connect. | `pages_show_list` |
| **`pages_read_engagement`** | Read Page ID, name, and access token required to perform Page-level publishing operations. | `pages_read_engagement` |
| **`pages_manage_posts`** | Publish owner-approved social posts directly to the connected Facebook Page. | `pages_manage_posts` |

---

## 3. Copy-Paste Justification Statements for Meta Reviewers

### Permission 1: `pages_show_list`
> **How is your app using this permission?**
> Havi is an AI marketing assistant designed for small businesses (e.g., spas, cafes, restaurants). When a shop owner connects their Facebook account via OAuth, Havi uses `pages_show_list` to show a selection list of the Facebook Pages they manage. The owner selects which specific Page they want Havi to publish approved content to.
>
> **English Version for Reviewer:**
> Havi is an AI marketing platform for small-business owners. We request `pages_show_list` to list the Facebook Pages managed by the authenticated user during the onboarding and connection process. This allows the user to choose which specific Page Havi should connect to for publishing their approved marketing posts.

---

### Permission 2: `pages_read_engagement`
> **How is your app using this permission?**
> Havi requires `pages_read_engagement` to retrieve the Page metadata (Page name, ID) and the Page Access Token associated with the Facebook Page chosen by the shop owner. This token is securely encrypted server-side using AES-128 Fernet encryption and is strictly used to publish content that the owner explicitly approves in the Havi dashboard.
>
> **English Version for Reviewer:**
> We request `pages_read_engagement` to read the metadata and Page access token for the user's selected Facebook Page. This access token is required to execute Graph API publishing endpoints when the user clicks 'Approve' or schedules a post inside our web application.

---

### Permission 3: `pages_manage_posts`
> **How is your app using this permission?**
> Havi uses `pages_manage_posts` to publish approved promotional posts (text + photos) to the connected Facebook Page. Content is NEVER published automatically without explicit user approval. All generated drafts remain in 'Pending Approval' until the shop owner verifies the copy and clicks 'Approve & Publish' or schedules a publishing time slot.
>
> **English Version for Reviewer:**
> Havi uses `pages_manage_posts` to post approved marketing updates and photo content directly to the user's Facebook Page. Our application operates strictly under an approval-first model (`review_first`): content is generated as a draft, reviewed by the shop owner, and only sent to the Meta Graph API `/feed` or `/photos` endpoints upon explicit user confirmation or scheduled execution.

---

## 4. Screencast Video Recording Script (2 Minutes)

Meta requires a clear video screencast demonstrating the complete flow. Follow this step-by-step script:

### Step 1: Login & Navigation (0:00 - 0:20)
1. Show the Havi Login screen at `https://<your-domain>/dang-nhap`.
2. Log in with a test account. Show the main Havi Dashboard.

### Step 2: Facebook Page OAuth Connection (0:20 - 0:50)
1. Navigate to **Cài đặt** (Settings) -> **Kênh liên kết** (Connected Channels).
2. Click **Kết nối Facebook** (Connect Facebook).
3. Show the official Facebook OAuth dialog opening.
4. Log in with the test Facebook account (managing a test Facebook Page).
5. Select the test Page and grant permissions (`pages_show_list`, `pages_read_engagement`, `pages_manage_posts`).
6. Redirect back to Havi and show the green **Đã kết nối** (Connected) status badge displaying the Page name.

### Step 3: Raw Input to Draft Generation (0:50 - 1:15)
1. Navigate to **Tạo bài** (Create Content).
2. Upload a sample product photo and type a short note (e.g., *"Khuyến mãi làm đẹp cuối tuần giảm 20%"*).
3. Click **Tạo bài nháp** (Generate Draft). Show the draft loading state.
4. Display the generated draft card tagged with **Trang Facebook**.

### Step 4: Owner Approval & Publishing (1:15 - 1:45)
1. Show the draft card in **Chờ duyệt** (Pending Approval).
2. Click **⚡ Đăng ngay** (Publish Now) or **Duyệt bài** (Approve).
3. Show the success notification toast: *"Đã đăng bài thành công lên Trang Facebook"*.

### Step 5: Verification on Facebook (1:45 - 2:00)
1. Switch to a new browser tab showing the test Facebook Page.
2. Refresh the Facebook Page feed.
3. Show the newly published post with text and photo matching what was approved in Havi.

---

## 5. Test Credentials & Verification Checklist

When submitting:
* **Test Account Email:** `tester@havi.vn` (or provided Meta test user)
* **Test Account Password:** `ProvidedInReviewNotes`
* **Test Facebook Page:** `Spa An Nhiên Test`

### Submission Pre-Check:
- [x] Privacy Policy URL is live and accessible (`/bao-mat`).
- [x] Data Deletion Instructions URL is live and accessible (`/huong-dan-xoa-du-lieu`).
- [x] Data Deletion Callback URL endpoint is live (`/connections/facebook/data-deletion`).
- [x] HTTPS is enforced on backend callback redirect URIs.
- [x] Screencast video MP4/MOV uploaded (showing entire flow from OAuth connect to published post).
- [x] Test account credentials populated in Meta Review submission form notes.
