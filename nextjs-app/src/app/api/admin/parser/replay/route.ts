import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

function resolvePythonBinary(): string {
  if (process.env.REPLAY_PYTHON_BIN) return process.env.REPLAY_PYTHON_BIN;
  if (existsSync('/home/neptun/venv/bin/python')) return '/home/neptun/venv/bin/python';
  return 'python3';
}

async function runReplay(text: string): Promise<Record<string, unknown>> {
  const script = path.join(process.cwd(), 'worker', 'scripts', 'replay_parse.py');
  const stdout = await new Promise<string>((resolve, reject) => {
    const child = spawn(resolvePythonBinary(), [script], {
      cwd: path.join(process.cwd(), 'worker'),
      stdio: ['pipe', 'pipe', 'pipe'],
      env: {
        ...process.env,
        TELEGRAM_API_ID: process.env.TELEGRAM_API_ID || '12345',
        TELEGRAM_API_HASH: process.env.TELEGRAM_API_HASH || '0123456789abcdef0123456789abcdef',
        QUEUE_DIR: process.env.QUEUE_DIR || '/tmp/neptun-parser-replay-queue',
      },
    });
    let out = '';
    let err = '';
    const timer = setTimeout(() => {
      child.kill('SIGKILL');
      reject(new Error('parser replay timed out'));
    }, 8000);

    child.stdout.setEncoding('utf8');
    child.stderr.setEncoding('utf8');
    child.stdout.on('data', (chunk: string) => {
      out += chunk;
      if (out.length > 1024 * 1024) {
        child.kill('SIGKILL');
        reject(new Error('parser replay output too large'));
      }
    });
    child.stderr.on('data', (chunk: string) => {
      err += chunk;
    });
    child.on('error', (error) => {
      clearTimeout(timer);
      reject(error);
    });
    child.on('close', (code) => {
      clearTimeout(timer);
      if (code === 0) {
        resolve(out);
      } else {
        reject(new Error(err || `parser replay exited with code ${code}`));
      }
    });
    child.stdin.end(JSON.stringify({ text }));
  });
  return JSON.parse(stdout) as Record<string, unknown>;
}

export async function GET(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  const url = new URL(request.url);
  const text = (url.searchParams.get('text') || url.searchParams.get('q') || '').trim();
  if (!text) {
    return NextResponse.json({ status: 'error', error: 'text query param is required' }, { status: 400 });
  }

  try {
    return NextResponse.json(await runReplay(text));
  } catch (error) {
    return NextResponse.json({
      status: 'error',
      error: error instanceof Error ? error.message : String(error),
    }, { status: 500 });
  }
}

export async function POST(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  const body = await request.json().catch(() => ({}));
  const text = typeof body.text === 'string' ? body.text.trim() : '';
  if (!text) {
    return NextResponse.json({ status: 'error', error: 'text is required' }, { status: 400 });
  }

  try {
    return NextResponse.json(await runReplay(text));
  } catch (error) {
    return NextResponse.json({
      status: 'error',
      error: error instanceof Error ? error.message : String(error),
    }, { status: 500 });
  }
}
