"use client";

import React from "react";
import { motion } from "framer-motion";

export function BackgroundBeams() {
    return (
        <div className="fixed inset-0 z-[-1] overflow-hidden pointer-events-none">
            {/* Dark Gradient Overlay */}
            <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[var(--bg-base)]/50 to-[var(--bg-base)]" />

            {/* Moving Blobs */}
            <motion.div
                animate={{
                    x: [0, 100, 0],
                    y: [0, -50, 0],
                    scale: [1, 1.2, 1],
                }}
                transition={{
                    duration: 20,
                    repeat: Infinity,
                    ease: "linear",
                }}
                className="absolute top-[-10%] left-[-10%] w-[40vw] h-[40vw] bg-indigo-600/10 rounded-full blur-[100px]"
            />

            <motion.div
                animate={{
                    x: [0, -100, 0],
                    y: [0, 100, 0],
                    scale: [1, 1.5, 1],
                }}
                transition={{
                    duration: 25,
                    repeat: Infinity,
                    ease: "linear",
                    delay: 2
                }}
                className="absolute bottom-[-10%] right-[-10%] w-[50vw] h-[50vw] bg-blue-600/10 rounded-full blur-[120px]"
            />

            <motion.div
                animate={{
                    x: [0, 50, 0],
                    y: [0, 50, 0],
                }}
                transition={{
                    duration: 15,
                    repeat: Infinity,
                    ease: "linear",
                    delay: 5
                }}
                className="absolute top-[40%] left-[30%] w-[30vw] h-[30vw] bg-purple-600/10 rounded-full blur-[80px]"
            />
        </div>
    );
}
