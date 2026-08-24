"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { useLanguage } from "@/lib/i18n/language-context";
import { fetchActiveGoal, fetchActiveRoadmap, type ActiveRoadmapData, type Goal } from "@/features/roadmap/roadmap.api";
import styles from "./coach.module.css";

type Message = {
  sender: "havi" | "user";
  text: string;
};

export function CoachScreen() {
  const { t } = useLanguage();
  const [goal, setGoal] = useState<Goal | null>(null);
  const [roadmapData, setRoadmapData] = useState<ActiveRoadmapData | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputVal, setInputVal] = useState("");

  useEffect(() => {
    async function init() {
      const [goalRes, roadmapRes] = await Promise.all([
        fetchActiveGoal(),
        fetchActiveRoadmap(),
      ]);

      if (goalRes.ok && goalRes.data) {
        setGoal(goalRes.data);
      }
      if (roadmapRes.ok && roadmapRes.data) {
        setRoadmapData(roadmapRes.data);
      }

      const initialText = goalRes.ok && goalRes.data
        ? `Chào bạn! Havi đang đồng hành cùng bạn với mục tiêu "${goalRes.data.title}". Hôm nay bạn có gặp khó khăn gì trong việc thực hiện nhiệm vụ đề xuất không?`
        : "Chào bạn! Tôi là Havi đồng hành. Hãy thiết lập mục tiêu đầu tiên của bạn để tôi có thể tư vấn lộ trình và hướng dẫn chi tiết từng bước!";

      setMessages([{ sender: "havi", text: initialText }]);
    }
    init();
  }, []);

  const handleSend = (text: string) => {
    if (!text.trim()) return;
    const userMsg: Message = { sender: "user", text: text.trim() };
    const nextTask = roadmapData?.tasks.find((t) => t.status === "pending");

    let reply = "Havi đã ghi nhận ý kiến của bạn.";
    if (text.includes("kẹt") || text.includes("khó")) {
      reply = `Nếu bạn đang bị kẹt ở nhiệm vụ hiện tại, hãy thử chia nhỏ việc ra thành 15 phút, hoặc chọn 'Phương án thay thế' ngay trên tab Hôm nay nhé!`;
    } else if (text.includes("video") || text.includes("quay")) {
      reply = `Để quay video ngắn hiệu quả, bạn chỉ cần mở Studio Video của Havi để xem máy nhắc chữ (Teleprompter) và làm theo hook 3 giây đầu tiên!`;
    } else if (nextTask) {
      reply = `Theo lộ trình mục tiêu "${goal?.title}", việc quan trọng nhất bạn nên tập trung hoàn thành lúc này là: "${nextTask.title}". Tiêu chuẩn xong là: ${nextTask.done_rule}.`;
    }

    setMessages((prev) => [...prev, userMsg, { sender: "havi", text: reply }]);
    setInputVal("");
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>{t({ vi: "Havi Đồng Hành (Hướng Dẫn Nhanh)", en: "Havi Action Guide" })}</h1>
        <p className={styles.subtitle}>
          {t({
            vi: "Trợ lý hướng dẫn bám sát theo mục tiêu, nhiệm vụ và phương án giải quyết khó khăn của bạn.",
            en: "Action guide grounded in your current goal and task context.",
          })}
        </p>
      </header>

      <section className={styles.coachCard}>
        <div className={styles.coachHeader}>
          <div className={styles.avatar}>✨</div>
          <div>
            <div className={styles.coachName}>Havi Executive Coach</div>
            <div className={styles.coachRole}>
              Đồng hành mục tiêu: {goal ? goal.title : "Chưa có mục tiêu"}
            </div>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "12px", minHeight: "200px" }}>
          {messages.map((msg, i) => (
            <div
              key={i}
              className={styles.adviceBox}
              style={{
                background: msg.sender === "user" ? "rgba(37, 99, 235, 0.05)" : "var(--bg-canvas)",
                borderLeftColor: msg.sender === "user" ? "#10b981" : "#2563eb",
                alignSelf: msg.sender === "user" ? "flex-end" : "flex-start",
                maxWidth: "85%",
              }}
            >
              <strong>{msg.sender === "user" ? "Bạn" : "Havi"}: </strong>
              {msg.text}
            </div>
          ))}
        </div>

        <div className={styles.quickPrompts}>
          <button
            type="button"
            className={styles.promptBtn}
            onClick={() => handleSend("Hôm nay tôi nên ưu tiên làm việc gì trước?")}
          >
            🎯 Việc ưu tiên hôm nay?
          </button>
          <button
            type="button"
            className={styles.promptBtn}
            onClick={() => handleSend("Tôi bị kẹt không có thời gian quay video")}
          >
            ⚠️ Tôi bị kẹt thời gian
          </button>
          <button
            type="button"
            className={styles.promptBtn}
            onClick={() => handleSend("Làm sao để đo lường bằng chứng hiệu quả?")}
          >
            📊 Cách đo bằng chứng?
          </button>
        </div>

        <div className={styles.chatInputRow}>
          <input
            className={styles.input}
            placeholder="Hỏi Havi về lộ trình, cách vượt qua rào cản..."
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSend(inputVal);
            }}
          />
          <Button variant="primary" onClick={() => handleSend(inputVal)}>
            Gửi
          </Button>
        </div>
      </section>
    </div>
  );
}
