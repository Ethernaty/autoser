import { LoginForm } from "@/features/auth/ui/login-form";

type LoginPageProps = {
  searchParams: {
    next?: string;
  };
};

export default function LoginPage({ searchParams }: LoginPageProps): JSX.Element {
  return <LoginForm nextPath={searchParams.next} />;
}
