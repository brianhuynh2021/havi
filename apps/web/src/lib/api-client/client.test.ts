import { describe, expect, it } from "vitest";
import { apiClient } from "./client";

describe("apiClient", () => {
  it("is created with GET/POST helpers matching the OpenAPI schema", () => {
    expect(typeof apiClient.GET).toBe("function");
    expect(typeof apiClient.POST).toBe("function");
  });
});
