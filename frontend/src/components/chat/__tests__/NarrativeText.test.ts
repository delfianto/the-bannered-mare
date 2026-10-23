// @vitest-environment jsdom

import { afterEach, describe, expect, it } from "vite-plus/test";
import { mount } from "@vue/test-utils";
import NarrativeText from "../NarrativeText.vue";
import { useTypography } from "@/composables/useTypography";

afterEach(() => useTypography().setNarrativeItalics(false));
describe("model-authored prose and HTML", () => {
  it("normalizes smart quotes and distinguishes dialogue from actions", () => {
    const wrapper = mount(NarrativeText, {
      props: { content: "*She waves.* “Hello, traveler.”\n\nIt’s quiet." },
    });
    expect(wrapper.text()).toContain("She waves.");
    expect(wrapper.get(".text-dialogue").text()).toBe('"Hello, traveler."');
    expect(wrapper.text()).toContain("It's quiet.");
    expect(wrapper.findAll("span").some((s) => s.text() === "She waves.")).toBe(true);
  });

  it("strips stray HTML and comments while preserving ordinary comparison symbols", () => {
    const wrapper = mount(NarrativeText, {
      props: {
        content: '5 < 10 and 8 > 2. <b>Bold</b><!-- hidden --><img src=x onerror="alert(1)">',
      },
    });
    expect(wrapper.text()).toContain("5 < 10 and 8 > 2. Bold");
    expect(wrapper.text()).not.toContain("hidden");
    expect(wrapper.find("img").exists()).toBe(false);
    expect(wrapper.find("b").exists()).toBe(false);
  });

  it("allows presentational GFX while stripping scripts, event handlers, links and media", () => {
    const wrapper = mount(NarrativeText, {
      props: {
        content:
          '<!-- GFX_START --><div style="color:red" onclick="alert(1)"><b>Map</b><script>alert(1)</script><a href="javascript:alert(1)">Link</a><img src="evil" onerror="alert(1)"><iframe src="evil"></iframe></div><!-- GFX_END -->',
      },
    });
    expect(wrapper.get("b").text()).toBe("Map");
    expect(wrapper.find("[style]").attributes("style")).toContain("color");
    expect(wrapper.find("[onclick]").exists()).toBe(false);
    expect(wrapper.find("script,a,img,iframe").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("alert(1)");
  });

  it("hides an unfinished GFX block while streaming and renders it only when complete", async () => {
    const wrapper = mount(NarrativeText, {
      props: { content: "Prose. <!-- GFX_START --><div>Secret card" },
    });
    expect(wrapper.text()).toBe("Prose.");
    await wrapper.setProps({
      content: "Prose. <!-- GFX_START --><div>Finished card</div><!-- GFX_END --> Tail.",
    });
    expect(wrapper.text()).toContain("Finished card");
    expect(wrapper.text()).toContain("Tail.");
  });

  it("handles multiple GFX cards interleaved with prose", () => {
    const wrapper = mount(NarrativeText, {
      props: {
        content:
          "<!-- GFX_START --><b>One</b><!-- GFX_END --> Between. <!-- GFX_START --><b>Two</b><!-- GFX_END -->",
      },
    });
    expect(wrapper.findAll("b").map((b) => b.text())).toEqual(["One", "Two"]);
    expect(wrapper.text()).toContain("Between.");
  });

  it("narrative italics applies to actions without changing dialogue", () => {
    useTypography().setNarrativeItalics(true);
    const wrapper = mount(NarrativeText, { props: { content: '*Nods.* "Hello"' } });
    expect(wrapper.get(".italic").text()).toBe("Nods.");
    expect(wrapper.get(".text-dialogue").classes()).not.toContain("italic");
  });
});
