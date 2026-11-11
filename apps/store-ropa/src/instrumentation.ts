export async function register() {
  if (process.env.NEXT_RUNTIME === 'nodejs') {
    const { runtime } = await import('./lib/server-runtime');
    runtime(); // Invalid configuration prevents the Next.js server from becoming available.
  }
}
