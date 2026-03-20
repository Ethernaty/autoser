import type { PropsWithChildren } from "react";

export function ContentContainer({ children }: PropsWithChildren): JSX.Element {
  return <div className="mx-auto w-full max-w-content px-3 py-3">{children}</div>;
}

