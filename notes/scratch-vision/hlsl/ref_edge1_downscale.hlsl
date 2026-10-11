// Stage 1 — box-average downscale (capture -> scaled color). Verified against edge_1_140272470.dxbc.
// CB dwords: c0=(g_width,g_height,g_dpi_scale,g_edge_threshold) c1=(g_scaled_width,g_scaled_height,g_coord_scale,pad)
Texture2D<float4> g_in : register(t0);
RWTexture2D<uint> g_out : register(u0);
cbuffer CB : register(b0) { float4 c0; float4 c1; };
[numthreads(16,16,1)]
void main(uint3 tid : SV_DispatchThreadID)
{
    if (tid.x >= (uint)c1.x || tid.y >= (uint)c1.y) return;          // scaled dims
    float ratio = c0.z;                                             // g_dpi_scale
    uint x0 = (uint)(tid.x * ratio), x1 = min((uint)((tid.x+1)*ratio), (uint)c0.x);
    uint y0 = (uint)(tid.y * ratio), y1 = min((uint)((tid.y+1)*ratio), (uint)c0.y);
    float4 sum = 0; uint n = 0;
    for (uint y = y0; y < y1; ++y) for (uint x = x0; x < x1; ++x) { sum += g_in.Load(int3(x,y,0)); ++n; }
    float4 avg = sum / max(n,1);
    uint4 q = (uint4)round(avg * 255.0);
    g_out[tid.xy] = (q.w << 24) | (q.x << 16) | (q.y << 8) | q.z;    // A<<24|R<<16|G<<8|B (B8G8R8A8 memory)
}
