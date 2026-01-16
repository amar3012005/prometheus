/**
 * Message components for conversation UI
 * Based on ElevenLabs official UI components
 */
import { cn } from "../../lib/utils"
import { forwardRef, HTMLAttributes, ReactNode } from "react"

// ════════════════════════════════════════════════════════════════════════════
// MESSAGE CONTAINER
// ════════════════════════════════════════════════════════════════════════════

interface MessageProps extends HTMLAttributes<HTMLDivElement> {
    from: "user" | "assistant"
    children: ReactNode
}

export const Message = forwardRef<HTMLDivElement, MessageProps>(
    ({ from, className, children, ...props }, ref) => {
        return (
            <div
                ref={ref}
                data-from={from}
                className={cn(
                    "group flex gap-3 w-full",
                    from === "user" ? "flex-row-reverse" : "flex-row",
                    className
                )}
                style={{
                    display: 'flex',
                    gap: '12px',
                    width: '100%',
                    flexDirection: from === 'user' ? 'row-reverse' : 'row',
                    alignItems: 'flex-start'
                }}
                {...props}
            >
                {children}
            </div>
        )
    }
)
Message.displayName = "Message"

// ════════════════════════════════════════════════════════════════════════════
// MESSAGE CONTENT
// ════════════════════════════════════════════════════════════════════════════

interface MessageContentProps extends HTMLAttributes<HTMLDivElement> {
    variant?: "contained" | "flat"
    children: ReactNode
}

export const MessageContent = forwardRef<HTMLDivElement, MessageContentProps>(
    ({ variant = "contained", className, children, ...props }, ref) => {
        return (
            <div
                ref={ref}
                className={cn("message-content", className)}
                style={{
                    padding: variant === 'contained' ? '12px 16px' : '8px 0',
                    borderRadius: '16px',
                    maxWidth: '85%',
                    fontSize: '14px',
                    lineHeight: '1.5',
                    // User messages (when parent has data-from="user")
                    ...(variant === 'contained' && {
                        background: 'var(--msg-bg, #F3F4F6)',
                        border: 'var(--msg-border, 1px solid #E5E5E5)',
                        color: 'var(--msg-color, #333)'
                    }),
                    ...(variant === 'flat' && {
                        background: 'transparent',
                        color: 'var(--msg-color, #333)'
                    })
                }}
                {...props}
            >
                {children}
            </div>
        )
    }
)
MessageContent.displayName = "MessageContent"

// ════════════════════════════════════════════════════════════════════════════
// MESSAGE AVATAR
// ════════════════════════════════════════════════════════════════════════════

interface MessageAvatarProps extends HTMLAttributes<HTMLDivElement> {
    src?: string
    name?: string
    isAgent?: boolean
}

export const MessageAvatar = forwardRef<HTMLDivElement, MessageAvatarProps>(
    ({ src, name, isAgent = false, className, ...props }, ref) => {
        const initials = name ? name.slice(0, 2).toUpperCase() : isAgent ? 'AI' : 'U'

        return (
            <div
                ref={ref}
                className={cn("message-avatar", className)}
                style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    flexShrink: 0,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '11px',
                    fontWeight: '600',
                    background: isAgent
                        ? 'linear-gradient(135deg, #CADCFC, #A0B9D1)'
                        : '#E5E5E5',
                    color: isAgent ? '#4A5568' : '#666',
                    border: '2px solid white',
                    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                    overflow: 'hidden'
                }}
                {...props}
            >
                {src ? (
                    <img
                        src={src}
                        alt={name || "Avatar"}
                        style={{
                            width: '100%',
                            height: '100%',
                            objectFit: 'cover'
                        }}
                    />
                ) : (
                    <span>{initials}</span>
                )}
            </div>
        )
    }
)
MessageAvatar.displayName = "MessageAvatar"

// ════════════════════════════════════════════════════════════════════════════
// CONVERSATION CONTAINER
// ════════════════════════════════════════════════════════════════════════════

interface ConversationProps extends HTMLAttributes<HTMLDivElement> {
    children: ReactNode
}

export const Conversation = forwardRef<HTMLDivElement, ConversationProps>(
    ({ className, children, ...props }, ref) => {
        return (
            <div
                ref={ref}
                className={cn("conversation", className)}
                style={{
                    display: 'flex',
                    flexDirection: 'column',
                    height: '100%',
                    overflow: 'hidden'
                }}
                {...props}
            >
                {children}
            </div>
        )
    }
)
Conversation.displayName = "Conversation"

// ════════════════════════════════════════════════════════════════════════════
// CONVERSATION CONTENT
// ════════════════════════════════════════════════════════════════════════════

interface ConversationContentProps extends HTMLAttributes<HTMLDivElement> {
    children: ReactNode
}

export const ConversationContent = forwardRef<HTMLDivElement, ConversationContentProps>(
    ({ className, children, ...props }, ref) => {
        return (
            <div
                ref={ref}
                className={cn("conversation-content", className)}
                style={{
                    flex: 1,
                    overflowY: 'auto',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '16px',
                    padding: '16px'
                }}
                {...props}
            >
                {children}
            </div>
        )
    }
)
ConversationContent.displayName = "ConversationContent"

export default Message
