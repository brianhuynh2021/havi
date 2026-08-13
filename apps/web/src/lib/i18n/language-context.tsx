"use client";

import {
  createContext,
  useContext,
  useState,
  type ReactNode,
} from "react";
import {
  translations,
  type Language,
  type TranslationKey,
} from "./translations";

type InlineText = {
  vi?: string;
  en?: string;
  VN?: string;
  EN?: string;
};

type LanguageContextType = {
  lang: Language;
  setLang: (lang: Language) => void;
  toggleLang: () => void;
  t: (
    keyOrText: TranslationKey | InlineText | string,
    fallback?: string
  ) => string;
};

const STORAGE_KEY = "havi_preferred_language";

function defaultT(
  keyOrText: TranslationKey | InlineText | string,
  fallback?: string
): string {
  if (typeof keyOrText === "object" && keyOrText !== null) {
    return keyOrText.VN || keyOrText.vi || fallback || "";
  }
  if (typeof keyOrText === "string") {
    const langDict = translations["VN"];
    if (keyOrText in langDict) {
      return langDict[keyOrText as TranslationKey];
    }
    return fallback || keyOrText;
  }
  return fallback || "";
}

const defaultValue: LanguageContextType = {
  lang: "VN",
  setLang: () => {},
  toggleLang: () => {},
  t: defaultT,
};

const LanguageContext = createContext<LanguageContextType>(defaultValue);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Language>(() => {
    if (typeof window === "undefined") return "VN";
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved === "EN" || saved === "VN") return saved;
    } catch {
      // Ignore localStorage errors
    }
    return "VN";
  });

  const setLang = (newLang: Language) => {
    setLangState(newLang);
    try {
      localStorage.setItem(STORAGE_KEY, newLang);
    } catch {
      // Ignore localStorage errors
    }
  };

  const toggleLang = () => {
    setLang(lang === "VN" ? "EN" : "VN");
  };

  const t = (
    keyOrText: TranslationKey | InlineText | string,
    fallback?: string
  ): string => {
    if (typeof keyOrText === "object" && keyOrText !== null) {
      if (lang === "VN") {
        return keyOrText.VN || keyOrText.vi || fallback || "";
      }
      return keyOrText.EN || keyOrText.en || keyOrText.VN || keyOrText.vi || fallback || "";
    }

    if (typeof keyOrText === "string") {
      const langDict = translations[lang];
      if (keyOrText in langDict) {
        return langDict[keyOrText as TranslationKey];
      }
      return fallback || keyOrText;
    }

    return fallback || "";
  };

  return (
    <LanguageContext.Provider
      value={{
        lang,
        setLang,
        toggleLang,
        t,
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  return context ?? defaultValue;
}
