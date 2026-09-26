// gamekit/_d3d11.cpp - D3D11 GPU renderer with vertex buffer batching.
// One DrawIndexed call for all rectangles per frame.
#define WIN32_LEAN_AND_MEAN
#include <Python.h>
#include <windows.h>
#include <d3d11.h>
#include <d3dcompiler.h>
#include <wrl/client.h>
#include <cstdio>

#pragma comment(lib, "d3d11.lib")
#pragma comment(lib, "dxgi.lib")
#pragma comment(lib, "d3dcompiler.lib")

using Microsoft::WRL::ComPtr;

typedef struct { float x, y, r, g, b, a; } Vertex;

static HWND g_hwnd = NULL;
static ComPtr<ID3D11Device> g_dev;
static ComPtr<ID3D11DeviceContext> g_ctx;
static ComPtr<IDXGISwapChain> g_swap;
static ComPtr<ID3D11RenderTargetView> g_rtv;
static ComPtr<ID3D11VertexShader> g_vs;
static ComPtr<ID3D11PixelShader> g_ps;
static ComPtr<ID3D11InputLayout> g_layout;
static ComPtr<ID3D11Buffer> g_vbuf;
static ComPtr<ID3D11Buffer> g_ibuf;
static ComPtr<ID3D11Buffer> g_vscb;
static UINT g_width = 800, g_height = 600;

static const char *vs_src =
    "cbuffer CB : register(b0) { float2 screen; };"
    "struct VSOut { float4 pos : SV_Position; float4 col : COLOR0; };"
    "VSOut main(float2 pos : POSITION, float4 col : COLOR0) {"
    "  VSOut o;"
    "  o.pos = float4(pos.x / screen.x * 2.0 - 1.0, 1.0 - pos.y / screen.y * 2.0, 0, 1);"
    "  o.col = col; return o; }";

static const char *ps_src =
    "struct VSOut { float4 pos : SV_Position; float4 col : COLOR0; };"
    "float4 main(VSOut i) : SV_Target { return i.col; }";

static PyObject *d3d_init(PyObject *self, PyObject *args)
{
    HWND hwnd;
    if (!PyArg_ParseTuple(args, "K", &hwnd)) return NULL;
    g_hwnd = hwnd;
    RECT rc; GetClientRect(hwnd, &rc);
    g_width = rc.right - rc.left; g_height = rc.bottom - rc.top;

    DXGI_SWAP_CHAIN_DESC scd = {};
    scd.BufferCount = 1;  // GDI-compatible swap chains only support 1 buffer
    scd.BufferDesc.Width = g_width; scd.BufferDesc.Height = g_height;
    scd.BufferDesc.Format = DXGI_FORMAT_B8G8R8A8_UNORM;  // GDI-compatible requires BGRA
    scd.BufferDesc.RefreshRate.Numerator = 60;
    scd.BufferDesc.RefreshRate.Denominator = 1;
    scd.Flags = DXGI_SWAP_CHAIN_FLAG_GDI_COMPATIBLE;
    scd.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
    scd.OutputWindow = hwnd;
    scd.SampleDesc.Count = 1;
    scd.Windowed = TRUE;
    scd.SwapEffect = DXGI_SWAP_EFFECT_SEQUENTIAL;

    UINT flags = 0;
    D3D_FEATURE_LEVEL fl;
    // Try hardware, fall back to WARP (like SDL2 does)
    HRESULT hr = D3D11CreateDeviceAndSwapChain(
        NULL, D3D_DRIVER_TYPE_HARDWARE, NULL, flags, NULL, 0,
        D3D11_SDK_VERSION, &scd, &g_swap, &g_dev, &fl, &g_ctx);
    if (FAILED(hr)) {
        // Software rasterizer fallback (like SDL2)
        hr = D3D11CreateDeviceAndSwapChain(
            NULL, D3D_DRIVER_TYPE_WARP, NULL, flags, NULL, 0,
            D3D11_SDK_VERSION, &scd, &g_swap, &g_dev, &fl, &g_ctx);
    }
    if (FAILED(hr)) {
        fprintf(stderr, "[d3d11] create failed: 0x%08X\n", (unsigned)hr);
        PyErr_SetString(PyExc_RuntimeError, "D3D11 create failed");
        return NULL;
    }

    ComPtr<ID3D11Texture2D> back;
    hr = g_swap->GetBuffer(0, IID_PPV_ARGS(&back));
    if (FAILED(hr)) {
        PyErr_SetString(PyExc_RuntimeError, "D3D11 GetBuffer failed");
        return NULL;
    }
    hr = g_dev->CreateRenderTargetView(back.Get(), NULL, g_rtv.GetAddressOf());
    if (FAILED(hr)) {
        // Explicit desc fallback
        D3D11_RENDER_TARGET_VIEW_DESC rtv_desc = {};
        rtv_desc.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
        rtv_desc.ViewDimension = D3D11_RTV_DIMENSION_TEXTURE2D;
        rtv_desc.Texture2D.MipSlice = 0;
        hr = g_dev->CreateRenderTargetView(back.Get(), &rtv_desc, g_rtv.GetAddressOf());
        if (FAILED(hr)) {
            PyErr_SetString(PyExc_RuntimeError, "CreateRTV failed");
            return NULL;
        }
    }
    g_ctx->OMSetRenderTargets(1, g_rtv.GetAddressOf(), NULL);

    // Compile shaders
    ComPtr<ID3DBlob> vsb, psb, err;
    D3DCompile(vs_src, strlen(vs_src), NULL, NULL, NULL, "main", "vs_4_0", 0, 0, &vsb, &err);
    D3DCompile(ps_src, strlen(ps_src), NULL, NULL, NULL, "main", "ps_4_0", 0, 0, &psb, &err);
    g_dev->CreateVertexShader(vsb->GetBufferPointer(), vsb->GetBufferSize(), NULL, &g_vs);
    g_dev->CreatePixelShader(psb->GetBufferPointer(), psb->GetBufferSize(), NULL, &g_ps);

    D3D11_INPUT_ELEMENT_DESC ied[] = {
        {"POSITION", 0, DXGI_FORMAT_R32G32_FLOAT, 0, 0, D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"COLOR", 0, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 8, D3D11_INPUT_PER_VERTEX_DATA, 0},
    };
    g_dev->CreateInputLayout(ied, 2, vsb->GetBufferPointer(), vsb->GetBufferSize(), &g_layout);
    g_ctx->IASetInputLayout(g_layout.Get());
    g_ctx->VSSetShader(g_vs.Get(), NULL, 0);
    g_ctx->PSSetShader(g_ps.Get(), NULL, 0);

    // Screen size constant buffer
    float screen[2] = {(float)g_width, (float)g_height};
    D3D11_BUFFER_DESC cbd = {};
    cbd.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
    cbd.ByteWidth = sizeof(float) * 4;
    cbd.Usage = D3D11_USAGE_DYNAMIC;
    cbd.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
    D3D11_SUBRESOURCE_DATA srd = {screen, 0, 0};
    g_dev->CreateBuffer(&cbd, &srd, &g_vscb);
    g_ctx->VSSetConstantBuffers(0, 1, g_vscb.GetAddressOf());

    // Vertex buffer (dynamic, updated per-frame)
    D3D11_BUFFER_DESC vbd = {};
    vbd.BindFlags = D3D11_BIND_VERTEX_BUFFER;
    vbd.ByteWidth = sizeof(Vertex) * 16000;  // 4000 rects * 4 verts
    vbd.Usage = D3D11_USAGE_DYNAMIC;
    vbd.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
    g_dev->CreateBuffer(&vbd, NULL, &g_vbuf);

    // Index buffer (static: 6 indices per rect, max 4000 rects)
    WORD indices[24000];
    for (int i = 0; i < 4000; i++) {
        int b = i * 4;
        indices[i*6+0] = b+0; indices[i*6+1] = b+1; indices[i*6+2] = b+2;
        indices[i*6+3] = b+0; indices[i*6+4] = b+2; indices[i*6+5] = b+3;
    }
    D3D11_BUFFER_DESC ibd = {};
    ibd.BindFlags = D3D11_BIND_INDEX_BUFFER;
    ibd.ByteWidth = sizeof(indices);
    ibd.Usage = D3D11_USAGE_IMMUTABLE;
    D3D11_SUBRESOURCE_DATA isrd = {indices, 0, 0};
    g_dev->CreateBuffer(&ibd, &isrd, &g_ibuf);
    g_ctx->IASetIndexBuffer(g_ibuf.Get(), DXGI_FORMAT_R16_UINT, 0);

    g_ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    UINT stride = sizeof(Vertex), offset = 0;
    g_ctx->IASetVertexBuffers(0, 1, g_vbuf.GetAddressOf(), &stride, &offset);

    Py_RETURN_NONE;
}

static PyObject *d3d_begin(PyObject *self, PyObject *args)
{
    float r, g, b, a;
    if (!PyArg_ParseTuple(args, "ffff", &r, &g, &b, &a)) return NULL;
    float clr[4] = {r, g, b, a};
    g_ctx->OMSetRenderTargets(1, g_rtv.GetAddressOf(), NULL);
    g_ctx->ClearRenderTargetView(g_rtv.Get(), clr);
    D3D11_VIEWPORT vp;
    vp.TopLeftX = 0; vp.TopLeftY = 0;
    vp.Width = (float)g_width; vp.Height = (float)g_height;
    vp.MinDepth = 0; vp.MaxDepth = 1;
    g_ctx->RSSetViewports(1, &vp);
    g_ctx->IASetInputLayout(g_layout.Get());
    g_ctx->VSSetShader(g_vs.Get(), NULL, 0);
    g_ctx->PSSetShader(g_ps.Get(), NULL, 0);
    UINT stride = sizeof(Vertex), offset = 0;
    g_ctx->IASetVertexBuffers(0, 1, g_vbuf.GetAddressOf(), &stride, &offset);
    g_ctx->IASetIndexBuffer(g_ibuf.Get(), DXGI_FORMAT_R16_UINT, 0);
    g_ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    Py_RETURN_NONE;
}

static PyObject *d3d_end(PyObject *self, PyObject *args)
{
    g_swap->Present(0, 0);  // vsync off
    Py_RETURN_NONE;
}

// ---- GDI overlay: get/release a GDI DC on the DXGI back buffer ----
// Lets text / ovals / lines (GDI) be drawn on top of GPU content before Present.
static ComPtr<IDXGISurface1> g_dxgi_surf;

static PyObject *d3d_get_dc(PyObject *self, PyObject *args)
{
    if (!g_dxgi_surf) {
        ComPtr<ID3D11Texture2D> back;
        g_swap->GetBuffer(0, IID_PPV_ARGS(&back));
        if (!back) { PyErr_SetString(PyExc_RuntimeError, "GetBuffer failed"); return NULL; }
        if (FAILED(back.As(&g_dxgi_surf))) {
            PyErr_SetString(PyExc_RuntimeError, "back buffer is not IDXGISurface1");
            return NULL;
        }
    }
    // Make sure GPU work is done before GDI reads/writes the surface
    g_ctx->Flush();
    HDC hdc = NULL;
    HRESULT hr = g_dxgi_surf->GetDC(FALSE, &hdc);  // FALSE: keep GPU content
    if (FAILED(hr)) {
        PyErr_SetString(PyExc_RuntimeError, "IDXGISurface1::GetDC failed");
        return NULL;
    }
    return PyLong_FromVoidPtr(hdc);
}

static PyObject *d3d_release_dc(PyObject *self, PyObject *args)
{
    if (g_dxgi_surf) {
        g_dxgi_surf->ReleaseDC(NULL);
    }
    Py_RETURN_NONE;
}

// Persistent sprites: created once, rendered every frame from C.
typedef struct { float x, y, w, h, r, g, b, a; int visible; } PSprite;static PSprite *g_psprites = NULL;
static int g_psprite_count = 0;
static int g_psprite_cap = 0;
static int s_need_update = 1;
static int s_last_count = 0;
static int s_drawn_count = 0;

static PyObject *d3d_register_sprite(PyObject *self, PyObject *args)
{
    float x,y,w,h,r,g,b,a;
    if (!PyArg_ParseTuple(args, "ffffffff", &x,&y,&w,&h,&r,&g,&b,&a)) return NULL;
    if (g_psprite_count >= g_psprite_cap) {
        g_psprite_cap = (g_psprite_cap + 1024) * 2;
        g_psprites = (PSprite *)realloc(g_psprites, g_psprite_cap * sizeof(PSprite));
    }
    int idx = g_psprite_count;
    g_psprites[idx] = {x,y,w,h,r,g,b,a,1};
    g_psprite_count++;
    return PyLong_FromLong(idx);
}

static PyObject *d3d_set_sprite_pos(PyObject *self, PyObject *args)
{
    long idx; float x, y;
    if (!PyArg_ParseTuple(args, "lff", &idx, &x, &y)) return NULL;
    if (idx >= 0 && idx < g_psprite_count) {
        g_psprites[idx].x = x; g_psprites[idx].y = y;
        s_need_update = 1;
    }
    Py_RETURN_NONE;
}

static PyObject *d3d_render_psprites(PyObject *self, PyObject *args)
{
    if (g_psprite_count == 0) Py_RETURN_NONE;
    // Only rebuild the vertex buffer when positions/count actually changed.
    // Static scenes skip the Map/Unmap entirely and just re-issue DrawIndexed.
    if (s_need_update || g_psprite_count != s_last_count) {
        D3D11_MAPPED_SUBRESOURCE ms;
        if (FAILED(g_ctx->Map(g_vbuf.Get(), 0, D3D11_MAP_WRITE_DISCARD, 0, &ms))) {
            PyErr_SetString(PyExc_RuntimeError, "Map failed");
            return NULL;
        }
        Vertex *verts = (Vertex *)ms.pData;
        int n = 0;
        for (int i = 0; i < g_psprite_count; i++) {
            if (!g_psprites[i].visible) continue;
            PSprite *s = &g_psprites[i];
            int v = n * 4;
            verts[v+0] = {s->x,     s->y,     s->r, s->g, s->b, s->a};
            verts[v+1] = {s->x+s->w, s->y,     s->r, s->g, s->b, s->a};
            verts[v+2] = {s->x+s->w, s->y+s->h, s->r, s->g, s->b, s->a};
            verts[v+3] = {s->x,     s->y+s->h, s->r, s->g, s->b, s->a};
            n++;
        }
        s_drawn_count = n;
        g_ctx->Unmap(g_vbuf.Get(), 0);
        s_need_update = 0;
        s_last_count = g_psprite_count;
    }
    g_ctx->DrawIndexed((UINT)(s_drawn_count * 6), 0, 0);
    Py_RETURN_NONE;
}

// Batch rects: pass flat float buffer [x,y,w,h,r,g,b,a] * N
static PyObject *d3d_draw_rects(PyObject *self, PyObject *args)
{
    PyObject *buf_obj;
    if (!PyArg_ParseTuple(args, "O", &buf_obj)) return NULL;
    Py_buffer view;
    if (PyObject_GetBuffer(buf_obj, &view, PyBUF_CONTIG_RO) < 0) return NULL;
    Py_ssize_t n = view.len / (sizeof(float) * 8);
    const float *data = (const float *)view.buf;

    D3D11_MAPPED_SUBRESOURCE ms;
    g_ctx->Map(g_vbuf.Get(), 0, D3D11_MAP_WRITE_DISCARD, 0, &ms);
    Vertex *verts = (Vertex *)ms.pData;
    for (Py_ssize_t i = 0; i < n; i++) {
        float x = data[i*8+0], y = data[i*8+1];
        float w = data[i*8+2], h = data[i*8+3];
        float r = data[i*8+4], g = data[i*8+5], b = data[i*8+6], a = data[i*8+7];
        int v = i * 4;
        verts[v+0] = {x,     y,     r, g, b, a};
        verts[v+1] = {x + w, y,     r, g, b, a};
        verts[v+2] = {x + w, y + h, r, g, b, a};
        verts[v+3] = {x,     y + h, r, g, b, a};
    }
    g_ctx->Unmap(g_vbuf.Get(), 0);
    g_ctx->DrawIndexed((UINT)(n * 6), 0, 0);
    PyBuffer_Release(&view);
    Py_RETURN_NONE;
}

static PyObject *d3d_resize(PyObject *self, PyObject *args)
{
    UINT w, h;
    if (!PyArg_ParseTuple(args, "II", &w, &h)) return NULL;
    g_width = w; g_height = h;
    g_rtv = nullptr;
    g_dxgi_surf = nullptr;  // back buffer replaced on resize
    g_swap->ResizeBuffers(0, w, h, DXGI_FORMAT_UNKNOWN, 0);
    ComPtr<ID3D11Texture2D> back;
    g_swap->GetBuffer(0, IID_PPV_ARGS(&back));
    g_dev->CreateRenderTargetView(back.Get(), NULL, g_rtv.GetAddressOf());
    g_ctx->OMSetRenderTargets(1, g_rtv.GetAddressOf(), NULL);
    // Update screen constant buffer
    D3D11_MAPPED_SUBRESOURCE ms;
    g_ctx->Map(g_vscb.Get(), 0, D3D11_MAP_WRITE_DISCARD, 0, &ms);
    float *p = (float *)ms.pData;
    p[0] = (float)w; p[1] = (float)h;
    g_ctx->Unmap(g_vscb.Get(), 0);
    Py_RETURN_NONE;
}

static PyObject *d3d_shutdown(PyObject *self, PyObject *args)
{
    // Wait for GPU to finish before releasing resources
    if (g_ctx) {
        g_ctx->Flush();
    }
    free(g_psprites);
    g_psprites = NULL;
    g_psprite_count = 0;
    g_psprite_cap = 0;
    g_dxgi_surf = nullptr;
    g_vbuf = nullptr; g_ibuf = nullptr; g_vscb = nullptr;
    g_layout = nullptr; g_vs = nullptr; g_ps = nullptr;
    g_rtv = nullptr; g_swap = nullptr; g_ctx = nullptr; g_dev = nullptr;
    Py_RETURN_NONE;
}

static PyMethodDef d3d_methods[] = {
    {"init", d3d_init, METH_VARARGS, "init(hwnd)"},
    {"begin", d3d_begin, METH_VARARGS, "begin(r,g,b,a)"},
    {"end", d3d_end, METH_VARARGS, "end()"},
    {"get_dc", d3d_get_dc, METH_VARARGS, "get_dc() -> hdc for GDI overlay"},
    {"release_dc", d3d_release_dc, METH_VARARGS, "release_dc()"},
    {"draw_rects", d3d_draw_rects, METH_VARARGS, "draw_rects(buffer)"},
    {"resize", d3d_resize, METH_VARARGS, "resize(w,h)"},
    {"shutdown", d3d_shutdown, METH_VARARGS, "shutdown()"},
    {"register_sprite", d3d_register_sprite, METH_VARARGS, "register_sprite(x,y,w,h,r,g,b,a)"},
    {"set_sprite_pos", d3d_set_sprite_pos, METH_VARARGS, "set_sprite_pos(idx,x,y)"},
    {"render_psprites", d3d_render_psprites, METH_VARARGS, "render_psprites()"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef d3d_module = {
    PyModuleDef_HEAD_INIT, "_d3d11", NULL, 0, d3d_methods
};

PyMODINIT_FUNC PyInit__d3d11(void)
{
    return PyModule_Create(&d3d_module);
}
