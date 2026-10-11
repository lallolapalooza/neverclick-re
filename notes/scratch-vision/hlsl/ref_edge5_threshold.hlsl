// Stage 5 — threshold to a boolean mask. Verified against edge_5_14026f520.dxbc.
// out = 1 if magnitude > g_edge_threshold (c0.w = 2.0) else 0.
Texture2D<float> g_in : register(t0);
RWTexture2D<uint> g_out : register(u0);
cbuffer CB : register(b0) { float4 c0; float4 c1; };
[numthreads(16,16,1)]
void main(uint3 tid : SV_DispatchThreadID)
{
    if (tid.x >= (uint)c1.x || tid.y >= (uint)c1.y) return;
    g_out[tid.xy] = (c0.w < g_in.Load(int3(tid.xy,0))) ? 1u : 0u;
}
