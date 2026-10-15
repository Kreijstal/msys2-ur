/*
 * d3dcompiler_47 entry points that libvkd3d-utils does not provide.
 *
 * Linked together with the static libvkd3d-utils/libvkd3d-shader into a
 * self-contained d3dcompiler_47.dll. File helpers follow Wine's
 * dlls/d3dcompiler_43 (compiler.c, blob.c); the remaining entry points are
 * stubs so that callers resolving the full export table do not fail to load.
 *
 * Copyright 2010 Matteo Bruni for CodeWeavers (Wine)
 * Copyright 2026 Kreijstal
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 */

#define COBJMACROS
#include <windows.h>
#include <d3dcommon.h>
#include <stdio.h>

/* From libvkd3d-utils (vkd3d_utils.h); declared here without dllimport.
 * <d3dcompiler.h> is not included: several of its prototypes use D3D11
 * interface types the stubs below do not need. */
HRESULT WINAPI D3DCreateBlob(SIZE_T data_size, ID3DBlob **blob);
HRESULT WINAPI D3DCompile2VKD3D(const void *data, SIZE_T data_size, const char *filename,
        const D3D_SHADER_MACRO *macros, ID3DInclude *include, const char *entry_point,
        const char *profile, UINT flags, UINT effect_flags, UINT secondary_flags,
        const void *secondary_data, SIZE_T secondary_data_size, ID3DBlob **shader_blob,
        ID3DBlob **messages_blob, unsigned int compiler_version);

static HRESULT read_file(const WCHAR *filename, void **data, DWORD *size)
{
    HANDLE file;
    DWORD read;
    LARGE_INTEGER len;

    file = CreateFileW(filename, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE)
        return HRESULT_FROM_WIN32(GetLastError());
    if (!GetFileSizeEx(file, &len) || len.QuadPart > 0x7fffffff)
    {
        CloseHandle(file);
        return E_FAIL;
    }
    *size = (DWORD)len.QuadPart;
    if (!(*data = HeapAlloc(GetProcessHeap(), 0, *size ? *size : 1)))
    {
        CloseHandle(file);
        return E_OUTOFMEMORY;
    }
    if (!ReadFile(file, *data, *size, &read, NULL) || read != *size)
    {
        HeapFree(GetProcessHeap(), 0, *data);
        CloseHandle(file);
        return E_FAIL;
    }
    CloseHandle(file);
    return S_OK;
}

HRESULT WINAPI D3DCompileFromFile(const WCHAR *filename, const D3D_SHADER_MACRO *macros,
        ID3DInclude *include, const char *entry_point, const char *target, UINT flags1,
        UINT flags2, ID3DBlob **code, ID3DBlob **errors)
{
    char *source_name;
    void *source;
    DWORD source_size;
    int len;
    HRESULT hr;

    if (!filename)
        return E_INVALIDARG;
    if (FAILED(hr = read_file(filename, &source, &source_size)))
        return hr;

    len = WideCharToMultiByte(CP_ACP, 0, filename, -1, NULL, 0, NULL, NULL);
    if (!(source_name = HeapAlloc(GetProcessHeap(), 0, len)))
    {
        HeapFree(GetProcessHeap(), 0, source);
        return E_OUTOFMEMORY;
    }
    WideCharToMultiByte(CP_ACP, 0, filename, -1, source_name, len, NULL, NULL);

    hr = D3DCompile2VKD3D(source, source_size, source_name, macros, include, entry_point,
            target, flags1, flags2, 0, NULL, 0, code, errors, 47);

    HeapFree(GetProcessHeap(), 0, source_name);
    HeapFree(GetProcessHeap(), 0, source);
    return hr;
}

HRESULT WINAPI D3DReadFileToBlob(const WCHAR *filename, ID3DBlob **contents)
{
    void *data;
    DWORD size;
    HRESULT hr;

    if (!filename || !contents)
        return E_INVALIDARG;
    if (FAILED(hr = read_file(filename, &data, &size)))
        return hr;
    if (SUCCEEDED(hr = D3DCreateBlob(size, contents)))
        memcpy(ID3D10Blob_GetBufferPointer(*contents), data, size);
    HeapFree(GetProcessHeap(), 0, data);
    return hr;
}

HRESULT WINAPI D3DWriteBlobToFile(ID3DBlob *blob, const WCHAR *filename, BOOL overwrite)
{
    DWORD written, size;
    HANDLE file;
    BOOL ok;

    if (!blob || !filename)
        return E_INVALIDARG;

    file = CreateFileW(filename, GENERIC_WRITE, FILE_SHARE_READ, NULL,
            overwrite ? CREATE_ALWAYS : CREATE_NEW, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE)
        return HRESULT_FROM_WIN32(GetLastError());

    size = (DWORD)ID3D10Blob_GetBufferSize(blob);
    ok = WriteFile(file, ID3D10Blob_GetBufferPointer(blob), size, &written, NULL);
    CloseHandle(file);
    if (!ok || written != size)
        return E_FAIL;
    return S_OK;
}

/* Not implemented by vkd3d; stubs return the same codes as Wine. */

HRESULT WINAPI D3DSetBlobPart(const void *data, SIZE_T data_size, int part,
        UINT flags, const void *part_data, SIZE_T part_size, ID3DBlob **blob)
{
    return E_NOTIMPL;
}

HRESULT WINAPI D3DCompressShaders(UINT num_shaders, void *shader_data,
        UINT flags, ID3DBlob **compressed_data)
{
    return E_NOTIMPL;
}

HRESULT WINAPI D3DDecompressShaders(const void *data, SIZE_T data_size, UINT num_shaders,
        UINT start_index, UINT *indices, UINT flags, ID3DBlob **shaders, UINT *total_shaders)
{
    return E_NOTIMPL;
}

HRESULT WINAPI D3DDisassembleRegion(const void *data, SIZE_T data_size, UINT flags,
        const char *comments, SIZE_T start_byte_offset, SIZE_T num_insts,
        SIZE_T *finish_byte_offset, ID3DBlob **disassembly)
{
    return E_NOTIMPL;
}

HRESULT WINAPI D3DDisassemble10Effect(void *effect, UINT flags, ID3DBlob **disassembly)
{
    return E_NOTIMPL;
}

HRESULT WINAPI D3DReflectLibrary(const void *data, SIZE_T data_size, REFIID riid, void **reflector)
{
    return E_NOTIMPL;
}

HRESULT WINAPI D3DLoadModule(const void *data, SIZE_T size, void **module)
{
    if (module)
        *module = NULL;
    return E_NOTIMPL;
}

HRESULT WINAPI D3DCreateLinker(void **linker)
{
    if (linker)
        *linker = NULL;
    return E_NOTIMPL;
}

HRESULT WINAPI D3DCreateFunctionLinkingGraph(UINT flags, void **graph)
{
    if (graph)
        *graph = NULL;
    return E_NOTIMPL;
}

HRESULT WINAPI D3DAssemble(const void *data, SIZE_T data_size, const char *filename,
        const D3D_SHADER_MACRO *macros, ID3DInclude *include, UINT flags,
        ID3DBlob **shader, ID3DBlob **error_messages)
{
    return E_NOTIMPL;
}

HRESULT WINAPI D3DDisassemble11Trace(const void *data, SIZE_T data_size, void *trace,
        UINT start_step, UINT num_steps, UINT flags, ID3DBlob **disassembly)
{
    return E_NOTIMPL;
}

HRESULT WINAPI D3DGetTraceInstructionOffsets(const void *data, SIZE_T data_size, UINT flags,
        SIZE_T start_inst_index, SIZE_T num_insts, SIZE_T *offsets, SIZE_T *total_insts)
{
    return E_NOTIMPL;
}

HRESULT WINAPI D3DReturnFailure1(void)
{
    return E_FAIL;
}

HRESULT WINAPI DebugSetMute(void)
{
    return S_OK;
}
