"use client";

import type { PropsWithChildren } from "react";
import { motion, useReducedMotion } from "framer-motion";

import { cn } from "@/core/lib/utils";

type MotionWrapProps = PropsWithChildren<{
  className?: string;
  delay?: number;
  y?: number;
  amount?: number;
}>;

const EASE_STANDARD = [0.22, 1, 0.36, 1] as const;

export function Reveal({ children, className, delay = 0, y = 24, amount = 0.24 }: MotionWrapProps): JSX.Element {
  const reduceMotion = useReducedMotion();

  if (reduceMotion) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount }}
      transition={{ duration: 0.58, ease: EASE_STANDARD, delay }}
    >
      {children}
    </motion.div>
  );
}

type StaggerProps = PropsWithChildren<{
  className?: string;
  delayChildren?: number;
  staggerChildren?: number;
}>;

export function RevealStagger({
  children,
  className,
  delayChildren = 0.04,
  staggerChildren = 0.08
}: StaggerProps): JSX.Element {
  const reduceMotion = useReducedMotion();

  if (reduceMotion) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      className={className}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, amount: 0.2 }}
      variants={{
        hidden: {},
        show: {
          transition: {
            delayChildren,
            staggerChildren
          }
        }
      }}
    >
      {children}
    </motion.div>
  );
}

type StaggerItemProps = PropsWithChildren<{
  className?: string;
  y?: number;
}>;

export function RevealItem({ children, className, y = 20 }: StaggerItemProps): JSX.Element {
  const reduceMotion = useReducedMotion();

  if (reduceMotion) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      className={className}
      variants={{
        hidden: { opacity: 0, y },
        show: { opacity: 1, y: 0 }
      }}
      transition={{ duration: 0.48, ease: EASE_STANDARD }}
    >
      {children}
    </motion.div>
  );
}

type FloatingLayerProps = PropsWithChildren<{
  className?: string;
  duration?: number;
  offset?: number;
}>;

export function FloatingLayer({ children, className, duration = 8, offset = 8 }: FloatingLayerProps): JSX.Element {
  const reduceMotion = useReducedMotion();

  if (reduceMotion) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      className={cn("will-change-transform", className)}
      animate={{ y: [-offset, offset, -offset] }}
      transition={{ duration, ease: "easeInOut", repeat: Infinity }}
    >
      {children}
    </motion.div>
  );
}

type InteractiveScaleProps = PropsWithChildren<{
  className?: string;
}>;

export function InteractiveScale({ children, className }: InteractiveScaleProps): JSX.Element {
  const reduceMotion = useReducedMotion();

  if (reduceMotion) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      className={className}
      whileHover={{ y: -2, scale: 1.01 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}

