#!/usr/bin/env node
/**
 * Đo độ phủ i18n — và vì sao cần một công cụ chứ không phải một lần rà tay.
 *
 * Havi từng có 446 chỗ gọi `t("câu tiếng Việt")` mà từ điển không có khoá nào
 * khớp, nên `t()` trả lại đúng nguyên văn. Bấm sang EN thì màn làm việc chính
 * **không đổi một chữ nào** — trong khi nút EN/VN vẫn nằm đó hứa hẹn. Đếm tay
 * không phát hiện được chuyện đó: mọi chuỗi *trông như* đã được bọc.
 *
 * Ba con số script này trả về, và ý nghĩa của từng con số:
 *
 * - `missing`   — chuỗi đã bọc `t()` nhưng chưa có bản EN. Đây là nợ dịch thuật:
 *                 người dùng chọn EN sẽ thấy đúng câu tiếng Việt.
 * - `unwrapped` — chuỗi người dùng đọc được nhưng nằm trần trong JSX. Không bọc
 *                 thì không trích ra được, và người dịch không bao giờ thấy nó.
 * - `dead`      — bản EN không còn chỗ nào gọi. Từ điển cũ có 60/99 khoá chết;
 *                 khoá chết làm người sửa tin rằng độ phủ cao hơn thực tế.
 *
 * Hai lối ra, đều phải nói lý do ngay trong file:
 *
 * - `// i18n-data` — chuỗi là **dữ liệu**, được `t()` dịch ở chỗ
 *   render (nhãn nav, thông báo lỗi từ module `.api.ts` — nơi không gọi hook
 *   được). Chúng không bị tính là "còn trần", nhưng **vẫn phải có bản EN**:
 *   người dùng đọc chúng, nên bỏ qua chúng là tự khai độ phủ cao hơn thật.
 * - `// i18n-exempt: <lý do>` — cố ý chỉ có tiếng Việt. Dùng cho văn bản pháp
 *   lý: một bản dịch Điều khoản sử dụng là **một văn bản pháp lý thứ hai**, việc
 *   của luật sư chứ không phải của codemod.
 *
 * Script in ra số file dùng mỗi lối, để chúng không lặng lẽ phình ra.
 *
 * Chạy: `node scripts/i18n-audit.mjs [--list]`
 * Thoát khác 0 khi còn `missing` hoặc `unwrapped`, để dùng được trong CI.
 */

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const SRC = new URL("../apps/web/src/", import.meta.url).pathname;
const DICT = join(SRC, "lib/i18n/translations.ts");

/** `t("...")` nhưng không phải `it("...")`, `format(...)`, `obj.t("...")`. */
const T_CALL = /(?<![A-Za-z0-9_$.])t\(\s*"((?:[^"\\]|\\.)*)"/g;

/**
 * Chuỗi người dùng đọc được, đoán theo hình dạng.
 *
 * Có dấu tiếng Việt là tín hiệu chắc nhất — không lập trình viên nào đặt tên
 * biến hay class CSS bằng chữ có dấu. Chuỗi ASCII thuần thì bỏ qua: `flex-end`,
 * `application/json`, `POST` đều lọt vào nếu chỉ xét "có khoảng trắng và chữ".
 */
const VIETNAMESE = /[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]/i;

/** Đường dẫn bỏ qua: test không hiện ra cho người dùng, i18n là chính từ điển. */
const SKIP = [".test.", ".spec.", "/lib/i18n/", "__fixtures__", ".fixture."];

function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) out.push(...walk(path));
    else if (/\.tsx?$/.test(name) && !SKIP.some((s) => path.includes(s))) out.push(path);
  }
  return out;
}

/** Bản EN, đọc bằng regex chứ không import: script phải chạy được không cần build. */
function readEnglish() {
  const body = readFileSync(DICT, "utf8");
  const start = body.indexOf("export const EN");
  if (start === -1) throw new Error("Không tìm thấy `export const EN` trong translations.ts");
  const keys = new Set();
  const entry = /^\s*"((?:[^"\\]|\\.)*)":/gm;
  for (const match of body.slice(start).matchAll(entry)) keys.add(match[1]);
  return keys;
}

/**
 * Bỏ chú thích trước khi soi chuỗi.
 *
 * Havi viết chú thích bằng tiếng Việt và viết rất nhiều. Không bỏ chúng ra thì
 * mỗi lời giải thích thành một "chuỗi chưa dịch", danh sách toàn báo động giả,
 * và một danh sách như thế thì người ta tắt script — lúc đó nó bằng không.
 */
function stripComments(body) {
  return body.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:"'`\\])\/\/[^\n]*/g, "$1");
}

/**
 * Mọi chuỗi người dùng đọc được mà **không** nằm trong `t()`.
 *
 * Cách nhận: một literal (nháy đơn, nháy kép, hay backtick) có chứa dấu tiếng
 * Việt. Dấu là tín hiệu chắc nhất — không ai đặt tên class CSS hay khoá JSON
 * bằng chữ có dấu, nên gần như không có báo động giả; đổi lại nó bỏ sót chuỗi
 * ASCII thuần như "Facebook Reels", và bỏ sót thì tốt hơn báo bừa.
 *
 * Chuỗi nằm ngay sau `t(` thì bỏ qua — kể cả `t(cond ? "A" : "B")`, nên phải
 * soi cả một đoạn sau `t(` chứ không chỉ ký tự liền kề.
 */
function unwrappedStrings(body, dataStrings) {
  // Vùng `i18n-data` đọc trên bản CÒN chú thích — chính chú thích là cái dấu.
  const data = markedRegions(body, "i18n-data");
  // `i18n-exempt` ở mức khai báo: chuỗi tiếng Việt là **giá trị**, không phải
  // chữ hiện ra — ví dụ giá trị mặc định của form phải khớp `value` của
  // `<option>`. Dịch nó là làm lựa chọn mặc định không còn khớp gì cả.
  const exempt = markedRegions(body, "i18n-exempt");
  const clean = stripComments(body);

  // Vùng đã bọc: từ mỗi `t(` tới dấu đóng ngoặc cân bằng tương ứng.
  const covered = [];
  for (const match of clean.matchAll(/(?<![A-Za-z0-9_$.])t\(/g)) {
    let depth = 0;
    for (let i = match.index + match[0].length - 1; i < clean.length; i++) {
      const ch = clean[i];
      if (ch === "(") depth++;
      else if (ch === ")") {
        depth--;
        if (depth === 0) {
          covered.push([match.index, i]);
          break;
        }
      }
    }
  }
  const inside = (at) => covered.some(([from, to]) => at > from && at < to);

  const LITERAL = /"((?:[^"\\\n]|\\.)*)"|'((?:[^'\\\n]|\\.)*)'|`((?:[^`\\]|\\.)*)`/g;
  const found = [];
  for (const match of clean.matchAll(LITERAL)) {
    const text = match[1] ?? match[2] ?? match[3] ?? "";
    if (!VIETNAMESE.test(text) || inside(match.index)) continue;
    if (isCode(clean, match.index)) continue;
    // Vị trí đo trên `clean` lệch so với `body` vì chú thích đã bị bỏ; đối chiếu
    // bằng chính nội dung chuỗi trong vùng dữ liệu thì không phụ thuộc vị trí.
    if (exempt.some(([from, to]) => body.slice(from, to).includes(text))) continue;
    if (data.some(([from, to]) => body.slice(from, to).includes(text))) {
      dataStrings.push(text);
      continue;
    }
    found.push(text);
  }
  return found;
}

/**
 * Vùng được đánh dấu `// i18n-data` hay `// i18n-exempt` ngay trên một khai báo.
 *
 * Cần đến mức khai báo vì các map nhãn (`STATUS_LABELS`, `PLAN_META`) nằm cùng
 * file với JSX thật. Miễn cả file thì phần JSX cũng thoát khỏi kiểm tra, và đúng
 * những chuỗi bị bỏ quên sẽ lọt — tức là cái giá của tiện lợi rơi vào chỗ mình
 * cần nhất.
 */
function markedRegions(body, tag) {
  const lines = body.split("\n");
  const offsets = [];
  let at = 0;
  for (const line of lines) {
    offsets.push(at);
    at += line.length + 1;
  }

  const regions = [];
  for (let i = 0; i < lines.length; i++) {
    if (!new RegExp(`^[ \\t]*//[ \\t]*${tag}\\b`).test(lines[i])) continue;
    // Khai báo cấp cao kết thúc bằng một dòng `};`, `];` hay `);` ở cột 0 —
    // định dạng của prettier, nên đây là mốc chắc chắn. Đếm ngoặc thì hỏng: dấu
    // `{` đầu tiên của `Record<string, { label: string }>` là ngoặc của kiểu, và
    // nó đóng lại trước cả khi tới object thật.
    let end = lines.length - 1;
    for (let j = i + 1; j < lines.length; j++) {
      if (/^[}\])];]/.test(lines[j])) {
        end = j;
        break;
      }
    }
    regions.push([offsets[i], offsets[end] + lines[end].length]);
  }
  return regions;
}

/**
 * Chuỗi tiếng Việt **không phải** chữ trên màn hình.
 *
 * Hai loại, và cả hai đều sẽ sai nếu đem dịch:
 *
 * - **Chuỗi so sánh**: `industry.includes("giáo dục")` — dịch nó thành
 *   `"education"` là làm nhánh điều kiện không bao giờ đúng nữa. Nó là một giá
 *   trị dữ liệu, tình cờ viết bằng tiếng Việt.
 * - **Thông điệp cho lập trình viên**: `throw new Error(…)`, `console.error(…)`.
 *   Người đọc chúng là người sửa code, không phải khách hàng.
 *
 * Không tách hai loại này ra thì danh sách đầy báo động giả, và một danh sách
 * như thế thì người ta tắt script — lúc đó nó bằng không.
 */
function isCode(body, at) {
  const before = body.slice(Math.max(0, at - 80), at);
  return (
    /\.(includes|startsWith|endsWith|indexOf|split|replace|replaceAll|match)\(\s*$/.test(before) ||
    /[=!]==?\s*$/.test(before) ||
    /new Error\(\s*$/.test(before) ||
    /console\.\w+\([^)]*$/.test(before)
  );
}

const files = walk(SRC);
const english = readEnglish();

const wrapped = new Map(); // chuỗi -> file đầu tiên gặp
const unwrapped = [];
const dataFiles = [];
const exemptFiles = [];

for (const path of files) {
  const body = readFileSync(path, "utf8");
  const where = relative(SRC, path);

  for (const match of body.matchAll(T_CALL)) {
    if (!wrapped.has(match[1])) wrapped.set(match[1], where);
  }

  if (/^\s*\/\/\s*i18n-exempt:/m.test(body)) {
    exemptFiles.push(where);
    continue;
  }

  const isData = /^\s*\/\/\s*i18n-data\b/.test(body);
  if (isData) dataFiles.push(where);
  const dataStrings = [];
  for (const text of unwrappedStrings(body, dataStrings)) {
    // File `i18n-data`: chuỗi được dịch ở chỗ render, nên nó **đã bọc** — chỉ là
    // bọc ở nơi khác. Vẫn phải có bản EN.
    if (isData) {
      if (!wrapped.has(text)) wrapped.set(text, where);
    } else {
      unwrapped.push({ text, where });
    }
  }
  for (const text of dataStrings) {
    if (!wrapped.has(text)) wrapped.set(text, where);
  }
}

const missing = [...wrapped].filter(([text]) => !english.has(text));
const dead = [...english].filter((key) => !wrapped.has(key));

/** Cắt danh sách để một lần chạy sai không đổ vài nghìn dòng vào terminal. */
const LIST_CAP = 2000;

const list = process.argv.includes("--list");
const show = (label, rows) => {
  if (!list || rows.length === 0) return;
  console.log(`\n── ${label} ──`);
  for (const row of rows.slice(0, LIST_CAP)) {
    console.log(Array.isArray(row) ? `  ${row[1]}  ${row[0]}` : `  ${row.where}  ${row.text}`);
  }
  if (rows.length > LIST_CAP) console.log(`  … còn ${rows.length - LIST_CAP} dòng`);
};

console.log(`đã bọc t()      : ${wrapped.size}`);
console.log(`có bản EN       : ${wrapped.size - missing.length}`);
console.log(`thiếu bản EN    : ${missing.length}`);
console.log(`còn trần trong JSX: ${unwrapped.length}`);
console.log(`bản EN không ai dùng: ${dead.length}`);
console.log(`file dịch ở chỗ render (i18n-data): ${dataFiles.length}`);
console.log(`file cố ý chỉ tiếng Việt (i18n-exempt): ${exemptFiles.length}`);

show("thiếu bản EN", missing);
show("còn trần", unwrapped);
show("bản EN chết", dead.map((k) => [k, "translations.ts"]));
show("cố ý chỉ tiếng Việt", exemptFiles.map((f) => [f, "i18n-exempt"]));

if (!list && (missing.length || unwrapped.length)) {
  console.log("\nChạy lại với --list để xem từng dòng.");
}
process.exit(missing.length || unwrapped.length ? 1 : 0);
