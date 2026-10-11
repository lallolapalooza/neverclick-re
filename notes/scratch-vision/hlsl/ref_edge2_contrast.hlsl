// Stage 2 — in-place contrast. Verified against edge_2_140271b50.dxbc.
// c4 = (g_contrast, g_contrast_midpoint)  [dwords 16,17]
RWTexture2D<uint> g_tex : register(u0);
cbuffer CB : register(b0) { float4 c0; float4 c1; float4 c2; float4 c3; float4 c4; };
[numthreads(16,16,1)]
void main(uint3 tid : SV_DispatchThreadID)
{
    if (tid.x >= (uint)c1.x || tid.y >= (uint)c1.y) return;
    uint px = g_tex[tid.xy];
    float b = (px & 0xFFu)/255.0, g = ((px>>8)&0xFFu)/255.0, r = ((px>>16)&0xFFu)/255.0, a = ((px>>24)&0xFFu)/255.0;
    float3 rgb = saturate((float3(r,g,b) - c4.y) * c4.x + c4.y);
    uint3 q = (uint3)round(rgb*255.0); uint qa = (uint)round(a*255.0);
    g_tex[tid.xy] = (qa<<24)|(q.x<<16)|(q.y<<8)|q.z;
}
