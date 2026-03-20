"use client";

import { useEffect } from "react";

type RovingFocusOptions = {
  container: React.RefObject<HTMLElement>;
  selector: string;
};

export function useRovingFocus({ container, selector }: RovingFocusOptions): void {
  useEffect(() => {
    const element = container.current;
    if (!element) {
      return;
    }

    const onKeyDown = (event: KeyboardEvent): void => {
      if (event.key !== "ArrowDown" && event.key !== "ArrowUp") {
        return;
      }

      const items = Array.from(element.querySelectorAll<HTMLElement>(selector));
      if (!items.length) {
        return;
      }

      const currentIndex = items.findIndex((item) => item === document.activeElement);
      const nextIndex = event.key === "ArrowDown" ? Math.min(items.length - 1, currentIndex + 1) : Math.max(0, currentIndex - 1);
      const target = items[nextIndex] ?? items[0];
      target.focus();
      event.preventDefault();
    };

    element.addEventListener("keydown", onKeyDown);
    return () => element.removeEventListener("keydown", onKeyDown);
  }, [container, selector]);
}
