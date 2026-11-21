import { renderHook } from "@testing-library/react";
import { useTabStopWhileScrolling } from "./useTabStopWhileScrolling";

// A ResizeObserver the test fires by hand, recording what it observes.
class FakeResizeObserver {
  static last: FakeResizeObserver | null = null;
  observed: Element[] = [];
  disconnected = false;
  constructor(private readonly callback: () => void) {
    FakeResizeObserver.last = this;
  }
  observe(target: Element) {
    this.observed.push(target);
  }
  unobserve() {}
  disconnect() {
    this.disconnected = true;
  }
  fire() {
    this.callback();
  }
}

// A container whose content height the test sets.
function container(clientHeight: number) {
  const element = document.createElement("div");
  const size = { scrollHeight: clientHeight };
  Object.defineProperty(element, "scrollHeight", { configurable: true, get: () => size.scrollHeight });
  Object.defineProperty(element, "clientHeight", { configurable: true, get: () => clientHeight });
  return { element, setContentHeight: (height: number) => (size.scrollHeight = height) };
}

beforeEach(() => {
  vi.stubGlobal("ResizeObserver", FakeResizeObserver);
});

afterEach(() => {
  vi.unstubAllGlobals();
  FakeResizeObserver.last = null;
});

describe("useTabStopWhileScrolling", () => {
  it("gives a container whose content is taller than it a tab stop when it renders", () => {
    const box = container(600);
    box.setContentHeight(900);
    renderHook(() => useTabStopWhileScrolling(box.element, null));
    expect(box.element.getAttribute("tabindex")).toBe("0");
  });

  it("gives a container whose content fits no tab stop", () => {
    const box = container(600);
    renderHook(() => useTabStopWhileScrolling(box.element, null));
    expect(box.element.hasAttribute("tabindex")).toBe(false);
  });

  it("follows the content as it grows and shrinks, through the size observer", () => {
    const box = container(600);
    const content = document.createElement("div");
    renderHook(() => useTabStopWhileScrolling(box.element, content));
    expect(FakeResizeObserver.last?.observed).toEqual([box.element, content]);
    box.setContentHeight(900);
    FakeResizeObserver.last?.fire();
    expect(box.element.getAttribute("tabindex")).toBe("0");
    box.setContentHeight(600);
    FakeResizeObserver.last?.fire();
    expect(box.element.hasAttribute("tabindex")).toBe(false);
  });

  it("stops observing when unmounted", () => {
    const { unmount } = renderHook(() => useTabStopWhileScrolling(container(600).element, null));
    unmount();
    expect(FakeResizeObserver.last?.disconnected).toBe(true);
  });
});
