import { webReadiness } from '@/lib/server-runtime';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const result = await webReadiness();
    return Response.json(result.body, { status: result.ready ? 200 : 503, headers: { 'Cache-Control': 'no-store' } });
  } catch {
    return Response.json({ service: 'web', status: 'not_ready', scope: 'foundation', checks: { configuration: 'invalid' } },
      { status: 503, headers: { 'Cache-Control': 'no-store' } });
  }
}
