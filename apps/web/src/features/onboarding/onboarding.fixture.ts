export type IndustryOption = {
  value:
    | "spa"
    | "food_beverage"
    | "real_estate"
    | "professional"
    | "online_shop"
    | "other";
  label: string;
  recommended?: boolean;
};

// Khớp core.enums.Industry — Spa là ngành pilot đề xuất (ROADMAP.md §1 QA/product).
export const industryOptions: IndustryOption[] = [
  { value: "spa", label: "Spa / Tiệm làm đẹp", recommended: true },
  { value: "food_beverage", label: "Ăn uống" },
  { value: "real_estate", label: "Bất động sản" },
  { value: "professional", label: "Dịch vụ chuyên môn" },
  { value: "online_shop", label: "Bán hàng online" },
  { value: "other", label: "Ngành khác" },
];
