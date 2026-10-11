// Stage 7 — gated boolean mask downsample (OR over an n x n block). Verified against edge_7_gated_14026eb20.dxbc.
// n = round(g_coord_scale / g_dpi_scale) = round(c1.z / c0.z); runs only when the label dims (c2.xy) differ.
Texture2D<uint> g_in : register(t0);
RWTexture2D<uint> g_out : register(u0);
cbuffer CB : register(b0) { float4 c0; float4 c1; float4 c2; };
[numthreads(16,16,1)]
void main(uint3 tid : SV_DispatchThreadID)
{
    if (tid.x >= (uint)c2.x || tid.y >= (uint)c2.y) return;      // label dims
    uint n = (uint)(c1.z / c0.z + 0.5);
    uint v = 0;
    for (uint j = 0; j < n; ++j)
        for (uint i = 0; i < n; ++i) {
            uint x = tid.x*n + i, y = tid.y*n + j;
            if (x < (uint)c1.x && y < (uint)c1.y && g_in.Load(int3(x,y,0)) != 0) v = 1;
        }
    g_out[tid.xy] = v;
}
