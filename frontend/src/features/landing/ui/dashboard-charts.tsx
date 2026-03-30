"use client";

import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import { landingVisualData } from "@/features/landing/content";

function ChartTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number; name: string }>; label?: string }): JSX.Element | null {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  return (
    <div className="rounded-[10px] border border-neutral-200 bg-neutral-0 px-[10px] py-[8px] shadow-sm">
      {label ? <p className="text-[11px] uppercase tracking-[0.08em] text-neutral-500">{label}</p> : null}
      {payload.map((item) => (
        <p key={`${item.name}-${item.value}`} className="text-[12px] font-semibold text-neutral-800">
          {item.name}: {item.value}
        </p>
      ))}
    </div>
  );
}

function ChartMountGuard({ children }: { children: React.ReactNode }): JSX.Element {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <div className="h-full w-full" />;
  }

  return <>{children}</>;
}

export function HeroOrdersTrendChart(): JSX.Element {
  return (
    <ChartMountGuard>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={landingVisualData.heroTrend} margin={{ top: 6, right: 6, left: -18, bottom: 0 }}>
          <defs>
            <linearGradient id="heroOrdersGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.24} />
              <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="hsl(var(--neutral-200))" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 11, fill: "hsl(var(--neutral-500))" }} axisLine={false} tickLine={false} />
          <YAxis hide domain={["dataMin - 2", "dataMax + 2"]} />
          <Tooltip content={<ChartTooltip />} cursor={{ stroke: "hsl(var(--primary))", strokeOpacity: 0.25 }} />
          <Area type="monotone" dataKey="orders" stroke="hsl(var(--primary))" strokeWidth={2.2} fill="url(#heroOrdersGradient)" />
        </AreaChart>
      </ResponsiveContainer>
    </ChartMountGuard>
  );
}

export function StatusDistributionChart(): JSX.Element {
  return (
    <ChartMountGuard>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={landingVisualData.statusDistribution}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius={32}
            outerRadius={56}
            paddingAngle={3}
            stroke="none"
          >
            {landingVisualData.statusDistribution.map((segment) => (
              <Cell key={segment.name} fill={segment.color} />
            ))}
          </Pie>
          <Tooltip content={<ChartTooltip />} />
        </PieChart>
      </ResponsiveContainer>
    </ChartMountGuard>
  );
}

export function PayrollBarChart(): JSX.Element {
  return (
    <ChartMountGuard>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={landingVisualData.payrollBars} margin={{ top: 6, right: 8, left: -20, bottom: 0 }}>
          <CartesianGrid stroke="hsl(var(--neutral-200))" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 11, fill: "hsl(var(--neutral-500))" }} axisLine={false} tickLine={false} />
          <YAxis
            tick={{ fontSize: 11, fill: "hsl(var(--neutral-500))" }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(value) => `${value}k`}
          />
          <Tooltip content={<ChartTooltip />} />
          <Bar dataKey="payout" fill="hsl(var(--primary))" radius={[6, 6, 0, 0]} maxBarSize={28} />
        </BarChart>
      </ResponsiveContainer>
    </ChartMountGuard>
  );
}

export function ReturnDynamicsChart(): JSX.Element {
  return (
    <ChartMountGuard>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={landingVisualData.returnDynamics} margin={{ top: 6, right: 6, left: -18, bottom: 0 }}>
          <defs>
            <linearGradient id="returnGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="hsl(var(--success))" stopOpacity={0.24} />
              <stop offset="100%" stopColor="hsl(var(--success))" stopOpacity={0.03} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="hsl(var(--neutral-200))" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 11, fill: "hsl(var(--neutral-500))" }} axisLine={false} tickLine={false} />
          <YAxis hide />
          <Tooltip content={<ChartTooltip />} />
          <Area type="monotone" dataKey="value" stroke="hsl(var(--success))" strokeWidth={2} fill="url(#returnGradient)" />
        </AreaChart>
      </ResponsiveContainer>
    </ChartMountGuard>
  );
}

export function OrderFlowChart(): JSX.Element {
  return (
    <ChartMountGuard>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={landingVisualData.orderFlow} layout="vertical" margin={{ top: 6, right: 8, left: 8, bottom: 0 }}>
          <CartesianGrid stroke="hsl(var(--neutral-200))" strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" hide />
          <YAxis
            dataKey="step"
            type="category"
            tick={{ fontSize: 11, fill: "hsl(var(--neutral-500))" }}
            axisLine={false}
            tickLine={false}
            width={74}
          />
          <Tooltip content={<ChartTooltip />} />
          <Bar dataKey="value" fill="hsl(var(--primary))" radius={[0, 6, 6, 0]} maxBarSize={20} />
        </BarChart>
      </ResponsiveContainer>
    </ChartMountGuard>
  );
}
