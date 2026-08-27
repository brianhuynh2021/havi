import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { uploadMedia } from "./content-creation.api";

const post = vi.fn();

vi.mock("@/lib/api-client/client", () => ({
  apiClient: { POST: (...args: unknown[]) => post(...args) },
}));

class FakeUploadRequest extends EventTarget {
  static holdOpen = false;
  static last: FakeUploadRequest | null = null;

  upload = new EventTarget();
  status = 0;

  constructor() {
    super();
    FakeUploadRequest.last = this;
  }

  open() {}

  send() {
    this.upload.dispatchEvent(
      new ProgressEvent("progress", {
        lengthComputable: true,
        loaded: 50,
        total: 100,
      }),
    );
    if (FakeUploadRequest.holdOpen) return;
    this.status = 204;
    this.dispatchEvent(new Event("load"));
  }

  abort() {
    this.dispatchEvent(new Event("abort"));
  }
}

const NativeXMLHttpRequest = globalThis.XMLHttpRequest;

describe("uploadMedia", () => {
  beforeEach(() => {
    post.mockReset();
    FakeUploadRequest.holdOpen = false;
    FakeUploadRequest.last = null;
    globalThis.XMLHttpRequest = FakeUploadRequest as unknown as typeof XMLHttpRequest;
  });

  afterEach(() => {
    globalThis.XMLHttpRequest = NativeXMLHttpRequest;
  });

  it("đo tiến độ bytes thật giữa bước xin ticket và xác nhận object", async () => {
    post
      .mockResolvedValueOnce({
        data: {
          asset_id: "asset-1",
          upload_url: "https://storage/upload",
          fields: { key: "workspace/asset-1.jpg" },
        },
      })
      .mockResolvedValueOnce({
        data: { id: "asset-1", type: "image", url: "https://storage/asset-1.jpg" },
      });
    const progress: number[] = [];

    const result = await uploadMedia(
      new File(["image"], "spa.jpg", { type: "image/jpeg" }),
      { onProgress: (value) => progress.push(value) },
    );

    expect(result.ok).toBe(true);
    expect(progress).toEqual([5, 20, 53, 85, 100]);
    expect(post).toHaveBeenCalledTimes(2);
  });

  it("AbortSignal huỷ request storage và trả trạng thái huỷ riêng", async () => {
    FakeUploadRequest.holdOpen = true;
    post.mockResolvedValueOnce({
      data: { asset_id: "asset-1", upload_url: "https://storage/upload", fields: {} },
    });
    const controller = new AbortController();
    const promise = uploadMedia(
      new File(["image"], "spa.jpg", { type: "image/jpeg" }),
      { signal: controller.signal },
    );
    await vi.waitFor(() => expect(FakeUploadRequest.last).not.toBeNull());

    controller.abort();

    await expect(promise).resolves.toEqual({ ok: false, message: "Đã huỷ tải ảnh." });
    expect(post).toHaveBeenCalledTimes(1);
  });
});
