"use client";

/**
 * Đội ngũ — ai đang ở trong workspace và mỗi người làm được gì.
 *
 * Vai trò hiện bằng **việc người đó làm được**, không bằng tên chức danh: "Người
 * duyệt — duyệt nội dung để Havi đăng lên kênh" nói rõ hơn "reviewer" với người
 * đang phải chọn vai cho nhân viên mới.
 */

import { useLanguage } from "@/lib/i18n/language-context";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state-views";
import {
  ROLE_LABELS,
  inviteMember,
  listMembers,
  resendInvite,
  updateMemberRole,
  removeMember,
  type WorkspaceMember,
  type WorkspaceRole,
} from "./team.api";
import { DangerConfirmModal } from "@/features/settings/danger-confirm-modal";
import styles from "./team.module.css";

const INVITABLE_ROLES: WorkspaceRole[] = ["marketer", "reviewer", "sales"];

export function TeamScreen() {
  const {
    t
  } = useLanguage();

  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [email, setEmail] = useState("");
  const [role, setRole] = useState<WorkspaceRole>("marketer");
  const [inviting, setInviting] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [removingMember, setRemovingMember] = useState<WorkspaceMember | null>(null);

  const load = useCallback(async () => {
    const result = await listMembers();
    if (result.ok) {
      setMembers(result.data);
      setError(null);
    } else {
      setError(result.message);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function onInvite() {
    if (!email.trim()) return;
    setInviting(true);
    const result = await inviteMember(email.trim(), role);
    setInviting(false);

    if (!result.ok) {
      setError(result.message);
      return;
    }
    setError(null);
    setEmail("");
    setNotice(`Đã thêm ${result.data.name} vào workspace.`);
    load();
  }

  function onRemoveRequested(member: WorkspaceMember) {
    setRemovingMember(member);
  }

  async function onRemove() {
    if (!removingMember) return;
    const member = removingMember;
    setRemovingMember(null);
    setBusyId(member.user_id);
    const result = await removeMember(member.user_id);
    setBusyId(null);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    setError(null);
    setNotice(`Đã gỡ ${member.name}.`);
    load();
  }

  async function onChangeRole(member: WorkspaceMember, newRole: WorkspaceRole) {
    if (member.role === newRole) return;
    setBusyId(member.user_id);
    const result = await updateMemberRole(member.user_id, newRole);
    setBusyId(null);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    setError(null);
    setNotice(`Đã đổi vai trò của ${member.name} thành ${ROLE_LABELS[newRole]?.name ?? newRole}.`);
    load();
  }

  async function onResendInvite(member: WorkspaceMember) {
    setBusyId(member.user_id);
    const result = await resendInvite(member.user_id);
    setBusyId(null);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    setError(null);
    setNotice(`Đã gửi lại lời mời cho ${member.name}.`);
  }

  return (
    <>
      <header className={styles.header}>
        <h1 className={styles.title}>{t("Đội ngũ")}</h1>
        <p className={styles.subtitle}>{t(
          "Ai đang ở trong workspace và mỗi người làm được gì. Người soạn và người\n          duyệt nên là hai người khác nhau — đó là điểm khiến bước duyệt có nghĩa."
        )}</p>
      </header>

      {error ? <ErrorState title={error} /> : null}
      {notice ? (
        <p className={styles.notice} role="status">
          {notice}
        </p>
      ) : null}

      {/* Tổ chức nhiều thương hiệu: mỗi thương hiệu có danh sách thành viên
          riêng, nên phải nói rõ màn này chỉ quản trị thương hiệu đang mở. */}
      <p className={styles.scopeNote}>{t(
        "Danh sách này thuộc về thương hiệu đang mở. Mỗi thương hiệu có đội ngũ\n        riêng — xem và mở thêm thương hiệu ở"
      )}{" "}
        <Link href="/app/brands">{t("Thương hiệu & chi nhánh")}</Link>.
      </p>

      <section className={styles.inviteCard} aria-labelledby="invite-title">
        <h2 id="invite-title" className={styles.sectionTitle}>{t("Thêm thành viên")}</h2>
        <p className={styles.inviteHint}>{t(
          "Người được mời phải có tài khoản Havi trước. Havi không tự tạo tài khoản\n          hộ ai."
        )}</p>
        <div className={styles.inviteRow}>
          <Input
            type="email"
            value={email}
            placeholder="email@congty.vn"
            aria-label={t("Email người muốn thêm")}
            onChange={(event) => setEmail(event.target.value)}
          />
          <select
            className={styles.roleSelect}
            value={role}
            aria-label={t("Vai trò")}
            onChange={(event) => setRole(event.target.value as WorkspaceRole)}
          >
            {INVITABLE_ROLES.map((value) => (
              <option key={value} value={value}>
                {ROLE_LABELS[value]?.name ?? value}
              </option>
            ))}
          </select>
          <Button variant="primary" onClick={onInvite} disabled={inviting || !email.trim()}>
            {inviting ? "Đang thêm…" : "Thêm"}
          </Button>
        </div>
        <p className={styles.roleHint}>{ROLE_LABELS[role]?.can}</p>
      </section>

      <section aria-labelledby="members-title">
        <h2 id="members-title" className={styles.sectionTitle}>{t("Thành viên hiện tại")}</h2>

        {loading ? (
          <LoadingState title={t("Đang tải danh sách…")} />
        ) : members.length === 0 ? (
          <EmptyState title={t("Chưa có thành viên nào")} body={t("Thêm người vào workspace ở trên.")} />
        ) : (
          <ul className={styles.memberList}>
            {members.map((member) => {
              const info = ROLE_LABELS[member.role];
              const isOwner = member.role === "owner";
              return (
                <li key={member.user_id} className={styles.memberRow}>
                  <div className={styles.memberMain}>
                    <strong className={styles.memberName}>{member.name}</strong>
                    {isOwner ? (
                      <span className={styles.roleTag}>{info?.name ?? member.role}</span>
                    ) : (
                      <select
                        className={styles.roleSelectInline}
                        value={member.role}
                        onChange={(e) => onChangeRole(member, e.target.value as WorkspaceRole)}
                        disabled={busyId === member.user_id}
                        aria-label={t("Đổi vai trò")}
                      >
                        {INVITABLE_ROLES.map((value) => (
                          <option key={value} value={value}>
                            {ROLE_LABELS[value]?.name ?? value}
                          </option>
                        ))}
                      </select>
                    )}
                    <p className={styles.roleCan}>{info?.can}</p>
                  </div>
                  {/* Chủ workspace không gỡ được: gỡ hết chủ là workspace không
                      còn ai mời lại được ai. */}
                  {isOwner ? null : (
                    <div className={styles.memberActions}>
                      <Button
                        variant="outline"
                        onClick={() => onResendInvite(member)}
                        disabled={busyId === member.user_id}
                      >{t("Gửi lại")}</Button>
                      <Button
                        variant="outline"
                        onClick={() => onRemoveRequested(member)}
                        disabled={busyId === member.user_id}
                      >{t("Gỡ")}</Button>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <DangerConfirmModal
        isOpen={removingMember !== null}
        type="custom"
        isDeleting={busyId === removingMember?.user_id}
        customKeyword="GOTHANHVIEN"
        customTitle={`Xác nhận gỡ ${removingMember?.name || "thành viên"}`}
        customLostItems={[
          `${removingMember?.name || "Người này"} sẽ bị mất quyền truy cập vào workspace này ngay lập tức.`,
          "Bạn sẽ phải mời lại từ đầu nếu đổi ý.",
        ]}
        onClose={() => setRemovingMember(null)}
        onConfirm={onRemove}
      />
    </>
  );
}
