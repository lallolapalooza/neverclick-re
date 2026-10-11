// Stage 3 — Sobel + orientation quantisation. Verified against edge_3_1402707a0.dxbc.
// out = (magnitude = |gx|+|gy|, orientation code in {0,1,2,3}, 0, 0); borders -> 0.
Texture2D<uint> g_in : register(t0);
RWTexture2D<float4> g_out : register(u0);
cbuffer CB : register(b0) { float4 c0; float4 c1; };
float gray(uint px) { return (float)((px & 0xFFu) + ((px>>8)&0xFFu) + ((px>>16)&0xFFu)) / 255.0; }
[numthreads(16,16,1)]
void main(uint3 tid : SV_DispatchThreadID)
{
    int w = (int)c1.x, h = (int)c1.y;
    if (tid.x >= (uint)w || tid.y >= (uint)h) return;
    if (tid.x == 0 || tid.y == 0 || tid.x >= (uint)(w-1) || tid.y >= (uint)(h-1)) { g_out[tid.xy] = 0; return; }
    int x = tid.x, y = tid.y;
    float TL = gray(g_in.Load(int3(x-1,y-1,0))), T = gray(g_in.Load(int3(x,y-1,0))), TR = gray(g_in.Load(int3(x+1,y-1,0)));
    float L  = gray(g_in.Load(int3(x-1,y  ,0))),                                  R = gray(g_in.Load(int3(x+1,y  ,0)));
    float BL = gray(g_in.Load(int3(x-1,y+1,0))), B = gray(g_in.Load(int3(x,y+1,0))), BR = gray(g_in.Load(int3(x+1,y+1,0)));
    float gx = (TR + 2*R + BR) - (TL + 2*L + BL);
    float gy = (BL + 2*B + BR) - (TL + T + TR);
    float mag = abs(gx) + abs(gy);
    float o = (2.41421356 * abs(gy) < abs(gx)) ? 0.0                       // |gx| dominant
            : (2.41421356 * abs(gx) < abs(gy)) ? 2.0                       // |gy| dominant
            : ((gx * gy) > 0 ? 1.0 : 3.0);                                 // diagonal (sign product)
    g_out[tid.xy] = float4(mag, o, 0, 0);
}
