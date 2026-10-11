// Stage 4 — non-max suppression along the quantised gradient direction. Verified against edge_4_14026fd10.dxbc.
// in = (magnitude, orientation, ..); out = magnitude or 0. Neighbours are clamped at the border.
Texture2D<float4> g_in : register(t0);
RWTexture2D<float4> g_out : register(u0);
cbuffer CB : register(b0) { float4 c0; float4 c1; };
[numthreads(16,16,1)]
void main(uint3 tid : SV_DispatchThreadID)
{
    int w = (int)c1.x, h = (int)c1.y;
    if (tid.x >= (uint)w || tid.y >= (uint)h) return;
    float4 s = g_in.Load(int3(tid.xy,0));
    if (s.x == 0) { g_out[tid.xy] = 0; return; }
    float o = s.y;
    // exact offsets recovered from the movc chain in the original asm:
    int2 d = (o < 0.5) ? int2(0, 1) : (o < 1.5) ? int2(1,-1) : (o < 2.5) ? int2(1, 0) : int2(-1, 1);
    int2 p1 = clamp(int2(tid.xy) + d, int2(0,0), int2(w-1,h-1));
    int2 p2 = clamp(int2(tid.xy) - d, int2(0,0), int2(w-1,h-1));
    float n1 = g_in.Load(int3(p1,0)).x, n2 = g_in.Load(int3(p2,0)).x;
    g_out[tid.xy] = (s.x >= n1 && s.x >= n2) ? s.x : 0;
}
