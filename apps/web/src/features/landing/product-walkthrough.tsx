"use client";

/**
 * Demo sản phẩm tự chạy — dựng bằng DOM thật, không phải file video.
 *
 * Vì sao không dùng video: một file MP4 60 giây nặng vài MB, mờ trên màn hình
 * lớn, bị chặn autoplay trên nhiều trình duyệt, và **lỗi thời ngay khi UI đổi**.
 * Dựng bằng DOM thì nét ở mọi độ phân giải, hiện tức thì, và khi giao diện thật
 * đổi thì đây là thứ đổi theo — thay vì một đoạn phim quay từ phiên bản cũ.
 *
 * Nội dung là **đúng luồng thật** của sản phẩm, không phải hoạt cảnh:
 *
 *     kể cho Havi → Havi soạn nháp → bạn duyệt & rải lịch → đọc lại Trang xác nhận
 *
 * Cảnh cuối là điểm khác biệt thật sự và không đối thủ nào demo: Havi **đọc lại
 * nền tảng** trước khi dám nói "đã đăng". Đó là lý do nó được dành nguyên một
 * cảnh, thay vì một dòng chữ nhỏ.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import styles from "./product-walkthrough.module.css";

type Scene = {
  id: string;
  label: string;
  caption: string;
};

const SCENES: Scene[] = [
  {
    id: "brief",
    label: "Kể cho Havi",
    caption: "Một tấm ảnh và vài dòng. Không cần biết viết prompt.",
  },
  {
    id: "draft",
    label: "Havi soạn nháp",
    caption: "Bản nháp nằm ở hàng chờ — chưa có gì lên Trang.",
  },
  {
    id: "schedule",
    label: "Bạn duyệt & rải lịch",
    caption: "Chuẩn bị cả tuần một lần, Havi đăng mỗi ngày một bài.",
  },
  {
    id: "verified",
    label: "Đọc lại Trang để xác nhận",
    caption: "Havi chỉ báo “đã đăng” sau khi thấy bài có thật trên Trang.",
  },
];

/** Mỗi cảnh dừng bao lâu. Cảnh cuối lâu hơn: đó là điểm cần đọng lại. */
const SCENE_MS = [4200, 4200, 5200, 6000];

export function ProductWalkthrough() {
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const goTo = useCallback((index: number) => {
    setActive(((index % SCENES.length) + SCENES.length) % SCENES.length);
  }, []);

  useEffect(() => {
    // Người dùng đã tắt hiệu ứng chuyển động thì không tự chạy: một khung tự
    // đổi cảnh là thứ gây khó chịu nhất với người nhạy cảm tiền đình.
    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduced || paused) return;

    timer.current = setTimeout(() => goTo(active + 1), SCENE_MS[active]);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [active, paused, goTo]);

  return (
    <figure
      className={styles.frame}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocusCapture={() => setPaused(true)}
      onBlurCapture={() => setPaused(false)}
    >
      {/* Khung trình duyệt: nói ngay đây là sản phẩm chạy trên web, không phải
          một hình minh hoạ. */}
      <div className={styles.chrome} aria-hidden="true">
        <span className={styles.dot} />
        <span className={styles.dot} />
        <span className={styles.dot} />
        <span className={styles.addressBar}>havi.vn/app</span>
      </div>

      <div className={styles.stage}>
        {/* Mỗi cảnh luôn nằm trong DOM và chỉ đổi opacity/transform: gắn rồi gỡ
            liên tục làm khung nhảy chiều cao mỗi lần chuyển. */}
        <Scene1 active={active === 0} />
        <Scene2 active={active === 1} />
        <Scene3 active={active === 2} />
        <Scene4 active={active === 3} />
      </div>

      <figcaption className={styles.caption}>
        <p className={styles.captionText} aria-live="polite">
          {SCENES[active].caption}
        </p>

        <div className={styles.steps} role="tablist" aria-label="Các bước trong luồng">
          {SCENES.map((scene, index) => (
            <button
              key={scene.id}
              type="button"
              role="tab"
              aria-selected={index === active}
              className={`${styles.step} ${index === active ? styles.stepActive : ""}`}
              onClick={() => goTo(index)}
            >
              <span className={styles.stepNum}>{index + 1}</span>
              <span className={styles.stepLabel}>{scene.label}</span>
              {/* Thanh tiến trình chỉ chạy ở bước đang mở, và dừng khi rê chuột
                  — người đang đọc không bị cảnh nhảy mất. */}
              {index === active && !paused ? (
                <span
                  className={styles.stepProgress}
                  style={{ animationDuration: `${SCENE_MS[index]}ms` }}
                />
              ) : null}
            </button>
          ))}
        </div>
      </figcaption>
    </figure>
  );
}

/* --- Bốn cảnh -------------------------------------------------------------
   Dùng lại đúng ngôn ngữ giao diện của app thật: cùng cách gọi tên, cùng thứ
   tự, cùng những gì được nhấn mạnh. Một demo nói khác app là một lời hứa sai. */

function Scene1({ active }: { active: boolean }) {
  return (
    <div className={`${styles.scene} ${active ? styles.sceneActive : ""}`} aria-hidden={!active}>
      <p className={styles.sceneHint}>Mục Nội dung</p>
      <div className={styles.chipRow}>
        <span className={styles.chip}>
          <span aria-hidden="true">🖼️</span> anh-tiem-goc-trai.jpg
        </span>
        <span className={styles.chip}>
          <span aria-hidden="true">✍️</span> Tuần này giảm 20% gói gội đầu thảo dược
        </span>
      </div>
      <div className={styles.composeBox}>
        <span className={styles.caret} aria-hidden="true" />
      </div>
      <div className={styles.primaryAction}>Để Havi viết bài</div>
    </div>
  );
}

function Scene2({ active }: { active: boolean }) {
  return (
    <div className={`${styles.scene} ${active ? styles.sceneActive : ""}`} aria-hidden={!active}>
      <p className={styles.sceneHint}>1 bản nháp chờ bạn duyệt</p>
      <article className={styles.draftCard}>
        <span className={styles.channelTag}>
          <span aria-hidden="true">📘</span> Facebook Page
        </span>
        <p className={styles.draftText}>
          Cuối tuần này tiệm có ưu đãi gội đầu thảo dược giảm 20% cho khách quen.
          Chị em nhắn tin để giữ giờ trước nhé, tiệm mở tới 20h30.
        </p>
        <div className={styles.draftActions}>
          <span className={styles.ghostBtn}>Sửa</span>
          <span className={styles.ghostBtn}>Thêm ảnh minh hoạ</span>
        </div>
      </article>
      <p className={styles.assurance}>
        <span aria-hidden="true">🔒</span> Chưa có gì lên Trang. Havi không tự đăng.
      </p>
    </div>
  );
}

function Scene3({ active }: { active: boolean }) {
  const rows = [
    { when: "T4 27/08", time: "08:00", what: "Ưu đãi gội đầu thảo dược" },
    { when: "T5 28/08", time: "08:00", what: "Khách quen tuần này nói gì" },
    { when: "T6 29/08", time: "08:00", what: "Giới thiệu gói chăm da mới" },
  ];
  return (
    <div className={`${styles.scene} ${active ? styles.sceneActive : ""}`} aria-hidden={!active}>
      <p className={styles.sceneHint}>Rải nhiều ngày · 1 bài/ngày</p>
      <ol className={styles.scheduleList}>
        {rows.map((row, index) => (
          <li
            key={row.when}
            className={styles.scheduleRow}
            style={{ animationDelay: `${index * 180}ms` }}
          >
            <span className={styles.scheduleWhen}>
              <b>{row.when}</b> {row.time}
            </span>
            <span className={styles.scheduleWhat}>{row.what}</span>
          </li>
        ))}
      </ol>
      <p className={styles.assurance}>
        <span aria-hidden="true">📅</span> Kín nội dung tới T6 29/08. Đổi giờ bất
        cứ lúc nào trước khi bài lên.
      </p>
    </div>
  );
}

function Scene4({ active }: { active: boolean }) {
  return (
    <div className={`${styles.scene} ${active ? styles.sceneActive : ""}`} aria-hidden={!active}>
      <p className={styles.sceneHint}>Sau khi gửi lên Facebook</p>
      <ol className={styles.verifyList}>
        <li className={styles.verifyDone}>
          <span className={styles.verifyMark} aria-hidden="true">✓</span>
          Đã gửi bài sang Facebook
        </li>
        <li className={styles.verifyDone} style={{ animationDelay: "500ms" }}>
          <span className={styles.verifyMark} aria-hidden="true">✓</span>
          Đọc lại Trang để kiểm tra
        </li>
        <li className={styles.verifyFinal} style={{ animationDelay: "1100ms" }}>
          <span className={styles.verifyMarkFinal} aria-hidden="true">✓</span>
          <span>
            <b>Đã lên Trang</b>
            <em className={styles.verifyNote}>Xác nhận bằng dữ liệu Facebook trả về</em>
          </span>
        </li>
      </ol>
      <p className={styles.assuranceStrong}>
        Nhiều công cụ báo “đã đăng” ngay khi gửi đi. Havi đợi tới lúc nhìn thấy
        bài trên Trang mới dám nói vậy.
      </p>
    </div>
  );
}
