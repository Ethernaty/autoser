export default function AuthLayout({ children }: { children: React.ReactNode }): JSX.Element {
  return (
    <div className="min-h-screen bg-neutral-50">
      <main className="mx-auto flex min-h-screen w-full max-w-content items-center justify-center p-4">{children}</main>
    </div>
  );
}
