"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useLanguage } from "@/lib/i18n/language-context";

export type VoiceRecorderState = "idle" | "recording" | "processing" | "ready" | "error";

type SpeechRecognitionInstance = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: Event) => void) | null;
  start: () => void;
  stop: () => void;
};

type SpeechRecognitionEvent = {
  results: {
    length: number;
    [index: number]: {
      [index: number]: {
        transcript: string;
      };
    };
  };
};

export function useVoiceRecorder() {
  const { t } = useLanguage();
  const [state, setState] = useState<VoiceRecorderState>("idle");
  const [recordingTime, setRecordingTime] = useState(0);
  const [liveTranscript, setLiveTranscript] = useState("");
  const [audioBase64, setAudioBase64] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const speechRecognitionRef = useRef<SpeechRecognitionInstance | null>(null);

  const clearTimer = useCallback(() => {
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
  }, []);

  const startRecording = useCallback(async () => {
    setErrorMessage(null);
    setLiveTranscript("");
    setAudioBase64(null);
    setRecordingTime(0);
    audioChunksRef.current = [];

    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("Trình duyệt không hỗ trợ ghi âm trực tiếp.");
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : MediaRecorder.isTypeSupported("audio/mp4")
        ? "audio/mp4"
        : "";

      const mediaRecorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);

      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.start(250); // Collect slices every 250ms
      setState("recording");

      // Start timer
      timerIntervalRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);

      // Initialize Web Speech API for instant live feedback if available
      const globalWindow = typeof window !== "undefined" ? (window as unknown as Record<string, unknown>) : {};
      const SpeechRecognitionConstructor = (globalWindow.SpeechRecognition ||
        globalWindow.webkitSpeechRecognition) as { new (): SpeechRecognitionInstance } | undefined;

      if (SpeechRecognitionConstructor) {
        try {
          const recognition = new SpeechRecognitionConstructor();
          recognition.continuous = true;
          recognition.interimResults = true;
          recognition.lang = "vi-VN";

          recognition.onresult = (event: SpeechRecognitionEvent) => {
            let fullText = "";
            for (let i = 0; i < event.results.length; i++) {
              fullText += event.results[i][0].transcript;
            }
            if (fullText.trim()) {
              setLiveTranscript(fullText.trim());
            }
          };

          recognition.onerror = () => {};
          recognition.start();
          speechRecognitionRef.current = recognition;
        } catch {
          // Speech recognition is an enhancement; silent fallback
        }
      }
    } catch (err: unknown) {
      setState("error");
      const errorObj = err as { name?: string; message?: string };
      if (errorObj?.name === "NotAllowedError" || errorObj?.name === "PermissionDeniedError") {
        setErrorMessage(t("Vui lòng cấp quyền Micro trên trình duyệt để Havi nghe được giọng nói."));
      } else {
        setErrorMessage(errorObj?.message || t("Không thể khởi động micro."));
      }
    }
  }, [t]);

  const stopRecording = useCallback((): Promise<{ base64: string; mimeType: string; transcript: string }> => {
    return new Promise((resolve, reject) => {
      clearTimer();

      if (speechRecognitionRef.current) {
        try {
          speechRecognitionRef.current.stop();
        } catch {}
      }

      const recorder = mediaRecorderRef.current;
      if (!recorder || recorder.state === "inactive") {
        setState("idle");
        reject(new Error("Không có bản ghi âm"));
        return;
      }

      setState("processing");

      recorder.onstop = async () => {
        try {
          const mimeType = recorder.mimeType || "audio/webm";
          const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });

          // Convert blob to base64
          const reader = new FileReader();
          reader.onloadend = () => {
            const dataUrl = reader.result as string;
            const base64Data = dataUrl.split(",")[1] || "";
            setAudioBase64(base64Data);
            setState("ready");

            // Stop all audio tracks to release microphone
            recorder.stream.getTracks().forEach((track) => track.stop());

            resolve({
              base64: base64Data,
              mimeType,
              transcript: liveTranscript,
            });
          };

          reader.onerror = () => {
            setState("error");
            setErrorMessage(t("Lỗi xử lý file âm thanh"));
            reject(new Error("Lỗi đọc file âm thanh"));
          };

          reader.readAsDataURL(audioBlob);
        } catch (err: unknown) {
          setState("error");
          const errorObj = err as { message?: string };
          setErrorMessage(errorObj?.message || t("Lỗi xử lý âm thanh"));
          reject(err);
        }
      };

      recorder.stop();
    });
  }, [clearTimer, liveTranscript, t]);

  const cancelRecording = useCallback(() => {
    clearTimer();

    if (speechRecognitionRef.current) {
      try {
        speechRecognitionRef.current.stop();
      } catch {}
    }

    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
      mediaRecorderRef.current.stop();
    }

    setState("idle");
    setRecordingTime(0);
    setLiveTranscript("");
    setAudioBase64(null);
    setErrorMessage(null);
  }, [clearTimer]);

  useEffect(() => {
    return () => {
      clearTimer();
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, [clearTimer]);

  return {
    state,
    recordingTime,
    liveTranscript,
    audioBase64,
    errorMessage,
    startRecording,
    stopRecording,
    cancelRecording,
    setLiveTranscript,
  };
}
