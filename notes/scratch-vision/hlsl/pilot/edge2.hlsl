RWTexture2D<uint> g_out : register(u0);
cbuffer cb0 : register(b0)
{
    uint4  g_c0;        // [0]
    uint4  g_dims;      // [1] xy = dims
    uint4  g_c2;
    uint4  g_c3;
    float4 g_contrast;  // [4] x = contrast, y = midpoint
};
[numthreads(16,16,1)]
void main(uint3 tid : SV_DispatchThreadID)
{
    if (tid.x >= g_dims.x || tid.y >= g_dims.y) return;
    uint px = g_out[tid.xy];
    float b = (px & 0xFFu) / 255.0;
    float g = ((px >> 8) & 0xFFu) / 255.0;
    float r = ((px >> 16) & 0xFFu) / 255.0;
    float a = ((px >> 24) & 0xFFu) / 255.0;
    float3 rgb = saturate((float3(r,g,b) - g_contrast.y) * g_contrast.x + g_contrast.y);
    uint3 o = (uint3)round(rgb * 255.0);
    g_out[tid.xy] = (uint(round(a*255.0)) << 24) | (o.x << 16) | (o.y << 8) | o.z;
}
