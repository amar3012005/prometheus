export default function AnimatedBackground() {
    return (
        <div style={{
            position: 'fixed',
            inset: 0,
            zIndex: 0,
            pointerEvents: 'none',
            overflow: 'hidden',
            background: '#FFFFFF'
        }}>
            {/* Static Dotted Grid Pattern */}
            <div style={{
                position: 'absolute',
                inset: 0,
                backgroundImage: `radial-gradient(circle, #D0D0D0 1px, transparent 1px)`,
                backgroundSize: '24px 24px'
            }} />
        </div>
    );
}
