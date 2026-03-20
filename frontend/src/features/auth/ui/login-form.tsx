"use client";

import { useEffect, useState } from "react";
import type { Route } from "next";
import { useRouter } from "next/navigation";

import { ROUTES } from "@/core/config/routes";
import { Button } from "@/design-system/primitives/button";
import { Card } from "@/design-system/primitives/card";
import { Input } from "@/design-system/primitives/input";
import { useLoginMutation } from "@/features/auth/hooks/use-login-mutation";
import { useAuthStore } from "@/features/auth/model/auth-store";
import { isApiClientError } from "@/shared/api/client";

type LoginFormProps = {
  nextPath?: string;
};

export function LoginForm({ nextPath }: LoginFormProps): JSX.Element {
  const router = useRouter();
  const status = useAuthStore((state) => state.status);
  const loginMutation = useLoginMutation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tenantSlug, setTenantSlug] = useState("");

  useEffect(() => {
    if (status === "authenticated") {
      router.replace((nextPath || ROUTES.app) as Route);
    }
  }, [nextPath, router, status]);

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();

    await loginMutation.mutateAsync({
      email,
      password,
      tenantSlug: tenantSlug.trim() || undefined
    });

    const nextRoute = (nextPath || ROUTES.app) as Route;
    router.replace(nextRoute);
  };

  const errorMessage = loginMutation.error
    ? isApiClientError(loginMutation.error)
      ? loginMutation.error.message
      : "Login failed"
    : null;

  return (
    <Card className="w-full max-w-[480px] space-y-3 p-4">
      <header className="space-y-1">
        <h1 className="text-[28px] leading-[36px] font-bold text-neutral-900">Sign in</h1>
        <p className="text-sm text-neutral-600">Use your workspace credentials.</p>
      </header>

      <form className="space-y-2" onSubmit={onSubmit}>
        <div className="space-y-1">
          <label className="text-sm font-medium text-neutral-700" htmlFor="email">
            Email
          </label>
          <Input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>

        <div className="space-y-1">
          <label className="text-sm font-medium text-neutral-700" htmlFor="password">
            Password
          </label>
          <Input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>

        <div className="space-y-1">
          <label className="text-sm font-medium text-neutral-700" htmlFor="tenantSlug">
            Tenant slug (optional)
          </label>
          <Input
            id="tenantSlug"
            name="tenantSlug"
            value={tenantSlug}
            onChange={(event) => setTenantSlug(event.target.value)}
          />
        </div>

        {errorMessage ? <p className="text-sm font-medium text-danger">{errorMessage}</p> : null}

        <Button className="w-full" type="submit" loading={loginMutation.isPending}>
          Sign in
        </Button>
      </form>
    </Card>
  );
}
