import { createWebApi } from '@/lib/web-api';
export const runtime='nodejs';
export const dynamic='force-dynamic';
export const GET=createWebApi();
export const POST=GET;
