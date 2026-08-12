from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.audit import EventLog
from domain.models.content import ContentItem
from domain.models.user import User
from domain.models.workspace import BrandProfile, Workspace, WorkspaceMember


@pytest.mark.asyncio
async def test_workspace_deletion_cascade_and_anonymization(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    # 1. Sign up user
    signup_res = await client.post(
        "/auth/sign-up",
        json={"name": "Owner User", "email": "owner_del@example.com", "password": "password123"},
    )
    assert signup_res.status_code == 201, signup_res.text
    signup_token = signup_res.json()

    # 2. Create workspace
    ws_res = await client.post(
        "/workspaces",
        json={"name": "Tiệm Spa Deletion Test", "industry": "spa"},
        headers={"Authorization": f"Bearer {signup_token['access_token']}"},
    )
    assert ws_res.status_code == 201, ws_res.text
    ws_id = ws_res.json()["id"]
    ws_uuid = UUID(ws_id)

    # Refresh token to get active_workspace_id in JWT
    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": signup_token["refresh_token"]}
    )
    assert refreshed.status_code == 200, refreshed.text
    active_headers = {"Authorization": f"Bearer {refreshed.json()['access_token']}"}

    # Update brand profile to create data
    bp_res = await client.put(
        "/brand-profile",
        json={
            "tone": "Thân thiện",
            "banned_claims": ["chữa dứt điểm"],
            "faq": [],
            "brand_colors": [],
        },
        headers=active_headers,
    )
    assert bp_res.status_code == 200, bp_res.text

    # Change publish mode (triggers consent event)
    patch_res = await client.patch(
        f"/workspaces/{ws_id}",
        json={"publish_mode": "full_auto"},
        headers=active_headers,
    )
    assert patch_res.status_code == 200, patch_res.text

    # Create content job
    job_res = await client.post(
        "/content/jobs",
        json={
            "raw_inputs": [{"kind": "text", "text": "Mẫu nail mới"}],
            "idempotency_key": str(uuid4()),
        },
        headers=active_headers,
    )
    assert job_res.status_code == 202, job_res.text

    # Verify brand profile row exists in DB
    bp_stmt = select(BrandProfile).where(BrandProfile.workspace_id == ws_uuid)
    profile = (await db_session.execute(bp_stmt)).scalar_one_or_none()
    assert profile is not None

    # 3. Delete workspace
    del_res = await client.delete(f"/workspaces/{ws_id}", headers=active_headers)
    assert del_res.status_code == 204, del_res.text

    # 4. Verify workspace and cascade entities are deleted
    ws_stmt = select(Workspace).where(Workspace.id == ws_uuid)
    ws_db = (await db_session.execute(ws_stmt)).scalar_one_or_none()
    assert ws_db is None

    profile_db = (await db_session.execute(bp_stmt)).scalar_one_or_none()
    assert profile_db is None

    item_stmt = select(ContentItem).where(ContentItem.workspace_id == ws_uuid)
    items_db = (await db_session.execute(item_stmt)).scalars().all()
    assert len(items_db) == 0

    member_stmt = select(WorkspaceMember).where(WorkspaceMember.workspace_id == ws_uuid)
    members_db = (await db_session.execute(member_stmt)).scalars().all()
    assert len(members_db) == 0

    # 5. Verify event logs are anonymized
    log_stmt = select(EventLog).where(EventLog.job_kind == "consent.publish_mode_changed")
    logs = (await db_session.execute(log_stmt)).scalars().all()
    assert len(logs) > 0
    for log in logs:
        assert log.workspace_id is None
        assert log.input_summary == "[redacted]"


@pytest.mark.asyncio
async def test_non_owner_cannot_delete_workspace(client: AsyncClient) -> None:
    # 1. Owner creates workspace
    owner_signup = await client.post(
        "/auth/sign-up",
        json={"name": "Owner", "email": "owner_non_owner@example.com", "password": "password123"},
    )
    assert owner_signup.status_code == 201, owner_signup.text
    owner_token = owner_signup.json()
    owner_headers = {"Authorization": f"Bearer {owner_token['access_token']}"}

    ws_res = await client.post(
        "/workspaces",
        json={"name": "Tiệm Multi-Member", "industry": "food_beverage"},
        headers=owner_headers,
    )
    assert ws_res.status_code == 201, ws_res.text
    ws_id = ws_res.json()["id"]

    # 2. Member signs up and gets invited
    member_signup = await client.post(
        "/auth/sign-up",
        json={"name": "Staff Member", "email": "staff_del@example.com", "password": "password123"},
    )
    assert member_signup.status_code == 201, member_signup.text
    member_token = member_signup.json()

    invite_res = await client.post(
        f"/workspaces/{ws_id}/members",
        json={"email": "staff_del@example.com", "role": "marketer"},
        headers=owner_headers,
    )
    assert invite_res.status_code == 201, invite_res.text

    member_auth_hdr = {"Authorization": f"Bearer {member_token['access_token']}"}
    member_activate = await client.post(
        f"/workspaces/{ws_id}/activate",
        headers=member_auth_hdr,
    )
    assert member_activate.status_code == 200, member_activate.text
    member_active_headers = {"Authorization": f"Bearer {member_activate.json()['access_token']}"}

    # 3. Marketer attempts to delete workspace -> 403 Forbidden
    del_res = await client.delete(f"/workspaces/{ws_id}", headers=member_active_headers)
    assert del_res.status_code == 403, del_res.text


@pytest.mark.asyncio
async def test_user_account_deletion_sole_owner(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    signup_res = await client.post(
        "/auth/sign-up",
        json={
            "name": "Single User",
            "email": "single_owner@example.com",
            "password": "password123",
        },
    )
    assert signup_res.status_code == 201, signup_res.text
    signup_token = signup_res.json()
    headers = {"Authorization": f"Bearer {signup_token['access_token']}"}

    ws_res = await client.post(
        "/workspaces",
        json={"name": "Tiệm Của Tôi", "industry": "online_shop"},
        headers=headers,
    )
    assert ws_res.status_code == 201, ws_res.text
    ws_id = ws_res.json()["id"]
    ws_uuid = UUID(ws_id)

    # Delete user account
    del_me_res = await client.delete("/auth/me", headers=headers)
    assert del_me_res.status_code == 204, del_me_res.text

    # User and sole workspace are both deleted
    user_stmt = select(User).where(User.email == "single_owner@example.com")
    user_db = (await db_session.execute(user_stmt)).scalar_one_or_none()
    assert user_db is None

    ws_stmt = select(Workspace).where(Workspace.id == ws_uuid)
    ws_db = (await db_session.execute(ws_stmt)).scalar_one_or_none()
    assert ws_db is None
