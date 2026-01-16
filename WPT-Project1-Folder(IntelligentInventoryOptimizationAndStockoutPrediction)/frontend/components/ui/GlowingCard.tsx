"use client";

import React from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface GlowingCardProps extends React.HTMLAttributes<HTMLDivElement> {
    children: React.ReactNode;
    className?: string;
    glowColor?: string;
}

export function GlowingCard({
    children,
    className,
    glowColor = "rgba(99, 102, 241, 0.5)", // default indigo
    ...props
}: GlowingCardProps) {
    return (
        <motion.div
            whileHover={{ y: -5, scale: 1.01 }}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className={cn(
                "relative rounded-xl border border-[var(--border-visible)] bg-[var(--glass-bg)] backdrop-blur-md overflow-hidden group/glow",
                className
            )}
            {...props}
        >
            {/* Moving Border Gradient */}
            <div
                className="absolute inset-0 opacity-0 group-hover/glow:opacity-100 transition-opacity duration-500 pointer-events-none"
                style={{
                    background: `radial-gradient(600px circle at var(--mouse-x, 50%) var(--mouse-y, 50%), ${glowColor}, transparent 40%)`,
                }}
            />

            {/* Inner Border Highlight */}
            <div
                className="absolute inset-[1px] rounded-[11px] bg-[var(--glass-bg)] z-0"
            />

            {/* Content */}
            <div className="relative z-10 h-full p-6">
                {children}
            </div>

            {/* Spotlight Effect helper (requires JS to update variables, implemented simply here with hover) */}
            <div
                className="absolute inset-0 z-0 opacity-0 group-hover/glow:opacity-20 transition-opacity duration-500"
                style={{ background: glowColor }}
            ></div>
        </motion.div>
    );
}
