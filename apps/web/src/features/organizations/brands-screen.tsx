"use client";

/**
 * Thương hiệu & chi nhánh — mở thêm không gian làm việc trong cùng doanh nghiệp.
 *
 * Mỗi thương hiệu là một workspace hoàn chỉnh và **tách biệt hoàn toàn**: kênh
 * riêng, nội dung riêng, kho media riêng, thành viên riêng. Màn này nói rõ điều
 * đó, vì kỳ vọng sai ở đây rất đắt — một người tưởng dữ liệu dùng chung sẽ soạn
 * nội dung ở nhầm chi nhánh rồi mới phát hiện lúc bài đã lên.
 */

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ErrorState, LoadingState } from "@/components/ui/state-views";
import { PERMISSIONS, usePermissions } from "@/lib/auth/use-permissions";
import {
  createBrand,
  listOrganizations,
  type Industry,
  type OrganizationWithBrands,
} from "./organizations.api";
import styles from "./organizations.module.css";

/** Khớp `Industry` ở backend — nhãn tiếng Việt, giá trị là enum thật. */
const INDUSTRIES: Array<{ value: Industry; label: string }> = [
  { value: "spa", label: "Spa / Làm đẹp" },
  { value: "food_beverage", label: "Ăn uống / Cà phê" },
  { value: "retail_shop", label: "Cửa hàng bán lẻ" },
  { value: "online_shop", label: "Bán hàng online" },
  { value: "education", label: "Giáo dục / Đào tạo" },
  { value: "local_service", label: "Dịch vụ tại chỗ" },
  { value: "real_estate", label: "Bất động sản" },
  { value: "professional", label: "Dịch vụ chuyên môn" },
  { value: "other", label: "Khác" },
];

export function BrandsScreen() {
  const { can } = usePermissions();
  // Mở thương hiệu mới là quyền cấp tổ chức, nhưng ở đây dùng chung cổng với
  // quản trị thành viên: cả hai đều là việc của người đứng đầu.
  const mayManage = can(PERMISSIONS.manageMembers);

  const [orgs, setOrgs] = useState<OrganizationWithBrands[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [industry, setIndustry] = useState<Industry>("spa");
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    const result = await listOrganizations();
    if (result.ok) {
      setOrgs(result.data);
      setError(null);
    } else {
      setError(result.message);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function onCreate(organizationId: string) {
    if (!name.trim()) return;
    setCreating(true);
    const result = await createBrand(organizationId, { name: name.trim(), industry });
    setCreating(false);

    if (!result.ok) {
      setError(result.message);
      return;
    }
    setError(null);
    setName("");
    setNotice(
      `Đã mở "${result.data.name}". Đổi sang thương hiệu đó ở góc trên bên trái để bắt đầu.`,
    );
    load();
  }

  if (loading) return <LoadingState title="Đang tải danh sách thương hiệu…" />;

  return (
    <>
      <header className={styles.header}>
        <h1 className={styles.title}>Thương hiệu &amp; chi nhánh</h1>
        <p className={styles.subtitle}>
          Mỗi thương hiệu là một không gian làm việc riêng biệt: kênh, nội dung,
          kho media và thành viên đều tách rời. Dữ liệu không dùng chung giữa các
          thương hiệu.
        </p>
      </header>

      {error ? <ErrorState title={error} /> : null}
      {notice ? (
        <p className={styles.notice} role="status">
          {notice}
        </p>
      ) : null}

      {orgs.map((entry) => (
        <section key={entry.organization.id} className={styles.orgCard}>
          <h2 className={styles.orgName}>{entry.organization.name}</h2>

          <ul className={styles.brandList}>
            {entry.brands.map((brand) => (
              <li key={brand.id} className={styles.brandRow}>
                <span className={styles.brandName}>{brand.name}</span>
                <span className={styles.brandIndustry}>
                  {INDUSTRIES.find((i) => i.value === brand.industry)?.label ?? brand.industry}
                </span>
              </li>
            ))}
          </ul>

          {mayManage ? (
            <div className={styles.createRow}>
              <Input
                value={name}
                placeholder="Tên chi nhánh mới, ví dụ: An Nhiên Quận 7"
                aria-label="Tên thương hiệu mới"
                onChange={(event) => setName(event.target.value)}
              />
              <select
                className={styles.industrySelect}
                value={industry}
                aria-label="Ngành"
                onChange={(event) => setIndustry(event.target.value as Industry)}
              >
                {INDUSTRIES.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
              <Button
                variant="primary"
                onClick={() => onCreate(entry.organization.id)}
                disabled={creating || !name.trim()}
              >
                {creating ? "Đang mở…" : "Mở thương hiệu"}
              </Button>
            </div>
          ) : (
            <p className={styles.blocked}>
              Chỉ chủ tổ chức mở được thương hiệu mới.
            </p>
          )}
        </section>
      ))}
    </>
  );
}
