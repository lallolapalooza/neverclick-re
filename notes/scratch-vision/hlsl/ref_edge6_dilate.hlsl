// Stage 6 — anisotropic rectangular dilate. Verified against edge_6_14026e140.dxbc.
// c3 = (g_dilate_left, g_dilate_right, g_dilate_up, g_dilate_down); window [x-L, x+R] x [y-U, y+D] inclusive.
Texture2D<uint> g_in : register(t0);
RWTexture2D<uint> g_out : register(u0);
cbuffer CB : register(b0) { float4 c0; float4 c1; float4 c2; float4 c3; };
[numthreads(16,16,1)]
void main(uint3 tid : SV_DispatchThreadID)
{
    int w = (int)c1.x, h = (int)c1.y;
    if (tid.x >= (uint)w || tid.y >= (uint)h) return;
    if (g_in.Load(int3(tid.xy,0)) != 0) { g_out[tid.xy] = 1; return; }
    int L=(int)c3.x, R=(int)c3.y, U=(int)c3.z, D=(int)c3.w;
    int x0=max((int)tid.x-L,0), x1=min((int)tid.x+R,w-1);
    int y0=max((int)tid.y-U,0), y1=min((int)tid.y+D,h-1);
    uint v = 0;
    for (int y=y0; y<=y1 && v==0; ++y)
        for (int x=x0; x<=x1; ++x)
            if (g_in.Load(int3(x,y,0)) != 0) { v = 1; break; }
    g_out[tid.xy] = v;
}
