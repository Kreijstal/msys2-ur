/*
 * d3dctest: compile HLSL through a given d3dcompiler DLL the way MonoGame's
 * mgfxc does (D3DCompile + D3DReflect/ID3D11ShaderReflection + D3DStripShader)
 * and print a normalized dump of everything mgfxc consumes, so that two DLLs
 * (e.g. the vkd3d-based d3dcompiler_47.dll and Windows' own) can be diffed.
 *
 * usage: d3dctest <compiler.dll> <preprocess.dll> <jobs.txt> [outdir]
 *
 * jobs.txt lines:  name|file|defines|entry|profile|flags|mode
 *   defines: NAME=VALUE;NAME2=VALUE2 (may be empty)
 *   flags:   D3DCOMPILE_* flags in hex
 *   mode:    mg  - preprocess with <preprocess.dll>, blank out technique
 *                  blocks (as mgfxc's parser does), compile the result
 *            raw - compile the file as is (e.g. fx_2_0 effects)
 *
 * Copyright 2026 Kreijstal; LGPL-2.1-or-later.
 */

#define COBJMACROS
#define INITGUID
#include <windows.h>
#include <initguid.h>
#include <d3dcompiler.h>
#include <d3d11shader.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

typedef HRESULT (WINAPI *pD3DCompile_t)(const void *, SIZE_T, const char *, const D3D_SHADER_MACRO *,
        ID3DInclude *, const char *, const char *, UINT, UINT, ID3DBlob **, ID3DBlob **);
typedef HRESULT (WINAPI *pD3DPreprocess_t)(const void *, SIZE_T, const char *, const D3D_SHADER_MACRO *,
        ID3DInclude *, ID3DBlob **, ID3DBlob **);
typedef HRESULT (WINAPI *pD3DReflect_t)(const void *, SIZE_T, REFIID, void **);
typedef HRESULT (WINAPI *pD3DStripShader_t)(const void *, SIZE_T, UINT, ID3DBlob **);

static pD3DCompile_t fnCompile;
static pD3DPreprocess_t fnPreprocess;
static pD3DReflect_t fnReflect;
static pD3DStripShader_t fnStripShader;

static char *read_text(const char *path, size_t *size)
{
    FILE *f = fopen(path, "rb");
    char *buf;
    long len;

    if (!f)
        return NULL;
    fseek(f, 0, SEEK_END);
    len = ftell(f);
    fseek(f, 0, SEEK_SET);
    buf = malloc(len + 1);
    *size = fread(buf, 1, len, f);
    buf[*size] = 0;
    fclose(f);
    /* Skip a UTF-8 BOM, as .NET's File.ReadAllText() does for mgfxc. */
    if (*size >= 3 && !memcmp(buf, "\xef\xbb\xbf", 3))
    {
        memmove(buf, buf + 3, *size - 2);
        *size -= 3;
    }
    return buf;
}

static void print_messages(const char *prefix, ID3DBlob *blob)
{
    const char *p, *end;

    if (!blob)
        return;
    p = ID3D10Blob_GetBufferPointer(blob);
    end = p + ID3D10Blob_GetBufferSize(blob);
    while (p < end && *p)
    {
        const char *nl = memchr(p, '\n', end - p);
        size_t len = nl ? (size_t)(nl - p) : (size_t)(end - p);
        if (len && p[len - 1] == '\r')
            --len;
        if (len)
            printf("%s%.*s\n", prefix, (int)len, p);
        if (!nl)
            break;
        p = nl + 1;
    }
}

/* Blank out "technique[10|11] name { ... }" blocks like mgfxc's
 * WhitespaceNodes(TokenType.Technique_Declaration). */
static void strip_techniques(char *s)
{
    char *p = s;

    while ((p = strstr(p, "technique")))
    {
        char *q = p + 9;
        int depth = 0;

        if ((p > s && (isalnum((unsigned char)p[-1]) || p[-1] == '_')))
        {
            p = q;
            continue;
        }
        while (isalnum((unsigned char)*q) || *q == '_')
            ++q;
        while (*q && *q != '{')
            ++q;
        for (; *q; ++q)
        {
            if (*q == '{')
                ++depth;
            else if (*q == '}' && !--depth)
            {
                ++q;
                break;
            }
        }
        for (char *r = p; r < q; ++r)
            if (!isspace((unsigned char)*r))
                *r = ' ';
        p = q;
    }
}

static void print_type(ID3D11ShaderReflectionType *type, const char *path, int depth)
{
    D3D11_SHADER_TYPE_DESC td;
    char sub[512];
    UINT i;

    if (FAILED(type->lpVtbl->GetDesc(type, &td)))
    {
        printf("    type %s: GetDesc failed\n", path);
        return;
    }
    printf("    type %s: class=%u type=%u rows=%u cols=%u elements=%u members=%u offset=%u name=%s\n",
            path, td.Class, td.Type, td.Rows, td.Columns, td.Elements, td.Members, td.Offset,
            td.Name ? td.Name : "(null)");
    if (depth > 4)
        return;
    for (i = 0; i < td.Members; ++i)
    {
        ID3D11ShaderReflectionType *m = type->lpVtbl->GetMemberTypeByIndex(type, i);
        const char *mname = type->lpVtbl->GetMemberTypeName(type, i);
        snprintf(sub, sizeof(sub), "%s.%s", path, mname ? mname : "(null)");
        if (m)
            print_type(m, sub, depth + 1);
    }
}

static void dump_reflection(const void *code, SIZE_T size)
{
    ID3D11ShaderReflection *refl;
    D3D11_SHADER_DESC desc;
    HRESULT hr;
    UINT i, j, k;

    if (FAILED(hr = fnReflect(code, size, &IID_ID3D11ShaderReflection, (void **)&refl)))
    {
        printf("  reflect: FAIL hr=%#lx\n", hr);
        return;
    }
    if (FAILED(hr = refl->lpVtbl->GetDesc(refl, &desc)))
    {
        printf("  reflect: GetDesc FAIL hr=%#lx\n", hr);
        refl->lpVtbl->Release(refl);
        return;
    }
    printf("  desc: version=%#x cbuffers=%u resources=%u inputs=%u outputs=%u\n",
            desc.Version, desc.ConstantBuffers, desc.BoundResources,
            desc.InputParameters, desc.OutputParameters);
    for (i = 0; i < desc.BoundResources; ++i)
    {
        D3D11_SHADER_INPUT_BIND_DESC b;
        if (FAILED(refl->lpVtbl->GetResourceBindingDesc(refl, i, &b)))
        {
            printf("  resource %u: FAIL\n", i);
            continue;
        }
        printf("  resource: name=%s type=%u bind=%u count=%u dim=%u ret=%u flags=%#x\n",
                b.Name, b.Type, b.BindPoint, b.BindCount, b.Dimension, b.ReturnType, b.uFlags);
    }
    for (i = 0; i < desc.InputParameters; ++i)
    {
        D3D11_SIGNATURE_PARAMETER_DESC s;
        if (SUCCEEDED(refl->lpVtbl->GetInputParameterDesc(refl, i, &s)))
            printf("  input: %s%u reg=%u sv=%u comp=%u mask=%#x rw=%#x\n", s.SemanticName,
                    s.SemanticIndex, s.Register, s.SystemValueType, s.ComponentType, s.Mask, s.ReadWriteMask);
    }
    for (i = 0; i < desc.OutputParameters; ++i)
    {
        D3D11_SIGNATURE_PARAMETER_DESC s;
        if (SUCCEEDED(refl->lpVtbl->GetOutputParameterDesc(refl, i, &s)))
            printf("  output: %s%u reg=%u sv=%u comp=%u mask=%#x\n", s.SemanticName,
                    s.SemanticIndex, s.Register, s.SystemValueType, s.ComponentType, s.Mask);
    }
    for (i = 0; i < desc.ConstantBuffers; ++i)
    {
        ID3D11ShaderReflectionConstantBuffer *cb = refl->lpVtbl->GetConstantBufferByIndex(refl, i);
        D3D11_SHADER_BUFFER_DESC cd;

        if (FAILED(cb->lpVtbl->GetDesc(cb, &cd)))
        {
            printf("  cbuffer %u: GetDesc FAIL\n", i);
            continue;
        }
        printf("  cbuffer: name=%s type=%u vars=%u size=%u flags=%#x\n",
                cd.Name, cd.Type, cd.Variables, cd.Size, cd.uFlags);
        for (j = 0; j < cd.Variables; ++j)
        {
            ID3D11ShaderReflectionVariable *v = cb->lpVtbl->GetVariableByIndex(cb, j);
            D3D11_SHADER_VARIABLE_DESC vd;

            if (FAILED(v->lpVtbl->GetDesc(v, &vd)))
            {
                printf("   var %u: GetDesc FAIL\n", j);
                continue;
            }
            printf("   var: name=%s offset=%u size=%u flags=%#x default=", vd.Name,
                    vd.StartOffset, vd.Size, vd.uFlags);
            if (vd.DefaultValue)
                for (k = 0; k < vd.Size; ++k)
                    printf("%02x", ((const unsigned char *)vd.DefaultValue)[k]);
            else
                printf("none");
            printf("\n");
            print_type(v->lpVtbl->GetType(v), vd.Name, 0);
        }
    }
    refl->lpVtbl->Release(refl);
}

static const char *regset_name(unsigned int r)
{
    static const char *names[] = {"bool", "int4", "float4", "sampler"};
    return r < 4 ? names[r] : "?";
}

/* D3D9 bytecode: dump the CTAB comment, which is what MojoShader reads. */
static void dump_ctab(const void *code, SIZE_T size)
{
    const DWORD *tok = code, *end = (const DWORD *)((const char *)code + size);

    printf("  d3dbc: version=%#lx\n", tok[0]);
    for (++tok; tok < end && *tok != 0x0000ffff;)
    {
        DWORD op = *tok;
        if ((op & 0xffff) == 0xfffe)
        {
            DWORD len = (op >> 16) & 0x7fff;
            if (len >= 1 && tok[1] == MAKEFOURCC('C', 'T', 'A', 'B'))
            {
                const char *base = (const char *)(tok + 2);
                const DWORD *hdr = (const DWORD *)base;
                DWORD count = hdr[3], info = hdr[4], i;

                printf("  ctab: constants=%lu flags=%#lx target=%s\n", count, hdr[5], base + hdr[6]);
                for (i = 0; i < count; ++i)
                {
                    const char *ci = base + info + i * 20;
                    DWORD name = *(const DWORD *)ci;
                    WORD regset = *(const WORD *)(ci + 4), regidx = *(const WORD *)(ci + 6),
                         regcnt = *(const WORD *)(ci + 8);
                    DWORD typeoff = *(const DWORD *)(ci + 12), defoff = *(const DWORD *)(ci + 16);
                    const WORD *t = (const WORD *)(base + typeoff);
                    printf("  const: name=%s set=%s reg=%u count=%u class=%u type=%u rows=%u cols=%u "
                            "elements=%u members=%u default=%s\n", base + name, regset_name(regset),
                            regidx, regcnt, t[0], t[1], t[2], t[3], t[4], t[5], defoff ? "yes" : "no");
                }
            }
            tok += len + 1;
            continue;
        }
        /* SM2+: instruction length in bits 24..27 */
        tok += ((op >> 24) & 0xf) + 1;
    }
}

static unsigned int split_defines(char *defs, D3D_SHADER_MACRO *macros)
{
    unsigned int n = 0;
    char *tok = strtok(defs, ";");

    while (tok && n < 31)
    {
        char *eq = strchr(tok, '=');
        if (eq)
            *eq++ = 0;
        macros[n].Name = tok;
        macros[n].Definition = eq ? eq : "1";
        ++n;
        tok = strtok(NULL, ";");
    }
    macros[n].Name = macros[n].Definition = NULL;
    return n;
}

int main(int argc, char **argv)
{
    HMODULE dll, ppdll;
    char line[4096];
    FILE *jobs;
    unsigned int total = 0, ok = 0;

    if (argc < 4)
    {
        fprintf(stderr, "usage: %s <compiler.dll> <preprocess.dll> <jobs.txt> [outdir]\n", argv[0]);
        return 2;
    }
    if (!(dll = LoadLibraryA(argv[1])) || !(ppdll = LoadLibraryA(argv[2])))
    {
        fprintf(stderr, "cannot load %s / %s (error %lu)\n", argv[1], argv[2], GetLastError());
        return 2;
    }
    fnCompile = (pD3DCompile_t)GetProcAddress(dll, "D3DCompile");
    fnReflect = (pD3DReflect_t)GetProcAddress(dll, "D3DReflect");
    fnStripShader = (pD3DStripShader_t)GetProcAddress(dll, "D3DStripShader");
    fnPreprocess = (pD3DPreprocess_t)GetProcAddress(ppdll, "D3DPreprocess");
    if (!fnCompile || !fnReflect || !fnStripShader || !fnPreprocess)
    {
        fprintf(stderr, "missing exports\n");
        return 2;
    }
    {
        char path[MAX_PATH];
        GetModuleFileNameA(dll, path, sizeof(path));
        printf("# compiler: %s\n", path);
    }
    if (!(jobs = fopen(argv[3], "r")))
        return 2;

    while (fgets(line, sizeof(line), jobs))
    {
        char *f[7], *p = line, *src, *defs;
        D3D_SHADER_MACRO macros[32];
        ID3DBlob *code = NULL, *errors = NULL, *pp = NULL;
        const void *compile_src;
        SIZE_T compile_size;
        size_t size;
        unsigned int n = 0, flags;
        HRESULT hr;

        line[strcspn(line, "\r\n")] = 0;
        if (!line[0] || line[0] == '#')
            continue;
        while (n < 7)
        {
            f[n++] = p;
            if (!(p = strchr(p, '|')))
                break;
            *p++ = 0;
        }
        if (n < 7)
            continue;
        ++total;
        flags = strtoul(f[5], NULL, 16);
        printf("JOB %s (%s %s)\n", f[0], f[3], f[4]);
        fflush(stdout);

        if (!(src = read_text(f[1], &size)))
        {
            printf("  result: FAIL cannot read %s\n", f[1]);
            continue;
        }
        defs = strdup(f[2]);
        split_defines(defs, macros);

        if (!strcmp(f[6], "mg"))
        {
            hr = fnPreprocess(src, size, f[1], macros, D3D_COMPILE_STANDARD_FILE_INCLUDE, &pp, &errors);
            if (FAILED(hr))
            {
                printf("  result: FAIL preprocess hr=%#lx\n", hr);
                print_messages("  msg: ", errors);
                goto next;
            }
            if (errors)
                ID3D10Blob_Release(errors), errors = NULL;
            free(src);
            size = ID3D10Blob_GetBufferSize(pp);
            src = malloc(size + 1);
            memcpy(src, ID3D10Blob_GetBufferPointer(pp), size);
            src[size] = 0;
            size = strlen(src);
            strip_techniques(src);
            compile_src = src;
            compile_size = size;
            hr = fnCompile(compile_src, compile_size, f[1], NULL, NULL, f[3], f[4], flags, 0, &code, &errors);
        }
        else
        {
            hr = fnCompile(src, size, f[1], macros, D3D_COMPILE_STANDARD_FILE_INCLUDE,
                    f[3][0] ? f[3] : NULL, f[4], flags, 0, &code, &errors);
        }

        if (FAILED(hr) || !code)
        {
            printf("  result: FAIL hr=%#lx\n", hr);
            print_messages("  msg: ", errors);
            goto next;
        }
        ++ok;
        {
            const unsigned char *c = ID3D10Blob_GetBufferPointer(code);
            SIZE_T csize = ID3D10Blob_GetBufferSize(code);

            printf("  result: OK size=%zu\n", (size_t)csize);
            print_messages("  warn: ", errors);
            if (argc > 4)
            {
                char out[MAX_PATH];
                FILE *o;
                snprintf(out, sizeof(out), "%s/%s.bin", argv[4], f[0]);
                if ((o = fopen(out, "wb")))
                {
                    fwrite(c, 1, csize, o);
                    fclose(o);
                }
            }
            if (csize >= 4 && !memcmp(c, "DXBC", 4))
            {
                ID3DBlob *stripped = NULL;
                hr = fnStripShader(c, csize, D3DCOMPILER_STRIP_REFLECTION_DATA
                        | D3DCOMPILER_STRIP_TEST_BLOBS | D3DCOMPILER_STRIP_DEBUG_INFO, &stripped);
                printf("  strip: %s\n", SUCCEEDED(hr) ? "OK" : "FAIL");
                if (stripped)
                    ID3D10Blob_Release(stripped);
                if (strncmp(f[4], "fx_", 3))
                    dump_reflection(c, csize);
            }
            else if (strncmp(f[4], "fx_", 3) && csize >= 4)
            {
                dump_ctab(c, csize);
            }
            else
            {
                printf("  effect: header=%#x\n", *(const unsigned int *)c);
            }
        }
next:
        if (code)
            ID3D10Blob_Release(code);
        if (errors)
            ID3D10Blob_Release(errors);
        if (pp)
            ID3D10Blob_Release(pp);
        free(defs);
        free(src);
        fflush(stdout);
    }
    printf("# total=%u ok=%u\n", total, ok);
    return 0;
}
