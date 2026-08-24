"use client";

import { useState } from "react";
import { useLanguage } from "@/lib/i18n/language-context";
import styles from "./social-auth-buttons.module.css";

type Props = {
  mode?: "login" | "signup";
};

export function SocialAuthButtons({ mode = "login" }: Props) {
  const { t } = useLanguage();
  const [loadingProvider, setLoadingProvider] = useState<"google" | "facebook" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSocialClick = async (provider: "google" | "facebook") => {
    setError(null);
    setLoadingProvider(provider);
    setTimeout(() => {
      setLoadingProvider(null);
      setError(
        provider === "google"
          ? "Đăng nhập Google đang được nâng cấp chứng thực bảo mật OAuth 2.0 PKCE. Vui lòng sử dụng Email & Mật khẩu."
          : "Đăng nhập Facebook đang được nâng cấp chứng thực bảo mật OAuth 2.0 PKCE. Vui lòng sử dụng Email & Mật khẩu."
      );
    }, 400);
  };

  return (
    <div className={styles.container}>
      <div className={styles.buttonGroup}>
        {/* Google Button */}
        <button
          type="button"
          className={`${styles.socialBtn} ${styles.googleBtn}`}
          onClick={() => handleSocialClick("google")}
          disabled={loadingProvider !== null}
          aria-label={t({
            vi: mode === "login" ? "Đăng nhập bằng Google" : "Đăng ký bằng Google",
            en: mode === "login" ? "Sign in with Google" : "Sign up with Google",
          })}
        >
          {loadingProvider === "google" ? (
            <span className={styles.spinner} />
          ) : (
            <svg className={styles.icon} viewBox="0 0 24 24">
              <path
                fill="#EA4335"
                d="M12 5c1.6 0 3 .6 4.1 1.7l3.1-3.1C17.3 1.8 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.3 9 5 12 5z"
              />
              <path
                fill="#4285F4"
                d="M23.5 12.3c0-.8-.1-1.7-.2-2.3H12v4.6h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.9z"
              />
              <path
                fill="#FBBC05"
                d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.3 0-.8.2-1.6.4-2.3L1.9 7.3C.7 9.7 0 10.8 0 12.5s.7 2.8 1.9 5.2l3.7-2.9z"
              />
              <path
                fill="#34A853"
                d="M12 23.5c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2.3-6.4-5.2L1.9 16.5C3.7 20.2 7.5 23.5 12 23.5z"
              />
            </svg>
          )}
          <span className={styles.btnText}>
            {loadingProvider === "google"
              ? t({ vi: "Đang kết nối Google…", en: "Connecting Google…" })
              : t({
                  vi: mode === "login" ? "Tiếp tục bằng Google" : "Đăng ký bằng Google",
                  en: mode === "login" ? "Continue with Google" : "Sign up with Google",
                })}
          </span>
        </button>

        {/* Facebook Button */}
        <button
          type="button"
          className={`${styles.socialBtn} ${styles.facebookBtn}`}
          onClick={() => handleSocialClick("facebook")}
          disabled={loadingProvider !== null}
          aria-label={t({
            vi: mode === "login" ? "Đăng nhập bằng Facebook" : "Đăng ký bằng Facebook",
            en: mode === "login" ? "Sign in with Facebook" : "Sign up with Facebook",
          })}
        >
          {loadingProvider === "facebook" ? (
            <span className={styles.spinner} />
          ) : (
            <svg className={styles.icon} viewBox="0 0 24 24" fill="#1877F2">
              <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
            </svg>
          )}
          <span className={styles.btnText}>
            {loadingProvider === "facebook"
              ? t({ vi: "Đang kết nối Facebook…", en: "Connecting Facebook…" })
              : t({
                  vi: mode === "login" ? "Tiếp tục bằng Facebook" : "Đăng ký bằng Facebook",
                  en: mode === "login" ? "Continue with Facebook" : "Sign up with Facebook",
                })}
          </span>
        </button>
      </div>

      {error ? <p className={styles.errorText}>{error}</p> : null}

      <div className={styles.divider}>
        <span>
          {t({
            vi: mode === "login" ? "hoặc đăng nhập bằng email" : "hoặc tạo tài khoản bằng email",
            en: mode === "login" ? "or sign in with email" : "or sign up with email",
          })}
        </span>
      </div>
    </div>
  );
}
