import type { PropsWithChildren } from "react";

export function ContentContainer({ children }: PropsWithChildren): JSX.Element {
  return <div className="mx-auto w-full max-w-content px-3 py-3 sm:px-4 sm:py-4 lg:px-5">{children}</div>;
}
