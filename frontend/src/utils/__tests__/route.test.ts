import { describe, it, expect } from "vitest";
import { routeParam } from "../route";

describe("routeParam", () => {
  it("passes strings through, unwraps arrays to the first entry, and defaults undefined to empty", () => {
    expect(routeParam("abc")).toBe("abc");
    expect(routeParam(["first", "second"])).toBe("first");
    expect(routeParam(undefined)).toBe("");
  });
});
