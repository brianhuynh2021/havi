"use client";

/**
 * Ngôn ngữ giao diện — một quy ước duy nhất: **khoá chính là câu tiếng Việt**.
 *
 * Vì sao đổi
 * ----------
 * Trước đây có ba cách cùng tồn tại, và chỉ hai cách chạy:
 *
 * - `t("nav.content")` — khoá có dấu chấm, tra trong từ điển. 29 chỗ dùng, và
 *   60 trong 99 khoá đã chết vì màn hình gọi chúng bị xoá từ lâu.
 * - `t({ vi: "…", en: "…" })` — object tại chỗ. 85 chỗ dùng, chạy đúng, nhưng
 *   bản dịch nằm rải trong JSX nên **không trích ra file được** — người dịch
 *   không phải lập trình viên, họ cần một file.
 * - `t("Trả lời khách")` — 446 chỗ dùng, và **không chạy**: từ điển không có
 *   khoá nào khớp nên `t()` trả lại đúng nguyên văn tiếng Việt.
 *
 * Nghĩa là bấm nút EN thì màn làm việc chính không đổi một chữ nào, trong khi
 * nút vẫn nằm đó hứa hẹn. Cách đông nhất (446) lại là cách không chạy.
 *
 * Nên giữ đúng cách đó và làm cho nó chạy: khoá là câu tiếng Việt, bản dịch nằm
 * trong `translations.ts`. Lập trình viên viết tiếng Việt như đang viết, người
 * dịch nhận một file, và `scripts/i18n-audit.mjs` đếm được chỗ nào còn thiếu.
 *
 * Hệ quả có chủ ý: một câu tiếng Việt chỉ có **một** bản tiếng Anh. Trước đây
 * "Lịch đăng" là `Schedule` ở nav và `Content Calendar` ở tiêu đề — cùng một
 * thứ, hai tên. Gộp lại là dọn, không phải mất mát.
 *
 * Thiếu bản dịch thì hiện tiếng Việt
 * ----------------------------------
 * Không hiện khoá thô, không hiện chuỗi rỗng. Một câu tiếng Việt lọt vào giao
 * diện tiếng Anh thì người đọc vẫn dùng được app và người sửa vẫn thấy ngay;
 * `MISSING_KEY` thì không được cái nào.
 */

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { ENGLISH_UI_ENABLED } from "./availability";
import { EN, type Language } from "./translations";

/** Giá trị chèn vào `{ô}` trong câu. Số cũng nhận, để chỗ gọi không phải `String()`. */
export type TextParams = Record<string, string | number>;

/**
 * Kiểu của `t`, để **truyền được vào hàm phụ** ngoài component.
 *
 * Các hàm định dạng (`formatWait`, `describeAsset`) nằm ở tầng module nên không
 * gọi hook được. Truyền `t` vào rõ hơn là để chúng tự đọc ngôn ngữ: hàm nhận gì
 * thì nhìn chữ ký là biết, và test gọi được nó mà không cần dựng Provider.
 */
export type Translate = (vietnamese: string, params?: TextParams) => string;

type LanguageContextType = {
  lang: Language;
  setLang: (lang: Language) => void;
  toggleLang: () => void;
  t: Translate;
};

const STORAGE_KEY = "havi_preferred_language";

/**
 * Chèn giá trị vào `{ô}`.
 *
 * Có mặt để câu **không bị chẻ**. Đoạn `{t("nối")} {days} {t("ngày")}` dịch sang
 * tiếng Anh sẽ sai trật tự từ, vì trật tự từ là chuyện của từng ngôn ngữ chứ
 * không phải của từng mảnh. Viết cả câu — `t("nối {days} ngày", { days })` — thì
 * người dịch được thấy trọn ngữ cảnh và tự đặt lại trật tự.
 *
 * Ô không có giá trị thì **để nguyên** `{tên}`: xoá nó đi là âm thầm làm câu mất
 * nghĩa, còn để lại thì lỗi lộ ra ngay trên màn hình.
 */
function interpolate(text: string, params?: TextParams): string {
  if (!params) return text;
  return text.replace(/\{(\w+)\}/g, (whole, name) =>
    name in params ? String(params[name]) : whole,
  );
}

export function translate(vietnamese: string, lang: Language, params?: TextParams): string {
  const text = lang === "EN" ? (EN[vietnamese] ?? vietnamese) : vietnamese;
  return interpolate(text, params);
}

function readSaved(): Language {
  if (!ENGLISH_UI_ENABLED) return "VN";
  if (typeof window === "undefined") return "VN";
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved === "EN" || saved === "VN" ? saved : "VN";
  } catch {
    // Chế độ riêng tư của Safari chặn localStorage. Mặc định tiếng Việt.
    return "VN";
  }
}

/**
 * Ngôn ngữ hiện tại, đọc thẳng từ localStorage.
 *
 * Dành cho chỗ **không gọi hook được**: các module `*.api.ts` dựng câu thông báo
 * lỗi rồi trả về cho màn hình hiện. Chúng chạy trong trình duyệt nên đọc được
 * đúng cái khoá mà `LanguageProvider` ghi.
 *
 * Không dùng trong component: giá trị này không kích hoạt render lại khi người
 * dùng đổi ngôn ngữ, nên nó chỉ đúng cho chuỗi dựng một lần tại thời điểm gọi.
 */
export function translateNow(vietnamese: string, params?: TextParams): string {
  return translate(vietnamese, readSaved(), params);
}

const defaultValue: LanguageContextType = {
  lang: "VN",
  setLang: () => {},
  toggleLang: () => {},
  t: (vietnamese, params) => translate(vietnamese, "VN", params),
};

const LanguageContext = createContext<LanguageContextType>(defaultValue);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Language>(readSaved);

  const setLang = useCallback((next: Language) => {
    const available = ENGLISH_UI_ENABLED ? next : "VN";
    setLangState(available);
    try {
      localStorage.setItem(STORAGE_KEY, available);
    } catch {
      // Không lưu được thì vẫn đổi trong phiên này.
    }
  }, []);

  const value = useMemo<LanguageContextType>(
    () => ({
      lang,
      setLang,
      toggleLang: () => {
        if (ENGLISH_UI_ENABLED) setLang(lang === "VN" ? "EN" : "VN");
      },
      t: (vietnamese, params) => translate(vietnamese, lang, params),
    }),
    [lang, setLang],
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  return useContext(LanguageContext);
}
