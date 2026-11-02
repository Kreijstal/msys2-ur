// Small pixel shader for check(): sampler + constants, SM2 and SM4 targets.
float4 Tint;
float  Amount;
#if defined(SM4)
Texture2D Tex : register(t0);
sampler TexSampler : register(s0);
#define SAMPLE(uv) Tex.Sample(TexSampler, uv)
#define TARGET SV_Target
#else
sampler2D TexSampler : register(s0);
#define SAMPLE(uv) tex2D(TexSampler, uv)
#define TARGET COLOR0
#endif

float4 main(float4 color : COLOR0, float2 uv : TEXCOORD0) : TARGET
{
    float4 c = SAMPLE(uv) * color;
    return lerp(c, c * Tint, Amount);
}
