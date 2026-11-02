// Shader-type register reservations, as in MonoGame's SM2 effect macros:
// A is c3 in the vertex shader and c5 in the pixel shader.
float4 A : register(vs, c3) : register(ps, c5);
float4 B : register(vs, c7);
float4 C : register(ps, c9);
sampler2D S : register(vs, s1) : register(ps, s2);

float4 vsmain(float4 p : POSITION) : POSITION
{
    return p * A + B + C;
}

float4 psmain(float2 uv : TEXCOORD0) : COLOR0
{
    float4 c = tex2D(S, uv) * A + B + C;
    clip(c.a - 0.5);
    return c;
}
