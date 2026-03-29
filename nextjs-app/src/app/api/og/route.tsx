import { ImageResponse } from 'next/og';

// Use Node.js runtime for standalone compatibility
export const dynamic = 'force-dynamic';

const BG = 'linear-gradient(145deg, #03060a 0%, #0a1220 42%, #0c1628 100%)';
const CYAN = '#36e4ff';
const CYAN_SOFT = '#7aefff';
const MINT = '#5ef5c4';
const TEXT = '#eef3f8';
const MUTED = '#8fa3b8';

export async function GET() {
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: BG,
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            opacity: 0.07,
            backgroundImage:
              `linear-gradient(rgba(54,228,255,0.35) 1px, transparent 1px), linear-gradient(90deg, rgba(54,228,255,0.35) 1px, transparent 1px)`,
            backgroundSize: '44px 44px',
          }}
        />

        <div
          style={{
            position: 'absolute',
            width: 560,
            height: 560,
            borderRadius: '50%',
            background: `radial-gradient(circle, rgba(54,228,255,0.14) 0%, rgba(155,135,255,0.08) 35%, transparent 68%)`,
            top: '46%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            display: 'flex',
          }}
        />

        <div
          style={{
            position: 'absolute',
            right: 72,
            top: '50%',
            transform: 'translateY(-50%)',
            width: 200,
            height: 200,
            display: 'flex',
            flexDirection: 'column',
            opacity: 0.14,
            borderRadius: 24,
            overflow: 'hidden',
          }}
        >
          <div style={{ flex: 1, background: '#005BBB', display: 'flex' }} />
          <div style={{ flex: 1, background: '#FFD500', display: 'flex' }} />
        </div>

        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'flex-start',
            padding: '56px 76px',
            width: '100%',
            position: 'relative',
          }}
        >
          <div
            style={{
              fontSize: 62,
              fontWeight: 800,
              letterSpacing: '14px',
              background: `linear-gradient(92deg, ${CYAN}, ${CYAN_SOFT}, #b8a3ff)`,
              backgroundClip: 'text',
              color: 'transparent',
              marginBottom: 18,
              display: 'flex',
            }}
          >
            NEPTUN
          </div>

          <div
            style={{
              fontSize: 36,
              fontWeight: 600,
              color: TEXT,
              lineHeight: 1.28,
              maxWidth: 720,
              marginBottom: 14,
              display: 'flex',
            }}
          >
            Карта тривог і шахедів України
          </div>

          <div
            style={{
              fontSize: 22,
              color: MUTED,
              lineHeight: 1.5,
              maxWidth: 620,
              marginBottom: 30,
              display: 'flex',
            }}
          >
            Повітряні тривоги • Шахеди • Ракети • БПЛА
          </div>

          <div style={{ display: 'flex', gap: 22 }}>
            {['Оновлення 24/7', 'Push-сповіщення', 'Безкоштовно'].map((feature) => (
              <div
                key={feature}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  background: 'rgba(54,228,255,0.09)',
                  border: '1px solid rgba(54,228,255,0.22)',
                  borderRadius: 14,
                  padding: '10px 22px',
                  fontSize: 18,
                  color: CYAN,
                }}
              >
                <div
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: MINT,
                    display: 'flex',
                  }}
                />
                {feature}
              </div>
            ))}
          </div>
        </div>

        <div
          style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            height: 5,
            background: `linear-gradient(90deg, ${CYAN}, ${MINT}, #a78bfa, ${CYAN})`,
            display: 'flex',
          }}
        />

        <div
          style={{
            position: 'absolute',
            bottom: 22,
            right: 76,
            fontSize: 20,
            color: MUTED,
            display: 'flex',
          }}
        >
          neptun.in.ua
        </div>
      </div>
    ),
    { width: 1200, height: 630 },
  );
}
