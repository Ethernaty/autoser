"use client";

import { type PropsWithChildren } from "react";

export function ZustandProvider({ children }: PropsWithChildren): JSX.Element {
  return <>{children}</>;
}
