import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cn } from "@/lib/utils"

export interface ButtonProps
    extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    asChild?: boolean
    variant?: 'primary' | 'secondary' | 'danger'
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
    ({ className, variant = 'primary', asChild = false, ...props }, ref) => {
        const Comp = asChild ? Slot : "button"

        // Variant styles
        const variants = {
            primary: "text-white hover:text-primary-100",
            secondary: "bg-bg-elevated hover:bg-bg-hover text-text-secondary",
            danger: "text-danger hover:text-red-400 border-danger/20 hover:border-danger/50"
        }

        return (
            <Comp
                className={cn(
                    "neu-button flex items-center justify-center",
                    variants[variant],
                    className
                )}
                ref={ref}
                {...props}
            />
        )
    }
)
Button.displayName = "Button"

export { Button }
