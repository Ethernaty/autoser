"use client";

import * as React from "react";

import { formatPhoneInput } from "@/core/lib/phone";
import { Input, type InputProps } from "@/design-system/primitives/input";

type PhoneInputProps = Omit<InputProps, "type" | "value" | "onChange" | "inputMode"> & {
  value: string;
  onChange: (value: string) => void;
};

export const PhoneInput = React.forwardRef<HTMLInputElement, PhoneInputProps>(
  ({ value, onChange, ...props }, ref) => {
    return (
      <Input
        ref={ref}
        {...props}
        type="tel"
        inputMode="tel"
        autoComplete="tel"
        placeholder={props.placeholder ?? "+1 555 123 4567"}
        value={value}
        onChange={(event) => onChange(formatPhoneInput(event.target.value))}
      />
    );
  }
);

PhoneInput.displayName = "PhoneInput";
