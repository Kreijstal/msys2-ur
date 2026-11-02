// Small D3DX9-style effect for check(): fx_2_0 technique/pass with
// render states, plus the same functions compiled as plain vs/ps.
// vkd3d 2.1 writes fx_2_0 parameters and techniques, but not yet sampler
// state initializers, state assignments or compiled shaders in passes;
// FX_PARAMS_ONLY leaves those out.
float4x4 WorldViewProj;
float4 Diffuse = float4(1, 1, 1, 1);
texture Texture;
#ifndef FX_PARAMS_ONLY
sampler TextureSampler = sampler_state
{
    Texture = <Texture>;
    MinFilter = Linear;
    MagFilter = Linear;
    AddressU = Clamp;
};
#endif

struct VSOut
{
    float4 pos : POSITION;
    float2 uv : TEXCOORD0;
};

VSOut VSMain(float4 pos : POSITION, float2 uv : TEXCOORD0)
{
    VSOut o;
    o.pos = mul(pos, WorldViewProj);
    o.uv = uv;
    return o;
}

float4 PSMain(float2 uv : TEXCOORD0) : COLOR0
{
#ifdef FX_PARAMS_ONLY
    return Diffuse;
#else
    return tex2D(TextureSampler, uv) * Diffuse;
#endif
}

technique Textured
{
    pass P0
    {
#ifndef FX_PARAMS_ONLY
        AlphaBlendEnable = true;
        SrcBlend = SrcAlpha;
        DestBlend = InvSrcAlpha;
        VertexShader = compile vs_2_0 VSMain();
        PixelShader = compile ps_2_0 PSMain();
#endif
    }
}
