/**
 * Cơ chế dịch — và cái bẫy mà bộ test này canh.
 *
 * Havi từng có nút EN/VN chạy được, 932 chỗ gọi `t()`, và **màn làm việc chính
 * không đổi một chữ nào** khi bấm sang tiếng Anh: từ điển dùng khoá có dấu chấm
 * (`nav.content`) trong khi hầu hết chỗ gọi truyền câu tiếng Việt, nên `t()` tra
 * không thấy và trả lại nguyên văn. Mọi thứ *trông như* đã dịch.
 *
 * Không test nào lúc đó đỏ, vì test kiểm chữ tiếng Việt — và tiếng Việt thì luôn
 * đúng. Bộ test này kiểm điều ngược lại: **chọn EN thì chữ phải đổi**.
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { LanguageProvider, translate, translateNow, useLanguage } from "./language-context";
import { EN } from "./translations";

beforeEach(() => {
  window.localStorage.clear();
});

describe("translate", () => {
  it("tiếng Việt trả lại đúng nguyên văn — nó là khoá, không phải mã", () => {
    expect(translate("Việc cần làm", "VN")).toBe("Việc cần làm");
  });

  it("tiếng Anh tra được bản dịch", () => {
    // Lấy một mục thật từ từ điển thay vì viết cứng: đổi lời văn trong
    // `translations.ts` không được làm test này đỏ oan.
    const [vietnamese, english] = Object.entries(EN)[0];
    expect(translate(vietnamese, "EN")).toBe(english);
  });

  it("thiếu bản dịch thì hiện TIẾNG VIỆT, không hiện khoá thô", () => {
    // Một câu tiếng Việt lọt vào giao diện tiếng Anh thì người đọc vẫn dùng được
    // app và người sửa vẫn thấy ngay. `MISSING_KEY` thì không được cái nào.
    const chuaDich = "Câu này chắc chắn không có trong từ điển 8f3a2c";
    expect(translate(chuaDich, "EN")).toBe(chuaDich);
  });

  it("chèn giá trị vào {ô}", () => {
    expect(translate("Còn khoảng {posts} bài trong tháng này", "VN", { posts: 42 })).toBe(
      "Còn khoảng 42 bài trong tháng này",
    );
  });

  it("ô không có giá trị thì GIỮ NGUYÊN, không xoá đi", () => {
    // Xoá đi là âm thầm làm câu mất nghĩa: "Còn khoảng bài trong tháng này".
    // Để lại thì lỗi lộ ra ngay trên màn hình và có người sửa.
    expect(translate("Còn khoảng {posts} bài trong tháng này", "VN", {})).toContain("{posts}");
  });

  it("chèn giá trị hoạt động trên CẢ bản tiếng Anh", () => {
    const withSlot = Object.keys(EN).find((key) => /\{\w+\}/.test(EN[key]));
    if (!withSlot) return; // chưa có mục nào có ô — không phải lỗi
    const name = /\{(\w+)\}/.exec(EN[withSlot])![1];
    expect(translate(withSlot, "EN", { [name]: "X" })).toContain("X");
  });
});

describe("từ điển", () => {
  it("không có mục nào tự dịch thành chính nó", () => {
    // `"Email": "Email"` là mục vô hại nhưng vô nghĩa — nó chỉ làm số liệu độ phủ
    // trông đẹp hơn thực tế. Ngoại lệ duy nhất là danh từ riêng.
    const NOUNS = new Set(["Email", "TikTok", "Facebook", "YouTube", "Zalo", "Havi"]);
    const selfMapping = Object.entries(EN).filter(
      ([vietnamese, english]) => vietnamese === english && !NOUNS.has(vietnamese),
    );
    expect(selfMapping).toEqual([]);
  });

  it("không có bản EN nào lại là khoá của một mục khác", () => {
    // Bất biến chống dịch HAI LẦN. Các module `*.api.ts` trả câu tiếng Việt rồi
    // màn hình hiện bằng `t(error)`; nếu chính chuỗi tiếng Anh đó lại là khoá thì
    // một câu đi qua `t()` hai lần sẽ biến thành câu khác hẳn.
    const keys = new Set(Object.keys(EN));
    const chained = Object.entries(EN)
      .filter(([vietnamese, english]) => vietnamese !== english && keys.has(english))
      .map(([vietnamese, english]) => `${vietnamese} → ${english}`);
    expect(chained).toEqual([]);
  });

  it("số ô chèn ở hai bản phải khớp nhau", () => {
    // Bản EN thiếu `{days}` thì con số biến mất khỏi câu mà không ai báo lỗi;
    // thừa một ô lạ thì `{abc}` hiện thẳng ra màn hình.
    const slots = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();
    const mismatched = Object.entries(EN)
      .filter(([vi, en]) => slots(vi).join(",") !== slots(en).join(","))
      .map(([vi, en]) => `${vi} → ${en}`);
    expect(mismatched).toEqual([]);
  });
});

function Probe() {
  const { t, lang, toggleLang } = useLanguage();
  const [vietnamese] = Object.entries(EN)[0];
  return (
    <div>
      <span data-testid="lang">{lang}</span>
      <span data-testid="text">{t(vietnamese)}</span>
      <button type="button" onClick={toggleLang}>
        đổi
      </button>
    </div>
  );
}

describe("LanguageProvider", () => {
  it("bấm đổi ngôn ngữ thì CHỮ ĐỔI THẬT", async () => {
    // Đây là bài kiểm tra mà bản cũ trượt: nút chạy, `lang` đổi, và chữ y nguyên.
    const [vietnamese, english] = Object.entries(EN)[0];
    render(
      <LanguageProvider>
        <Probe />
      </LanguageProvider>,
    );

    expect(screen.getByTestId("text")).toHaveTextContent(vietnamese);

    await userEvent.click(screen.getByRole("button", { name: "đổi" }));

    expect(screen.getByTestId("lang")).toHaveTextContent("EN");
    expect(screen.getByTestId("text")).toHaveTextContent(english);
  });

  it("nhớ lựa chọn qua lần mở sau", async () => {
    render(
      <LanguageProvider>
        <Probe />
      </LanguageProvider>,
    );
    await userEvent.click(screen.getByRole("button", { name: "đổi" }));

    // Mở lại từ đầu: đọc từ localStorage, không quay về mặc định.
    render(
      <LanguageProvider>
        <Probe />
      </LanguageProvider>,
    );
    expect(screen.getAllByTestId("lang").at(-1)).toHaveTextContent("EN");
  });
});

describe("translateNow", () => {
  it("đọc đúng lựa chọn mà Provider đã ghi", () => {
    // Dành cho module `*.api.ts` — không gọi hook được nhưng vẫn chạy trong
    // trình duyệt, nên phải đọc cùng một khoá localStorage.
    const [vietnamese, english] = Object.entries(EN)[0];
    window.localStorage.setItem("havi_preferred_language", "EN");
    expect(translateNow(vietnamese)).toBe(english);
  });

  it("chưa chọn gì thì mặc định tiếng Việt", () => {
    const [vietnamese] = Object.entries(EN)[0];
    expect(translateNow(vietnamese)).toBe(vietnamese);
  });
});
