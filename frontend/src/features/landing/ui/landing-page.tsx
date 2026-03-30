"use client";

import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import {
  AlertTriangle,
  ArrowRight,
  Calculator,
  Car,
  CheckCircle2,
  ClipboardList,
  Clock3,
  FileText,
  Gauge,
  History,
  Mail,
  MessageCircle,
  Monitor,
  Phone,
  ShieldCheck,
  UserCog,
  Users,
  Wallet,
  Wrench
} from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";

import { cn } from "@/core/lib/utils";
import { ROUTES } from "@/core/config/routes";
import { landingContent, type LandingIcon } from "@/features/landing/content";
import {
  HeroOrdersTrendChart,
  OrderFlowChart,
  PayrollBarChart,
  ReturnDynamicsChart,
  StatusDistributionChart
} from "@/features/landing/ui/dashboard-charts";
import { InteractiveScale, Reveal, RevealItem, RevealStagger } from "@/features/landing/ui/motion-primitives";

const iconMap: Record<LandingIcon, LucideIcon> = {
  users: Users,
  car: Car,
  clipboard: ClipboardList,
  userCog: UserCog,
  calculator: Calculator,
  history: History,
  alert: AlertTriangle,
  clock: Clock3,
  gauge: Gauge,
  monitor: Monitor,
  wallet: Wallet,
  wrench: Wrench,
  shield: ShieldCheck,
  fileText: FileText
};

const primaryCtaClass =
  "group inline-flex h-[44px] items-center justify-center rounded-[10px] border border-primary/20 bg-primary px-[20px] text-[14px] font-semibold text-primary-foreground shadow-sm shadow-primary/20 transition-colors duration-150 hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/35";
const secondaryCtaClass =
  "inline-flex h-[44px] items-center justify-center rounded-[10px] border border-neutral-300 bg-neutral-0/90 px-[20px] text-[14px] font-semibold text-neutral-900 transition-colors duration-150 hover:border-neutral-400 hover:bg-neutral-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/35";

function SectionIntro({ title, subtitle, align = "left" }: { title: string; subtitle?: string; align?: "left" | "center" }): JSX.Element {
  return (
    <div className={cn("space-y-[12px]", align === "center" ? "mx-auto max-w-[760px] text-center" : "max-w-[760px]")}>
      <h2 className="text-[30px] font-semibold leading-[38px] tracking-[-0.02em] text-neutral-900 md:text-[38px] md:leading-[46px]">{title}</h2>
      {subtitle ? <p className="text-[16px] leading-[26px] text-neutral-600">{subtitle}</p> : null}
    </div>
  );
}

function StatusPill({ status }: { status: "new" | "in_progress" | "ready" }): JSX.Element {
  const statusConfig =
    status === "ready"
      ? { label: "Готово", className: "border-success/30 bg-success/10 text-success" }
      : status === "in_progress"
        ? { label: "В работе", className: "border-warning/30 bg-warning/10 text-warning" }
        : { label: "Новый", className: "border-primary/30 bg-primary/10 text-primary" };

  return (
    <span className={cn("inline-flex items-center rounded-full border px-[10px] py-[2px] text-[12px] font-medium leading-[16px]", statusConfig.className)}>
      {statusConfig.label}
    </span>
  );
}

function MotionLinkButton({
  href,
  className,
  children,
  onClick
}: {
  href: string;
  className: string;
  children: React.ReactNode;
  onClick?: (event: React.MouseEvent<HTMLAnchorElement>) => void;
}): JSX.Element {
  const reduceMotion = useReducedMotion();
  return (
    <motion.span whileHover={reduceMotion ? undefined : { y: -1, scale: 1.01 }} whileTap={reduceMotion ? undefined : { scale: 0.99 }}>
      <a href={href} className={className} onClick={onClick}>
        {children}
      </a>
    </motion.span>
  );
}

function AnimatedBackground(): JSX.Element {
  const reduceMotion = useReducedMotion();

  return (
    <>
      <motion.div
        className="pointer-events-none absolute left-1/2 top-[-260px] h-[540px] w-[900px] -translate-x-1/2 rounded-full bg-primary/15 blur-3xl"
        animate={reduceMotion ? undefined : { scale: [1, 1.08, 1], opacity: [0.45, 0.72, 0.45] }}
        transition={reduceMotion ? undefined : { duration: 12, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="pointer-events-none absolute right-[-120px] top-[420px] h-[360px] w-[360px] rounded-full bg-neutral-200/75 blur-3xl"
        animate={reduceMotion ? undefined : { y: [0, -22, 0], opacity: [0.6, 0.85, 0.6] }}
        transition={reduceMotion ? undefined : { duration: 14, repeat: Infinity, ease: "easeInOut" }}
      />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,rgba(248,250,252,0.72)_0%,rgba(248,250,252,1)_30%)]" />
    </>
  );
}

export function LandingPage(): JSX.Element {
  const reduceMotion = useReducedMotion();
  const handleAnchorNavigation = (event: React.MouseEvent<HTMLAnchorElement>, href: string): void => {
    if (!href.startsWith("#")) {
      return;
    }

    const target = document.querySelector<HTMLElement>(href);
    if (!target) {
      return;
    }

    event.preventDefault();
    const header = document.querySelector<HTMLElement>("[data-landing-header='true']");
    const headerOffset = (header?.offsetHeight ?? 72) + 12;
    const targetTop = target.getBoundingClientRect().top + window.scrollY - headerOffset;
    window.history.replaceState(null, "", href);
    window.scrollTo({
      top: targetTop,
      behavior: reduceMotion ? "auto" : "smooth"
    });
  };
  const getAnchorClickHandler = (href: string): ((event: React.MouseEvent<HTMLAnchorElement>) => void) | undefined =>
    href.startsWith("#") ? (event) => handleAnchorNavigation(event, href) : undefined;

  return (
    <div className="landing-theme relative min-h-screen overflow-x-clip bg-neutral-50">
      <AnimatedBackground />

      <header data-landing-header="true" className="sticky top-0 z-50 border-b border-neutral-200/80 bg-neutral-0/85 backdrop-blur-xl">
        <div className="mx-auto flex w-full max-w-content items-center justify-between px-[16px] py-[12px] md:px-[24px]">
          <InteractiveScale>
            <Link href="/" className="flex items-center gap-[10px]">
              <span className="inline-flex h-[36px] w-[36px] items-center justify-center rounded-[10px] bg-primary text-[13px] font-bold text-primary-foreground shadow-sm shadow-primary/30">AS</span>
              <div className="leading-none">
                <p className="text-[15px] font-semibold text-neutral-900">{landingContent.brand.name}</p>
                <p className="text-[12px] text-neutral-500">{landingContent.brand.tagline}</p>
              </div>
            </Link>
          </InteractiveScale>

          <nav className="hidden items-center gap-[20px] lg:flex" aria-label="Разделы лендинга">
            {landingContent.navigation.map((item) => (
              <motion.div key={item.href} whileHover={reduceMotion ? undefined : { y: -1 }}>
                <a
                  href={item.href}
                  onClick={getAnchorClickHandler(item.href)}
                  className="relative text-[14px] font-medium text-neutral-600 transition-colors hover:text-neutral-900 after:absolute after:bottom-[-5px] after:left-0 after:h-[2px] after:w-0 after:rounded-full after:bg-primary after:transition-all after:duration-200 hover:after:w-full"
                >
                  {item.label}
                </a>
              </motion.div>
            ))}
          </nav>

          <div className="flex items-center gap-[8px]">
            <motion.div whileHover={reduceMotion ? undefined : { y: -1 }}>
              <Link href={ROUTES.login} className="hidden text-[14px] font-semibold text-neutral-700 transition-colors hover:text-neutral-900 sm:inline-flex">
                {landingContent.cta.secondaryLabel}
              </Link>
            </motion.div>
            <MotionLinkButton href={landingContent.cta.href} className={primaryCtaClass} onClick={getAnchorClickHandler(landingContent.cta.href)}>
              {landingContent.cta.label}
            </MotionLinkButton>
          </div>
        </div>
      </header>

      <main className="relative z-10">
        <section className="relative">
          <div className="mx-auto grid w-full max-w-content gap-[32px] px-[16px] pb-[72px] pt-[56px] md:px-[24px] md:pb-[96px] md:pt-[88px] lg:grid-cols-[1.04fr_0.96fr] lg:gap-[40px]">
            <Reveal className="space-y-[24px]" y={18}>
              <span className="inline-flex items-center rounded-full border border-neutral-300 bg-neutral-0/90 px-[12px] py-[6px] text-[12px] font-semibold uppercase tracking-[0.08em] text-neutral-600 shadow-sm">
                {landingContent.brand.tagline}
              </span>
              <h1 className="max-w-[800px] text-[36px] font-semibold leading-[44px] tracking-[-0.03em] text-neutral-900 md:text-[54px] md:leading-[60px]">{landingContent.hero.title}</h1>
              <p className="max-w-[700px] text-[17px] leading-[28px] text-neutral-600">{landingContent.hero.subtitle}</p>

              <div className="flex flex-wrap items-center gap-[12px]">
                <MotionLinkButton href={landingContent.cta.href} className={primaryCtaClass} onClick={getAnchorClickHandler(landingContent.cta.href)}>
                  {landingContent.cta.label}
                  <ArrowRight className="ml-[8px] h-[16px] w-[16px] transition-transform duration-200 group-hover:translate-x-[2px]" aria-hidden />
                </MotionLinkButton>
                <MotionLinkButton href="#preview" className={secondaryCtaClass} onClick={getAnchorClickHandler("#preview")}>
                  Посмотреть интерфейс
                </MotionLinkButton>
              </div>

              <RevealStagger className="grid gap-[10px] sm:grid-cols-2">
                {landingContent.hero.proofPoints.map((point) => (
                  <RevealItem key={point}>
                    <InteractiveScale>
                      <li className="flex items-start gap-[8px] rounded-[10px] border border-neutral-200 bg-neutral-0/95 p-[12px] text-[14px] leading-[20px] text-neutral-700 shadow-sm">
                        <CheckCircle2 className="mt-[2px] h-[16px] w-[16px] shrink-0 text-primary" aria-hidden />
                        <span>{point}</span>
                      </li>
                    </InteractiveScale>
                  </RevealItem>
                ))}
              </RevealStagger>
            </Reveal>

            <Reveal className="relative" delay={0.06}>
              <div className="relative z-10 rounded-[20px] border border-neutral-200 bg-neutral-0/95 p-[18px] shadow-[0_20px_60px_rgba(15,23,42,0.12)] md:p-[24px]">
                <div className="mb-[16px] flex items-center justify-between">
                  <div>
                    <p className="text-[15px] font-semibold text-neutral-900">Операционная панель сервиса</p>
                    <p className="text-[13px] text-neutral-500">Сегодня, 30 марта</p>
                  </div>
                  <div className="flex items-center gap-[8px]">
                    <span className="hidden rounded-full border border-neutral-300 bg-neutral-50 px-[10px] py-[4px] text-[12px] font-medium text-neutral-600 sm:inline-flex">
                      Возврат клиентов +18%
                    </span>
                    <span className="inline-flex rounded-full border border-primary/25 bg-primary/10 px-[10px] py-[4px] text-[12px] font-medium text-primary">Онлайн</span>
                  </div>
                </div>

                <RevealStagger className="grid gap-[10px] sm:grid-cols-3">
                  {landingContent.hero.preview.kpis.map((kpi) => (
                    <RevealItem key={kpi.label}>
                      <article className="rounded-[12px] border border-neutral-200 bg-neutral-50/95 p-[12px] transition-colors duration-150 hover:border-neutral-300 hover:bg-neutral-0">
                        <p className="text-[12px] leading-[16px] text-neutral-500">{kpi.label}</p>
                        <p className="mt-[8px] text-[24px] font-semibold leading-[30px] text-neutral-900">{kpi.value}</p>
                      </article>
                    </RevealItem>
                  ))}
                </RevealStagger>

                <div className="mt-[14px] rounded-[12px] border border-neutral-200 bg-neutral-50/90 p-[10px]">
                  <div className="flex items-center justify-between pb-[6px]">
                    <p className="text-[12px] font-semibold uppercase tracking-[0.08em] text-neutral-500">Динамика заказов</p>
                    <span className="text-[12px] font-semibold text-primary">Неделя</span>
                  </div>
                  <div className="h-[148px]">
                    <HeroOrdersTrendChart />
                  </div>
                </div>

                <div className="mt-[16px] rounded-[12px] border border-neutral-200 bg-neutral-0">
                  <div className="flex items-center justify-between border-b border-neutral-200 px-[12px] py-[10px]">
                    <p className="text-[13px] font-semibold text-neutral-700">Активные заказ-наряды</p>
                    <Link href={ROUTES.login} className="text-[12px] font-semibold text-primary transition-colors hover:text-primary/80">
                      Открыть сервис
                    </Link>
                  </div>
                  <ul className="divide-y divide-neutral-200">
                    {landingContent.hero.preview.activeOrders.map((order) => (
                      <motion.li
                        key={order.code}
                        className="flex items-start justify-between gap-[12px] px-[12px] py-[10px]"
                        whileHover={reduceMotion ? undefined : { backgroundColor: "hsl(var(--neutral-50))" }}
                        transition={{ duration: 0.18 }}
                      >
                        <div className="space-y-[2px]">
                          <p className="text-[13px] font-semibold text-neutral-900">{order.code}</p>
                          <p className="text-[12px] text-neutral-600">{order.client}</p>
                          <p className="text-[12px] text-neutral-500">{order.car}</p>
                        </div>
                        <StatusPill status={order.status} />
                      </motion.li>
                    ))}
                  </ul>
                </div>
              </div>
            </Reveal>
          </div>
        </section>
        <section id="pain" className="border-y border-neutral-200 bg-neutral-100/70">
          <div className="mx-auto w-full max-w-content px-[16px] py-[72px] md:px-[24px] md:py-[96px]">
            <Reveal>
              <SectionIntro title={landingContent.pain.title} subtitle={landingContent.pain.subtitle} />
            </Reveal>
            <RevealStagger className="mt-[32px] grid gap-[12px] md:grid-cols-2 xl:grid-cols-3">
              {landingContent.pain.items.map((item) => {
                const Icon = iconMap[item.icon];
                return (
                  <RevealItem key={item.title}>
                    <InteractiveScale>
                      <article className="rounded-[14px] border border-neutral-200 bg-neutral-0/95 p-[16px] shadow-sm">
                        <div className="mb-[12px] inline-flex h-[32px] w-[32px] items-center justify-center rounded-[8px] bg-error/10 text-error">
                          <Icon className="h-[16px] w-[16px]" aria-hidden />
                        </div>
                        <h3 className="text-[18px] font-semibold leading-[24px] text-neutral-900">{item.title}</h3>
                        <p className="mt-[8px] text-[15px] leading-[24px] text-neutral-600">{item.description}</p>
                      </article>
                    </InteractiveScale>
                  </RevealItem>
                );
              })}
            </RevealStagger>
          </div>
        </section>

        <section id="solution">
          <div className="mx-auto w-full max-w-content px-[16px] py-[72px] md:px-[24px] md:py-[96px]">
            <Reveal>
              <SectionIntro title={landingContent.solution.title} subtitle={landingContent.solution.subtitle} />
            </Reveal>
            <RevealStagger className="mt-[32px] grid gap-[12px] lg:grid-cols-3">
              {landingContent.solution.pillars.map((pillar) => {
                const Icon = iconMap[pillar.icon];
                return (
                  <RevealItem key={pillar.title}>
                    <InteractiveScale>
                      <article className="rounded-[14px] border border-neutral-200 bg-neutral-0/95 p-[18px] shadow-sm">
                        <div className="mb-[16px] inline-flex h-[36px] w-[36px] items-center justify-center rounded-[10px] bg-primary/10 text-primary">
                          <Icon className="h-[18px] w-[18px]" aria-hidden />
                        </div>
                        <h3 className="text-[19px] font-semibold leading-[26px] text-neutral-900">{pillar.title}</h3>
                        <p className="mt-[8px] text-[15px] leading-[24px] text-neutral-600">{pillar.description}</p>
                      </article>
                    </InteractiveScale>
                  </RevealItem>
                );
              })}
            </RevealStagger>
          </div>
        </section>

        <section id="features" className="bg-neutral-100/55">
          <div className="mx-auto w-full max-w-content px-[16px] py-[72px] md:px-[24px] md:py-[96px]">
            <Reveal>
              <SectionIntro title={landingContent.features.title} />
            </Reveal>
            <RevealStagger className="mt-[32px] grid gap-[12px] md:grid-cols-2 xl:grid-cols-3">
              {landingContent.features.items.map((feature) => {
                const Icon = iconMap[feature.icon];
                return (
                  <RevealItem key={feature.title}>
                    <InteractiveScale>
                      <article className="rounded-[14px] border border-neutral-200 bg-neutral-0/95 p-[16px] shadow-sm">
                        <div className="mb-[12px] inline-flex h-[32px] w-[32px] items-center justify-center rounded-[8px] bg-primary/10 text-primary">
                          <Icon className="h-[16px] w-[16px]" aria-hidden />
                        </div>
                        <h3 className="text-[18px] font-semibold leading-[24px] text-neutral-900">{feature.title}</h3>
                        <p className="mt-[8px] text-[15px] leading-[24px] text-neutral-600">{feature.description}</p>
                      </article>
                    </InteractiveScale>
                  </RevealItem>
                );
              })}
            </RevealStagger>
          </div>
        </section>

        <section id="workflow">
          <div className="mx-auto w-full max-w-content px-[16px] py-[72px] md:px-[24px] md:py-[96px]">
            <Reveal>
              <SectionIntro title={landingContent.workflow.title} />
            </Reveal>
            <RevealStagger className="mt-[32px] grid gap-[12px] md:grid-cols-2 xl:grid-cols-5">
              {landingContent.workflow.steps.map((item) => (
                <RevealItem key={item.step}>
                  <InteractiveScale>
                    <li className="rounded-[14px] border border-neutral-200 bg-neutral-0/95 p-[16px] shadow-sm">
                      <span className="inline-flex h-[32px] min-w-[32px] items-center justify-center rounded-full border border-primary/20 bg-primary/10 px-[10px] text-[12px] font-semibold text-primary">{item.step}</span>
                      <h3 className="mt-[12px] text-[17px] font-semibold leading-[24px] text-neutral-900">{item.title}</h3>
                      <p className="mt-[8px] text-[14px] leading-[22px] text-neutral-600">{item.description}</p>
                    </li>
                  </InteractiveScale>
                </RevealItem>
              ))}
            </RevealStagger>
          </div>
        </section>

        <section id="benefits" className="border-y border-neutral-200 bg-neutral-100/65">
          <div className="mx-auto w-full max-w-content px-[16px] py-[72px] md:px-[24px] md:py-[96px]">
            <Reveal>
              <SectionIntro title={landingContent.benefits.title} />
            </Reveal>
            <div className="mt-[32px] grid gap-[12px] lg:grid-cols-[1.2fr_0.8fr]">
              <RevealStagger className="grid gap-[12px] md:grid-cols-2">
                {landingContent.benefits.items.map((item) => {
                  const Icon = iconMap[item.icon];
                  return (
                    <RevealItem key={item.title}>
                      <InteractiveScale>
                        <article className="rounded-[14px] border border-neutral-200 bg-neutral-0/95 p-[16px] shadow-sm">
                          <div className="mb-[12px] inline-flex h-[32px] w-[32px] items-center justify-center rounded-[8px] bg-success/10 text-success">
                            <Icon className="h-[16px] w-[16px]" aria-hidden />
                          </div>
                          <h3 className="text-[18px] font-semibold leading-[24px] text-neutral-900">{item.title}</h3>
                          <p className="mt-[8px] text-[15px] leading-[24px] text-neutral-600">{item.description}</p>
                        </article>
                      </InteractiveScale>
                    </RevealItem>
                  );
                })}
              </RevealStagger>

              <Reveal>
                <aside className="rounded-[14px] border border-neutral-200 bg-neutral-0/95 p-[20px] shadow-[0_14px_40px_rgba(15,23,42,0.10)]">
                  <p className="text-[14px] font-semibold uppercase tracking-[0.06em] text-neutral-500">Результат для владельца</p>
                  <p className="mt-[12px] text-[28px] font-semibold leading-[36px] tracking-[-0.02em] text-neutral-900">Понятная и управляемая ежедневная работа сервиса</p>
                  <p className="mt-[12px] text-[15px] leading-[24px] text-neutral-600">
                    Вместо постоянного ручного контроля и поиска информации вы получаете рабочую систему, где ключевые данные и статусы всегда перед глазами.
                  </p>
                  <div className="mt-[16px] rounded-[12px] border border-neutral-200 bg-neutral-50/90 p-[10px]">
                    <p className="text-[12px] font-semibold uppercase tracking-[0.08em] text-neutral-500">Структура статусов заказов</p>
                    <div className="h-[154px]">
                      <StatusDistributionChart />
                    </div>
                  </div>
                  <div className="mt-[18px]">
                    <MotionLinkButton href={landingContent.cta.href} className={cn(primaryCtaClass, "w-full")} onClick={getAnchorClickHandler(landingContent.cta.href)}>
                      {landingContent.cta.label}
                    </MotionLinkButton>
                  </div>
                </aside>
              </Reveal>
            </div>
          </div>
        </section>
        <section id="preview">
          <div className="mx-auto w-full max-w-content px-[16px] py-[72px] md:px-[24px] md:py-[96px]">
            <Reveal>
              <SectionIntro title={landingContent.preview.title} subtitle={landingContent.preview.subtitle} align="center" />
            </Reveal>

            <RevealStagger className="mt-[32px] grid gap-[12px] md:grid-cols-2">
              {landingContent.preview.cards.map((card, index) => (
                <RevealItem key={card.title}>
                  <InteractiveScale>
                    <article className="rounded-[14px] border border-neutral-200 bg-neutral-0/95 p-[16px] shadow-sm">
                      <div className="mb-[12px] flex items-center justify-between">
                        <div>
                          <h3 className="text-[18px] font-semibold leading-[24px] text-neutral-900">{card.title}</h3>
                          <p className="text-[13px] text-neutral-500">{card.label}</p>
                        </div>
                        <span className="inline-flex rounded-full border border-neutral-200 bg-neutral-50 px-[10px] py-[3px] text-[12px] font-medium text-neutral-600">Рабочий экран</span>
                      </div>
                      <div className="rounded-[12px] border border-neutral-200 bg-neutral-50/95">
                        <ul className="divide-y divide-neutral-200">
                          {card.rows.map((row) => (
                            <li key={`${card.title}-${row.name}`} className="grid grid-cols-[1fr_auto] gap-[16px] px-[12px] py-[10px]">
                              <span className="text-[13px] text-neutral-600">{row.name}</span>
                              <span className="text-[13px] font-semibold text-neutral-900">{row.value}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                      {index === 3 ? (
                        <div className="mt-[12px] rounded-[12px] border border-neutral-200 bg-neutral-50/90 p-[10px]">
                          <p className="text-[12px] font-semibold uppercase tracking-[0.08em] text-neutral-500">Сумма выплат по сотрудникам</p>
                          <div className="h-[148px]">
                            <PayrollBarChart />
                          </div>
                        </div>
                      ) : null}
                    </article>
                  </InteractiveScale>
                </RevealItem>
              ))}

              <RevealItem>
                <InteractiveScale>
                  <article className="rounded-[14px] border border-neutral-200 bg-neutral-0/95 p-[16px] shadow-sm">
                    <div className="mb-[12px] flex items-center justify-between">
                      <div>
                        <h3 className="text-[18px] font-semibold leading-[24px] text-neutral-900">Динамика возврата клиентов</h3>
                        <p className="text-[13px] text-neutral-500">Иллюстрация интерфейса CRM</p>
                      </div>
                    </div>
                    <div className="h-[182px] rounded-[12px] border border-neutral-200 bg-neutral-50/90 p-[10px]">
                      <ReturnDynamicsChart />
                    </div>
                  </article>
                </InteractiveScale>
              </RevealItem>

              <RevealItem>
                <InteractiveScale>
                  <article className="rounded-[14px] border border-neutral-200 bg-neutral-0/95 p-[16px] shadow-sm">
                    <div className="mb-[12px] flex items-center justify-between">
                      <div>
                        <h3 className="text-[18px] font-semibold leading-[24px] text-neutral-900">Поток статусов заказа</h3>
                        <p className="text-[13px] text-neutral-500">Приёмка → диагностика → ремонт → выдача</p>
                      </div>
                    </div>
                    <div className="h-[182px] rounded-[12px] border border-neutral-200 bg-neutral-50/90 p-[10px]">
                      <OrderFlowChart />
                    </div>
                  </article>
                </InteractiveScale>
              </RevealItem>
            </RevealStagger>
          </div>
        </section>

        <section id="audience" className="bg-neutral-100/65">
          <div className="mx-auto w-full max-w-content px-[16px] py-[72px] md:px-[24px] md:py-[96px]">
            <Reveal>
              <SectionIntro title={landingContent.audience.title} />
            </Reveal>
            <RevealStagger className="mt-[32px] grid gap-[12px] md:grid-cols-2">
              {landingContent.audience.items.map((item) => {
                const Icon = iconMap[item.icon];
                return (
                  <RevealItem key={item.title}>
                    <InteractiveScale>
                      <article className="rounded-[14px] border border-neutral-200 bg-neutral-0/95 p-[16px] shadow-sm">
                        <div className="mb-[12px] inline-flex h-[32px] w-[32px] items-center justify-center rounded-[8px] bg-primary/10 text-primary">
                          <Icon className="h-[16px] w-[16px]" aria-hidden />
                        </div>
                        <h3 className="text-[18px] font-semibold leading-[24px] text-neutral-900">{item.title}</h3>
                        <p className="mt-[8px] text-[15px] leading-[24px] text-neutral-600">{item.description}</p>
                      </article>
                    </InteractiveScale>
                  </RevealItem>
                );
              })}
            </RevealStagger>
          </div>
        </section>

        <section id="faq">
          <div className="mx-auto w-full max-w-content px-[16px] py-[72px] md:px-[24px] md:py-[96px]">
            <Reveal>
              <SectionIntro title={landingContent.faq.title} />
            </Reveal>
            <RevealStagger className="mt-[24px] space-y-[10px]" staggerChildren={0.05}>
              {landingContent.faq.items.map((item) => (
                <RevealItem key={item.question} y={14}>
                  <motion.details className="group rounded-[12px] border border-neutral-200 bg-neutral-0/95 p-[14px] shadow-sm transition-colors hover:border-neutral-300" whileHover={reduceMotion ? undefined : { y: -1 }}>
                    <summary className="cursor-pointer list-none text-[16px] font-semibold leading-[24px] text-neutral-900">
                      <span className="inline-flex items-center gap-[10px]">
                        <span className="inline-flex h-[20px] w-[20px] items-center justify-center rounded-full bg-primary/10 text-[12px] font-bold text-primary">?</span>
                        {item.question}
                      </span>
                    </summary>
                    <p className="pt-[10px] text-[15px] leading-[24px] text-neutral-600">{item.answer}</p>
                  </motion.details>
                </RevealItem>
              ))}
            </RevealStagger>
          </div>
        </section>

        <section id="request-demo" className="relative border-y border-[#193461] text-white" style={{ backgroundColor: "#081428" }}>
          <motion.div
            className="pointer-events-none absolute inset-0 bg-[radial-gradient(80%_60%_at_50%_10%,rgba(29,78,216,0.28),rgba(17,24,39,0.05)_50%,rgba(17,24,39,0)_100%)]"
            animate={reduceMotion ? undefined : { opacity: [0.7, 0.95, 0.7] }}
            transition={reduceMotion ? undefined : { duration: 9, repeat: Infinity, ease: "easeInOut" }}
          />

          <div className="relative mx-auto grid w-full max-w-content gap-[24px] px-[16px] py-[72px] md:grid-cols-[1fr_auto] md:px-[24px] md:py-[88px]">
            <Reveal className="max-w-[780px]">
              <p className="text-[13px] font-semibold uppercase tracking-[0.08em] text-slate-300">Финальный шаг</p>
              <h2 className="mt-[10px] text-[34px] font-semibold leading-[42px] tracking-[-0.02em] text-white md:text-[44px] md:leading-[50px]">{landingContent.finalCta.title}</h2>
              <p className="mt-[14px] text-[16px] leading-[26px] text-slate-300">{landingContent.finalCta.subtitle}</p>
            </Reveal>
            <Reveal className="flex items-start" delay={0.06}>
              <MotionLinkButton href={ROUTES.login} className={secondaryCtaClass}>
                {landingContent.cta.secondaryLabel}
              </MotionLinkButton>
            </Reveal>
          </div>

          <div className="relative mx-auto w-full max-w-content px-[16px] pb-[72px] md:px-[24px] md:pb-[88px]">
            <Reveal className="rounded-[16px] border border-[#24456f] bg-[#0b1b36]/85 p-[18px] shadow-[0_18px_44px_rgba(2,6,23,0.42)] md:p-[22px]">
              <div className="flex flex-wrap items-center gap-[10px]">
                <MotionLinkButton href="mailto:sales@autoservice-crm.example?subject=Запрос%20демо%20AutoService%20CRM" className={primaryCtaClass}>
                  {landingContent.cta.label}
                  <ArrowRight className="ml-[8px] h-[16px] w-[16px] transition-transform duration-200 group-hover:translate-x-[2px]" aria-hidden />
                </MotionLinkButton>
                <span className="rounded-[8px] border border-[#2a4a73] bg-[#081428]/70 px-[10px] py-[8px] text-[12px] text-slate-300">
                  Ответим с шагами запуска и персональным демонстрационным сценарием
                </span>
              </div>

              <RevealStagger className="mt-[18px] grid gap-[10px] md:grid-cols-3" staggerChildren={0.06}>
                {landingContent.finalCta.contacts.map((contact) => {
                  const iconByLabel = contact.label === "Email" ? Mail : contact.label === "Телефон" ? Phone : MessageCircle;
                  const Icon = iconByLabel;
                  return (
                    <RevealItem key={contact.label}>
                      <InteractiveScale>
                        <article className="rounded-[12px] border border-[#2a4a73] bg-[#0b1b36]/70 p-[12px]">
                          <p className="flex items-center gap-[8px] text-[12px] uppercase tracking-[0.08em] text-slate-400">
                            <Icon className="h-[14px] w-[14px]" aria-hidden />
                            {contact.label}
                          </p>
                          <a href={contact.href} className="mt-[6px] inline-flex text-[14px] leading-[22px] text-white transition-opacity hover:opacity-80">
                            {contact.value}
                          </a>
                        </article>
                      </InteractiveScale>
                    </RevealItem>
                  );
                })}
              </RevealStagger>

              <p className="mt-[12px] text-[12px] text-slate-400">{landingContent.finalCta.contactNote}</p>
            </Reveal>
          </div>
        </section>
      </main>
    </div>
  );
}

