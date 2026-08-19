import Link from "next/link";
import { Logo } from "@/components/ui/logo";
import { CONTACT_EMAIL, LAST_UPDATED, type Section } from "./legal.content";
import styles from "./legal.module.css";

type Props = {
  title: string;
  intro: string;
  sections: Section[];
};

export function LegalPage({ title, intro, sections }: Props) {
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <Link href="/" className={styles.brand}>
            <Logo size={34} />
            <span className={styles.brandText}>Havi</span>
          </Link>
          <Link href="/" className={styles.backLink}>
            ← Về trang chủ
          </Link>
        </div>
      </header>

      <main className={styles.main}>
        <h1 className={styles.title}>{title}</h1>
        <p className={styles.updated}>Cập nhật lần cuối: {LAST_UPDATED}</p>
        <p className={styles.intro}>{intro}</p>

        {sections.map((section) => (
          <section key={section.heading} className={styles.section}>
            <h2 className={styles.heading}>{section.heading}</h2>
            {section.paragraphs.map((text) => (
              <p key={text} className={styles.paragraph}>
                {text}
              </p>
            ))}
          </section>
        ))}

        <section className={styles.section}>
          <h2 className={styles.heading}>Liên hệ</h2>
          <p className={styles.paragraph}>
            Có câu hỏi về dữ liệu của bạn, hoặc muốn xoá tài khoản? Gửi email
            tới{" "}
            <a href={`mailto:${CONTACT_EMAIL}`} className={styles.link}>
              {CONTACT_EMAIL}
            </a>
            .
          </p>
        </section>

        <nav className={styles.crossLinks} aria-label="Trang pháp lý khác">
          <Link href="/about">Về Havi</Link>
          <Link href="/terms">Điều khoản sử dụng</Link>
          <Link href="/privacy">Chính sách bảo mật</Link>
          <Link href="/data-deletion">Hướng dẫn xóa dữ liệu</Link>
        </nav>
      </main>
    </div>
  );
}
